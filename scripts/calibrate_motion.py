#!/usr/bin/env python3
"""Interactive calibration for tool-up motion compensation.

Drives a known move pattern with the motor piston LIFTED, collects measured
positions through a MeasurementProvider, fits compensation parameters, prints
recommendations, and offers to write them to config/settings.json.

Usage:
    python3 scripts/calibrate_motion.py --axis x
    python3 scripts/calibrate_motion.py --axis y
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.motion_calibration import fit_scale_offset, fit_backlash
from core.measurement_provider import ManualMeasurementProvider
from hardware.interfaces.hardware_factory import get_hardware_interface

SETTINGS_PATH = "config/settings.json"

# Forward pass mixes long/short distances; reverse pass shares the 30 cm point
# so backlash can be computed at a common target.
FORWARD_TARGETS = [10.0, 30.0, 50.0]
REVERSE_TARGET = 30.0
COMMON_TARGET = 30.0


def _lift(hw, axis):
    if axis == "x":
        hw.row_motor_piston_up()
    else:
        hw.line_motor_piston_up()


def _lower(hw, axis):
    if axis == "x":
        hw.row_motor_piston_down()
    else:
        hw.line_motor_piston_down()


def _move(hw, axis, pos):
    if axis == "x":
        return hw.move_x(pos)
    return hw.move_y(pos)


def run(axis):
    provider = ManualMeasurementProvider()
    hw = get_hardware_interface()

    print(f"\n=== Calibrating axis {axis.upper()} (tool UP) ===")
    print("Make sure the machine is homed and the work area is clear.")
    input("Press Enter to lift the motor piston and begin...")

    _lift(hw, axis)

    # Forward pass (ascending) — fit scale + offset.
    commanded, measured = [], []
    for t in FORWARD_TARGETS:
        _move(hw, axis, t)
        m = provider.measure(axis=axis, commanded_cm=t)
        commanded.append(t)
        measured.append(m)
    forward_at_common = measured[FORWARD_TARGETS.index(COMMON_TARGET)]

    # Reverse pass — approach COMMON_TARGET from above to expose backlash.
    _move(hw, axis, max(FORWARD_TARGETS) + 10.0)
    _move(hw, axis, REVERSE_TARGET)
    reverse_at_common = provider.measure(axis=axis, commanded_cm=REVERSE_TARGET)

    _lower(hw, axis)

    scale, offset = fit_scale_offset(commanded, measured)
    backlash = fit_backlash(forward_at_common, reverse_at_common)

    print("\n--- Recommended motion_compensation values ---")
    print(f"  enabled:            true")
    print(f"  scale:              {scale:.5f}")
    print(f"  offset_cm:          {offset:+.3f}")
    print(f"  backlash_cm:        {backlash:.3f}")
    print(f"  approach_direction: 1   (forward/ascending pass)")
    if abs(scale - 1.0) < 1e-4 and abs(offset) < 0.02 and backlash < 0.02:
        print("\n  Residual is tiny — error may be non-repeatable (lost steps).")
        print("  Consider slower tool-up feed/accel instead of static compensation.")

    if input("\nWrite these into config/settings.json? [y/N] ").strip().lower() == "y":
        with open(SETTINGS_PATH) as f:
            settings = json.load(f)
        mc = settings["hardware_config"]["arduino_grbl"].setdefault("motion_compensation", {})
        mc[axis] = {
            "enabled": True,
            "offset_cm": round(offset, 3),
            "scale": round(scale, 5),
            "backlash_cm": round(backlash, 3),
            "approach_direction": 1,
        }
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        print(f"  Wrote motion_compensation.{axis} to {SETTINGS_PATH}")
    else:
        print("  Not written. Copy the values manually if you want them.")


def main():
    ap = argparse.ArgumentParser(description="Calibrate tool-up motion compensation")
    ap.add_argument("--axis", choices=["x", "y"], required=True)
    run(ap.parse_args().axis)


if __name__ == "__main__":
    main()

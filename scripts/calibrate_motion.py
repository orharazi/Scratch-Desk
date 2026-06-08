#!/usr/bin/env python3
"""Interactive calibration for tool-up motion compensation.

Drives a known move pattern the same way production does — each move runs with
the motor piston LIFTED, then the piston is LOWERED at the destination before
the measurement is taken. This makes the calibration reflect the real resting
position the mark lands on (including any shift caused by lowering), not the
tool-up position. Measurements are collected through a MeasurementProvider, the
script fits compensation parameters, prints recommendations, and offers to write
them to config/settings.json.

Per-stop sequence (mirrors execution_engine long moves):
    lift -> move (tool up) -> lower -> measure -> lift (for next move)

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


def _print_homing_progress(step_number, step_name, status, message=None):
    """Console progress callback for the homing sequence."""
    line = f"  [home] step {step_number}: {step_name} — {status}"
    if message:
        line += f" ({message})"
    print(line)


def run(axis):
    provider = ManualMeasurementProvider()
    hw = get_hardware_interface()

    print(f"\n=== Calibrating axis {axis.upper()} (tool UP move, measured DOWN) ===")
    print("This runs the FULL homing sequence (it moves the machine and cycles")
    print("the pistons), then drives a calibration pattern. Clear the work area.")
    print("At each stop the piston lowers before you measure (matches marking).")
    input("Press Enter to home and begin...")

    # Open the air pressure valve before any piston motion. The main app does
    # this on startup (index.py); without it the pistons have no air supply and
    # the homing sequence's line-motor lift does nothing. Keep it open for the
    # whole calibration (every stop cycles the motor piston) and close it on exit.
    print("\nOpening air pressure valve...")
    hw.air_pressure_valve_down()

    try:
        _run_calibration(hw, axis, provider)
    finally:
        print("\nClosing air pressure valve...")
        hw.air_pressure_valve_up()


def _run_calibration(hw, axis, provider):
    # Run the SAME comprehensive homing sequence the main software uses:
    # applies GRBL config, checks/lifts pistons, runs $H, resets work coords
    # to (0,0), and lowers the line-motor pistons back down. With air pressure
    # now on, step 4 actually lifts the line motor and step 8 lowers it again.
    print("\nRunning complete homing sequence (pistons + $H)...")
    homed, home_msg = hw.perform_complete_homing_sequence(
        progress_callback=_print_homing_progress
    )
    if not homed:
        print(f"\nERROR: homing failed: {home_msg}")
        print("  Aborting calibration — fix homing before continuing.")
        return
    print("✓ Homing complete.\n")

    # Forward pass (ascending) — fit scale + offset.
    # Each stop mirrors production: move with tool up, lower, measure, lift.
    commanded, measured = [], []
    for t in FORWARD_TARGETS:
        _lift(hw, axis)                 # tool up for the move
        _move(hw, axis, t)              # long move (tool up) — the inaccurate part
        _lower(hw, axis)               # lower at destination, as when marking
        m = provider.measure(axis=axis, commanded_cm=t)  # measure resting position
        commanded.append(t)
        measured.append(m)
    forward_at_common = measured[FORWARD_TARGETS.index(COMMON_TARGET)]

    # Reverse pass — approach COMMON_TARGET from above to expose backlash,
    # then lower and measure (same as the forward stops).
    _lift(hw, axis)
    _move(hw, axis, max(FORWARD_TARGETS) + 10.0)
    _move(hw, axis, REVERSE_TARGET)
    _lower(hw, axis)
    reverse_at_common = provider.measure(axis=axis, commanded_cm=REVERSE_TARGET)

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

    # Sanity check for unusually large values
    if abs(scale - 1.0) > 0.05 or abs(offset) > 0.5 or backlash > 1.0:
        print("\n  ⚠️  WARNING: Fitted values look unusually large!")
        print("      scale offset/deviation > 0.05  or  offset > 0.5cm  or  backlash > 1.0cm")
        print("      This may indicate a measurement error or deeper mechanical problem.")
        print("      Please double-check your measurements before applying these values.")

    if input("\nWrite these into config/settings.json? [y/N] ").strip().lower() == "y":
        try:
            with open(SETTINGS_PATH) as f:
                settings = json.load(f)
        except Exception as e:
            print(f"ERROR: could not read {SETTINGS_PATH}: {e}")
            print("  Not written. Check the file and try again.")
            return

        try:
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
            print(f"✓ Wrote motion_compensation.{axis} to {SETTINGS_PATH}")
        except Exception as e:
            print(f"ERROR: could not write {SETTINGS_PATH}: {e}")
            print("  Changes were not saved. Check file permissions and try again.")
    else:
        print("  Not written. Copy the values manually if you want them.")


def main():
    ap = argparse.ArgumentParser(description="Calibrate tool-up motion compensation")
    ap.add_argument("--axis", choices=["x", "y"], required=True)
    run(ap.parse_args().axis)


if __name__ == "__main__":
    main()

# Tool-Up Motion Compensation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make tool-up (lifted) positioning moves accurate for both X (rows) and Y (lines) via a per-axis feed-forward compensation layer, plus an on-machine calibration routine to derive the correction values — without touching the already-accurate tool-down marking moves.

**Architecture:** A pure `MotionCompensator` (offset + scale + backlash terms, per axis) computes corrected waypoints for a target. The execution engine invokes it only when `_should_lift_motor_for_move` is True (the tool-up case). A pure `motion_calibration` module fits the parameters from measured-vs-commanded positions. A `scripts/calibrate_motion.py` runner drives a known pattern, collects measurements through a pluggable `MeasurementProvider`, fits parameters, and offers to write them to `settings.json`. All tunables live in `config/settings.json`.

**Tech Stack:** Python 3.7+, pytest, existing GRBL/mock hardware abstraction.

---

## File Structure

- Create `core/motion_compensation.py` — `MotionCompensator`, pure waypoint logic.
- Create `core/motion_calibration.py` — `fit_scale_offset`, `fit_backlash`, pure fitting.
- Create `core/measurement_provider.py` — `MeasurementProvider` ABC + `ManualMeasurementProvider` + `SensorMeasurementProvider` stub.
- Create `scripts/calibrate_motion.py` — interactive calibration runner.
- Modify `config/settings.json` — add `hardware_config.arduino_grbl.motion_compensation`.
- Modify `core/execution_engine.py` — call compensator in `move_x` / `move_y` / combined-move handlers; extend run-log.
- Create `tests/test_motion_compensation.py`, `tests/test_motion_calibration.py`, `tests/test_execution_compensation_hook.py`.

---

## Task 1: Settings block for compensation

**Files:**
- Modify: `config/settings.json` (under `hardware_config.arduino_grbl`)

- [ ] **Step 1: Add the `motion_compensation` block**

In `config/settings.json`, inside `hardware_config.arduino_grbl` (a sibling of `grbl_settings` / `grbl_configuration`), add:

```json
"motion_compensation": {
  "x": { "enabled": false, "offset_cm": 0.0, "scale": 1.0, "backlash_cm": 0.0, "approach_direction": 1 },
  "y": { "enabled": false, "offset_cm": 0.0, "scale": 1.0, "backlash_cm": 0.0, "approach_direction": 1 }
}
```

Defaults are a no-op so machine behavior is unchanged until enabled.

- [ ] **Step 2: Validate JSON**

Run: `python3 -m json.tool config/settings.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Auto-fill admin descriptions**

Run: `python3 scripts/verify_config_alignment.py --fix`
Expected: completes without error; missing descriptions for the new keys are added to `config/config_descriptions.json`.

- [ ] **Step 4: Commit**

```bash
git add config/settings.json config/config_descriptions.json
git commit -m "feat: add motion_compensation settings block (no-op defaults)"
```

---

## Task 2: `MotionCompensator` pure module

**Files:**
- Create: `core/motion_compensation.py`
- Test: `tests/test_motion_compensation.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_motion_compensation.py`:

```python
import os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.motion_compensation import MotionCompensator


def test_disabled_axis_is_noop():
    c = MotionCompensator({"x": {"enabled": False, "offset_cm": 5.0}})
    assert c.compensate("x", 0.0, 10.0) == [10.0]


def test_missing_axis_is_noop():
    c = MotionCompensator({})
    assert c.compensate("x", 0.0, 10.0) == [10.0]


def test_offset_only():
    c = MotionCompensator({"x": {"enabled": True, "offset_cm": 0.2}})
    assert c.compensate("x", 0.0, 10.0) == pytest.approx([10.2])


def test_scale_only():
    c = MotionCompensator({"x": {"enabled": True, "scale": 1.01}})
    assert c.compensate("x", 0.0, 100.0) == pytest.approx([101.0])


def test_scale_and_offset():
    c = MotionCompensator({"x": {"enabled": True, "scale": 1.01, "offset_cm": 0.2}})
    assert c.compensate("x", 0.0, 100.0) == pytest.approx([101.2])


def test_backlash_no_overshoot_when_travel_matches_approach():
    # approach +1, moving 0 -> 10 is +1: no overshoot needed
    c = MotionCompensator({"x": {"enabled": True, "backlash_cm": 0.3, "approach_direction": 1}})
    assert c.compensate("x", 0.0, 10.0) == pytest.approx([10.0])


def test_backlash_overshoot_when_travel_opposes_approach():
    # approach +1, moving 20 -> 10 is -1: overshoot below target then settle up
    c = MotionCompensator({"x": {"enabled": True, "backlash_cm": 0.3, "approach_direction": 1}})
    assert c.compensate("x", 20.0, 10.0) == pytest.approx([9.7, 10.0])


def test_backlash_negative_approach_direction():
    # approach -1, moving 0 -> 10 is +1: overshoot above target then settle down
    c = MotionCompensator({"x": {"enabled": True, "backlash_cm": 0.3, "approach_direction": -1}})
    assert c.compensate("x", 0.0, 10.0) == pytest.approx([10.3, 10.0])


def test_backlash_combines_with_offset():
    # corrected = 10 + 0.2 = 10.2; travel 20->10 is -1 opposes +1 -> overshoot 9.9 then 10.2
    c = MotionCompensator({"x": {"enabled": True, "offset_cm": 0.2,
                                 "backlash_cm": 0.3, "approach_direction": 1}})
    assert c.compensate("x", 20.0, 10.0) == pytest.approx([9.9, 10.2])


def test_y_axis_independent_of_x():
    c = MotionCompensator({"x": {"enabled": True, "offset_cm": 0.2},
                           "y": {"enabled": False}})
    assert c.compensate("y", 0.0, 10.0) == [10.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_motion_compensation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.motion_compensation'`.

- [ ] **Step 3: Implement `core/motion_compensation.py`**

```python
"""Feed-forward motion compensation for tool-up (lifted) positioning moves.

Pure logic, no hardware dependencies. Applies a per-axis correction made of
three independently-toggleable terms — fixed offset, distance scale, and
backlash overshoot — to the target of a lifted move. Tool-down marking moves
must never be passed through this module; the execution engine invokes it only
when the motor piston is lifted for a long move.

See docs/superpowers/specs/2026-06-07-tool-up-motion-compensation-design.md
"""

from typing import List


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


class MotionCompensator:
    """Computes corrected waypoints for tool-up positioning moves."""

    def __init__(self, config: dict):
        # config is the `motion_compensation` block: {"x": {...}, "y": {...}}
        self._config = config or {}

    def _axis_cfg(self, axis: str) -> dict:
        return self._config.get(axis, {}) or {}

    def compensate(self, axis: str, current_pos_cm: float, target_cm: float) -> List[float]:
        """Return ordered absolute waypoints (cm) to drive `axis` to `target_cm`.

        axis: 'x' or 'y'
        current_pos_cm: start position, used to decide backlash direction
        target_cm: commanded absolute target

        Returns [target_cm] unchanged when the axis is disabled.
        """
        cfg = self._axis_cfg(axis)
        if not cfg.get("enabled", False):
            return [target_cm]

        scale = cfg.get("scale", 1.0)
        offset_cm = cfg.get("offset_cm", 0.0)
        corrected = scale * target_cm + offset_cm

        backlash_cm = cfg.get("backlash_cm", 0.0)
        if backlash_cm and backlash_cm > 0:
            approach_dir = _sign(cfg.get("approach_direction", 1)) or 1
            travel_dir = _sign(target_cm - current_pos_cm)
            # Overshoot only when natural travel opposes the preferred approach.
            if travel_dir != 0 and travel_dir != approach_dir:
                overshoot = corrected - approach_dir * backlash_cm
                return [overshoot, corrected]

        return [corrected]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_motion_compensation.py -v`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add core/motion_compensation.py tests/test_motion_compensation.py
git commit -m "feat: add MotionCompensator pure waypoint logic"
```

---

## Task 3: Calibration fitting (pure)

**Files:**
- Create: `core/motion_calibration.py`
- Test: `tests/test_motion_calibration.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_motion_calibration.py`:

```python
import os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.motion_calibration import fit_scale_offset, fit_backlash


def test_fit_recovers_offset_only():
    # machine lands 0.2 short: measured = commanded - 0.2
    commanded = [10.0, 30.0, 50.0]
    measured = [9.8, 29.8, 49.8]
    scale, offset = fit_scale_offset(commanded, measured)
    assert scale == pytest.approx(1.0)
    assert offset == pytest.approx(0.2)


def test_fit_recovers_scale():
    # measured = 0.99 * commanded -> correction scale = 1/0.99, offset ~ 0
    commanded = [10.0, 50.0, 100.0]
    measured = [9.9, 49.5, 99.0]
    scale, offset = fit_scale_offset(commanded, measured)
    assert scale == pytest.approx(1.0 / 0.99)
    assert offset == pytest.approx(0.0, abs=1e-9)


def test_fit_requires_two_points():
    with pytest.raises(ValueError):
        fit_scale_offset([10.0], [9.8])


def test_fit_rejects_identical_commands():
    with pytest.raises(ValueError):
        fit_scale_offset([10.0, 10.0], [9.8, 9.9])


def test_backlash_gap():
    assert fit_backlash(10.0, 9.7) == pytest.approx(0.3)
    assert fit_backlash(9.7, 10.0) == pytest.approx(0.3)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_motion_calibration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.motion_calibration'`.

- [ ] **Step 3: Implement `core/motion_calibration.py`**

```python
"""Fit motion-compensation parameters from measured-vs-commanded positions.

Pure logic, no hardware dependencies.

Model: the machine's transfer is  measured = a * commanded + b  (least squares).
To land on a desired target T we must command  C = (T - b) / a, i.e. the
compensator stores  scale = 1/a  and  offset = -b/a  so that
corrected = scale * T + offset.
"""

from typing import List, Tuple


def fit_scale_offset(commanded: List[float], measured: List[float]) -> Tuple[float, float]:
    """Return (scale, offset) for the compensator from a forward-pass dataset."""
    n = len(commanded)
    if n < 2 or n != len(measured):
        raise ValueError("need >= 2 matched commanded/measured points")

    mean_c = sum(commanded) / n
    mean_m = sum(measured) / n
    sxx = sum((c - mean_c) ** 2 for c in commanded)
    if sxx == 0:
        raise ValueError("commanded positions are all identical")
    sxy = sum((c - mean_c) * (m - mean_m) for c, m in zip(commanded, measured))

    a = sxy / sxx                 # slope of measured vs commanded
    b = mean_m - a * mean_c       # intercept
    if a == 0:
        raise ValueError("degenerate fit (zero slope)")

    scale = 1.0 / a
    offset = -b / a
    return scale, offset


def fit_backlash(forward_measured: float, reverse_measured: float) -> float:
    """Backlash magnitude = gap between forward/reverse landings at one target."""
    return abs(forward_measured - reverse_measured)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_motion_calibration.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add core/motion_calibration.py tests/test_motion_calibration.py
git commit -m "feat: add motion calibration parameter fitting"
```

---

## Task 4: Wire compensator into the execution engine

**Files:**
- Modify: `core/execution_engine.py` (import; new helper; `move_x` ~915-972, `move_y` ~974-1030, combined-move ~1039-1060)
- Test: `tests/test_execution_compensation_hook.py`

- [ ] **Step 1: Write the failing test for the helper seam**

Create `tests/test_execution_compensation_hook.py`:

```python
import os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.execution_engine as ee
from core.execution_engine import ExecutionEngine


class FakeHW:
    def __init__(self):
        self.x = 20.0
        self.y = 0.0
    def get_current_x(self):
        return self.x
    def get_current_y(self):
        return self.y


def test_compensated_waypoints_disabled_returns_target(monkeypatch):
    monkeypatch.setattr(ee, "load_settings", lambda: {})
    engine = ExecutionEngine()
    engine.hardware = FakeHW()
    assert engine._compensated_waypoints("x", 10.0) == [10.0]


def test_compensated_waypoints_applies_offset_and_backlash(monkeypatch):
    cfg = {"hardware_config": {"arduino_grbl": {"motion_compensation": {
        "x": {"enabled": True, "offset_cm": 0.2, "backlash_cm": 0.3, "approach_direction": 1},
        "y": {"enabled": False},
    }}}}
    monkeypatch.setattr(ee, "load_settings", lambda: cfg)
    engine = ExecutionEngine()
    engine.hardware = FakeHW()           # current x = 20 -> moving to 10 is -1 (opposes +1)
    # corrected = 10 + 0.2 = 10.2 ; overshoot = 10.2 - 0.3 = 9.9
    assert engine._compensated_waypoints("x", 10.0) == pytest.approx([9.9, 10.2])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_execution_compensation_hook.py -v`
Expected: FAIL — `AttributeError: 'ExecutionEngine' object has no attribute '_compensated_waypoints'`.

- [ ] **Step 3: Add the import**

In `core/execution_engine.py`, near the other `from core...` imports at the top, add:

```python
from core.motion_compensation import MotionCompensator
```

- [ ] **Step 4: Add the helper method**

In `core/execution_engine.py`, add this method to `ExecutionEngine` (place it directly after `_should_lift_motor_for_move`, around line 1268):

```python
    def _compensated_waypoints(self, axis, target):
        """Return ordered waypoints (cm) for a tool-up move, applying compensation.

        Reads live settings each call (same pattern as _should_lift_motor_for_move).
        Falls back to [target] if anything is unavailable.
        """
        try:
            cfg = (load_settings()
                   .get('hardware_config', {})
                   .get('arduino_grbl', {})
                   .get('motion_compensation', {}))
            comp = MotionCompensator(cfg)
            if axis == 'x':
                current = self.hardware.get_current_x()
            else:
                current = self.hardware.get_current_y()
            return comp.compensate(axis, current, target)
        except Exception as e:
            self.logger.warning(f"Compensation failed, using raw target: {e}", category="execution")
            return [target]
```

- [ ] **Step 5: Run the helper test to verify it passes**

Run: `python3 -m pytest tests/test_execution_compensation_hook.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Use the helper in `move_x`**

In `core/execution_engine.py`, replace the single `move_x` call block (currently around lines 924-937):

```python
                # Check if motor piston should be lifted for long move
                should_lift, move_dist = self._should_lift_motor_for_move('x', target_x)
                if should_lift:
                    self.logger.info(f"Long X move ({move_dist:.1f}cm) - lifting row motor piston", category="execution")
                    self.hardware.row_motor_piston_up()
                    self._engine_lowered_tools.discard('row_motor_piston')

                # Execute movement and wait for completion
                move_result = self.hardware.move_x(target_x)

                # Lower motor piston back if we lifted it
                if should_lift:
                    self.logger.info(f"X move complete - lowering row motor piston", category="execution")
                    self.hardware.row_motor_piston_down()
                    self._engine_lowered_tools.add('row_motor_piston')
```

with:

```python
                # Check if motor piston should be lifted for long move
                should_lift, move_dist = self._should_lift_motor_for_move('x', target_x)
                if should_lift:
                    self.logger.info(f"Long X move ({move_dist:.1f}cm) - lifting row motor piston", category="execution")
                    self.hardware.row_motor_piston_up()
                    self._engine_lowered_tools.discard('row_motor_piston')
                    waypoints = self._compensated_waypoints('x', target_x)
                else:
                    waypoints = [target_x]

                # Execute movement(s) and wait for completion. Last waypoint is the
                # real target; any earlier ones are anti-backlash overshoots.
                move_result = True
                for idx, wp in enumerate(waypoints):
                    is_overshoot = idx < len(waypoints) - 1
                    move_result = self.hardware.move_x(wp)
                    _cur_y_wp = getattr(self.hardware.grbl, 'current_y', 0.0) if hasattr(self.hardware, 'grbl') and self.hardware.grbl else 0.0
                    self._log_grbl_move('G1', wp, _cur_y_wp, _feed, None, description, is_overshoot=is_overshoot, axis='x')
                    if not move_result:
                        break

                # Lower motor piston back if we lifted it
                if should_lift:
                    self.logger.info(f"X move complete - lowering row motor piston", category="execution")
                    self.hardware.row_motor_piston_down()
                    self._engine_lowered_tools.add('row_motor_piston')
```

Note: the existing post-move run-log line at ~970 (`self._log_grbl_move('G1', target_x, _cur_y, _feed, actual_x_cm, description, axis='x')`) stays — it records the final commanded target with the measured GRBL position. The new per-waypoint logging records the overshoot path.

- [ ] **Step 7: Use the helper in `move_y`**

In `core/execution_engine.py`, replace the `move_y` call block (currently around lines 978-991):

```python
                # Check if motor piston should be lifted for long move
                should_lift, move_dist = self._should_lift_motor_for_move('y', target_y)
                if should_lift:
                    self.logger.info(f"Long Y move ({move_dist:.1f}cm) - lifting line motor piston", category="execution")
                    self.hardware.line_motor_piston_up()
                    self._engine_lowered_tools.discard('line_motor_piston')

                # Execute movement and wait for completion
                move_result = self.hardware.move_y(target_y)

                # Lower motor piston back if we lifted it
                if should_lift:
                    self.logger.info(f"Y move complete - lowering line motor piston", category="execution")
                    self.hardware.line_motor_piston_down()
                    self._engine_lowered_tools.add('line_motor_piston')
```

with:

```python
                # Check if motor piston should be lifted for long move
                should_lift, move_dist = self._should_lift_motor_for_move('y', target_y)
                if should_lift:
                    self.logger.info(f"Long Y move ({move_dist:.1f}cm) - lifting line motor piston", category="execution")
                    self.hardware.line_motor_piston_up()
                    self._engine_lowered_tools.discard('line_motor_piston')
                    waypoints = self._compensated_waypoints('y', target_y)
                else:
                    waypoints = [target_y]

                # Execute movement(s); last waypoint is the real target.
                move_result = True
                for idx, wp in enumerate(waypoints):
                    is_overshoot = idx < len(waypoints) - 1
                    move_result = self.hardware.move_y(wp)
                    _cur_x_wp = getattr(self.hardware.grbl, 'current_x', 0.0) if hasattr(self.hardware, 'grbl') and self.hardware.grbl else 0.0
                    self._log_grbl_move('G1', _cur_x_wp, wp, 1000, None, description, is_overshoot=is_overshoot, axis='y')
                    if not move_result:
                        break

                # Lower motor piston back if we lifted it
                if should_lift:
                    self.logger.info(f"Y move complete - lowering line motor piston", category="execution")
                    self.hardware.line_motor_piston_down()
                    self._engine_lowered_tools.add('line_motor_piston')
```

- [ ] **Step 8: Apply compensation in the combined-move handler**

In `core/execution_engine.py`, the combined handler (around lines 1039-1060) computes `should_lift_x`/`should_lift_y` then calls `self.hardware.move_x(target_x)` and `self.hardware.move_y(target_y)`. Replace those two calls so each lifted axis uses its compensated final waypoint:

Replace:

```python
                move_x_result = self.hardware.move_x(target_x)
                if not move_x_result:
                    self.logger.error(f"move_x to {target_x} failed or did not complete", category="execution")
```

with:

```python
                x_waypoints = self._compensated_waypoints('x', target_x) if should_lift_x else [target_x]
                move_x_result = True
                for wp in x_waypoints:
                    move_x_result = self.hardware.move_x(wp)
                    if not move_x_result:
                        break
                if not move_x_result:
                    self.logger.error(f"move_x to {target_x} failed or did not complete", category="execution")
```

Replace:

```python
                move_y_result = self.hardware.move_y(target_y)
                if not move_y_result:
                    self.logger.error(f"move_y to {target_y} failed or did not complete", category="execution")
```

with:

```python
                y_waypoints = self._compensated_waypoints('y', target_y) if should_lift_y else [target_y]
                move_y_result = True
                for wp in y_waypoints:
                    move_y_result = self.hardware.move_y(wp)
                    if not move_y_result:
                        break
                if not move_y_result:
                    self.logger.error(f"move_y to {target_y} failed or did not complete", category="execution")
```

- [ ] **Step 9: Run the full test suite**

Run: `python3 -m pytest tests/ -q`
Expected: PASS — all existing tests plus the new ones (no regressions; defaults are no-op so existing behavior is unchanged).

- [ ] **Step 10: Mock-mode smoke check**

Confirm the app still imports and runs in mock mode (`use_real_hardware: false`).
Run: `python3 -c "import core.execution_engine as ee; ee.ExecutionEngine(); print('engine OK')"`
Expected: `engine OK` (no import or syntax errors).

- [ ] **Step 11: Commit**

```bash
git add core/execution_engine.py tests/test_execution_compensation_hook.py
git commit -m "feat: apply tool-up motion compensation in execution engine"
```

---

## Task 5: Measurement provider interface

**Files:**
- Create: `core/measurement_provider.py`
- Test: `tests/test_measurement_provider.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_measurement_provider.py`:

```python
import os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.measurement_provider import ManualMeasurementProvider, MeasurementProvider


def test_manual_provider_parses_typed_value():
    typed = iter(["9.8"])
    p = ManualMeasurementProvider(input_fn=lambda prompt: next(typed))
    assert p.measure(axis="x", commanded_cm=10.0) == pytest.approx(9.8)


def test_manual_provider_reprompts_on_bad_input():
    typed = iter(["oops", "12.3"])
    p = ManualMeasurementProvider(input_fn=lambda prompt: next(typed))
    assert p.measure(axis="x", commanded_cm=10.0) == pytest.approx(12.3)


def test_is_a_measurement_provider():
    p = ManualMeasurementProvider(input_fn=lambda prompt: "1.0")
    assert isinstance(p, MeasurementProvider)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_measurement_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.measurement_provider'`.

- [ ] **Step 3: Implement `core/measurement_provider.py`**

```python
"""Measurement providers for motion calibration.

A MeasurementProvider returns the *physically measured* position of an axis
after the machine was commanded to a target. Manual entry is implemented now;
sensor-based auto-measurement is stubbed for later.
"""

from abc import ABC, abstractmethod


class MeasurementProvider(ABC):
    @abstractmethod
    def measure(self, axis: str, commanded_cm: float) -> float:
        """Return the measured physical position (cm) for the given axis."""
        raise NotImplementedError


class ManualMeasurementProvider(MeasurementProvider):
    """Operator reads a ruler/caliper and types the measured position."""

    def __init__(self, input_fn=input):
        self._input = input_fn

    def measure(self, axis: str, commanded_cm: float) -> float:
        while True:
            raw = self._input(
                f"[{axis.upper()}] commanded {commanded_cm:.3f} cm — "
                f"enter MEASURED position in cm: "
            )
            try:
                return float(str(raw).strip())
            except (ValueError, TypeError):
                print("  ! not a number, try again")


class SensorMeasurementProvider(MeasurementProvider):
    """Placeholder for RS485 edge-sensor based auto-measurement (future work)."""

    def __init__(self, hardware):
        self._hardware = hardware

    def measure(self, axis: str, commanded_cm: float) -> float:
        raise NotImplementedError(
            "Sensor-based measurement not implemented yet; use ManualMeasurementProvider"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_measurement_provider.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add core/measurement_provider.py tests/test_measurement_provider.py
git commit -m "feat: add measurement provider interface for calibration"
```

---

## Task 6: Calibration runner script

**Files:**
- Create: `scripts/calibrate_motion.py`

This is an interactive on-machine tool (no automated test — it drives real hardware and prompts the operator). It composes the already-tested pure pieces.

- [ ] **Step 1: Implement `scripts/calibrate_motion.py`**

```python
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
```

- [ ] **Step 2: Verify it parses and the CLI works**

Run: `python3 scripts/calibrate_motion.py --help`
Expected: argparse usage text showing `--axis {x,y}`.

- [ ] **Step 3: Commit**

```bash
git add scripts/calibrate_motion.py
git commit -m "feat: add interactive tool-up motion calibration script"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run the whole suite**

Run: `python3 -m pytest tests/ -q`
Expected: all tests pass (existing + new).

- [ ] **Step 2: Confirm no-op default behavior**

Confirm `config/settings.json` still has `enabled: false` for both axes (compensation off until calibrated).
Run: `python3 -c "import json; mc=json.load(open('config/settings.json'))['hardware_config']['arduino_grbl']['motion_compensation']; print(mc['x']['enabled'], mc['y']['enabled'])"`
Expected: `False False`

- [ ] **Step 3: Update CLAUDE.md quick reference (optional but recommended)**

Add to the "Run Commands" section of `CLAUDE.md`:

```
# Calibrate tool-up motion compensation (run on the real machine)
python3 scripts/calibrate_motion.py --axis x   # rows
python3 scripts/calibrate_motion.py --axis y   # lines
```

Commit:

```bash
git add CLAUDE.md
git commit -m "docs: document motion calibration commands"
```

---

## On-machine workflow (after implementation)

1. Home the machine. Run `python3 scripts/calibrate_motion.py --axis x`, follow prompts, measure with a ruler, let it write values.
2. Repeat for `--axis y`.
3. Run a real sheet; inspect the run-log (commanded vs GRBL vs measured residual).
4. If residual is small and repeatable → done. If it varies run-to-run → that's lost steps; pursue slower tool-up feed/accel (documented follow-up in the spec), not static compensation.

---

## Self-Review notes

- **Spec coverage:** offset/scale/backlash per-axis model (Task 2) ✓; settings block with no-op defaults (Task 1) ✓; execution hook only on `should_lift` (Task 4) ✓; run-log records overshoot waypoints (Task 4) ✓; calibration fit (Task 3) ✓; pluggable MeasurementProvider with manual now / sensor stub (Task 5) ✓; calibration runner (Task 6) ✓; lost-step follow-up documented (workflow + spec) ✓.
- **Type/name consistency:** `MotionCompensator.compensate(axis, current_pos_cm, target_cm)`, `_compensated_waypoints(axis, target)`, `fit_scale_offset`, `fit_backlash`, `MeasurementProvider.measure(axis, commanded_cm)` used consistently across tasks.
- **No placeholders:** all steps contain runnable code/commands and expected output.

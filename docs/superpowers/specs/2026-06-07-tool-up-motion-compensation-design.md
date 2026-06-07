# Tool-Up Motion Compensation + Calibration — Design

**Date:** 2026-06-07
**Status:** Approved (design), pending implementation plan

## Problem

Motor moves are accurate when the tool is **down** (marking/cutting): a commanded
10.5 cm move physically travels 10.5 cm. They are **inaccurate** when the motor
piston is **lifted** for a long traverse move. Observed symptoms:

- Lines, sefer 60: first line marked ~0.2 cm lower than intended.
- Rows: repeated mismatch causing rows to be misaligned.
- Unknown (as of writing) whether the error is a fixed amount, proportional to
  distance, direction-dependent, or accumulating across a sheet.

## Root-cause analysis (evidence gathered)

1. **Not a speed problem.** `real_hardware.move_x`/`move_y` call
   `arduino_grbl.move_to(...)` **without** `rapid=True`, so marking moves and
   repositioning moves both run at the same `feed_rate` (1000 mm/min). The
   `rapid` path (G1 at `rapid_rate`) is effectively unused in production.
   See `hardware/implementations/real/arduino_grbl/arduino_grbl.py:457-462` and
   `hardware/implementations/real/real_hardware.py:142-174`.

2. **Anti-backlash is not implemented in production.** It is only a comment
   placeholder at `arduino_grbl.py:100`. The 0.2 cm overshoot seen in
   `data/sefer60_grbl_commands.txt` is produced by the prototype in
   `tests/test_sefer60_grbl_commands.py`, not the running machine.

3. **The differentiator is mechanical preload, not speed.** With the tool
   pressed down, drivetrain friction takes up the slack (backlash), so motion is
   accurate. With the tool up, the axis is free and lost-motion / backlash
   appears on direction reversals. That the reported error (0.2 cm) equals the
   prototyped anti-backlash value is a strong hint the dominant cause is
   backlash, though a fixed offset and/or scale error are not yet ruled out.

4. **GRBL is open-loop.** `get_status` / `wait_for_movement_complete` report
   GRBL's *internal* position, which always matches the command. Backlash and
   lost steps are invisible to GRBL. Therefore the software cannot self-measure
   the physical error from GRBL alone — it must be measured physically (ruler /
   caliper) or via the RS485 edge sensors.

5. **Clean hook already exists.** `execution_engine._should_lift_motor_for_move`
   (`core/execution_engine.py:1228-1268`) returns `(should_lift, move_dist)` and
   is True exactly when a move exceeds a distance threshold AND the relevant
   motor piston is currently down — i.e. the "long move where the motor lifts"
   case. `get_current_x/y()` provides the start position, so travel direction is
   known. This is the precise place to apply compensation.

## Goals

- Make tool-up (lifted) positioning moves accurate, for both X (rows) and Y
  (lines).
- Never alter tool-down marking moves (they are already accurate).
- Support a **fixed offset**, a **distance-proportional scale**, and a
  **backlash** correction, independently toggleable per axis.
- Provide an on-machine way to **measure** the error and **derive** the right
  correction values, since the error is not yet characterized.
- All tunable values live in `config/settings.json` (no hardcoding, per
  CLAUDE.md rule #1).

## Non-goals

- No change to marking/cutting motion.
- No closed-loop control. GRBL stays open-loop; correction is feed-forward.
- GRBL/mechanical tuning (slower tool-up feed/accel, belt/screw tightening) is a
  documented follow-up, not part of this work — see "Future / follow-up".

## Design

### Component 1 — `core/motion_compensation.py` (pure logic)

A `MotionCompensator` class constructed from the `motion_compensation` settings
block. Pure Python, no hardware dependencies, unit-testable in mock mode (same
style as `tests/test_sefer60_grbl_commands.py`).

Primary method:

```
compensate(axis, current_pos_cm, target_cm) -> List[float]
```

Returns an ordered list of physical waypoints to drive the axis through. Logic:

```
cfg = config[axis]
if not cfg.enabled:
    return [target_cm]                      # no-op

corrected = cfg.scale * target_cm + cfg.offset_cm

if cfg.backlash_cm > 0:
    travel_dir = sign(target_cm - current_pos_cm)
    if travel_dir == cfg.approach_direction or travel_dir == 0:
        return [corrected]                  # already approaching from preferred side
    # approaching from the wrong side: overshoot past target, then settle back
    overshoot = corrected - cfg.approach_direction * cfg.backlash_cm
    return [overshoot, corrected]
return [corrected]
```

- **offset_cm** — fixes a constant error (e.g. the 0.2 cm).
- **scale** (default 1.0) — fixes distance-proportional error.
- **backlash_cm** + **approach_direction** (+1/−1) — guarantees the final
  position is always settled from one consistent direction; inserts an overshoot
  move only when natural travel is opposite. Order-independent, robust.

Each term is independently effective; `enabled=false` or default values make the
whole thing a no-op.

### Component 2 — Settings

Under `hardware_config.arduino_grbl.motion_compensation`:

```jsonc
{
  "x": { "enabled": false, "offset_cm": 0.0, "scale": 1.0,
         "backlash_cm": 0.0, "approach_direction": 1 },
  "y": { "enabled": false, "offset_cm": 0.0, "scale": 1.0,
         "backlash_cm": 0.0, "approach_direction": 1 }
}
```

Defaults are a no-op, so machine behavior is unchanged until explicitly enabled.
Add matching entries to `config/config_descriptions.json` so the admin tool
shows descriptions (per the config-alignment convention).

### Component 3 — Execution-engine integration

In `core/execution_engine.py`, in the `move_x`, `move_y`, and combined-move
(~line 1039) handlers:

- When `should_lift` is True for an axis, obtain `current_pos` via
  `get_current_x/y()`, call `compensator.compensate(axis, current_pos, target)`,
  and execute the returned waypoints in order through
  `self.hardware.move_x/move_y`.
- When `should_lift` is False, behavior is unchanged (no compensation).
- The compensator is instantiated from freshly loaded settings (consistent with
  the existing live-reload pattern in `_should_lift_motor_for_move`).
- Extend the run-log (`_log_grbl_move`) so each compensated move records the
  compensated target and any overshoot waypoint, keeping every run auditable.

### Component 4 — Calibration routine

`scripts/calibrate_motion.py` (and optionally an admin-tool button later).

Procedure, per axis:

1. Home / zero, then lift the motor piston (tool up) so calibration reflects the
   tool-up regime.
2. Drive a fixed pattern that mixes distances and includes a direction reversal,
   e.g. X targets `10 → 30 → 50 → 30 → 10` cm.
3. At each stop, obtain the real measured position through a
   **`MeasurementProvider`** interface:
   - `ManualMeasurementProvider` (implemented now) — operator reads a
     ruler/caliper and types the value.
   - `SensorMeasurementProvider` (interface defined now, implemented later) —
     reads RS485 edge sensors.
4. Fit the model:
   - Forward-pass measured-vs-commanded linear regression → `scale` (slope) and
     `offset_cm` (intercept).
   - Difference between forward and reverse readings at the same nominal target →
     `backlash_cm` (and which `approach_direction` to prefer).
   - Report whether readings are repeatable; non-repeatability flags lost steps
     (not software-correctable — see follow-up).
5. Print recommended per-axis values and offer to write them into
   `config/settings.json`.

The fitting math is pure and unit-testable independent of hardware.

## Testing

- Unit tests for `MotionCompensator.compensate`: no-op when disabled; offset
  only; scale only; backlash overshoot inserted only on wrong-direction
  approach; combined terms; both axes.
- Unit tests for the calibration fit: synthetic measured data with known
  offset/scale/backlash recovers those parameters.
- Execution-engine integration verified in mock mode: compensated waypoints are
  issued for lifted moves and not for short (non-lift) moves.

## Operator workflow (what to take to the machine)

1. Run `calibrate_motion.py` for X (rows) and Y (lines); enter measured values.
2. Apply the recommended terms via settings; re-run a sheet.
3. Inspect the run-log residual error; iterate values if needed.
4. If error accumulates across a sheet (calibration shows non-repeatability),
   pursue the follow-up (slower tool-up feed/accel) — static compensation cannot
   fix lost steps.

## Future / follow-up (not in this work)

- `SensorMeasurementProvider` using RS485 edge sensors for auto-calibration.
- Separate, slower feed/accel for tool-up moves (and/or `$120`/`$110` tuning) to
  eliminate lost steps if calibration shows non-repeatable drift.
- Admin-tool button to launch calibration from the GUI.

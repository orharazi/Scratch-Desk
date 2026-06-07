# Tool-Up Motion Calibration Guide

How to measure and correct the inaccuracy that appears on **long moves where the
motor piston lifts** (tool up). Short tool-down marking/cutting moves are already
accurate and are never touched by this system.

This guide covers running `scripts/calibrate_motion.py`, what it does on the
machine, how to measure, and how to apply and verify the results.

---

## When to use this

Use it when tool-up positioning is off — e.g. the first line lands ~0.2 cm low,
or rows don't line up. The calibration figures out **which kind** of error you
have and the exact numbers to fix it:

| Symptom | Knob it sets |
|---|---|
| Constant offset (same amount every move) | `offset_cm` |
| Error grows with distance | `scale` |
| Error appears when the axis reverses direction | `backlash_cm` |

You can have any combination; the calibration measures all three.

---

## Before you run

1. **Real hardware mode.** In `config/settings.json`, set
   `hardware_config.use_real_hardware` to `true`. (In mock mode the script runs
   but the "measurements" are simulated and meaningless.)
2. **Arduino/GRBL and the Pi GPIO connected and powered** (the same setup the
   main app needs). The script connects automatically on startup.
3. **Clear the work area and clear travel.** The default pattern drives the axis
   to **10, 30, 50, then ~60 cm**, so you need at least ~60 cm of clear travel on
   the axis being calibrated.
4. **Have a ruler/caliper ready.** The script can't measure position itself
   (GRBL is open-loop — it always *thinks* it's exactly on target). You provide
   reality by measuring.

> Run everything from the **repository root** so the relative config path
> (`config/settings.json`) resolves.

---

## What to run

Calibrate one axis at a time:

```bash
# Rows (X axis)
python3 scripts/calibrate_motion.py --axis x

# Lines (Y axis)
python3 scripts/calibrate_motion.py --axis y
```

---

## What happens, step by step

### 1. Homing (same as the main software)
The script runs the **exact homing sequence the main app uses**
(`hardware.perform_complete_homing_sequence`). That sequence:

1. Applies the GRBL configuration from `settings.json`
2. Checks the row-motor piston is up
3. Lifts the line-motor pistons
4. Runs GRBL homing (`$H`)
5. Resets work coordinates to (0, 0)
6. Lowers the line-motor pistons back down

Progress prints to the console as `[home] step N: ... — status`. If homing
fails, the script reports the error and **aborts** — fix homing first.

### 2. Forward pass (ascending) — finds offset + scale
For each target **10 → 30 → 50 cm**, each stop mirrors a real long move:

```
lift piston → move (tool UP) → lower piston → YOU MEASURE → lift piston
```

At each stop it prompts:

```
[X] commanded 30.000 cm — enter MEASURED position in cm:
```

Measure the **actual physical position after the piston has lowered** (the
position a mark would land on) and type it in. Bad input re-prompts.

### 3. Reverse pass — finds backlash
It moves out to ~60 cm, then comes **back down to 30 cm** (approaching the same
point from the opposite direction), lowers, and asks you to measure once more.
The difference between the 30 cm reading going **up** vs coming **down** is the
backlash.

### 4. Results
It prints recommended values, e.g.:

```
--- Recommended motion_compensation values ---
  enabled:            true
  scale:              1.00120
  offset_cm:          +0.187
  backlash_cm:        0.250
  approach_direction: 1   (forward/ascending pass)
```

Two automatic warnings:
- **Residual is tiny** (everything ≈ 0): the error isn't repeatable — that's a
  sign of **lost steps**, which static compensation can't fix. See
  "If it's lost steps" below.
- **Values look unusually large** (`|scale−1| > 0.05`, `|offset| > 0.5 cm`, or
  `backlash > 1.0 cm`): likely a measurement mistake or a mechanical problem —
  double-check before applying.

### 5. Apply
It asks:

```
Write these into config/settings.json? [y/N]
```

- Type **`y`** to write the values into
  `hardware_config.arduino_grbl.motion_compensation.<axis>` and set
  `enabled: true`. Read/write errors are reported, not crashed.
- Anything else leaves settings unchanged (copy the values in by hand if you
  prefer).

---

## After applying

1. Run a real sheet.
2. Check the run-log in `data/grbl_run_logs/` — it records commanded vs GRBL
   position and flags any anti-backlash overshoot waypoints.
3. Measure the result. If there's still residual error, re-run the calibration
   (or nudge the values) and repeat. The three knobs are independent, so you can
   tune one without disturbing the others.

To turn compensation off again, set `enabled: false` for that axis in
`settings.json` (or via the Admin Tool). Defaults are a no-op.

---

## How the settings look

```jsonc
"motion_compensation": {
  "x": { "enabled": true,  "offset_cm": 0.187, "scale": 1.00120,
         "backlash_cm": 0.250, "approach_direction": 1 },
  "y": { "enabled": false, "offset_cm": 0.0,   "scale": 1.0,
         "backlash_cm": 0.0,  "approach_direction": 1 }
}
```

- **offset_cm** — added to every tool-up target on that axis.
- **scale** — multiplies the target (fixes distance-proportional error).
- **backlash_cm** — overshoot distance used when the move approaches from the
  wrong side, so the final position is always settled from one direction.
- **approach_direction** — `+1` settles the final position by approaching from
  below (ascending); `-1` from above. The calibration recommends `+1` because it
  fits from the ascending pass.

Compensation is applied **only** when the engine lifts the piston for a long
move, and every resulting waypoint is clamped to the axis travel limits
(`hardware_limits.max_x_position` / `max_y_position`) for safety.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `homing failed: ...` then abort | Resolve homing in the main app first (GRBL connected, pistons free, limits OK). |
| `PORT NOT FOUND` / GPIO errors | Not connected to the real machine, or `use_real_hardware` is false. |
| Pattern runs off the end of travel | Axis has less than ~60 cm clear; clear more travel or ask to make the targets configurable. |
| "Residual is tiny" warning | Likely lost steps — see below; don't apply tiny values. |
| Values flagged "unusually large" | Re-measure; suspect a reading error or mechanical fault before applying. |

### If it's lost steps (non-repeatable error)
Static compensation can't fix steps the motor drops. Instead, slow the tool-up
moves and/or reduce acceleration (GRBL `$120`/`$121` and `$110`/`$111`) and
re-test, or check belts/couplers. This is noted as a follow-up in the design
spec (`docs/superpowers/specs/2026-06-07-tool-up-motion-compensation-design.md`).

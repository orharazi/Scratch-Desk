# CNC SCRATCH DESK - Quick System Brief for AI Agents

## What is This?
CNC machine control software for marking and cutting scratch cards (lottery tickets). Written in Python with Tkinter GUI.

## Architecture Overview

### Hardware Stack
```
Raspberry Pi (GPIO) → Pistons (5) + Sensors (9) + Limit Switches (5)
Raspberry Pi (Serial) → Arduino GRBL → X/Y Motors + Motor Limit Switches (4)
```

### Software Stack
```
GUI (Tkinter) → Execution Engine → Step Generator → Hardware Interface → Mock/Real Hardware
                       ↓
                 Safety System (prevents dangerous operations)
```

## Key Files

- **`settings.json`** - ALL configuration (hardware pins, colors, timing, limits) - NEVER hard-code values
- **`mock_hardware.py`** - Hardware abstraction (mock mode), all state variables
- **`hardware/hardware_interface.py`** - Real hardware interface (Raspberry Pi + Arduino)
- **`step_generator.py`** - Converts CSV programs → execution steps
- **`execution_engine.py`** - Executes steps sequentially with safety checks
- **`safety_system.py`** - Enforces safety rules (e.g., can't move Y if row marker down)
- **`gui/main_app.py`** - Main GUI coordinator
- **`gui/canvas_manager.py`** - Canvas visualization
- **`gui/panels/hardware_status_panel.py`** - Live hardware monitoring (200ms updates)

## Critical Rules

### 1. Configuration
❌ **NEVER**: `time.sleep(0.1)` or `color="#FF0000"`
✅ **ALWAYS**: `time.sleep(timing_settings.get("tool_action_delay", 0.1))` and `color=operation_colors["mark"]["pending"]`

### 2. Hardware State (mock_hardware.py)
**Every variable MUST appear in Hardware Status Panel (1:1 mapping)**

**Motors**: `current_x_position`, `current_y_position` (in cm)

**Lines Tools** (Y-axis, horizontal operations):
- `line_marker_piston`, `line_marker_state`
- `line_cutter_piston`, `line_cutter_state`
- `line_motor_piston`, `line_motor_piston_sensor`

**Rows Tools** (X-axis, vertical operations):
- `row_marker_piston`, `row_marker_state`
- `row_cutter_piston`, `row_cutter_state`

**Limit Switches**: `limit_switch_states['y_top', 'y_bottom', 'x_left', 'x_right', 'rows']`

### 3. Coordinate System
- **X-axis (Rows Motor)**: Horizontal (0-120cm), controls vertical marking/cutting
- **Y-axis (Lines Motor)**: Vertical (0-80cm), controls horizontal marking/cutting
- **Origin**: Bottom-left (0, 0)
- **Units**: Centimeters throughout (converted to mm for GRBL)

### 4. Safety Rules
**CRITICAL**: Y-axis CANNOT move if `row_marker_state == "down"` (marker blocks Y-axis path)

**Line Motor Piston**: ONLY lifts during UPWARD Y movement (from lower to higher Y), NOT when moving down

### 5. Piston Pattern
```python
# Activate tool sequence:
1. piston_down()      # Lower assembly
2. tool_down()        # Activate tool
3. [perform operation]
4. tool_up()          # Deactivate tool
5. piston_up()        # Raise assembly
```

### 6. Hardware Modes
**Mock Mode** (default): `use_real_hardware: false` in settings.json - simulation only
**Real Mode**: `use_real_hardware: true` - connects to Raspberry Pi + Arduino

Use `mock_hardware.py` functions - abstraction layer handles both modes.

## Quick Reference

### Starting Point
```bash
python3 index.py  # Launch main application
python3 hardware/hardware_test_gui.py  # Hardware test interface
```

### Program Flow
1. Load CSV → Program Data
2. `step_generator.py` → Execution Steps
3. `execution_engine.py` → Execute each step:
   - Check safety
   - Call `mock_hardware.function()`
   - Update GUI (canvas + panels)

### Adding Features

**New Piston/Sensor?**
1. Add GPIO pin to `settings.json` → `hardware_config.raspberry_pi`
2. Add variable to `mock_hardware.py`
3. Add to `hardware_status_panel.py` display
4. GPIO interface auto-loads from settings

**New Step Type?**
1. Generate in `step_generator.py`
2. Handle in `execution_engine.py`
3. Implement in `mock_hardware.py`

**New Safety Rule?**
1. Add check to `safety_system.py`
2. Call in `execution_engine.py` before step execution

### Canvas Colors (from settings.json)
**MARK operations** (lines, dashed):
- Pending: `#880808` (red)
- In Progress: `#FF8800` (orange)
- Completed: `#00AA00` (green)

**CUT operations** (rows/cuts, solid):
- Pending: `#8800FF` (purple)
- In Progress: `#FF0088` (pink)
- Completed: `#AA00AA` (purple)

## Common Tasks

### Update Hardware Display
All state changes auto-update via 200ms polling in `hardware_status_panel.py`. Just modify `mock_hardware.py` variables.

### Change Timing/Behavior
Edit `settings.json`, NO code changes needed.

### Test Hardware
```bash
python3 hardware/hardware_test_gui.py  # Interactive GUI
python3 hardware/test_motor_movement.py  # Motor tests
python3 hardware/test_gpio.py  # GPIO tests
```

### Git Workflow
```bash
git add <files>
git commit -m "descriptive message"
git push
```

## Important Notes

- **Thread Safety**: GUI updates in main thread, execution in worker thread
- **Sensor Handling**: Triggers ignored during safety pauses, buffers flushed on resume
- **State Sync**: Canvas, status panel, operations panel all update from same source (200ms interval)
- **Error Handling**: Safety violations pause execution, user must fix and resume
- **Documentation**: See `SYSTEM_ARCHITECTURE.md` for complete details

## Troubleshooting

**Import errors?** Run from project root: `python3 index.py` (not `cd gui && python3 main_app.py`)

**Values not from settings?** Check if hard-coded values exist - they shouldn't!

**GUI not updating?** Verify 200ms update interval in `settings.json` → `hardware_monitor.update_interval_ms`

**Safety not working?** Ensure `safety_system.enable_safety()` called in `execution_engine.py`

## For More Details
Read `SYSTEM_ARCHITECTURE.md` for comprehensive documentation (970+ lines covering everything).

---

**Remember**: This system is ready for real hardware - just flip `use_real_hardware: true` in settings.json when Raspberry Pi and Arduino are connected!

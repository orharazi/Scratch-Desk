# Scratch-Desk CNC Control System - Claude Code Guide

## Project Overview

**Scratch-Desk** is a CNC (Computer Numerical Control) machine control system designed to mark and cut scratch cards (lottery tickets). The system controls:
- **Y-axis motor** for horizontal line operations (marking/cutting)
- **X-axis motor** for vertical row operations (marking/cutting)
- **Pneumatic pistons** for lowering/raising tools
- **Sensors** for edge detection and tool position feedback
- **Safety systems** to prevent dangerous operations

### Hardware Stack
| Component | Interface | Purpose |
|-----------|-----------|---------|
| Arduino MEGA + GRBL | Serial 115200 baud | Motor control via G-code |
| Raspberry Pi GPIO | Direct pins | Piston control (6 outputs) |
| N4DIH32 RS485 Module | Modbus RTU 9600 baud | 32-channel sensor reading |

### Software Stack
- **Language**: Python 3.7+
- **GUI**: Tkinter (built-in)
- **Libraries**: PySerial, PyModbus, RPi.GPIO

---

## Quick Reference

### Run Commands
```bash
# Start main application (mock mode by default for development)
python3 index.py

# Admin Tool - hardware testing, safety rules, system configuration
python3 admin_tool.py

# Verify config alignment (or use /align-settings in Claude Code)
python3 scripts/verify_config_alignment.py        # Check alignment
python3 scripts/verify_config_alignment.py --fix  # Auto-fix missing descriptions

# RS485 sensor diagnostics
python3 quick_rs485_test.py
python3 comprehensive_rs485_test.py
```

### Configuration
- **Master config**: `config/settings.json` (ALL timing, hardware, GUI settings)
- **Safety rules**: `config/safety_rules.json` (Safety rule definitions)
- **Config descriptions**: `config/config_descriptions.json` (Setting descriptions for admin UI)
- **Hardware mode**: Set `hardware_config.use_real_hardware` to `true`/`false`
- **Admin Tool**: Use `python3 admin_tool.py` to edit settings via GUI

### Git Workflow
```bash
git add <files>
git commit -m "descriptive message"
git push
```

---

## Critical Rules (MUST FOLLOW)

### 1. No Hardcoded Values
**NEVER** use hardcoded timing values, pin numbers, or configuration constants.
**ALWAYS** read from `config/settings.json`.

```python
# WRONG
time.sleep(0.5)
GPIO.setup(17, GPIO.OUT)

# CORRECT
settings = load_settings()
time.sleep(settings['timing']['tool_action_delay'])
GPIO.setup(settings['hardware_config']['raspberry_pi']['pistons']['line_marker_piston'], GPIO.OUT)
```

### 2. Settings.json Integrity
When modifying `config/settings.json`:
- **No duplicate values** - each setting serves a unique purpose
- **Preserve structure** - don't reorganize sections
- **Add comments sparingly** - JSON doesn't support comments, use descriptive keys
- **Validate JSON** before committing

### 3. Hardware Abstraction Pattern
All hardware access goes through the factory pattern:
```python
from hardware.interfaces.hardware_factory import get_hardware_interface
hw = get_hardware_interface()
hw.move_x(position)  # Works in both mock and real mode
```

### 4. Safety System
**CRITICAL SAFETY RULE**: Cannot move Y-axis if row marker is DOWN (blocks Y-axis path)
- Always check `safety_system.check_step_safety()` before motor operations
- Never bypass safety checks without explicit user confirmation

### 5. Thread Safety
- Hardware operations use thread-safe command queues
- Serial ports have exclusive locks
- GUI updates only from main thread (via callbacks)

---

## Project Architecture

### Directory Structure
```
Scratch-Desk/
├── index.py                    # Main entry point
├── config/
│   └── settings.json           # ALL configuration (2000+ lines)
├── core/                       # Business logic
│   ├── program_model.py        # ScratchDeskProgram data structure
│   ├── csv_parser.py           # CSV file parsing
│   ├── step_generator.py       # Convert programs to execution steps
│   ├── execution_engine.py     # Step execution with threading
│   ├── safety_system.py        # Safety violation detection
│   ├── machine_state.py        # Global state management
│   ├── translations.py         # Hebrew UI translations
│   └── logger.py               # Logging with colors/icons
├── hardware/                   # Hardware abstraction
│   ├── interfaces/
│   │   └── hardware_factory.py # Mock vs Real factory
│   ├── implementations/
│   │   ├── mock/
│   │   │   └── mock_hardware.py       # Simulated hardware
│   │   └── real/
│   │       ├── real_hardware.py       # Hardware coordinator
│   │       ├── arduino_grbl/
│   │       │   └── arduino_grbl.py    # G-code motor control
│   │       └── raspberry_pi/
│   │           ├── raspberry_pi_gpio.py   # GPIO piston control
│   │           └── rs485_modbus.py        # Modbus sensor reading
│   └── tools/
│       └── hardware_test_gui.py    # Standalone testing
├── gui/                        # User interface
│   ├── main_app.py             # Main application window
│   ├── canvas/                 # Visualization components
│   ├── panels/                 # UI panels
│   ├── execution/              # Engine-GUI bridge
│   └── dialogs/                # Modal dialogs
├── tests/                      # Test scripts
└── docs/                       # Documentation
```

### Key Modules

| Module | Responsibility | Key Classes/Functions |
|--------|---------------|----------------------|
| `core/program_model.py` | Program data structure | `ScratchDeskProgram` |
| `core/csv_parser.py` | Parse CSV programs | `parse_csv_file()` |
| `core/step_generator.py` | Generate execution steps | `generate_steps()` |
| `core/execution_engine.py` | Execute steps with threading | `ExecutionEngine` |
| `core/safety_system.py` | Safety checks | `check_step_safety()` |
| `hardware/implementations/mock/mock_hardware.py` | Simulate hardware | All `move_*`, `*_down()`, `*_up()` |
| `gui/main_app.py` | Main window orchestrator | `ScratchDeskApp` |

### Data Flow
```
CSV File → csv_parser → ScratchDeskProgram → step_generator → Steps
                                                                  ↓
GUI ← execution_controller ← ExecutionEngine ← Steps (executed sequentially)
                                    ↓
                        hardware_factory → Mock/Real Hardware
```

---

## Hardware Details

### GPIO Pin Mapping (from settings.json)
```
Pistons (OUTPUT):
  line_marker_piston: 6
  line_cutter_piston: 16
  line_motor_piston: 13
  row_marker_piston: 5
  row_cutter_piston: 19
```

### RS485 Sensor Mapping
Sensors are read via Modbus RTU from the N4DIH32 module:
- Registers 0xC0 (192) and 0xC1 (193) - 16 bits each
- Edge sensors: x_left, x_right, y_top, y_bottom
- Tool sensors: up/down pairs for each tool

### GRBL G-Code Commands
```
G0 X__ Y__   # Rapid positioning
G1 X__ Y__ F__ # Feed rate movement
$H           # Home machine
?            # Status query
!            # Feed hold (emergency)
~            # Resume
Ctrl-X       # Soft reset
```

---

## Common Development Tasks

### Adding a New Setting
1. Add to appropriate section in `config/settings.json`
2. Document the setting's purpose with a clear key name
3. Load via `settings['section']['key']` in code
4. Never duplicate existing settings

### Adding a New Tool/Piston
1. Add GPIO pin in `settings.json` under `hardware_config.raspberry_pi.pistons`
2. Add sensor mappings in `rs485.sensor_bit_mapping`
3. Add mock implementation in `mock_hardware.py`
4. Add real implementation in `raspberry_pi_gpio.py`
5. Update safety_system.py if needed

### Adding a New Step Type
1. Define step structure in `core/step_generator.py`
2. Add execution logic in `core/execution_engine.py`
3. Add Hebrew translation in `core/translations.py`
4. Update canvas visualization if needed

### Testing Changes
1. **Mock mode first**: Set `use_real_hardware: false`
2. Run `python3 index.py` and test functionality
3. Check hardware status panel for state changes
4. **Real hardware**: Set `use_real_hardware: true` and test on Pi

---

## Testing Approach

### Mock Mode Testing
- Default mode for development
- Hardware is simulated with realistic timing
- All state changes visible in hardware status panel
- Safe for rapid iteration

### Real Hardware Testing
- Requires Raspberry Pi + Arduino setup
- Set `use_real_hardware: true` in settings
- Use `hardware_test_gui.py` for isolated component tests
- RS485 diagnostics: `quick_rs485_test.py`, `comprehensive_rs485_test.py`

### Diagnostic Commands
```bash
# Test RS485 connection
python3 quick_rs485_test.py

# Full RS485 diagnostics
python3 comprehensive_rs485_test.py

# Scan RS485 bus for devices
python3 ultra_rs485_scanner.py

# Standalone hardware test GUI
python3 hardware/tools/hardware_test_gui.py
```

---

## Code Style & Conventions

### Python Style
- Use type hints for function signatures
- Docstrings for public functions
- Hebrew allowed in UI strings and logs
- English for code, comments, and variable names

### Naming Conventions
- `snake_case` for functions and variables
- `PascalCase` for classes
- `UPPER_CASE` for constants (avoid - use settings.json)
- Prefix mock functions with actual function names (consistency)

### Error Handling
- Raise `SafetyViolation` for safety-related errors
- Log all hardware communication errors
- Use try/except for serial operations (can timeout)
- Graceful degradation when hardware unavailable

---

## Important Context for AI Agents

### Language
- **UI is in Hebrew** (RTL support)
- **Code and logs in English**
- Hebrew translations in `core/translations.py`

### Units
- **Internal**: Centimeters (cm)
- **GRBL**: Millimeters (mm) - auto-converted
- **Workspace**: 120cm x 80cm

### Sensor Logic
- Most sensors are **Normally Closed (NC)**
- Sensor "triggered" means circuit opened (HIGH signal after inversion)
- Edge sensors detect paper edges during movement

### Piston States
- **HIGH** = Extended (down position)
- **LOW** = Retracted (up position)
- Each tool has separate up/down position sensors

---

## Troubleshooting

### Common Issues

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| Serial port not found | Wrong port in settings | Check `/dev/ttyUSB*` or `/dev/ttyACM*` |
| RS485 no response | Baud rate mismatch | Verify 9600 baud |
| Motor not moving | GRBL not connected | Check Arduino connection, run `$X` to unlock |
| Safety violation | Row marker down during Y move | Raise row marker first |
| GUI not updating | Callback not threaded properly | Use `root.after()` for GUI updates |

### Debug Logging
Enable detailed logging in `settings.json`:
```json
"logging": {
  "level": "DEBUG",
  "categories": {
    "hardware": "DEBUG",
    "grbl": "DEBUG"
  }
}
```

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| `docs/SYSTEM_ARCHITECTURE.md` | Complete architecture guide |
| `docs/CONFIGURATION_GUIDE.md` | Settings reference |
| `docs/GRBL_COMMANDS_REFERENCE.md` | G-code reference |
| `hardware/README.md` | Hardware integration guide |
| `docs/GPIO_DEBOUNCING_FIX.md` | GPIO optimization |
| `docs/RS485_OPTIMIZATION_50MS_TRIGGERS.md` | RS485 timing |

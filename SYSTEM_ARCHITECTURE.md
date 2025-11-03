# CNC SCRATCH DESK - COMPLETE SYSTEM ARCHITECTURE

## SYSTEM OVERVIEW

### What is the CNC Scratch Desk?
The CNC Scratch Desk is a specialized CNC machine for marking and cutting scratch cards (lottery tickets). It operates on pre-printed paper sheets, marking lines and cutting them into individual cards according to programmed patterns.

### Core Purpose
- **Mark horizontal lines** (using Y-axis motor movement)
- **Mark vertical lines** (using X-axis motor movement)
- **Cut horizontal sections** (separating rows)
- **Cut vertical sections** (separating columns)
- **Detect paper edges** automatically using sensors
- **Execute operations safely** with multiple safety checks

---

## PHYSICAL HARDWARE ARCHITECTURE

### Hardware Components Hierarchy

```
CNC SCRATCH DESK MACHINE
│
├── RASPBERRY PI (Control Computer)
│   ├── GPIO Pins → Control all pistons and read all sensors
│   └── Serial Port → Connects to Arduino for motor control
│
├── ARDUINO MEGA + GRBL FIRMWARE
│   ├── Serial Communication → Receives G-code commands
│   ├── X Motor (Rows Motor) → Horizontal movement (0-120cm)
│   ├── Y Motor (Lines Motor) → Vertical movement (0-80cm)
│   └── 4 Limit Switches → Safety boundaries
│       ├── x_left, x_right → Horizontal boundaries
│       └── y_top, y_bottom → Vertical boundaries
│
├── LINES TOOLS (Horizontal operations, controlled by Y motor)
│   ├── Line Marker Assembly
│   │   ├── line_marker_piston → Lifts/lowers marker assembly
│   │   └── line_marker_state (sensor) → Detects marker position
│   ├── Line Cutter Assembly
│   │   ├── line_cutter_piston → Lifts/lowers cutter assembly
│   │   └── line_cutter_state (sensor) → Detects cutter position
│   └── Line Motor Piston (Y-axis lift mechanism)
│       ├── line_motor_piston → Lifts entire Y motor during upward movement
│       └── line_motor_piston_sensor → Detects piston position
│
├── ROWS TOOLS (Vertical operations, controlled by X motor)
│   ├── Row Marker Assembly
│   │   ├── row_marker_piston → Lifts/lowers marker assembly
│   │   └── row_marker_state (sensor) → Detects marker position
│   └── Row Cutter Assembly
│       ├── row_cutter_piston → Lifts/lowers cutter assembly
│       └── row_cutter_state (sensor) → Detects cutter position
│
├── EDGE DETECTION SENSORS (Paper boundary detection)
│   ├── x_left_edge → Detects left paper edge during line operations
│   ├── x_right_edge → Detects right paper edge during line operations
│   ├── y_top_edge → Detects top paper edge during row operations
│   └── y_bottom_edge → Detects bottom paper edge during row operations
│
└── SAFETY LIMIT SWITCH
    └── rows (door sensor) → Prevents operation when door open
```

### Critical Hardware Understanding

**COORDINATE SYSTEM:**
- **X-axis (Rows Motor)**: Horizontal movement, controls ROWS operations (vertical marking/cutting)
- **Y-axis (Lines Motor)**: Vertical movement, controls LINES operations (horizontal marking/cutting)
- **Origin (0, 0)**: Bottom-left corner of the machine
- **Units**: Centimeters (cm) throughout the application, converted to millimeters for GRBL

**PISTON OPERATION:**
- **UP**: Default safe position (retracted)
- **DOWN**: Active operation position (extended)
- GPIO: HIGH = DOWN (extended), LOW = UP (retracted)

**SENSOR OPERATION:**
- **READY**: Sensor not triggered (HIGH signal with pull-up)
- **TRIGGERED**: Sensor activated (LOW signal, pulled to ground)

**IMPORTANT SAFETY RULE:**
The line motor piston ONLY lifts during UPWARD Y movement (from lower to higher Y position). It does NOT lift when moving down. This prevents collision with row marker.

---

## SOFTWARE ARCHITECTURE

### Directory Structure

```
Scratch-Desk/
│
├── settings.json                    # ALL configuration (hardware, GUI, timing, colors)
├── CLAUDE.md                        # Project instructions for AI
├── SYSTEM_ARCHITECTURE.md           # This document
│
├── index.py                         # Main entry point - starts the GUI application
│
├── mock_hardware.py                 # Hardware abstraction layer (MOCK MODE)
│   └── All motor/tool functions return immediately with simulated behavior
│
├── hardware/                        # Real hardware connection (REAL MODE)
│   ├── __init__.py
│   ├── raspberry_pi_gpio.py        # Raspberry Pi GPIO control (pistons/sensors)
│   ├── arduino_grbl.py             # Arduino GRBL motor control (G-code)
│   ├── hardware_interface.py       # Unified interface (switches mock/real)
│   ├── hardware_test_gui.py        # Standalone test GUI
│   ├── test_motor_movement.py      # Motor testing suite
│   ├── test_gpio.py                # GPIO testing suite
│   └── requirements.txt            # Hardware dependencies
│
├── step_generator.py                # Converts program data → execution steps
│
├── execution_engine.py              # Executes steps sequentially
│   └── Calls mock_hardware functions for each step
│
├── safety_system.py                 # Safety checks and violations
│   └── Prevents dangerous operations (e.g., Y movement with row marker down)
│
├── gui/                             # User interface components
│   ├── main_app.py                 # Main application window
│   ├── canvas_manager.py           # Canvas visualization coordinator
│   ├── canvas_*.py                 # Canvas rendering modules
│   │   ├── canvas_base.py          # Base canvas setup
│   │   ├── canvas_grid.py          # Grid rendering
│   │   ├── canvas_operations.py    # Work lines/rows rendering with colors
│   │   ├── canvas_pointer.py       # Motor position pointer
│   │   ├── canvas_sensors.py       # Sensor trigger visualization
│   │   └── canvas_paper.py         # Paper boundary visualization
│   └── panels/                     # GUI panels
│       ├── control_panel.py        # Start/Stop/Load controls
│       ├── steps_panel.py          # Step execution display
│       ├── hardware_status_panel.py # Live hardware monitoring
│       └── work_operations_panel.py # Operation status display
│
└── sample_programs.csv              # Example program data
```

### Key Module Responsibilities

#### **1. mock_hardware.py** (Hardware Abstraction - MOCK MODE)
**Purpose**: Simulates hardware behavior for development/testing

**State Variables** (ALL map 1:1 to Hardware Status Panel):
```python
# Motor positions
current_x_position = 0.0  # cm
current_y_position = 0.0  # cm

# Lines tools (Y-axis operations)
line_marker_piston = "up"           # Piston control
line_marker_state = "up"            # Sensor reading
line_cutter_piston = "up"
line_cutter_state = "up"
line_motor_piston = "down"          # Default DOWN
line_motor_piston_sensor = "down"

# Rows tools (X-axis operations)
row_marker_piston = "up"
row_marker_state = "up"
row_cutter_piston = "up"
row_cutter_state = "up"

# Limit switches (in limit_switch_states dict)
limit_switch_states = {
    'y_top': False,
    'y_bottom': False,
    'x_right': False,
    'x_left': False,
    'rows': False  # Door safety
}
```

**Key Functions**:
- `move_x(position)` - Move X motor, automatic piston handling
- `move_y(position)` - Move Y motor, lifts line_motor_piston ONLY on upward movement
- `line_marker_down()/up()` - Controls piston + state together
- `row_marker_down()/up()` - Controls piston + state together
- (Similar for all tools)

**CRITICAL**: Uses `settings.json` for ALL values - no hard-coded delays, speeds, or configurations.

#### **2. hardware/** (Hardware Abstraction - REAL MODE)

**hardware_interface.py** - Unified interface
- Checks `settings.json` → `hardware_config.use_real_hardware`
- If TRUE: Uses real Raspberry Pi + Arduino
- If FALSE: Returns mock responses immediately
- Provides identical API to mock_hardware.py

**raspberry_pi_gpio.py** - GPIO Control
- Reads pin mappings from `settings.json` → `hardware_config.raspberry_pi`
- Controls 5 pistons (OUTPUT pins)
- Reads 9 sensors (INPUT pins with pull-up)
- Reads 5 limit switches (INPUT pins with pull-up)
- Auto-fallback to mock if RPi.GPIO not available

**arduino_grbl.py** - Motor Control
- Serial communication with Arduino running GRBL firmware
- Sends G-code commands: G0 (rapid), G1 (feed), $H (home)
- Converts cm → mm automatically
- Thread-safe command queue
- Auto-fallback to mock if pyserial not available

#### **3. step_generator.py** (Program → Steps Converter)

**Purpose**: Converts high-level program data into low-level execution steps

**Input**: Program data from CSV
```python
{
    'lines_num': 10,              # Number of horizontal lines
    'rows_num': 5,                # Number of vertical rows
    'page_side': 'RTL',           # Right-to-left or Left-to-right
    'cut_method': 'rows_first',   # Cutting order
    # ... more fields
}
```

**Output**: List of execution steps
```python
[
    {
        'operation': 'move_x',
        'parameters': {'position': 0.0},
        'description': 'Init: Move rows motor to home position (X=0)'
    },
    {
        'operation': 'wait_sensor',
        'parameters': {'sensor': 'x_left'},
        'description': 'Wait for LEFT X sensor to detect paper edge'
    },
    # ... many more steps
]
```

**Step Types**:
- `move_x`, `move_y` - Motor movements
- `tool_action` - Marker/cutter up/down operations
- `wait_sensor` - Wait for edge detection
- `wait_user` - Pause for user confirmation

**Key Logic**:
- Generates steps for lines marking (Y motor moves, line marker down)
- Generates steps for rows marking (X motor moves, row marker down)
- Generates cutting sequences based on cut_method
- Adds Y motor home position initialization (line 58-62)

#### **4. execution_engine.py** (Step Executor)

**Purpose**: Executes steps sequentially, manages state, enforces safety

**Key Components**:
```python
class ExecutionEngine:
    is_running = False        # Currently executing
    is_paused = False         # Paused by safety violation
    is_blocked = False        # Blocked waiting for sensor/user
    current_step_index = 0    # Which step we're on
    steps = []                # All steps to execute
```

**Execution Flow**:
1. Load steps from step_generator
2. Start execution thread
3. For each step:
   - Check safety (via safety_system)
   - Execute operation (via mock_hardware)
   - Update UI (canvas, step panel, status)
   - Wait for completion
4. Handle blocking (sensors, user input)
5. Handle pausing (safety violations)

**Thread Safety**:
- Main thread: GUI updates
- Execution thread: Step execution
- Safety thread: Continuous monitoring

#### **5. safety_system.py** (Safety Enforcement)

**Purpose**: Prevents dangerous operations that could damage hardware

**Key Safety Rules**:

**RULE 1: Y-axis movement safety**
```python
def check_y_axis_movement_safety():
    # CANNOT move Y motor if row marker is DOWN
    # Reason: Row marker lies across Y-axis path
    row_marker_state = get_row_marker_state()
    row_marker_limit = get_row_motor_limit_switch()

    if row_marker_state == "down" or row_marker_limit == "down":
        raise SafetyViolation("Cannot move Y-axis: row marker is DOWN")
```

**When Safety Violated**:
1. Execution pauses immediately
2. Safety message displayed to user
3. Sensor triggers during pause are ignored (flushed)
4. User must fix issue and resume
5. Sensor buffers cleared before resuming

#### **6. GUI System** (gui/ directory)

**main_app.py** - Main window coordinator
- Creates all panels
- Manages application lifecycle
- Holds references to engine, canvas, program data

**canvas_manager.py** - Canvas coordinator
- Creates canvas modules (grid, operations, pointer, sensors)
- Coordinates rendering updates
- Manages motor operation mode (LINES vs ROWS)

**canvas_operations.py** - Work lines/rows rendering
```python
# Renders lines and rows with color-coded states:
# - MARK operations (lines): Dashed lines
#   - Pending: #880808
#   - In Progress: #FF8800
#   - Completed: #00AA00
# - CUT operations (rows/cuts): Solid lines
#   - Pending: #8800FF
#   - In Progress: #FF0088
#   - Completed: #AA00AA
```

**Colors from settings.json** - `operation_colors` section

**hardware_status_panel.py** - Live hardware monitoring
- Updates every 200ms
- Shows all pistons, sensors, limit switches
- Color-coded: GREEN=active/ready, RED=down/triggered, GRAY=up/inactive

**work_operations_panel.py** - Operation status
- Shows line marking progress (1/10, 2/10, etc.)
- Shows row marking progress
- Shows cutting progress
- Color-coded status indicators

---

## DATA FLOW ARCHITECTURE

### Program Execution Flow

```
1. USER LOADS CSV
   ↓
2. CSV → Program Data (dict)
   ↓
3. Program Data → step_generator.py → Execution Steps (list)
   ↓
4. Steps → execution_engine.py → Execute sequentially
   ↓
5. Each step → safety_system.check() → Verify safe
   ↓
6. If safe → mock_hardware.function() → Execute operation
   ↓
7. Hardware state changes → GUI updates (200ms interval)
   ↓
8. Canvas renders current state (operations, pointer, sensors)
   ↓
9. Repeat until all steps complete
```

### Sensor Flow (Edge Detection)

```
1. Step: wait_sensor (e.g., wait for x_left)
   ↓
2. execution_engine sets is_blocked = True
   ↓
3. Canvas shows "WAITING FOR LEFT EDGE" message
   ↓
4. User presses sensor button (GUI or hardware)
   ↓
5. mock_hardware.trigger_x_left_sensor() called
   ↓
6. Sensor event set → wait_sensor returns
   ↓
7. execution_engine sets is_blocked = False
   ↓
8. Execution continues to next step
```

### Safety Violation Flow

```
1. safety_system detects violation (e.g., row marker down during Y movement)
   ↓
2. Raises SafetyViolation exception
   ↓
3. execution_engine catches exception
   ↓
4. Sets is_paused = True, is_blocked = True
   ↓
5. GUI shows pause message with safety reason
   ↓
6. All sensor triggers ignored (flushed) during pause
   ↓
7. User fixes issue (raises row marker)
   ↓
8. User presses Resume
   ↓
9. Safety check passes → flush_all_sensor_buffers()
   ↓
10. Execution resumes from same step
```

---

## CONFIGURATION SYSTEM (settings.json)

### Structure Overview

```json
{
  "hardware_limits": {
    "max_x_position": 120.0,      // Maximum X travel (cm)
    "max_y_position": 80.0,       // Maximum Y travel (cm)
    "paper_start_x": 15.0         // Paper left edge offset
  },

  "timing": {
    "motor_movement_delay_per_cm": 0.002,  // Movement simulation speed
    "tool_action_delay": 0.02,             // Tool up/down delay
    "sensor_poll_timeout": 0.01            // Sensor reading frequency
  },

  "operation_colors": {
    "mark": {                     // Lines (MARK operations)
      "pending": "#880808",       // Red - ready to mark
      "in_progress": "#FF8800",   // Orange - currently marking
      "completed": "#00AA00"      // Green - marking done
    },
    "cuts": {                     // Rows/Cuts (CUT operations)
      "pending": "#8800FF",       // Purple - ready to cut
      "in_progress": "#FF0088",   // Pink - currently cutting
      "completed": "#AA00AA"      // Purple - cutting done
    }
  },

  "visualization": {
    "line_width_marks": 3,              // Line thickness for marks
    "dash_pattern_pending": [5, 5],     // Dashed for MARK operations
    "sensor_indicator_size": 3          // Sensor marker size
  },

  "hardware_config": {
    "use_real_hardware": false,   // Toggle mock/real hardware

    "raspberry_pi": {
      "gpio_mode": "BCM",         // GPIO numbering mode
      "pistons": {                // OUTPUT pins
        "line_marker_piston": 17,
        "line_cutter_piston": 27,
        "line_motor_piston": 22,
        "row_marker_piston": 23,
        "row_cutter_piston": 24
      },
      "sensors": {                // INPUT pins (pull-up)
        "line_marker_state": 5,
        "line_cutter_state": 6,
        "line_motor_piston_sensor": 13,
        "row_marker_state": 19,
        "row_cutter_state": 26,
        "x_left_edge": 20,
        "x_right_edge": 21,
        "y_top_edge": 16,
        "y_bottom_edge": 12
      },
      "limit_switches": {         // INPUT pins (pull-up)
        "rows_door": 25
      }
    },

    "arduino_grbl": {
      "serial_port": "/dev/ttyACM0",
      "baud_rate": 115200,
      "grbl_settings": {
        "feed_rate": 1000,        // mm/min (normal speed)
        "rapid_rate": 3000        // mm/min (fast travel)
      }
    }
  }
}
```

### Configuration Usage Rules

**CRITICAL**: ALL configuration MUST come from settings.json. NO hard-coded values allowed.

**Examples**:
- ❌ `time.sleep(0.1)` - WRONG
- ✅ `time.sleep(timing_settings.get("tool_action_delay", 0.1))` - CORRECT

- ❌ `canvas.create_line(x, y, fill="#FF0000")` - WRONG
- ✅ `canvas.create_line(x, y, fill=operation_colors["mark"]["pending"])` - CORRECT

---

## CRITICAL OPERATIONAL CONCEPTS

### 1. Motor-Tool Relationship

**LINES Operations (Horizontal lines)**:
- Motor: Y-axis (Lines Motor) moves UP/DOWN
- Tools: Line Marker, Line Cutter (move with Y motor)
- Edge Detection: X sensors (left/right) detect paper width
- Line Motor Piston: Lifts Y motor assembly ONLY during upward movement

**ROWS Operations (Vertical lines)**:
- Motor: X-axis (Rows Motor) moves LEFT/RIGHT
- Tools: Row Marker, Row Cutter (move with X motor)
- Edge Detection: Y sensors (top/bottom) detect paper height

### 2. Piston Control Pattern

**Standard Tool Operation Sequence**:
```python
# To activate tool (mark or cut):
1. Lower piston (bring assembly down)
2. Activate tool (marker/cutter down)
3. Perform operation (motor movement)
4. Deactivate tool (marker/cutter up)
5. Raise piston (return to safe position)
```

**Example - Line Marker Operation**:
```python
def line_marker_down():
    if line_marker_piston != "down":
        line_marker_piston = "down"  # Lower assembly first
    line_marker_state = "down"        # Then activate marker

def line_marker_up():
    line_marker_state = "up"          # Deactivate marker first
    if line_marker_piston != "up":
        line_marker_piston = "up"     # Then raise assembly
```

### 3. Step Execution States

**Step Status Values**:
- `pending` - Not yet executed
- `in_progress` - Currently executing
- `completed` - Successfully finished
- `failed` - Error occurred

**Execution Engine States**:
- `is_running` - Execution thread active
- `is_paused` - Paused due to safety violation
- `is_blocked` - Waiting for sensor/user input
- `block_reason` - String explaining why blocked

### 4. Canvas Operation States

**Operation State Tracking**:
```python
# Canvas tracks which operations are in what state:
line_states = {
    1: 'pending',      # Line 1 not marked yet
    2: 'in_progress',  # Line 2 currently marking
    3: 'completed'     # Line 3 already marked
}

# Colors change based on state:
# pending → in_progress → completed
# Red → Orange → Green (for marks)
# Purple → Pink → Purple (for cuts)
```

**State Transitions**:
- Detected from execution log parsing
- Regular expressions match keywords:
  - "marking line 1" → line 1 in_progress
  - "line 1 marked" → line 1 completed
  - "cutting row 2" → row 2 in_progress

---

## IMPORTANT DESIGN PATTERNS

### 1. Hardware Abstraction Pattern

**Problem**: Need to develop on non-Raspberry Pi systems
**Solution**: Dual-mode hardware interface

```python
# settings.json controls mode
"use_real_hardware": false  # Mock mode (development)
"use_real_hardware": true   # Real mode (production)

# Code works identically in both modes:
hardware.move_x(10)  # Works in mock OR real
hardware.line_marker_down()  # Works in mock OR real
```

### 2. Settings-Driven Configuration

**Problem**: Values scattered throughout code, hard to tune
**Solution**: Single source of truth (settings.json)

```python
# Load settings once at startup
settings = json.load('settings.json')

# Access settings everywhere
max_x = settings['hardware_limits']['max_x_position']
color = settings['operation_colors']['mark']['pending']
```

### 3. State Synchronization Pattern

**Problem**: Multiple displays show same hardware state
**Solution**: Periodic polling with state cache

```python
# Hardware status panel updates every 200ms:
def update_hardware_status():
    # Read from mock_hardware
    x_pos = get_current_x()
    line_marker = get_line_marker_state()

    # Update display
    self.x_label.config(text=f"X: {x_pos:.2f}cm")
    self.marker_label.config(
        text=line_marker.upper(),
        bg=color_for_state(line_marker)
    )
```

### 4. Safety Check Injection

**Problem**: Safety checks needed throughout execution
**Solution**: Pre-execution safety check before each step

```python
def execute_step(step):
    # ALWAYS check safety first
    safety_system.check_y_axis_movement_safety()
    safety_system.check_line_tools_not_down()

    # Only if safe, execute step
    operation = step['operation']
    if operation == 'move_y':
        move_y(step['parameters']['position'])
```

### 5. Sensor Buffer Management

**Problem**: Sensors triggered during safety pause should be ignored
**Solution**: Flush sensor buffers on resume

```python
# When safety violation occurs:
execution_paused = True

# Any sensor triggers during pause are ignored in wait loops:
if execution_engine.is_paused:
    print("Sensor trigger ignored - execution paused")
    sensor_events['x_left'].clear()
    continue

# When resuming:
flush_all_sensor_buffers()  # Clear all pending triggers
execution_paused = False
```

---

## FILE FORMATS

### CSV Program Format

```csv
id,lines_num,rows_num,rows_per_page,page_side,cut_method,lines,cuts
1,10,5,2,RTL,rows_first,0-10,0-5
```

**Fields**:
- `id`: Program identifier
- `lines_num`: Total horizontal lines to mark
- `rows_num`: Total vertical rows to mark
- `rows_per_page`: Rows per page (used for page calculations)
- `page_side`: "RTL" (right-to-left) or "LTR" (left-to-right)
- `cut_method`: "rows_first" or "lines_first"
- `lines`: Range of lines to execute (e.g., "0-10" or "5-8")
- `cuts`: Range of cuts to execute (e.g., "0-5")

---

## TESTING AND DEBUGGING

### Mock Mode Testing
```bash
# Run main application (mock mode by default)
python3 index.py

# Load sample_programs.csv
# Click "Start Program"
# Watch execution in GUI
```

### Hardware Test GUI
```bash
# Launch standalone hardware test interface
python3 hardware/hardware_test_gui.py

# Features:
# - Manual motor movement
# - Piston control buttons
# - Live sensor monitoring
# - Emergency stop
```

### Real Hardware Mode
```bash
# 1. Edit settings.json
"use_real_hardware": true

# 2. Connect Raspberry Pi + Arduino
# 3. Run application
python3 index.py
```

---

## CRITICAL RULES FOR AI AGENTS

### 1. NEVER Hard-Code Values
- ❌ `time.sleep(0.1)`
- ✅ `time.sleep(timing_settings.get("tool_action_delay", 0.1))`

### 2. ALWAYS Check settings.json First
Before adding ANY new constant, check if it should be in settings.json.

### 3. Respect Hardware Abstraction
- Use mock_hardware.py functions, NOT direct GPIO access
- Let hardware_interface.py decide mock vs real

### 4. Follow Naming Conventions
- Pistons: `*_piston` (control)
- Sensors: `*_state` or `*_sensor` (reading)
- Positions: Always in centimeters (cm)
- Switches: `*_limit_switch`

### 5. Maintain 1:1 Hardware Mapping
Every variable in mock_hardware.py MUST appear in Hardware Status Panel.
No orphaned variables, no missing displays.

### 6. Safety First
- NEVER skip safety checks
- ALWAYS verify safety before motor movements
- Row marker down = Y-axis CANNOT move

### 7. Thread Safety
- GUI updates: Main thread only
- Hardware operations: Execution thread only
- Use locks for shared state

### 8. State Consistency
- Update ALL displays when state changes
- Canvas, status panel, operations panel must sync
- Use polling (200ms) for state updates

### 9. Git Workflow
After EVERY code change:
```bash
git add <files>
git commit -m "descriptive message"
git push
```

### 10. Documentation
When adding new features:
- Update this document if architecture changes
- Update settings.json if new config added
- Update hardware README if hardware changes

---

## COMMON OPERATIONS REFERENCE

### Adding a New Piston/Sensor

1. **Add to settings.json**:
```json
"raspberry_pi": {
  "pistons": {
    "new_piston_name": 30  // GPIO pin
  },
  "sensors": {
    "new_sensor_name": 31  // GPIO pin
  }
}
```

2. **Add to mock_hardware.py**:
```python
# Global variable
new_piston = "up"
new_sensor_state = "up"

# Reset function
def reset_hardware():
    global new_piston, new_sensor_state
    new_piston = "up"
    new_sensor_state = "up"

# Control functions
def new_piston_down():
    global new_piston
    new_piston = "down"

def new_piston_up():
    global new_piston
    new_piston = "up"

# Getter functions
def get_new_piston_state():
    return new_piston

def get_new_sensor_state():
    return new_sensor_state
```

3. **Add to hardware_status_panel.py**:
```python
# Import
from mock_hardware import get_new_piston_state, get_new_sensor_state

# Update display
new_piston_state = get_new_piston_state().upper()
self._update_widget('new_piston_label', new_piston_state, color)
```

4. **Add to hardware/raspberry_pi_gpio.py**:
Already automatically handled via settings.json config!

### Adding a New Step Type

1. **Define in step_generator.py**:
```python
steps.append({
    'operation': 'new_operation',
    'parameters': {'param1': value1},
    'description': 'Human readable description'
})
```

2. **Handle in execution_engine.py**:
```python
elif operation == 'new_operation':
    param1 = parameters.get('param1')
    # Execute operation
    result = mock_hardware.new_function(param1)
```

3. **Implement in mock_hardware.py**:
```python
def new_function(param1):
    print(f"MOCK: new_function({param1})")
    # Simulation logic
    time.sleep(timing_settings.get("delay_key", 0.1))
    return True
```

### Adding a New Safety Check

1. **Add to safety_system.py**:
```python
def check_new_safety_condition(self):
    if not self.safety_enabled:
        return True

    # Check condition
    if dangerous_condition():
        raise SafetyViolation(
            "Safety message explaining issue",
            safety_code="SAFETY_CODE_NAME"
        )

    return True
```

2. **Call in execution_engine.py**:
```python
def _execute_step(self, step):
    # Add to safety checks
    self.safety_system.check_new_safety_condition()

    # Execute step
    ...
```

---

## TROUBLESHOOTING GUIDE

### Issue: "No module named 'hardware'"
**Solution**: Run from project root, not from subdirectory
```bash
# Wrong:
cd hardware && python3 test_motor_movement.py

# Correct:
python3 hardware/test_motor_movement.py
```

### Issue: Mock hardware not updating in GUI
**Solution**: Check 200ms update interval in hardware_status_panel.py
```python
# Ensure update_interval_ms is set in settings.json
"hardware_monitor": {
  "update_interval_ms": 200
}
```

### Issue: Safety violations not pausing execution
**Solution**: Verify safety_enabled is True
```python
safety_system = SafetySystem()
safety_system.enable_safety()  # Must call this
```

### Issue: Sensor triggers ignored
**Solution**: Check if execution is paused or blocked
```python
# Sensors ignored when paused
if execution_engine.is_paused:
    print("Cannot trigger sensor - execution paused")
```

### Issue: Colors not matching WORK OPERATIONS STATUS
**Solution**: Verify settings.json operation_colors section
All colors must match exactly between canvas and status panel.

---

## SUMMARY FOR AI AGENTS

**This is a CNC scratch card marking/cutting machine control system with:**

1. **Dual-mode operation**: Mock (development) and Real (production)
2. **Complete hardware abstraction**: raspberry_pi_gpio.py + arduino_grbl.py
3. **Safety-first architecture**: Prevents dangerous operations
4. **Settings-driven**: NO hard-coded values, everything in settings.json
5. **Real-time GUI**: Live hardware monitoring, canvas visualization
6. **Step-based execution**: High-level programs → low-level steps
7. **Thread-safe design**: Separate GUI, execution, and safety threads
8. **Comprehensive testing**: Mock mode + hardware test GUI

**When working on this system:**
- Read settings.json FIRST
- Use mock_hardware.py functions
- Check safety implications
- Update ALL related displays
- Test in mock mode before real hardware
- Commit and push after each change

**The system is ready for real hardware integration** - just flip `use_real_hardware` to `true` in settings.json when Raspberry Pi and Arduino are connected.

---

*Last Updated: [Current Date]*
*Version: 1.0*
*For questions or clarifications, refer to code comments and inline documentation.*

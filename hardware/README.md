# Hardware Connection Module

Real hardware interface for CNC Scratch Desk control system.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Main Application                      │
│                 (mock_hardware.py)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              hardware_interface.py                      │
│         (Unified Hardware Interface)                    │
│  Switches between Mock and Real Hardware                │
└─────────────┬────────────────────┬──────────────────────┘
              │                    │
              ▼                    ▼
┌─────────────────────┐  ┌─────────────────────────────┐
│ raspberry_pi_gpio.py│  │   arduino_grbl.py           │
│                     │  │                             │
│ - Pistons (OUTPUT)  │  │ - Motor Control (G-code)    │
│ - Sensors (INPUT)   │  │ - X/Y Motors                │
│ - Limit Switches    │  │ - Position Tracking         │
└──────────┬──────────┘  └──────────┬──────────────────┘
           │                        │
           ▼                        ▼
    ┌─────────────┐          ┌──────────────┐
    │ Raspberry Pi│          │Arduino + GRBL│
    │    GPIO     │          │   (Serial)   │
    └─────────────┘          └──────────────┘
```

## Hardware Configuration

All hardware settings are configured in `settings.json`:

### GPIO Pin Mapping (Raspberry Pi)

**Pistons (Output Pins):**
- `line_marker_piston`: GPIO 17
- `line_cutter_piston`: GPIO 27
- `line_motor_piston`: GPIO 22
- `row_marker_piston`: GPIO 23
- `row_cutter_piston`: GPIO 24

**Sensors (Input Pins with Pull-up):**
- `line_marker_state`: GPIO 5
- `line_cutter_state`: GPIO 6
- `line_motor_piston_sensor`: GPIO 13
- `row_marker_state`: GPIO 19
- `row_cutter_state`: GPIO 26
- `x_left_edge`: GPIO 20
- `x_right_edge`: GPIO 21
- `y_top_edge`: GPIO 16
- `y_bottom_edge`: GPIO 12

**Limit Switches (Input Pins with Pull-up):**
- `rows_door`: GPIO 25

### Arduino GRBL Configuration

- **Serial Port**: `/dev/ttyACM0` (Linux/Raspberry Pi)
- **Baud Rate**: 115200
- **Units**: Millimeters (converted from cm internally)
- **Feed Rate**: 1000 mm/min
- **Rapid Rate**: 3000 mm/min

## Usage

### 1. Enable Real Hardware

Edit `settings.json`:

```json
{
  "hardware_config": {
    "use_real_hardware": true
  }
}
```

### 2. Basic Usage

```python
from hardware.hardware_interface import HardwareInterface

# Create interface
hardware = HardwareInterface()

# Initialize all hardware
if hardware.initialize():
    # Move motors
    hardware.move_to(10, 10)  # Move to (10cm, 10cm)

    # Control pistons
    hardware.line_marker_piston_down()
    hardware.line_marker_piston_up()

    # Read sensors
    sensors = hardware.read_edge_sensors()
    print(sensors)

    # Cleanup
    hardware.shutdown()
```

### 3. Test Individual Components

**Test GPIO (Pistons & Sensors):**
```bash
cd hardware
python3 test_gpio.py
```

**Test Motor Movement:**
```bash
cd hardware
python3 test_motor_movement.py
```

**Test Individual Modules:**
```bash
# Test GPIO only
python3 -m hardware.raspberry_pi_gpio

# Test GRBL only
python3 -m hardware.arduino_grbl

# Test unified interface
python3 -m hardware.hardware_interface
```

## Pin Configuration Reference

### Piston Control (Active HIGH)
- **HIGH (3.3V)** = Piston extended (DOWN position)
- **LOW (0V)** = Piston retracted (UP position)

### Sensor Reading (Pull-up enabled)
- **LOW (0V)** = Sensor triggered (detected)
- **HIGH (3.3V)** = Sensor not triggered (normal state)

### Limit Switch Reading (Pull-up enabled)
- **LOW (0V)** = Switch activated (pressed/closed)
- **HIGH (3.3V)** = Switch inactive (open)

## G-code Commands Used

The Arduino GRBL interface uses standard G-code:

- `G90` - Absolute positioning mode
- `G21` - Millimeter units
- `$H` - Home machine
- `G0 X__ Y__` - Rapid positioning
- `G1 X__ Y__ F__` - Linear move with feed rate
- `G92 X0 Y0` - Set current position as origin
- `?` - Status query
- `!` - Emergency stop (feed hold)
- `~` - Resume operation
- `Ctrl-X` - Soft reset

## Safety Features

1. **Emergency Stop**: `hardware.emergency_stop()`
2. **Graceful Shutdown**: `hardware.shutdown()` returns all pistons to safe position
3. **Connection Timeout**: Commands timeout if hardware doesn't respond
4. **Mock Mode**: Automatically falls back to mock if hardware unavailable

## Troubleshooting

### GPIO Issues

**Error: "Permission denied" when accessing GPIO**
- Solution: Run with sudo or add user to gpio group:
  ```bash
  sudo usermod -a -G gpio $USER
  ```

**Error: "RPi.GPIO not available"**
- Solution: Install RPi.GPIO library:
  ```bash
  pip3 install RPi.GPIO
  ```

### GRBL Issues

**Error: "Serial port not found"**
- Solution: Check Arduino connection and update `serial_port` in settings.json:
  ```bash
  ls /dev/tty*  # List available ports
  ```

**Error: "No response from GRBL"**
- Check Arduino is powered and GRBL firmware is uploaded
- Verify baud rate matches GRBL configuration (usually 115200)
- Try resetting Arduino

**Error: "Homing failed"**
- GRBL homing may not be configured
- Check limit switches are connected
- Disable homing in GRBL settings if not needed

## Customizing Pin Configuration

To change GPIO pins, edit `settings.json`:

```json
{
  "hardware_config": {
    "raspberry_pi": {
      "gpio_mode": "BCM",
      "pistons": {
        "line_marker_piston": 17,  // Change pin number here
        // ... other pistons
      }
    }
  }
}
```

## Integration with Main Application

The main application (`mock_hardware.py`) should be updated to use the hardware interface:

```python
# At startup
from hardware.hardware_interface import HardwareInterface

hardware = HardwareInterface()
if hardware.initialize():
    print("Real hardware connected")
else:
    print("Using mock hardware")

# In movement functions
def move_x(position):
    if hardware.use_real_hardware:
        return hardware.move_x(position)
    else:
        # Use existing mock implementation
        pass
```

## Dependencies

- **Python 3.7+**
- **RPi.GPIO** (for Raspberry Pi GPIO)
- **pyserial** (for Arduino serial communication)

Install dependencies:
```bash
pip3 install RPi.GPIO pyserial
```

## Notes

- All positions are in **centimeters** (automatically converted to mm for GRBL)
- GPIO pins use **BCM numbering** by default
- Piston control is **inverted** (HIGH = extended, LOW = retracted)
- Sensor inputs use **pull-up resistors** (triggered = LOW)
- Thread-safe serial communication with command locks

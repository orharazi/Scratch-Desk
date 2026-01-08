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
│ - RS485 Sensors     │  │ - X/Y Motors                │
│ - Direct GPIO       │  │ - Position Tracking         │
│ - Limit Switches    │  │                             │
└──────────┬──────────┘  └──────────┬──────────────────┘
           │                        │
           ▼                        ▼
    ┌─────────────┐          ┌──────────────┐
    │ Raspberry Pi│          │Arduino + GRBL│
    │    GPIO     │          │   (Serial)   │
    │  + RS485    │          │              │
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

**RS485 Sensors (via Modbus RTU):**
12 piston position sensors connected via RS485 Modbus:
- Line tools: marker (up/down), cutter (up/down), motor left/right (up/down)
- Row tools: marker (up/down), cutter (up/down)
- Serial Port: `/dev/ttyAMA0` (default)
- Protocol: Modbus RTU
- Baud Rate: 9600 (default)
- Each sensor has a unique Modbus slave address (1-12)

**Direct GPIO Sensors (Input Pins with Pull-down):**
- `x_left_edge`: GPIO 4
- `x_right_edge`: GPIO 17
- `y_top_edge`: GPIO 7
- `y_bottom_edge`: GPIO 8

**Limit Switches:**
- Door switch: Via Arduino GRBL (moved from Raspberry Pi GPIO)

### RS485 Modbus Configuration

- **Serial Port**: `/dev/ttyAMA0` (Raspberry Pi UART)
- **Baud Rate**: 9600
- **Protocol**: Modbus RTU
- **Data Format**: 8N1 (8 data bits, no parity, 1 stop bit)
- **Timeout**: 1.0 second
- **Sensor Addresses**: Configurable in settings.json (1-12 by default)

### Arduino GRBL Configuration

- **Serial Port**: `/dev/ttyACM0` or `/dev/ttyUSB0` (Linux/Raspberry Pi)
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

**Test RS485 Sensors:**
```bash
python3 tests/test_rs485_sensors.py
```

**Test RS485 Sensors with GUI:**
```bash
python3 tests/test_mux_sensor_gui.py
```

**Test Motor Movement:**
```bash
cd hardware
python3 test_motor_movement.py
```

**Test Individual Modules:**
```bash
# Test GPIO + RS485
python3 -m hardware.implementations.real.raspberry_pi.raspberry_pi_gpio

# Test GRBL only
python3 -m hardware.implementations.real.arduino_grbl.arduino_grbl

# Test RS485 interface only
python3 -m hardware.implementations.real.raspberry_pi.rs485_modbus
```

## Pin Configuration Reference

### Piston Control (Active HIGH)
- **HIGH (3.3V)** = Piston extended (DOWN position)
- **LOW (0V)** = Piston retracted (UP position)

### RS485 Sensor Reading (Modbus RTU)
- **Modbus Read Discrete Inputs** (Function Code 02)
- **TRUE** = Sensor triggered (HIGH signal)
- **FALSE** = Sensor not triggered (LOW signal)
- Each sensor has unique Modbus slave address (1-247)
- Register address: 0 (configurable)

### Direct GPIO Sensor Reading (Pull-down enabled)
- **HIGH (3.3V)** = Sensor triggered (detected)
- **LOW (0V)** = Sensor not triggered (normal state)

### Limit Switch Reading (via Arduino GRBL)
- Queried through GRBL status commands

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

### RS485 Issues

**Error: "pymodbus library not available"**
- Solution: Install pymodbus library:
  ```bash
  pip3 install pymodbus
  ```

**Error: "Failed to connect to RS485"**
- Check RS485 adapter is connected to correct serial port
- Verify serial port in settings.json (`/dev/ttyAMA0` or `/dev/ttyUSB0`)
- Check permissions: `ls -l /dev/ttyAMA0`
- Add user to dialout group: `sudo usermod -a -G dialout $USER`

**Error: "Modbus read error"**
- Verify sensor Modbus slave addresses match settings.json
- Check RS485 bus wiring (A, B, GND)
- Verify baud rate matches sensor configuration (default 9600)
- Check RS485 termination resistors if bus is long

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

## Customizing Configuration

To change GPIO pins or RS485 settings, edit `settings.json`:

```json
{
  "hardware_config": {
    "raspberry_pi": {
      "gpio_mode": "BCM",
      "pistons": {
        "line_marker_piston": 11,  // Change pin number here
        // ... other pistons
      },
      "rs485": {
        "enabled": true,
        "serial_port": "/dev/ttyAMA0",  // Change serial port
        "baudrate": 9600,               // Change baud rate
        "sensor_addresses": {
          "line_marker_up_sensor": 1,   // Change Modbus addresses
          // ... other sensors
        }
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
- **pymodbus** (for RS485 Modbus RTU communication)

Install dependencies:
```bash
pip3 install RPi.GPIO pyserial pymodbus
```

## Notes

- All positions are in **centimeters** (automatically converted to mm for GRBL)
- GPIO pins use **BCM numbering** by default
- Piston control is **inverted** (HIGH = extended, LOW = retracted)
- RS485 sensors use **Modbus RTU protocol** with unique slave addresses
- Direct GPIO sensors use **pull-down resistors** (triggered = HIGH)
- Thread-safe serial communication with command locks for both GRBL and RS485

# Configuration Guide

**Last Updated:** January 15, 2026
**Version:** 1.0

This guide documents all configuration options available in `config/settings.json` for the Scratch Desk system.

---

## Table of Contents

1. [Timing Configuration](#timing-configuration)
2. [Logging Configuration](#logging-configuration)
3. [Hardware Configuration](#hardware-configuration)
   - [Raspberry Pi GPIO](#raspberry-pi-gpio)
   - [RS485 Modbus](#rs485-modbus)
   - [Arduino GRBL](#arduino-grbl)
4. [Performance Tuning](#performance-tuning)
5. [Troubleshooting](#troubleshooting)

---

## Timing Configuration

All timing values are located under the `timing` section in `settings.json`. Values are in seconds unless otherwise specified.

### GPIO and General Timing

| Parameter | Type | Default | Description | Valid Range |
|-----------|------|---------|-------------|-------------|
| `piston_gpio_settling_delay` | float | 0.05 | Delay after GPIO state change for hardware settling | 0.01 - 0.2 |
| `gpio_cleanup_delay` | float | 0.1 | Delay during GPIO cleanup operations | 0.05 - 0.5 |
| `gpio_busy_recovery_delay` | float | 0.05 | Recovery delay when GPIO is busy | 0.01 - 0.2 |
| `gpio_debounce_samples` | int | 3 | Number of samples for GPIO debouncing | 1 - 10 |
| `gpio_debounce_delay_ms` | int | 1 | Delay between GPIO debounce samples (milliseconds) | 0 - 10 |
| `gpio_test_read_delay_ms` | int | 1 | Delay during GPIO test reads (milliseconds) | 0 - 10 |

**Usage Notes:**
- `piston_gpio_settling_delay`: Increase if pistons show erratic behavior
- `gpio_debounce_samples`: Reduce for faster response, increase for noise immunity
- `gpio_debounce_delay_ms`: Keep low (1-2ms) for responsive sensor reading

### Sensor Polling Timing

| Parameter | Type | Default | Description | Valid Range |
|-----------|------|---------|-------------|-------------|
| `switch_polling_interval_ms` | int | 10 | Main sensor polling interval (milliseconds) | 5 - 100 |
| `polling_thread_join_timeout` | float | 1.0 | Timeout for polling thread shutdown | 0.5 - 5.0 |
| `polling_status_update_frequency` | int | 1000 | Status update every N polls | 100 - 10000 |
| `polling_error_recovery_delay` | float | 0.1 | Delay after polling error before retry | 0.05 - 1.0 |
| `limit_switch_test_read_delay_ms` | int | 1 | Delay for limit switch test reads (milliseconds) | 0 - 10 |

**Usage Notes:**
- `switch_polling_interval_ms`: **Critical for trigger detection!**
  - 10ms = 100 Hz polling, detects 50ms triggers reliably
  - 25ms = 40 Hz polling, may miss short triggers
  - Lower values = higher CPU usage but better responsiveness

### RS485 Communication Timing

| Parameter | Type | Default | Description | Valid Range |
|-----------|------|---------|-------------|-------------|
| `rs485_retry_delay` | float | 0.01 | Delay between RS485 retry attempts | 0.005 - 0.1 |

**Usage Notes:**
- `rs485_retry_delay`: Keep low for fast retries on transient errors

### GRBL Timing

| Parameter | Type | Default | Description | Valid Range |
|-----------|------|---------|-------------|-------------|
| `grbl_initialization_delay` | float | 2.0 | Delay after GRBL connection for initialization | 1.0 - 5.0 |
| `grbl_serial_poll_delay` | float | 0.01 | Delay between GRBL serial reads | 0.005 - 0.1 |
| `grbl_reset_delay` | float | 2.0 | Delay after GRBL reset command | 1.0 - 5.0 |

**Usage Notes:**
- `grbl_initialization_delay`: Increase if GRBL commands fail after connection
- `grbl_serial_poll_delay`: Keep low for responsive command processing

### Legacy Timing (Deprecated)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `motor_movement_delay_per_cm` | float | 0.002 | Delay per cm of motor movement (legacy) |
| `max_motor_movement_delay` | float | 0.1 | Maximum motor movement delay (legacy) |
| `tool_action_delay` | float | 0.02 | Tool action delay (legacy) |
| `sensor_poll_timeout` | float | 0.01 | Sensor poll timeout (legacy) |
| `row_marker_stable_delay` | float | 0.05 | Row marker stabilization delay (legacy) |
| `safety_check_interval` | float | 0.02 | Safety check interval (legacy) |
| `execution_loop_delay` | float | 0.01 | Execution loop delay (legacy) |
| `transition_monitor_interval` | float | 0.1 | Transition monitor interval (legacy) |
| `thread_join_timeout_execution` | float | 2.0 | Execution thread join timeout (legacy) |
| `thread_join_timeout_safety` | float | 1.0 | Safety thread join timeout (legacy) |

---

## Logging Configuration

Located under the `logging` section in `settings.json`.

### Queue Configuration

| Parameter | Type | Default | Description | Valid Range |
|-----------|------|---------|-------------|-------------|
| `queue_timeout_seconds` | float | 0.1 | Timeout for log queue operations | 0.05 - 1.0 |

**Usage Notes:**
- Controls how long the logger waits for new messages in the queue
- Lower values = more responsive shutdown, higher CPU usage
- Higher values = lower CPU usage, slower shutdown

### Other Logging Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | string | "INFO" | Global log level: DEBUG, INFO, WARNING, ERROR |
| `show_timestamps` | bool | true | Show timestamps in log output |
| `show_thread_names` | bool | false | Show thread names in log output |
| `console_output` | bool | true | Enable console output |
| `file_output` | bool | false | Enable file logging |
| `file_path` | string | "logs/scratch_desk.log" | Log file path |
| `use_colors` | bool | true | Use ANSI colors in console |
| `use_icons` | bool | true | Use emoji icons in console |

---

## Hardware Configuration

### Raspberry Pi GPIO

Located under `hardware_config.raspberry_pi` in `settings.json`.

| Parameter | Type | Default | Description | Valid Range |
|-----------|------|---------|-------------|-------------|
| `gpio_mode` | string | "BCM" | GPIO numbering mode: BCM or BOARD | "BCM", "BOARD" |
| `debounce_count` | int | 2 | Number of consecutive identical reads for confirmation | 1 - 5 |

**Usage Notes:**
- `debounce_count`: **Critical for trigger detection!**
  - 2 = 20ms confirmation time with 10ms polling (recommended)
  - 3 = 30ms confirmation time with 10ms polling
  - Lower values = faster response, higher noise sensitivity

### RS485 Modbus

Located under `hardware_config.raspberry_pi.rs485` in `settings.json`.

#### Connection Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | true | Enable RS485 interface |
| `serial_port` | string | "/dev/ttyUSB0" | Serial port for RS485 adapter |
| `baudrate` | int | 9600 | Communication speed (bps) |
| `bytesize` | int | 8 | Data bits |
| `parity` | string | "N" | Parity: N (None), E (Even), O (Odd) |
| `stopbits` | int | 1 | Stop bits |
| `timeout` | float | 1.0 | Read timeout (seconds) |
| `protocol` | string | "modbus_rtu" | Protocol type |

#### Modbus Settings

| Parameter | Type | Default | Description | Valid Range |
|-----------|------|---------|-------------|-------------|
| `modbus_device_id` | int | 1 | Modbus slave/device ID | 1 - 247 |
| `modbus_function_code` | int | 3 | Modbus function code (03 = Read Holding Registers) | 1 - 255 |
| `input_count` | int | 32 | Total number of digital inputs | 1 - 64 |
| `register_address_low` | int | 192 | Starting register address (0x00C0 for N4DIH32) | 0 - 65535 |
| `bulk_read_register_count` | int | 2 | Number of registers to read in bulk | 1 - 10 |

#### Performance Settings

| Parameter | Type | Default | Description | Valid Range |
|-----------|------|---------|-------------|-------------|
| `bulk_read_enabled` | bool | true | Enable bulk read optimization | - |
| `bulk_read_cache_age_ms` | int | 10 | Max age of bulk cache (milliseconds) | 5 - 100 |
| `default_retry_count` | int | 2 | Number of retries on read failure | 0 - 5 |

**Usage Notes:**
- `bulk_read_cache_age_ms`: **Critical for trigger detection!**
  - 10ms = fresh data every 10ms, matches polling rate (recommended)
  - Higher values = reduced RS485 bus traffic, stale data risk
  - Should match or be less than `switch_polling_interval_ms`

#### Sensor Addresses

Located under `hardware_config.raspberry_pi.rs485.sensor_addresses`.

Each sensor is mapped to an input index (0-31) on the N4DIH32 module:

```json
"sensor_addresses": {
  "line_marker_up_sensor": 14,
  "line_marker_down_sensor": 15,
  "line_cutter_up_sensor": 2,
  "line_cutter_down_sensor": 3,
  "row_cutter_up_sensor": 4,
  "row_cutter_down_sensor": 5,
  "row_marker_up_sensor": 6,
  "row_marker_down_sensor": 7,
  "line_motor_left_up_sensor": 8,
  "line_motor_left_down_sensor": 9,
  "line_motor_right_up_sensor": 10,
  "line_motor_right_down_sensor": 11
}
```

**Mapping to N4DIH32 Hardware:**
- Input 0-15 → Register 0x00C0 (192), bits 0-15
- Input 16-31 → Register 0x00C1 (193), bits 0-15
- Input 14 → Register 0x00C0, bit 14 (X14 terminal)
- Input 15 → Register 0x00C0, bit 15 (X15 terminal)

### Arduino GRBL

Located under `hardware_config.arduino_grbl` in `settings.json`.

#### Connection Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `serial_port` | string | "/dev/ttyUSB0" | Serial port for Arduino |
| `baud_rate` | int | 115200 | GRBL baud rate |
| `connection_timeout` | float | 5.0 | Connection timeout (seconds) |
| `command_timeout` | float | 10.0 | Command timeout (seconds) |

#### Operation Timeouts

| Parameter | Type | Default | Description | Valid Range |
|-----------|------|---------|-------------|-------------|
| `homing_timeout` | float | 30.0 | Timeout for homing operation (seconds) | 10.0 - 120.0 |
| `door_switch_read_timeout` | float | 1.0 | Timeout for door switch reads (seconds) | 0.5 - 5.0 |

**Usage Notes:**
- `homing_timeout`: Increase if homing fails on large machines
- `door_switch_read_timeout`: Adjust based on sensor response time

#### GRBL Settings

Located under `hardware_config.arduino_grbl.grbl_settings`.

| Parameter | Type | Default | Description | Valid Values |
|-----------|------|---------|-------------|--------------|
| `units` | string | "mm" | Coordinate units | "mm", "inch" |
| `positioning_mode` | string | "G90" | Positioning mode | "G90" (absolute), "G91" (relative) |
| `feed_rate` | int | 1000 | Feed rate (units/min) | 100 - 10000 |
| `rapid_rate` | int | 3000 | Rapid movement rate (units/min) | 1000 - 30000 |
| `acceleration` | int | 50 | Acceleration (units/sec²) | 10 - 500 |

**Usage Notes:**
- `positioning_mode`: G90 (absolute) is recommended for safety
- `feed_rate`: Adjust based on machine capabilities
- `acceleration`: Higher values = faster movements, more stress on hardware

---

## Performance Tuning

### For Fast Trigger Detection (50ms pulses)

Optimize these parameters:

```json
{
  "timing": {
    "switch_polling_interval_ms": 10,
    "rs485_retry_delay": 0.01
  },
  "hardware_config": {
    "raspberry_pi": {
      "debounce_count": 2,
      "rs485": {
        "bulk_read_enabled": true,
        "bulk_read_cache_age_ms": 10,
        "default_retry_count": 2
      }
    }
  }
}
```

**Rationale:**
- 10ms polling = 100 Hz = 5 polls during 50ms trigger
- 2-sample debounce = 20ms confirmation
- 10ms cache age = fresh data on every poll
- Result: 20-30ms detection time for 50ms triggers

### For Reduced CPU Usage

If trigger speed is not critical, optimize for lower CPU usage:

```json
{
  "timing": {
    "switch_polling_interval_ms": 50,
    "rs485_retry_delay": 0.05
  },
  "hardware_config": {
    "raspberry_pi": {
      "debounce_count": 3,
      "rs485": {
        "bulk_read_enabled": true,
        "bulk_read_cache_age_ms": 50,
        "default_retry_count": 1
      }
    }
  }
}
```

**Trade-offs:**
- Slower sensor response (150-200ms)
- Reduced CPU usage (~80% reduction)
- May miss very short triggers (<100ms)

### For Noisy Environments

If experiencing false triggers from electrical noise:

```json
{
  "timing": {
    "gpio_debounce_samples": 5,
    "gpio_debounce_delay_ms": 2
  },
  "hardware_config": {
    "raspberry_pi": {
      "debounce_count": 3,
      "rs485": {
        "default_retry_count": 3
      }
    }
  }
}
```

**Trade-offs:**
- More robust noise immunity
- Slower response time (~50ms added latency)
- Higher CPU usage for debouncing

---

## Troubleshooting

### Sensors Not Responding

**Symptoms:** Sensor triggers not detected or delayed

**Check:**
1. `switch_polling_interval_ms` - Should be ≤ 10ms for fast response
2. `bulk_read_cache_age_ms` - Should match polling interval
3. `debounce_count` - Try reducing to 1 for testing
4. RS485 connection and wiring

**Solution:**
```json
{
  "timing": {
    "switch_polling_interval_ms": 10
  },
  "hardware_config": {
    "raspberry_pi": {
      "debounce_count": 1,
      "rs485": {
        "bulk_read_cache_age_ms": 10
      }
    }
  }
}
```

### False Triggers

**Symptoms:** Sensors triggering without physical activation

**Check:**
1. `debounce_count` - Increase to require more consistent reads
2. `gpio_debounce_samples` - Increase for GPIO sensors
3. Hardware grounding and shielding
4. Piston interference (EMI)

**Solution:**
```json
{
  "timing": {
    "gpio_debounce_samples": 5,
    "gpio_debounce_delay_ms": 2
  },
  "hardware_config": {
    "raspberry_pi": {
      "debounce_count": 3
    }
  }
}
```

### RS485 Communication Errors

**Symptoms:** "Modbus exception" or "read error" in logs

**Check:**
1. Serial port settings match hardware (baudrate, parity, stopbits)
2. `modbus_device_id` matches DIP switch configuration
3. RS485 adapter power and connections
4. `default_retry_count` - Increase for unstable connections

**Solution:**
```json
{
  "hardware_config": {
    "raspberry_pi": {
      "rs485": {
        "serial_port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "parity": "N",
        "stopbits": 1,
        "timeout": 2.0,
        "default_retry_count": 3
      }
    }
  }
}
```

### GRBL Connection Issues

**Symptoms:** GRBL commands fail or timeout

**Check:**
1. `grbl_initialization_delay` - Increase if commands fail after connect
2. `connection_timeout` - Increase for slow USB connections
3. Serial port permissions (`sudo usermod -a -G dialout $USER`)
4. USB cable quality and length

**Solution:**
```json
{
  "timing": {
    "grbl_initialization_delay": 3,
    "grbl_serial_poll_delay": 0.02
  },
  "hardware_config": {
    "arduino_grbl": {
      "connection_timeout": 10.0,
      "command_timeout": 15.0,
      "homing_timeout": 60.0
    }
  }
}
```

### High CPU Usage

**Symptoms:** Raspberry Pi running hot, system sluggish

**Check:**
1. `switch_polling_interval_ms` - Increase to reduce polling frequency
2. `bulk_read_cache_age_ms` - Increase to reduce RS485 traffic
3. `logging.level` - Set to WARNING to reduce log processing

**Solution:**
```json
{
  "timing": {
    "switch_polling_interval_ms": 50
  },
  "hardware_config": {
    "raspberry_pi": {
      "rs485": {
        "bulk_read_cache_age_ms": 50
      }
    }
  },
  "logging": {
    "level": "WARNING"
  }
}
```

---

## Configuration Best Practices

1. **Start with defaults** - Only change values when you have a specific problem
2. **Change one parameter at a time** - Test after each change
3. **Document your changes** - Add comments in settings.json (use separate docs)
4. **Test thoroughly** - Verify sensor response and system stability
5. **Monitor logs** - Watch for errors and warnings after configuration changes
6. **Keep backups** - Save working configurations before experimenting

---

## Related Documentation

- [RS485 Optimization for 50ms Triggers](RS485_OPTIMIZATION_50MS_TRIGGERS.md)
- [Hardware README](../hardware/README.md)
- [GPIO Pin Configuration](CLAUDE.md)

---

**Questions or Issues?**

If you encounter configuration issues not covered in this guide, check:
1. Application logs for specific error messages
2. Hardware connection and wiring
3. System resources (CPU, memory)
4. USB/serial device enumeration (`ls -l /dev/tty*`)

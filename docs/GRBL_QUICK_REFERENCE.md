# GRBL Quick Reference Guide

Fast lookup for common GRBL commands and operations.

## Quick Command Index

### Essential Commands
| Command | Action | Example |
|---------|--------|---------|
| `$H` | Home machine | `$H` |
| `$X` | Unlock/clear alarm | `$X` |
| `?` | Get status | `?` |
| `!` | Emergency stop (feed hold) | `!` |
| `~` | Resume | `~` |
| `Ctrl-X` | Soft reset | `0x18` |

### Basic Movement
| Command | Action | Example |
|---------|--------|---------|
| `G0 X__ Y__` | Rapid move | `G0 X50 Y35` |
| `G1 X__ Y__ F__` | Linear move with feed | `G1 X50 Y35 F1000` |
| `G90` | Absolute positioning | `G90` |
| `G91` | Incremental positioning | `G91` |

### Jogging (Manual Control)
| Command | Action |
|---------|--------|
| `$J=G91 X10 F500` | Jog X+ by 10mm |
| `$J=G91 X-10 F500` | Jog X- by 10mm |
| `$J=G91 Y10 F500` | Jog Y+ by 10mm |
| `$J=G91 Y-10 F500` | Jog Y- by 10mm |
| `0x85` | Cancel jog |

### Work Coordinate Setup
| Command | Action | Example |
|---------|--------|---------|
| `G10 L20 P1 X0 Y0` | Zero current position | `G10 L20 P1 X0 Y0` |
| `G92 X0 Y0` | Temporary zero | `G92 X0 Y0` |
| `G54` | Use work coordinate 1 | `G54` |
| `G55-G59` | Use work coordinate 2-6 | `G55` |

### Settings & Info
| Command | Action | Response |
|---------|--------|----------|
| `$$` | View all settings | `$0=10\n$1=25...` |
| `$#` | View offsets | `[G54:0.000,0.000,0.000]` |
| `$G` | View parser state | `[GC:G0 G54 G17...]` |
| `$I` | View version | `[VER:1.1h...]` |

## Quick Start Sequence

```gcode
$H              # Home machine
$X              # Unlock if needed
G21             # Millimeters
G90             # Absolute positioning
G54             # Work coordinate 1
G0 X0 Y0        # Go to work zero
```

## Status Response Format

```
<Idle|MPos:0.000,0.000,0.000|WPos:0.000,0.000,0.000>
```

- **State**: `Idle`, `Run`, `Hold`, `Alarm`, `Home`, `Check`
- **MPos**: Machine position (from home)
- **WPos**: Work position (from work zero)

## Modal Groups

Commands in the same group override each other:

| Group | Commands | Default |
|-------|----------|---------|
| Motion | G0, G1, G2, G3, G80 | G0 |
| Coordinate | G54-G59 | G54 |
| Plane | G17, G18, G19 | G17 |
| Distance | G90, G91 | G90 |
| Feed Rate | G93, G94 | G94 |
| Units | G20, G21 | G21 |

## GUI Button Mappings

### Quick Access Buttons
```python
BUTTONS = {
    "Home": "$H",
    "Unlock": "$X",
    "Go to Zero": "G90 G0 X0 Y0",
    "Set Zero": "G10 L20 P1 X0 Y0",
    "Status": "?",
}
```

### Jog Buttons (1mm step)
```python
JOG = {
    "X+": "$J=G91 X1.0 F500",
    "X-": "$J=G91 X-1.0 F500",
    "Y+": "$J=G91 Y1.0 F500",
    "Y-": "$J=G91 Y-1.0 F500",
}
```

### Emergency Controls
```python
EMERGENCY = {
    "Stop": "!",           # Feed hold
    "Resume": "~",         # Cycle start
    "Reset": "\x18",       # Soft reset (Ctrl-X)
}
```

## Common Patterns

### Move to Position
```gcode
G90              # Absolute mode
G0 X50 Y35       # Rapid to position
```

### Draw Square
```gcode
G90 G0 X0 Y0           # Start at origin
G1 X50 Y0 F1000        # Draw right
G1 X50 Y50             # Draw up
G1 X0 Y50              # Draw left
G1 X0 Y0               # Draw down
```

### Draw Circle (Center at 50,50, Radius 20)
```gcode
G90 G0 X30 Y50         # Start at left edge
G2 X30 Y50 I20 J0 F500 # Draw full circle
```

### Zero at Current Position
```gcode
G10 L20 P1 X0 Y0 Z0    # Set work zero here
```

## Error Codes

Common GRBL error codes:

| Code | Meaning |
|------|---------|
| error:1 | G-code command letter repeated |
| error:2 | Bad number format |
| error:3 | Invalid $ command |
| error:9 | G-code command not supported |
| error:20 | Soft limit triggered |
| error:21 | Line overflow (too long) |

## Alarm Codes

| Code | Meaning | Solution |
|------|---------|----------|
| ALARM:1 | Hard limit | Check limit switches, `$X` to unlock |
| ALARM:2 | Soft limit | Move away from limit, `$X` to unlock |
| ALARM:3 | Reset during cycle | Normal after Ctrl-X |
| ALARM:9 | Homing not enabled | Enable `$22=1` or skip homing |

## Configuration Settings

Key settings for CNC setup:

```
$100=250.0    # X steps per mm
$101=250.0    # Y steps per mm
$110=1000.0   # X max rate mm/min
$111=1000.0   # Y max rate mm/min
$120=10.0     # X acceleration mm/sec²
$121=10.0     # Y acceleration mm/sec²
$130=200.0    # X max travel mm
$131=200.0    # Y max travel mm
$22=1         # Homing enable
```

## Troubleshooting

### Machine Won't Move
1. Check status: `?`
2. If in Alarm, unlock: `$X`
3. Check homing: `$H`
4. Verify connection: `$I`

### Position Lost
1. Home machine: `$H`
2. Set work zero: `G10 L20 P1 X0 Y0`

### Commands Ignored
1. Check state: `?`
2. If in Hold, resume: `~`
3. If in Alarm, unlock: `$X`
4. If in Check mode, reset: `Ctrl-X`

## Tips

1. **Always home first**: `$H` before any work
2. **Set work zero**: After homing, position and use `G10 L20 P1 X0 Y0`
3. **Use jogging**: For manual control, use `$J=` commands
4. **Poll status**: Send `?` every 100-250ms for position updates
5. **Emergency stop**: Keep `!` button easily accessible
6. **Soft limits**: Enable with `$20=1` to prevent crashes

## Connection Settings

- **Baud Rate**: 115200
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Flow Control**: None
- **Line Ending**: `\n` (newline)

## Python Integration Example

```python
from hardware.grbl_commands import generate_gcode, generate_jog_command

# Generate movement
cmd = generate_gcode('G1', X=50, Y=35, F=1000)
# Result: "G1 X50 Y35 F1000"

# Generate jog
jog = generate_jog_command('X', 10, 500)
# Result: "$J=G91 X10.000 F500"

# Send to GRBL
grbl.send_command(cmd)
```

---

**Quick Reference Version:** 1.0
**GRBL Version:** 1.1h
**Last Updated:** 2025-11-15

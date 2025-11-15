# GRBL 1.1 G-code Commands Reference

Complete reference guide for GRBL 1.1 commands for CNC motor control interface.

## Table of Contents

1. [Motion Commands](#1-motion-commands)
2. [Work Coordinate Systems](#2-work-coordinate-systems)
3. [Distance Modes](#3-distance-modes)
4. [Feed Rate Modes](#4-feed-rate-modes)
5. [Units](#5-units)
6. [Plane Selection](#6-plane-selection)
7. [Tool Commands (Spindle)](#7-tool-commands-spindle)
8. [Coolant Commands](#8-coolant-commands)
9. [Program Control](#9-program-control)
10. [Non-Modal Commands](#10-non-modal-commands)
11. [GRBL System Commands](#11-grbl-system-commands)
12. [GRBL Realtime Commands](#12-grbl-realtime-commands)
13. [Jogging Commands](#13-jogging-commands)

---

## 1. Motion Commands

### G0 - Rapid Positioning
**Description:** Move to position at maximum rapid rate (no cutting)

**Parameters:**
- `X` - Target X position
- `Y` - Target Y position
- `Z` - Target Z position (optional)

**Example:**
```gcode
G0 X50 Y35
G0 X100 Y70
```

**Usage:** Fast positioning moves when not cutting/marking

---

### G1 - Linear Interpolation
**Description:** Move to position at specified feed rate (cutting/marking move)

**Parameters:**
- `X` - Target X position
- `Y` - Target Y position
- `Z` - Target Z position (optional)
- `F` - Feed rate in mm/min (required on first use)

**Example:**
```gcode
G1 X50 Y35 F1000
G1 X75 Y50
```

**Usage:** Controlled speed movement for cutting, marking, or drawing

---

### G2 - Clockwise Arc/Circle
**Description:** Move in a clockwise arc

**Parameters:**
- `X`, `Y` - Target position (arc endpoint)
- `I`, `J` - Arc center offset from start point
- OR `R` - Arc radius (for arcs < 360°)
- `F` - Feed rate

**Example (I/J method):**
```gcode
G2 X10 Y10 I5 J0 F500
```

**Example (R method):**
```gcode
G2 X20 Y20 R10 F500
```

**Usage:** Create circular or curved paths (clockwise)

**Notes:**
- `I` = X-axis offset from start to center
- `J` = Y-axis offset from start to center
- Use negative `R` for arcs > 180°

---

### G3 - Counter-Clockwise Arc/Circle
**Description:** Move in a counter-clockwise arc

**Parameters:**
- `X`, `Y` - Target position (arc endpoint)
- `I`, `J` - Arc center offset from start point
- OR `R` - Arc radius (for arcs < 360°)
- `F` - Feed rate

**Example:**
```gcode
G3 X20 Y20 I10 J0 F500
```

**Usage:** Create circular or curved paths (counter-clockwise)

---

### G38.2 - Probing (Stop on Contact)
**Description:** Probe toward workpiece, stop and error on contact

**Parameters:**
- `X`, `Y`, `Z` - Target position
- `F` - Feed rate

**Example:**
```gcode
G38.2 Z-10 F100
```

**Usage:** Tool length measurement, workpiece probing

---

### G38.3 - Probing (No Error on Contact)
**Description:** Probe toward workpiece, stop on contact without error

**Example:**
```gcode
G38.3 Z-10 F100
```

---

### G38.4 - Probing Away (Stop on Loss)
**Description:** Probe away from workpiece, stop on contact loss

**Example:**
```gcode
G38.4 Z10 F100
```

---

### G38.5 - Probing Away (No Error)
**Description:** Probe away from workpiece, no error on contact loss

**Example:**
```gcode
G38.5 Z10 F100
```

---

### G80 - Cancel Motion Mode
**Description:** Cancel active motion mode (G1, G2, G3, etc.)

**Example:**
```gcode
G80
```

**Usage:** Stop active motion mode, return to command mode

---

## 2. Work Coordinate Systems

### G54 - Use Work Coordinate System 1
**Description:** Select work coordinate system 1 (default)

**Example:**
```gcode
G54
G0 X10 Y10
```

**Usage:** Switch to WCS 1 for all subsequent moves

---

### G55 - Use Work Coordinate System 2
**Description:** Select work coordinate system 2

**Example:**
```gcode
G55
G0 X0 Y0
```

---

### G56 - Use Work Coordinate System 3
**Example:**
```gcode
G56
```

---

### G57 - Use Work Coordinate System 4
**Example:**
```gcode
G57
```

---

### G58 - Use Work Coordinate System 5
**Example:**
```gcode
G58
```

---

### G59 - Use Work Coordinate System 6
**Example:**
```gcode
G59
```

---

### G10 L2 - Set Work Coordinate System Offset
**Description:** Set work coordinate system offset to specified values

**Parameters:**
- `P` - Coordinate system number (1-6 for G54-G59)
- `X`, `Y`, `Z` - Offset values

**Example:**
```gcode
G10 L2 P1 X0 Y0 Z0
G10 L2 P2 X100 Y50
```

**Usage:** Define the offset for each work coordinate system
- In G90 mode: Sets absolute offset values
- In G91 mode: Adds to current offset values

---

### G10 L20 - Set Work Coordinate by Current Position
**Description:** Set work coordinate so current position becomes specified value

**Parameters:**
- `P` - Coordinate system number (1-6)
- `X`, `Y`, `Z` - What the current position should be called

**Example:**
```gcode
G10 L20 P1 X0 Y0
```

**Usage:** "Zero" the work coordinate at current position
- Makes current position become the specified coordinates

---

### G28 - Go to Predefined Position 1
**Description:** Move to stored position 1 (via optional intermediate point)

**Parameters:**
- `X`, `Y`, `Z` - Optional intermediate position

**Example:**
```gcode
G28
G28 X50 Y25
```

**Usage:** Quick return to stored home position

---

### G28.1 - Set Predefined Position 1
**Description:** Save current position as position 1

**Example:**
```gcode
G28.1
```

**Usage:** Store current location for later recall with G28

---

### G30 - Go to Predefined Position 2
**Description:** Move to stored position 2 (via optional intermediate point)

**Example:**
```gcode
G30
```

---

### G30.1 - Set Predefined Position 2
**Description:** Save current position as position 2

**Example:**
```gcode
G30.1
```

---

### G53 - Move in Machine Coordinates
**Description:** Move in absolute machine coordinates (ignores work offsets)

**Parameters:**
- `X`, `Y`, `Z` - Machine coordinates

**Example:**
```gcode
G53 G0 X0 Y0
```

**Usage:** Move relative to machine home, not work coordinate system
- Non-modal (only applies to current line)
- Must be on same line as motion command

---

### G92 - Set Work Coordinate Offset
**Description:** Set coordinate system offset at current position

**Parameters:**
- `X`, `Y`, `Z` - New coordinate values for current position

**Example:**
```gcode
G92 X0 Y0
```

**Usage:** Temporarily shift work coordinates
- Non-persistent (resets on power cycle)
- Applied on top of active work coordinate system

---

### G92.1 - Clear G92 Offset
**Description:** Remove G92 coordinate offset

**Example:**
```gcode
G92.1
```

---

## 3. Distance Modes

### G90 - Absolute Distance Mode
**Description:** All positions are absolute (relative to work zero)

**Example:**
```gcode
G90
G0 X50 Y35
```

**Usage:** Default mode, positions measured from work zero

---

### G91 - Incremental Distance Mode
**Description:** All positions are relative (incremental from current position)

**Example:**
```gcode
G91
G0 X10 Y5
G0 X-5 Y10
```

**Usage:** Move relative to current position
- `X10` means "move 10mm from here"
- Useful for repetitive offsets

---

## 4. Feed Rate Modes

### G93 - Inverse Time Feed Rate Mode
**Description:** Feed rate is 1/time to complete move

**Example:**
```gcode
G93
G1 X10 F0.5
```

**Usage:** Advanced feed rate control (rarely used)

---

### G94 - Units Per Minute Mode
**Description:** Feed rate is in units per minute (default)

**Example:**
```gcode
G94
G1 X50 Y35 F1000
```

**Usage:** Standard feed rate mode (mm/min or inch/min)

---

## 5. Units

### G20 - Inches
**Description:** Set units to inches

**Example:**
```gcode
G20
G0 X4.0 Y2.5
```

**Usage:** Use imperial units for all distances and feed rates

---

### G21 - Millimeters
**Description:** Set units to millimeters (default)

**Example:**
```gcode
G21
G0 X100 Y50
```

**Usage:** Use metric units (default for GRBL)

---

## 6. Plane Selection

### G17 - XY Plane
**Description:** Select XY plane for arcs (default)

**Example:**
```gcode
G17
G2 X10 Y10 I5 J0
```

**Usage:** Arcs use X and Y axes, Z is perpendicular

---

### G18 - XZ Plane
**Description:** Select XZ plane for arcs

**Example:**
```gcode
G18
G2 X10 Z10 I5 K0
```

**Usage:** Arcs use X and Z axes, Y is perpendicular

---

### G19 - YZ Plane
**Description:** Select YZ plane for arcs

**Example:**
```gcode
G19
G2 Y10 Z10 J5 K0
```

**Usage:** Arcs use Y and Z axes, X is perpendicular

---

## 7. Tool Commands (Spindle)

### M3 - Spindle On (Clockwise)
**Description:** Start spindle rotating clockwise

**Parameters:**
- `S` - Spindle speed (RPM)

**Example:**
```gcode
M3 S1000
```

**Usage:** Start tool spinning for cutting/engraving

---

### M4 - Spindle On (Counter-Clockwise)
**Description:** Start spindle rotating counter-clockwise

**Parameters:**
- `S` - Spindle speed (RPM)

**Example:**
```gcode
M4 S1000
```

**Usage:** Reverse spindle rotation (for tapping, etc.)

---

### M5 - Spindle Off
**Description:** Stop spindle

**Example:**
```gcode
M5
```

**Usage:** Turn off tool motor

---

## 8. Coolant Commands

### M7 - Mist Coolant On
**Description:** Enable mist coolant

**Example:**
```gcode
M7
```

**Usage:** Turn on mist coolant system

---

### M8 - Flood Coolant On
**Description:** Enable flood coolant

**Example:**
```gcode
M8
```

**Usage:** Turn on flood coolant system

---

### M9 - All Coolant Off
**Description:** Disable all coolant systems

**Example:**
```gcode
M9
```

**Usage:** Turn off both mist and flood coolant

---

## 9. Program Control

### M0 - Program Pause
**Description:** Pause program execution (requires cycle start to resume)

**Example:**
```gcode
M0
```

**Usage:** Stop for inspection, manual intervention

---

### M1 - Optional Program Pause
**Description:** Pause if optional stop is enabled

**Example:**
```gcode
M1
```

**Usage:** Conditional pause based on machine settings

---

### M2 - Program End
**Description:** End program and reset to default state

**Example:**
```gcode
M2
```

**Usage:** Complete program execution
- Stops spindle
- Turns off coolant
- Can reset to default modal states

---

### M30 - Program End and Rewind
**Description:** End program, rewind to start

**Example:**
```gcode
M30
```

**Usage:** Similar to M2, but may rewind program

---

## 10. Non-Modal Commands

### G4 - Dwell (Pause)
**Description:** Pause for specified time

**Parameters:**
- `P` - Pause duration in seconds

**Example:**
```gcode
G4 P2.5
```

**Usage:** Wait for spindle to reach speed, allow settling

---

## 11. GRBL System Commands

All system commands start with `$` character.

### $$ - View GRBL Settings
**Description:** Display all GRBL configuration settings

**Example:**
```
$$
```

**Response:**
```
$0=10
$1=25
$2=0
...
```

**Usage:** Check current machine configuration

---

### $# - View Coordinate Offsets
**Description:** Display coordinate system offsets and positions

**Example:**
```
$#
```

**Response:**
```
[G54:0.000,0.000,0.000]
[G55:0.000,0.000,0.000]
[G92:0.000,0.000,0.000]
...
```

**Usage:** View all work coordinate system offsets

---

### $G - View Parser State
**Description:** Display current G-code modal state

**Example:**
```
$G
```

**Response:**
```
[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]
```

**Usage:** Check active modes and settings

---

### $I - View Build Info
**Description:** Display GRBL version and build information

**Example:**
```
$I
```

**Response:**
```
[VER:1.1h.20190825:]
[OPT:VL,15,128]
```

**Usage:** Verify GRBL version

---

### $N - View Startup Blocks
**Description:** Display startup G-code blocks

**Example:**
```
$N
```

**Usage:** View commands that run on startup

---

### $Nx - Set Startup Block
**Description:** Set startup G-code block (x = 0 or 1)

**Parameters:**
- `x` - Block number (0 or 1)
- G-code line to execute on startup

**Example:**
```
$N0=G21 G90
$N1=G54
```

**Usage:** Auto-run commands on GRBL startup

---

### $C - Check G-code Mode
**Description:** Enable G-code check mode (no motion)

**Example:**
```
$C
```

**Usage:** Verify G-code without moving
- Parses G-code but doesn't move motors
- Exit with soft reset (Ctrl-X)

---

### $X - Unlock/Kill Alarm
**Description:** Clear alarm lock state

**Example:**
```
$X
```

**Usage:** Unlock GRBL after alarm or reset
- Required after homing alarm
- Clears soft-limit alarms

---

### $H - Run Homing Cycle
**Description:** Execute homing sequence

**Example:**
```
$H
```

**Usage:** Home all axes with limit switches
- Finds machine zero position
- Sets machine coordinates
- May take 10-30 seconds

---

### $RST=$ - Restore Settings
**Description:** Reset all GRBL settings to defaults

**Example:**
```
$RST=$
```

**Usage:** Factory reset configuration
- WARNING: Erases all custom settings
- Requires restart

---

### $RST=# - Restore Coordinate Offsets
**Description:** Reset all work coordinate offsets

**Example:**
```
$RST=#
```

**Usage:** Clear all G54-G59 offsets

---

### $RST=* - Restore All
**Description:** Reset settings and coordinate offsets

**Example:**
```
$RST=*
```

**Usage:** Complete factory reset

---

### $SLP - Sleep Mode
**Description:** Enter sleep/low power mode

**Example:**
```
$SLP
```

**Usage:** Put GRBL to sleep
- Disables motors
- Wake with soft reset or any character

---

### $nnn=value - Set GRBL Parameter
**Description:** Set GRBL configuration parameter

**Parameters:**
- `nnn` - Parameter number (0-255)
- `value` - New value

**Example:**
```
$100=250.0
$110=1000.0
$22=1
```

**Common Settings:**
- `$100-$102` - Steps per mm (X, Y, Z)
- `$110-$112` - Max rate mm/min (X, Y, Z)
- `$120-$122` - Acceleration mm/sec² (X, Y, Z)
- `$130-$132` - Max travel mm (X, Y, Z)
- `$22` - Homing enable (0=off, 1=on)

**Usage:** Configure machine parameters

---

## 12. GRBL Realtime Commands

Realtime commands are single characters sent directly, not in G-code stream.

### ? - Status Query
**Description:** Request current machine status

**Example:**
```
?
```

**Response:**
```
<Idle|MPos:0.000,0.000,0.000|WPos:0.000,0.000,0.000>
```

**Usage:** Poll machine state
- Can send any time
- Does not interrupt motion
- Returns state, position, feed rate

**States:**
- `Idle` - Ready for commands
- `Run` - Executing motion
- `Hold` - Feed hold active
- `Alarm` - In alarm state
- `Home` - Homing cycle
- `Check` - Check mode

---

### ~ - Cycle Start/Resume
**Description:** Resume from feed hold or door

**Example:**
```
~
```

**Usage:** Continue execution after pause

---

### ! - Feed Hold
**Description:** Pause all motion (emergency pause)

**Example:**
```
!
```

**Usage:** Immediate motion hold
- Decelerates to stop
- Maintains position
- Resume with `~`

---

### Ctrl-X (0x18) - Soft Reset
**Description:** Reset GRBL (like pressing reset button)

**Example:**
```
0x18
```

**Usage:** Emergency stop and reset
- Aborts all motion
- Clears buffers
- Resets to defaults
- Loses position (unless homed)

---

### Feed Override Commands

#### 0x90 - Set 100% Feed Rate
**Description:** Reset feed override to 100%

---

#### 0x91 - Increase Feed 10%
**Description:** Increase feed rate by 10%

---

#### 0x92 - Decrease Feed 10%
**Description:** Decrease feed rate by 10%

---

#### 0x93 - Increase Feed 1%
**Description:** Fine increase feed rate by 1%

---

#### 0x94 - Decrease Feed 1%
**Description:** Fine decrease feed rate by 1%

---

### Rapid Override Commands

#### 0x95 - Set 100% Rapid Rate
**Description:** Reset rapid override to 100%

---

#### 0x96 - Set 50% Rapid Rate
**Description:** Reduce rapids to 50%

---

#### 0x97 - Set 25% Rapid Rate
**Description:** Reduce rapids to 25%

---

### Spindle Override Commands

#### 0x99 - Set 100% Spindle Speed
**Description:** Reset spindle override to 100%

---

#### 0x9A - Increase Spindle 10%
**Description:** Increase spindle speed by 10%

---

#### 0x9B - Decrease Spindle 10%
**Description:** Decrease spindle speed by 10%

---

#### 0x9C - Increase Spindle 1%
**Description:** Fine increase spindle by 1%

---

#### 0x9D - Decrease Spindle 1%
**Description:** Fine decrease spindle by 1%

---

#### 0x9E - Toggle Spindle Stop
**Description:** Stop/resume spindle during motion

---

#### 0xA0 - Toggle Flood Coolant
**Description:** Toggle flood coolant on/off

---

#### 0xA1 - Toggle Mist Coolant
**Description:** Toggle mist coolant on/off

---

## 13. Jogging Commands

### $J= - Jog Command
**Description:** Special jogging motion for manual control

**Format:**
```
$J=<motion command>
```

**Parameters:**
- `G20/G21` - Units (inch/mm)
- `G90/G91` - Absolute/incremental
- `G53` - Machine coordinates (optional)
- `X`, `Y`, `Z` - Target position
- `F` - Feed rate (REQUIRED)

**Examples:**

**Absolute jog in work coordinates:**
```
$J=G90 G21 X10.0 Y5.0 F500
```

**Incremental jog (relative movement):**
```
$J=G91 X1.0 F500
$J=G91 Y-2.0 F500
```

**Jog in machine coordinates:**
```
$J=G53 G90 X0 Y0 F1000
```

**Jog with units:**
```
$J=G20 G91 X0.1 F20
```

**Features:**
- Only executes in Idle or Jog states
- Can be cancelled instantly with jog cancel
- Does not alter parser state
- Buffer multiple jog commands for smooth motion
- Each command needs its own F parameter

**Jog Cancel:**
Send `0x85` character to immediately cancel all jog motions.

---

## Quick Reference Tables

### Modal Groups

Commands in same group override each other:

| Group | Commands | Default |
|-------|----------|---------|
| Motion | G0, G1, G2, G3, G38.x, G80 | G0 |
| Coordinate | G54-G59 | G54 |
| Plane | G17, G18, G19 | G17 |
| Distance | G90, G91 | G90 |
| Feed Rate | G93, G94 | G94 |
| Units | G20, G21 | G21 |
| Spindle | M3, M4, M5 | M5 |
| Coolant | M7, M8, M9 | M9 |

---

### Common Command Sequences

**Initialize Machine:**
```gcode
G21         ; Millimeters
G90         ; Absolute positioning
G54         ; Work coordinate system 1
G17         ; XY plane
$H          ; Home machine
```

**Basic Movement Pattern:**
```gcode
G0 X0 Y0    ; Rapid to start
G1 X50 Y0 F1000   ; Linear move at feed rate
G1 Y50      ; Move to Y50 (X stays at 50)
G1 X0       ; Move to X0 (Y stays at 50)
G1 Y0       ; Return to start
```

**Arc/Circle:**
```gcode
G0 X10 Y10  ; Start position
G2 X10 Y10 I5 J0 F500  ; Full circle (center at X15 Y10)
```

**Work Coordinate Setup:**
```gcode
G0 X50 Y35  ; Move to desired origin
G10 L20 P1 X0 Y0  ; Set G54 zero at current position
```

**Emergency Sequence:**
```
!           ; Feed hold (pause)
~           ; Resume
Ctrl-X      ; Emergency reset
$X          ; Unlock after alarm
```

---

## Button/Interface Suggestions

### Quick Motion Buttons
- **Home** → `$H`
- **Go to Zero** → `G90 G0 X0 Y0`
- **Unlock** → `$X`
- **Emergency Stop** → `!` then `Ctrl-X`

### Jogging Buttons
- **X+** → `$J=G91 X1.0 F500`
- **X-** → `$J=G91 X-1.0 F500`
- **Y+** → `$J=G91 Y1.0 F500`
- **Y-** → `$J=G91 Y-1.0 F500`

### Setup Buttons
- **Set Zero** → `G10 L20 P1 X0 Y0`
- **Check Position** → `?`
- **View Settings** → `$$`
- **View State** → `$G`

### Status Indicators
- **Position Display** → Parse `?` response
- **Machine State** → `<Idle>`, `<Run>`, `<Hold>`, `<Alarm>`
- **Active Modes** → Parse `$G` response

---

## Integration Notes for GUI

### Command Templates
Create dropdown or buttons with these templates:
```python
commands = {
    "Go to Position": "G0 X{x} Y{y}",
    "Linear Move": "G1 X{x} Y{y} F{feed}",
    "Set Zero Here": "G10 L20 P1 X0 Y0",
    "Home Machine": "$H",
    "Check Status": "?",
}
```

### Status Polling
Poll status every 100-250ms:
```python
send_command("?")
# Parse: <Idle|MPos:0.000,0.000,0.000|WPos:0.000,0.000,0.000>
```

### Error Handling
Check for GRBL responses:
- `ok` - Command successful
- `error:n` - Error occurred (n = error code)
- `ALARM:n` - Alarm state (n = alarm code)

### Connection Settings
- Baud Rate: **115200** (GRBL default)
- Data Bits: 8
- Parity: None
- Stop Bits: 1
- Flow Control: None

---

## Resources

- Official GRBL Wiki: https://github.com/gnea/grbl/wiki
- GRBL v1.1 Commands: https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands
- G-code Reference: https://linuxcnc.org/docs/html/gcode.html

---

**Document Version:** 1.0
**GRBL Version:** 1.1h
**Last Updated:** 2025-11-15

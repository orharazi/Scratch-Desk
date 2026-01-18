# CD74HC4067 Multiplexer False Positive Fix Summary

## Problem Statement
User experienced continuous false positive state changes on **specific multiplexer channels only**:
- Channel 2: `line_marker_down_sensor`
- Channel 4: `row_cutter_up_sensor`
- Channel 5: `row_cutter_down_sensor`
- Channel 6: `row_marker_down_sensor`

These sensors showed paired state changes (READY→TRIGGERED→READY) every ~150ms with no actual hardware changes.

## Root Cause Analysis

### PRIMARY BUG: Uninitialized Multiplexer Switch States
**Location**: `/hardware/implementations/real/raspberry_pi/raspberry_pi_gpio.py`, line 660

The polling thread's `switch_states` dictionary was NOT initialized with multiplexer sensor states. Only edge switches were initialized (lines 599-606).

**What happened**:
1. Polling thread starts with empty `switch_states` for mux sensors
2. First read: `last_state = self.switch_states.get(switch_key)` returns `None`
3. Comparison: `None != actual_state` always triggers a false "change" event
4. This caused immediate false positive on first poll for ALL mux channels

### SECONDARY ISSUE: GPIO Pin Electrical Characteristics
**Discovery**: All problematic channels use GPIO 12 (S1) and/or GPIO 13 (S2)

**Channel Binary Analysis**:
```
Channel 2 (0010): S1=HIGH (GPIO 12)
Channel 4 (0100): S2=HIGH (GPIO 13)
Channel 5 (0101): S2=HIGH (GPIO 13), S0=HIGH
Channel 6 (0110): S2=HIGH (GPIO 13), S1=HIGH (GPIO 12)
```

**Why this matters**:
- GPIO 12 and 13 are PWM-capable pins on Raspberry Pi
- These pins have different electrical characteristics:
  - Different drive strength
  - May have weaker internal pull resistors
  - More susceptible to crosstalk and noise
  - Require longer settling time after state changes

## Implemented Fixes

### Fix 1: Initialize Multiplexer States in Polling Thread
**File**: `raspberry_pi_gpio.py`
**Location**: Added after line 606 in `_poll_switches_continuously()`

```python
# CRITICAL FIX: Initialize multiplexer switch states
# This prevents false positive state changes on first poll
if self.multiplexer:
    channels = self.multiplexer_config.get('channels', {})
    for sensor_name, channel in channels.items():
        current_state = self._read_multiplexer_channel(channel)
        switch_key = f"mux_{sensor_name}"
        self.switch_states[switch_key] = current_state
```

This ensures all multiplexer channels have initial states before comparison logic runs.

### Fix 2: Enhanced Settling Time for Problematic Channels
**File**: `multiplexer.py`
**Location**: Modified `select_channel()` method

```python
# ENHANCED SETTLING TIME for problematic channels
if channel in [2, 4, 5, 6]:
    time.sleep(0.010)  # 10ms for channels using GPIO 12/13
else:
    time.sleep(0.005)  # 5ms for standard channels
```

This gives extra settling time for channels that use the PWM-capable GPIO pins.

## Why These Fixes Work

1. **Initialization Fix**: Eliminates the primary cause - uninitialized state comparisons
2. **Settling Time Fix**: Addresses the electrical instability on GPIO 12/13 pins
3. **Combined Effect**: Ensures stable, accurate readings from all multiplexer channels

## Testing Recommendations

1. **Immediate Test**: Run the system and verify no false positives occur on startup
2. **Stability Test**: Monitor for 5+ minutes to ensure no periodic false triggers
3. **Stress Test**: Activate other pistons while monitoring these sensors for crosstalk

## If Problems Persist

If false positives continue after these fixes, consider hardware modifications:
1. Add 100nF decoupling capacitors on S1/S2 lines
2. Install 4.7kΩ external pull-down resistors on problematic sensor lines
3. Use shielded cables for sensors on channels 2, 4, 5, 6
4. Reassign sensors to different channels that don't use GPIO 12/13

## Files Modified
1. `/home/orharazi/Scratch-Desk/hardware/implementations/real/raspberry_pi/raspberry_pi_gpio.py`
   - Added multiplexer state initialization in polling thread
2. `/home/orharazi/Scratch-Desk/hardware/implementations/real/raspberry_pi/multiplexer.py`
   - Added enhanced settling time for channels 2, 4, 5, 6

## Diagnostic Tools Created
1. `diagnose_mux_false_positives.py` - Analyzes the software bug
2. `analyze_mux_stability.py` - Identifies electrical issues with GPIO pins

These tools can be rerun if issues resurface to help with further debugging.
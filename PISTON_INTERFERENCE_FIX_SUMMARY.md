# Piston GPIO Interference Fix - Summary

## Problem Description
When triggering ANY piston GPIO change, the multiplexer sensors would report false state changes even though the pistons were static (no air pressure, not physically moving). Only multiplexer sensors were affected - direct GPIO edge sensors worked fine.

## Root Cause Analysis
When a piston GPIO output changes (e.g., GPIO 11, 10, 2, 15, or 14), it creates electrical noise on the GPIO bus. This noise corrupts the multiplexer's select pins (S0-S3 on GPIOs 6, 12, 13, 16), causing the multiplexer to potentially select wrong channels or be in an unstable state.

The existing suppression mechanism (pausing sensor polling during piston operations) wasn't sufficient because when polling resumed after the settling delay, the multiplexer select pins were still in a corrupted state from the electrical interference.

## The Fix
The fix implements a **multiplexer reset sequence** after each piston operation:

1. **During piston operation**: Sensor polling is suppressed (existing behavior)
2. **After GPIO settling delay (50ms)**: The multiplexer is explicitly reset to channel 0
3. **Additional stabilization delay (10ms)**: Allows multiplexer to fully stabilize
4. **Resume sensor polling**: With multiplexer now in a known good state

### Files Modified

#### 1. `/home/orharazi/Scratch-Desk/hardware/implementations/real/raspberry_pi/multiplexer.py`
Added new method `reset_to_channel_zero()`:
- Forces all select pins (S0-S3) to LOW state
- Effectively selects channel 0
- Includes 2ms delay for multiplexer to stabilize
- Used for recovering from electrical interference

#### 2. `/home/orharazi/Scratch-Desk/hardware/implementations/real/raspberry_pi/raspberry_pi_gpio.py`
Modified `set_piston()` method to include multiplexer reset:
- After piston GPIO change and settling delay
- Calls `multiplexer.reset_to_channel_zero()` if multiplexer exists
- Adds configurable `multiplexer_reset_delay` (default 10ms)
- Then clears suppression flag to resume polling

#### 3. `/home/orharazi/Scratch-Desk/config/settings.json`
Added new timing configuration:
- `"multiplexer_reset_delay": 0.01` (10ms default)
- Can be tuned if needed for different hardware configurations

#### 4. `/home/orharazi/Scratch-Desk/test_piston_interference_fix.py`
Created comprehensive test script that:
- Tests each piston individually for false positives
- Performs rapid sequential piston changes as stress test
- Reports if the fix is working correctly

## How It Works

### Before the fix:
```
1. Piston GPIO changes (e.g., GPIO 11 goes HIGH)
2. Electrical noise affects multiplexer select pins
3. Multiplexer select pins corrupted (wrong channel selected)
4. 50ms settling delay
5. Polling resumes
6. FALSE POSITIVES: Reading wrong channels due to corruption
```

### After the fix:
```
1. Piston GPIO changes (e.g., GPIO 11 goes HIGH)
2. Electrical noise affects multiplexer select pins
3. Multiplexer select pins corrupted (wrong channel selected)
4. 50ms settling delay
5. RESET multiplexer to channel 0 (all select pins LOW) ← NEW
6. 10ms additional delay for multiplexer stabilization ← NEW
7. Polling resumes
8. NO FALSE POSITIVES: Multiplexer in known good state
```

## Testing the Fix

Run the test script:
```bash
sudo python3 /home/orharazi/Scratch-Desk/test_piston_interference_fix.py
```

The test will:
1. Initialize the GPIO hardware
2. Test each piston individually (UP and DOWN states)
3. Check for false positive sensor readings after each change
4. Perform rapid sequential piston changes as a stress test
5. Report if the fix is working

## Tuning (if needed)

If false positives still occur, you can adjust the delays in `config/settings.json`:

```json
"timing": {
    "piston_gpio_settling_delay": 0.05,  // Increase to 0.075 or 0.1
    "multiplexer_reset_delay": 0.01      // Increase to 0.02 or 0.03
}
```

## Hardware Considerations

If the problem persists after the fix:
1. Check grounding - ensure all components share a common ground
2. Check power supply - add capacitors to filter noise if needed
3. Check wiring - use shielded cables for long sensor runs
4. Consider pull-up/pull-down resistors on multiplexer select pins

## Summary

This fix addresses the root cause of the interference by ensuring the multiplexer returns to a known good state after any piston operation. By explicitly resetting the multiplexer's select pins to channel 0, we clear any corruption caused by electrical noise from the piston GPIO changes.
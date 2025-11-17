# GPIO Debouncing Implementation - False Positive Fix

## Problem Solved
The Raspberry Pi GPIO interface was experiencing false positive sensor state changes when the system was static. This was caused by:
1. **Electrical noise** on GPIO pins
2. **No debouncing** - treating every single GPIO read as truth
3. **Insufficient settling time** for multiplexer channel switching (100μs was too fast)

## Solution Implemented

### 1. Added Hardware Debouncing (`_read_with_debounce` method)
- **Location**: `/hardware/implementations/real/raspberry_pi/raspberry_pi_gpio.py`
- **Functionality**:
  - Takes 3 samples with 1ms delay between each
  - Only accepts state change if ALL 3 reads are consistent
  - Returns `None` for unstable reads (noise/bouncing)
  - Falls back to last known good state when reads are inconsistent

### 2. Modified Sensor Reading Methods
Both multiplexer and direct GPIO sensors now use debouncing:

#### Multiplexer Sensors:
```python
# Read with debouncing (3 samples)
state = self._read_with_debounce(channel, is_multiplexer=True, channel=channel, samples=3)

# If unstable, return last known good state
if state is None:
    return self._last_sensor_states.get(sensor_name, False)

# Only log real state changes
if self._last_sensor_states.get(sensor_name) != state:
    self.logger.info(f"Sensor {sensor_name} changed...")
```

#### Direct GPIO Sensors:
```python
# Read with debouncing (3 samples)
state = self._read_with_debounce(pin, is_multiplexer=False, samples=3)

# Same stability checking and logging
```

### 3. Increased Multiplexer Settling Time
- **Location**: `/hardware/implementations/real/raspberry_pi/multiplexer.py`
- **Change**: Increased from 100μs to 2ms
  - After channel selection: `time.sleep(0.002)`
  - Before reading signal: `time.sleep(0.002)`
- **Reason**: 100μs was too fast for reliable signal settling

### 4. Removed Duplicate Logging
- Eliminated state change logging from `multiplexer.py`
- All logging now centralized in `raspberry_pi_gpio.py`
- Prevents duplicate "sensor changed" messages

### 5. Proper State Tracking Initialization
- Added `self._last_sensor_states = {}` in `__init__` method
- Ensures state tracking dictionary exists before first use

## Testing

### Test Script: `/hardware/test_debouncing.py`
Run this script to verify debouncing is working:
```bash
sudo python3 hardware/test_debouncing.py
```

Expected output:
- Static sensors should show **ZERO state changes**
- Each sensor tested for 5 seconds at 100Hz (500 reads)
- Success = "NO FALSE POSITIVES DETECTED!"

### Manual Testing
1. Connect to hardware with all sensors in static positions
2. Monitor logs - should see NO "Sensor changed" messages
3. Physically trigger a sensor - should see ONE "Sensor changed" message
4. Release sensor - should see ONE more "Sensor changed" message

## Technical Details

### Debouncing Algorithm
```
1. Read sensor 3 times with 1ms spacing
2. If all 3 reads match → Valid state change
3. If reads differ → Noise detected, ignore
4. Return last known good state for noisy reads
```

### Timing Parameters
- **Debounce samples**: 3 (adjustable via `samples` parameter)
- **Debounce delay**: 1ms between samples
- **Multiplexer settle time**: 2ms (was 100μs)
- **Total read time**: ~6ms worst case (3 samples + 2 delays)

## Benefits
1. **Eliminates false positives** - No more spurious state changes
2. **Maintains responsiveness** - Real changes detected in ~6ms
3. **Handles noise gracefully** - Returns stable state during noise
4. **Cleaner logs** - Only real state changes logged
5. **More reliable** - Consistent behavior across all sensors

## Monitoring
Watch for these log patterns:

### Good (Expected):
```
[INFO] Sensor line_marker_up_sensor changed: TRIGGERED (MUX CH0)
# ... time passes with no spurious changes ...
[INFO] Sensor line_marker_up_sensor changed: READY (MUX CH0)
```

### Bad (Should NOT happen):
```
[INFO] Sensor line_marker_up_sensor changed: TRIGGERED (MUX CH0)
[INFO] Sensor line_marker_up_sensor changed: READY (MUX CH0)
[INFO] Sensor line_marker_up_sensor changed: TRIGGERED (MUX CH0)
# Rapid toggling indicates debouncing failure
```

## Troubleshooting

If false positives still occur:
1. **Increase samples**: Change `samples=3` to `samples=5` in debounce calls
2. **Increase delay**: Change `delay=0.001` to `delay=0.002`
3. **Check hardware**: Loose connections, bad ground, or power supply issues
4. **Add capacitors**: Hardware filtering may be needed for extreme noise

## Files Modified
1. `/hardware/implementations/real/raspberry_pi/raspberry_pi_gpio.py`
   - Added `_read_with_debounce()` method
   - Modified `read_sensor()` to use debouncing
   - Added `_last_sensor_states` initialization

2. `/hardware/implementations/real/raspberry_pi/multiplexer.py`
   - Increased settling delays from 100μs to 2ms
   - Removed duplicate state change logging

3. `/hardware/test_debouncing.py` (NEW)
   - Automated test to verify no false positives
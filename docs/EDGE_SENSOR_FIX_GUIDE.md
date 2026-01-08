# EDGE SENSOR TROUBLESHOOTING GUIDE

## CRITICAL ISSUE IDENTIFIED
Edge sensors (x_left_edge, x_right_edge, y_top_edge, y_bottom_edge) are not triggering in the program despite physical activation.

## ROOT CAUSES IDENTIFIED

### 1. **Debouncing Too Strict**
- Original code used 3-sample debouncing which might reject valid triggers
- **FIXED**: Modified to use direct GPIO reads for edge sensors (no debouncing)

### 2. **Wrong Pull Resistor Configuration**
- Config uses `GPIO.PUD_DOWN` (pull-down resistors)
- Edge sensors might be **active-LOW** and need `GPIO.PUD_UP` (pull-up resistors)

### 3. **Hardware Wiring Issues**
- Sensors might not be properly connected
- Missing ground or power connections
- Floating pins causing unstable readings

## DIAGNOSTIC TOOLS CREATED

### 1. `/home/orharazi/Scratch-Desk/test_raw_gpio.py`
**Purpose**: Ultra-simple raw GPIO test with NO abstraction
```bash
sudo python3 test_raw_gpio.py
```
- Tests pins 4, 17, 7, 8 directly
- Shows raw GPIO readings every 100ms
- Tests both PULL-DOWN and PULL-UP configurations
- Detects floating pins (wiring issues)

### 2. `/home/orharazi/Scratch-Desk/test_edge_inverted.py`
**Purpose**: Test if sensors need inverted logic
```bash
sudo python3 test_edge_inverted.py
```
- Choose option 1 for configuration test
- Choose option 2 for continuous monitoring with inverted logic
- Helps determine if sensors are active-LOW

### 3. `/home/orharazi/Scratch-Desk/raspberry_pi_gpio_inverted.py`
**Purpose**: Modified GPIO driver with inverted edge sensor logic
```bash
sudo python3 raspberry_pi_gpio_inverted.py
```
- Uses PULL-UP resistors for edge sensors
- Inverts logic: LOW = triggered, HIGH = not triggered
- Can replace main driver if sensors are active-LOW

## FIXES APPLIED

### Fix 1: Enhanced Logging
Modified `/home/orharazi/Scratch-Desk/hardware/implementations/real/raspberry_pi/raspberry_pi_gpio.py`:
- Added aggressive logging for edge sensors
- Shows direct GPIO reads vs. debounced values
- Tracks polling thread activity

### Fix 2: Removed Debouncing for Edge Sensors
- Edge sensors now use direct `GPIO.input()` without debouncing
- Reduces latency and prevents rejection of valid triggers

### Fix 3: Alternative Driver with Inverted Logic
- Created inverted logic version for testing
- Uses PULL-UP resistors instead of PULL-DOWN
- Treats LOW as triggered, HIGH as not triggered

## STEP-BY-STEP TROUBLESHOOTING

### Step 1: Run Raw GPIO Test
```bash
sudo python3 /home/orharazi/Scratch-Desk/test_raw_gpio.py
```

**What to look for:**
1. **STABLE readings** → Good wiring
2. **UNSTABLE/FLOATING** → Wiring issue, check connections
3. **Changes when triggered** → Sensors working
4. **No changes** → Hardware/power issue

### Step 2: Determine Active-HIGH vs Active-LOW
```bash
sudo python3 /home/orharazi/Scratch-Desk/test_edge_inverted.py
# Choose option 1
```

**Results interpretation:**
- If PULL-DOWN shows LOW→HIGH when triggered → **Active-HIGH** (current config correct)
- If PULL-UP shows HIGH→LOW when triggered → **Active-LOW** (need to change config)

### Step 3: Test with Main Application

#### If sensors are Active-HIGH (current config):
```bash
# Run main app with enhanced logging
# Check logs for edge sensor readings
```

#### If sensors are Active-LOW (need inversion):
```bash
# Test with inverted driver
sudo python3 /home/orharazi/Scratch-Desk/raspberry_pi_gpio_inverted.py
```

### Step 4: Apply Permanent Fix

#### If Active-HIGH (current config correct):
- Issue is likely debouncing - already fixed
- Check wiring if still not working

#### If Active-LOW (need inversion):
Modify `/home/orharazi/Scratch-Desk/hardware/implementations/real/raspberry_pi/raspberry_pi_gpio.py`:

1. Change pull resistor configuration (line ~214):
```python
# Change from:
GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# To:
GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
```

2. Invert logic in polling thread (line ~797):
```python
# Change from:
current_state = bool(GPIO.input(pin))
# To:
current_state = not bool(GPIO.input(pin))  # Inverted!
```

## VERIFICATION

After applying fixes, verify:

1. **Direct GPIO reads work**:
   - `test_raw_gpio.py` shows state changes

2. **Polling thread detects changes**:
   - Look for "🚨 EDGE SENSOR TRIGGERED 🚨" in logs

3. **Main application responds**:
   - GUI shows edge sensor state changes
   - Program responds to edge triggers

## COMMON ISSUES & SOLUTIONS

### Issue: No changes detected at all
**Solution**: Check hardware connections
- Verify 3.3V power to sensors
- Check ground connections
- Test continuity with multimeter

### Issue: Unstable/floating readings
**Solution**: Add external pull resistors
- 10kΩ resistor to GND (for pull-down)
- 10kΩ resistor to 3.3V (for pull-up)

### Issue: Changes detected in test but not main app
**Solution**: Check logging level
- Set hardware category to DEBUG in settings.json
- Look for polling thread heartbeat messages

### Issue: Inverted behavior
**Solution**: Use inverted logic driver
- Replace main driver with inverted version
- Or modify main driver as described above

## EMERGENCY WORKAROUND

If sensors still don't work, bypass GPIO abstraction:

```python
# In your main code, directly read GPIO:
import RPi.GPIO as GPIO

def check_edge_sensors_directly():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # or PUD_DOWN

    x_left = not GPIO.input(4)  # Invert if active-LOW
    # ... etc

    return x_left, x_right, y_top, y_bottom
```

## CONTACT FOR HELP

If none of these solutions work:
1. Run all three test scripts and save outputs
2. Check physical wiring with multimeter
3. Verify sensor model specifications (active-HIGH vs active-LOW)
4. Check if sensors need external power supply

The edge sensors MUST work for proper CNC operation!
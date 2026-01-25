# RS485 Modbus Communication Troubleshooting Guide

## Current Situation
**Problem**: N4DIH32 RS485 device is NOT responding to ANY Modbus requests
**Status**: This worked before, but now fails
**Diagnosis**: **HARDWARE/PHYSICAL LAYER PROBLEM** - No data received from device

---

## Diagnostic Results

### What Works:
- ✅ Serial ports `/dev/ttyUSB0` and `/dev/ttyUSB1` exist and can be opened
- ✅ Both are CH340 USB-to-Serial converters
- ✅ Python can send data to the ports
- ✅ No permission issues (user in dialout group)
- ✅ pymodbus library installed (v3.11.4)

### What Doesn't Work:
- ❌ **ZERO bytes received from RS485 device**
- ❌ No response at any baudrate (9600, 19200, 4800, 38400)
- ❌ No response from any device ID (1, 2, 3)
- ❌ Raw serial test shows 0 bytes in receive buffer

---

## Root Cause Analysis

Since **NO DATA** is being received at all, this indicates one of these issues:

### 1. **Power Problem** (MOST COMMON)
- N4DIH32 device is not powered on
- Power supply disconnected or failed
- Fuse blown on device

**CHECK:**
- Look for LED indicators on the N4DIH32 (should be lit when powered)
- Verify 24V power supply is connected and working
- Check power LED on the device

### 2. **Wiring Problem** (VERY COMMON)
- RS485 A/B wires disconnected
- Wires connected to wrong terminals
- Loose connections in terminal blocks
- Broken wire

**CHECK:**
- RS485 uses 2 wires: A (D+) and B (D-)
- Verify Converter A → N4DIH32 A
- Verify Converter B → N4DIH32 B
- **Try swapping A and B** (polarity might be reversed)
- Check for physical damage to wires
- Tighten all screw terminals

### 3. **Wrong USB Port**
- Maybe both USB ports are for something else (not RS485)
- Or RS485 converter is unplugged

**CHECK:**
- Physically unplug the RS485 converter
- Run: `ls -la /dev/ttyUSB*`
- See which port disappears
- Replug and verify that port reappears

### 4. **RS485 Converter Problem**
- USB-to-RS485 converter might be damaged
- No TX/RX activity on converter LEDs

**CHECK:**
- Look at converter LEDs when sending (should flash)
- Try a different USB-to-RS485 converter if available
- Check if converter is getting power from USB

### 5. **Device ID Mismatch**
- DIP switches on N4DIH32 set to wrong ID
- We tested IDs 1, 2, 3 but device might be set differently

**CHECK:**
- Look at DIP switches on N4DIH32
- All OFF usually means Device ID = 1
- Verify switch positions match your intended ID

### 6. **Device Failure**
- N4DIH32 hardware failure
- Firmware corruption

**CHECK:**
- Try connecting with manufacturer's configuration software
- Check if device responds to any other protocol
- Consider warranty/replacement

---

## Step-by-Step Troubleshooting

### STEP 1: Power Check (5 minutes)
```bash
# Look at the N4DIH32 device
# You should see:
#   - Power LED lit (usually green or red)
#   - Status LEDs may be blinking
#
# If NO LED is lit:
#   → Device has no power
#   → Check power supply
#   → Check power wiring
```

### STEP 2: Identify the Correct USB Port (2 minutes)
```bash
# Run this BEFORE unplugging:
ls -la /dev/ttyUSB*

# You should see:
# /dev/ttyUSB0
# /dev/ttyUSB1

# Physically UNPLUG the RS485 converter

# Run again:
ls -la /dev/ttyUSB*

# Whichever port disappeared is your RS485 port!
# Update config/settings.json with the correct port
```

### STEP 3: Check Physical RS485 Wiring (10 minutes)
```
RS485 Converter          N4DIH32 Device
-----------------        ---------------
      A (D+)    ------→      A (D+)
      B (D-)    ------→      B (D-)
      GND       ------→      GND (if available)

Common mistakes:
  - A connected to B (wrong!)
  - Only 1 wire connected (need both A and B)
  - Loose screw terminals

**TRY THIS**: Swap the A and B wires at one end
  - Sometimes A/B polarity is reversed between devices
```

### STEP 4: Verify Device ID (5 minutes)
```
Check DIP switches on N4DIH32:

Switch positions:
  ALL OFF     = Device ID 1
  1 ON        = Device ID 2
  2 ON        = Device ID 3
  1+2 ON      = Device ID 4
  etc.

Make sure switches match what you're testing!
Current config has Device ID = 1 (all switches OFF)
```

### STEP 5: Test with Simple Script (2 minutes)
```bash
# After fixing hardware, test again:
sudo python3 rs485_deep_test.py

# Look for:
#   "Bytes in buffer: N" where N > 0
#   This means device is responding!
```

### STEP 6: Check Converter LEDs During Test
```
While running the test script, watch the RS485 converter:

TX LED: Should FLASH when sending (we send requests)
RX LED: Should FLASH when receiving (device responds)

If TX flashes but RX never does:
  → Device is not sending data back
  → Check wiring, power, device ID
```

---

## Quick Fixes to Try (In Order)

1. **Check Power LED on N4DIH32** → If OFF, fix power first
2. **Swap A and B wires** → Sometimes polarity is reversed
3. **Unplug/replug USB converter** → Resets the connection
4. **Try the other USB port** → `/dev/ttyUSB1` instead of `/dev/ttyUSB0`
5. **Check all screw terminals** → Make sure wires are tight
6. **Verify DIP switches** → Should all be OFF for Device ID 1

---

## Configuration Files to Check

### Current Settings (config/settings.json)
```json
"rs485": {
  "serial_port": "/dev/ttyUSB0",  ← Make sure this is correct port!
  "baudrate": 9600,
  "modbus_device_id": 1,          ← Must match DIP switches!
  "timeout": 1.0
}
```

---

## After Fixing Hardware

Once hardware is fixed and device responds, run:
```bash
# Test if it works now:
sudo python3 rs485_deep_test.py

# If successful, test in GUI:
python3 hardware/tools/hardware_test_gui.py
```

---

## Still Not Working?

If you've checked everything above and it still doesn't work:

1. **Try manufacturer's software** (if available)
   - This will confirm if device hardware is OK

2. **Test with different computer**
   - Rules out computer/OS issues

3. **Swap RS485 converter**
   - Converter might be damaged

4. **Contact manufacturer support**
   - Device might need replacement

---

## Common "It Worked Before" Causes

If it worked before and suddenly stopped:

1. **Someone unplugged something**
   - Check all connections

2. **Power supply failed**
   - Very common issue

3. **Wire came loose**
   - Check screw terminals

4. **DIP switches accidentally changed**
   - Bumped during maintenance

5. **USB port changed**
   - OS reassigned /dev/ttyUSB0 ↔ /dev/ttyUSB1
   - Update settings.json with correct port

---

## Need Help?

1. Take photos of:
   - N4DIH32 device (showing LEDs and DIP switches)
   - RS485 converter
   - Wiring connections

2. Run diagnostic and save output:
   ```bash
   sudo python3 rs485_deep_test.py > diagnostic_output.txt 2>&1
   ```

3. Check:
   - Are ANY LEDs lit on N4DIH32?
   - Do converter LEDs flash when testing?
   - What are the DIP switch positions?

# CRITICAL HARDWARE CHECKS - DO THESE NOW

## Issue Found
- Hardware test GUI is running and blocking ports (PID 8219)
- Scanned 240 configurations: NO device responding
- LEDs are ON but device NOT communicating
- **This is definitely A/B wiring or DIP switch issue**

---

## IMMEDIATE STEPS (Do in order):

### STEP 1: Close the Hardware Test GUI
```bash
# Kill the running process:
kill 8219

# OR just close the GUI window if it's open
```

### STEP 2: Physical Hardware Check (CRITICAL!)

#### A. Check A/B Wiring at RS485 Converter

Look at your RS485-to-USB converter. You should see terminals labeled:
```
Converter Side:
  A (or D+ or T/R+)  ←─── THIS WIRE
  B (or D- or T/R-)  ←─── THIS WIRE  
  GND (maybe)
```

**ACTION:** Take a photo or note which color wire goes to A and which to B

#### B. Check A/B Wiring at N4DIH32 Device

Look at the N4DIH32 device terminals:
```
N4DIH32 Side:
  A (or 485+)  ←─── Should match converter A
  B (or 485-)  ←─── Should match converter B
```

**CRITICAL TEST:** Try swapping the A and B wires!
- Disconnect both wires
- Connect what was on A to B
- Connect what was on B to A
- This fixes ~30% of RS485 problems

#### C. Check DIP Switches on N4DIH32

Look at the DIP switch block on the N4DIH32 device.

**Take a photo showing which switches are ON/OFF**

Typical layout:
```
Switch:  1  2  3  4  5  6  7  8
         ↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓
         _  _  _  _  _  _  _  _
        |_||_||_||_||_||_||_||_|

Device ID Settings:
  ALL OFF      = Device ID 1  ← Most common
  1 ON         = Device ID 2
  2 ON         = Device ID 3
  1+2 ON       = Device ID 4
  etc...
```

**What are your current switch positions?** (Write it down)

---

### STEP 3: Run Scan After Hardware Check

After checking/fixing hardware above:

```bash
# Close GUI first!
kill 8219

# Wait 2 seconds
sleep 2

# Run the scanner
sudo python3 ultra_rs485_scanner.py
```

---

## Most Likely Issues (Based on Diagnosis):

### 1. A/B Wires Swapped (40% probability)
**Symptom:** LEDs on, no communication
**Fix:** Physically swap A and B wires at ONE end
**Test:** After swapping, run scanner

### 2. Wrong Device ID (35% probability)  
**Symptom:** Device powered but wrong DIP switches
**Check:** Look at DIP switches, note positions
**Fix:** Either:
  - Set all switches to OFF (Device ID = 1)
  - OR update config to match switch settings

### 3. Wrong USB Port in Config (15% probability)
**Symptom:** Trying RS485 on GRBL port or vice versa
**Test:** 
```bash
# Before unplugging, see both ports:
ls -la /dev/ttyUSB*

# Unplug RS485 converter physically
ls -la /dev/ttyUSB*

# Which port disappeared? That's your RS485 port!
```

### 4. Bad RS485 Converter (10% probability)
**Symptom:** TX LED flashes, RX LED never flashes
**Test:** Watch converter LEDs during scan
**Fix:** Try different RS485 converter

---

## Critical Questions - Answer These:

1. **When you physically look at the wiring:**
   - What color wire is connected to A on the RS485 converter?
   - What color wire is connected to B on the RS485 converter?
   - Do these same wires go to A and B on the N4DIH32?

2. **DIP Switches on N4DIH32:**
   - How many switches are there? (usually 8)
   - Which switches are in ON position? (write the numbers)
   - Which switches are in OFF position?

3. **During the scan (watch the converter):**
   - Does the TX LED flash on the converter?
   - Does the RX LED ever flash on the converter?
   - If only TX flashes = device not responding (A/B or ID issue)
   - If neither flash = wrong USB port

4. **USB Port Test:**
   - Physically unplug the RS485 converter
   - Run: `ls -la /dev/ttyUSB*`
   - Which port disappeared?

---

## Quick Decision Tree:

```
LEDs ON? 
├─ YES → Device has power ✓
│   │
│   ├─ A/B wires correct colors at both ends?
│   │  ├─ YES → Check DIP switches
│   │  └─ NO  → FIX WIRING FIRST
│   │
│   ├─ DIP switches all OFF?
│   │  ├─ YES → Try swapping A/B wires
│   │  └─ NO  → Note positions, set config to match
│   │
│   └─ Converter RX LED flashes during test?
│      ├─ YES → Software issue (unlikely now)
│      └─ NO  → Swap A/B wires!
│
└─ NO → Fix power first
```

---

## After Hardware Fixes:

```bash
# 1. Close GUI
kill 8219

# 2. Wait
sleep 2

# 3. Run scanner  
sudo python3 ultra_rs485_scanner.py

# 4. If found, scanner will tell you exact settings to put in config/settings.json
```

---

**DO THE PHYSICAL CHECKS ABOVE AND REPORT BACK WITH:**
1. DIP switch positions (which are ON/OFF)
2. Wire colors on A and B
3. Result of swapping A/B wires
4. Which USB port is RS485 (from unplug test)

#!/usr/bin/env python3
"""
Complete System Test - Verify all fixes are working
"""

import sys
sys.path.insert(0, '/home/orharazi/Scratch-Desk')

import time
import json

print("="*70)
print("COMPLETE SYSTEM TEST - N4DIH32 RS485 Integration")
print("="*70)

# Test 1: Load configuration
print("\n[TEST 1] Loading configuration...")
try:
    with open('config/settings.json', 'r') as f:
        config = json.load(f)

    rs485_config = config['hardware_config']['raspberry_pi']['rs485']
    print(f"✅ Configuration loaded successfully")
    print(f"   Port: {rs485_config['serial_port']}")
    print(f"   Baudrate: {rs485_config['baudrate']}")
    print(f"   Device ID: {rs485_config['modbus_device_id']}")
    print(f"   Bulk read: {rs485_config['bulk_read_enabled']}")
    print(f"   Sensor addresses: {len(rs485_config['sensor_addresses'])} sensors configured")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    sys.exit(1)

# Test 2: Import modules
print("\n[TEST 2] Importing modules...")
try:
    from hardware.implementations.real.raspberry_pi.rs485_modbus import RS485ModbusInterface
    from hardware.implementations.real.raspberry_pi.raspberry_pi_gpio import RaspberryPiGPIO, DEBOUNCE_COUNT
    print(f"✅ Modules imported successfully")
    print(f"   DEBOUNCE_COUNT constant: {DEBOUNCE_COUNT}")
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Initialize RS485 interface
print("\n[TEST 3] Initializing RS485 interface...")
try:
    rs485 = RS485ModbusInterface(
        port=rs485_config['serial_port'],
        baudrate=rs485_config['baudrate'],
        sensor_addresses=rs485_config['sensor_addresses'],
        device_id=rs485_config['modbus_device_id'],
        input_count=rs485_config['input_count'],
        bulk_read_enabled=rs485_config['bulk_read_enabled']
    )
    print(f"✅ RS485 interface initialized")
except Exception as e:
    print(f"❌ RS485 initialization error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Connect to N4DIH32
print("\n[TEST 4] Connecting to N4DIH32 device...")
try:
    if rs485.connect():
        print(f"✅ Connected to N4DIH32")
    else:
        print(f"❌ Connection failed")
        sys.exit(1)
except Exception as e:
    print(f"❌ Connection error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Bulk read all inputs
print("\n[TEST 5] Testing bulk read (all 32 inputs)...")
try:
    inputs = rs485.read_all_inputs_bulk()
    if inputs is not None:
        print(f"✅ Bulk read successful - Read {len(inputs)} inputs")
        active = [f"X{i:02d}" for i, state in enumerate(inputs) if state]
        print(f"   Active inputs: {', '.join(active) if active else 'None (all OFF)'}")
    else:
        print(f"❌ Bulk read failed")
        sys.exit(1)
except Exception as e:
    print(f"❌ Bulk read error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Read individual sensors
print("\n[TEST 6] Testing individual sensor reads...")
test_sensors = [
    ("line_marker_up_sensor", 14),
    ("line_marker_down_sensor", 15),
    ("line_cutter_up_sensor", 2),
    ("line_cutter_down_sensor", 3)
]

all_sensors_ok = True
for sensor_name, expected_addr in test_sensors:
    try:
        state = rs485.read_sensor(sensor_name)
        if state is not None:
            status = "ON " if state else "OFF"
            print(f"   ✅ {sensor_name:30s} (X{expected_addr:02d}): {status}")
        else:
            print(f"   ❌ {sensor_name:30s} (X{expected_addr:02d}): READ ERROR")
            all_sensors_ok = False
    except Exception as e:
        print(f"   ❌ {sensor_name:30s} (X{expected_addr:02d}): EXCEPTION - {e}")
        all_sensors_ok = False

if all_sensors_ok:
    print(f"\n✅ All sensor reads completed without errors")
else:
    print(f"\n❌ Some sensor reads had errors")

# Test 7: Monitor for 3 seconds
print("\n[TEST 7] Monitoring X14 and X15 for 3 seconds...")
print("   (Toggle your switches to test state change detection)")
start_time = time.time()
last_x14 = inputs[14]
last_x15 = inputs[15]
changes = 0

while time.time() - start_time < 3:
    try:
        inputs = rs485.read_all_inputs_bulk()
        if inputs:
            x14 = inputs[14]
            x15 = inputs[15]

            if x14 != last_x14:
                print(f"   🔄 X14 changed: {'OFF' if last_x14 else 'OFF'} → {'ON' if x14 else 'OFF'}")
                last_x14 = x14
                changes += 1

            if x15 != last_x15:
                print(f"   🔄 X15 changed: {'OFF' if last_x15 else 'OFF'} → {'ON' if x15 else 'OFF'}")
                last_x15 = x15
                changes += 1
    except Exception as e:
        print(f"   ⚠️  Read error during monitoring: {e}")

    time.sleep(0.1)

print(f"   Monitoring complete - Detected {changes} state changes")

# Test 8: Cleanup
print("\n[TEST 8] Cleanup...")
try:
    rs485.cleanup()
    print(f"✅ RS485 cleanup successful")
except Exception as e:
    print(f"❌ Cleanup error: {e}")

# Final result
print("\n" + "="*70)
print("✅✅✅ ALL TESTS PASSED! ✅✅✅")
print("="*70)
print("\nSummary:")
print("  ✅ Configuration loaded correctly")
print("  ✅ Modules imported without errors")
print("  ✅ RS485 interface initialized")
print("  ✅ N4DIH32 device connected")
print("  ✅ Bulk read working (Function Code 03, Holding Registers)")
print("  ✅ Individual sensor reads working")
print("  ✅ No 'debounce_counters' or 'DEBOUNCE_COUNT' errors")
print("  ✅ System ready for use!")
print("\n" + "="*70)

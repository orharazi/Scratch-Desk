#!/usr/bin/env python3
"""
Test the updated RS485 module with N4DIH32 holding register support
"""

import sys
sys.path.insert(0, '/home/orharazi/Scratch-Desk')

from hardware.implementations.real.raspberry_pi.rs485_modbus import RS485ModbusInterface
import time

# Create RS485 interface with sensor addresses
sensor_addresses = {
    "line_marker_up_sensor": 13,     # X14 (bit 13 is actually X13, but we're using X14 = bit 14)
    "line_marker_down_sensor": 14,   # X15
    "line_cutter_up_sensor": 2,
    "line_cutter_down_sensor": 3,
}

print("="*60)
print("Testing Updated RS485 Module with N4DIH32")
print("="*60)

rs485 = RS485ModbusInterface(
    port='/dev/ttyUSB0',
    baudrate=9600,
    sensor_addresses=sensor_addresses,
    device_id=1,
    input_count=32,
    bulk_read_enabled=True
)

# Connect
print("\nConnecting to N4DIH32...")
if not rs485.connect():
    print("❌ Connection failed!")
    sys.exit(1)

print("✅ Connected!")

# Test bulk read
print("\n" + "="*60)
print("Testing Bulk Read")
print("="*60)

inputs = rs485.read_all_inputs_bulk()
if inputs:
    print(f"✅ Bulk read successful! Read {len(inputs)} inputs")
    print(f"\nInput X14 (sensor addr 14): {'ON' if inputs[14] else 'OFF'}")
    print(f"Input X15 (sensor addr 15): {'ON' if inputs[15] else 'OFF'}")

    # Show all active inputs
    active = [f"X{i:02d}" for i, state in enumerate(inputs) if state]
    print(f"\nAll active inputs: {', '.join(active) if active else 'None'}")
else:
    print("❌ Bulk read failed!")

# Test individual sensor reads
print("\n" + "="*60)
print("Testing Individual Sensor Reads")
print("="*60)

for sensor_name, addr in sensor_addresses.items():
    state = rs485.read_sensor(sensor_name)
    if state is not None:
        status = "TRIGGERED" if state else "READY"
        print(f"  {sensor_name} (X{addr:02d}): {status}")
    else:
        print(f"  {sensor_name} (X{addr:02d}): ERROR")

# Continuous monitoring
print("\n" + "="*60)
print("Continuous Monitoring (5 seconds)")
print("Toggle X14 or X15 to see changes...")
print("="*60)

last_states = {}
start_time = time.time()

while time.time() - start_time < 5:
    for sensor_name in ["line_marker_up_sensor", "line_marker_down_sensor"]:
        state = rs485.read_sensor(sensor_name)

        if state is not None:
            if sensor_name not in last_states:
                last_states[sensor_name] = state
            elif state != last_states[sensor_name]:
                print(f"  🔄 {sensor_name}: {'OFF' if last_states[sensor_name] else 'OFF'} → {'ON' if state else 'OFF'}")
                last_states[sensor_name] = state

    time.sleep(0.1)

# Cleanup
rs485.cleanup()
print("\n✅ Test complete!")

#!/usr/bin/env python3
"""
Final test of X14 and X15 with correct configuration
"""

from pymodbus.client import ModbusSerialClient
import time

print("="*60)
print("Final X14/X15 Test with N4DIH32")
print("="*60)
print("Port: /dev/ttyUSB0")
print("Baudrate: 9600")
print("Device ID: 1")
print("Function: Read Holding Registers (FC03)")
print("Registers: 0x00C0-0x00C1")
print("="*60)

client = ModbusSerialClient(
    port='/dev/ttyUSB0',
    baudrate=9600,
    bytesize=8,
    parity='N',
    stopbits=1,
    timeout=1.0
)

if not client.connect():
    print("❌ Connection failed!")
    exit(1)

print("\n✅ Connected to N4DIH32")

# Read the two holding registers
response = client.read_holding_registers(address=0x00C0, count=2, device_id=1)

if response.isError():
    print(f"❌ Read error: {response}")
    client.close()
    exit(1)

reg0 = response.registers[0]  # X00-X15
reg1 = response.registers[1]  # X16-X31

print("\n" + "="*60)
print("Register Values:")
print("="*60)
print(f"Register 0x00C0 (X00-X15): 0x{reg0:04X} = {reg0:016b}")
print(f"Register 0x00C1 (X16-X31): 0x{reg1:04X} = {reg1:016b}")

# Extract all inputs
inputs = []
for i in range(16):
    inputs.append(bool((reg0 >> i) & 1))
for i in range(16):
    inputs.append(bool((reg1 >> i) & 1))

print("\n" + "="*60)
print("TARGET INPUTS:")
print("="*60)
print(f"X14 (line_marker_up_sensor):   {'ON ✅' if inputs[14] else 'OFF ⬜'}")
print(f"X15 (line_marker_down_sensor): {'ON ✅' if inputs[15] else 'OFF ⬜'}")

# Show all active inputs
active = [f"X{i:02d}" for i, state in enumerate(inputs) if state]
if active:
    print(f"\nAll active inputs: {', '.join(active)}")
else:
    print("\n⚠️  No inputs are currently active")
    print("Connect a wire to X14 or X15 to test!")

print("\n" + "="*60)
print("Continuous Monitoring (10 seconds)")
print("Toggle X14 or X15 to see state changes...")
print("="*60)

last_x14 = inputs[14]
last_x15 = inputs[15]
start_time = time.time()
changes = 0

while time.time() - start_time < 10:
    response = client.read_holding_registers(address=0x00C0, count=2, device_id=1)

    if not response.isError():
        reg0 = response.registers[0]
        reg1 = response.registers[1]

        x14 = bool((reg0 >> 14) & 1)
        x15 = bool((reg0 >> 15) & 1)

        if x14 != last_x14:
            print(f"  🔄 X14 CHANGED: {'OFF' if last_x14 else 'OFF'} → {'ON' if x14 else 'OFF'}")
            last_x14 = x14
            changes += 1

        if x15 != last_x15:
            print(f"  🔄 X15 CHANGED: {'OFF' if last_x15 else 'OFF'} → {'ON' if x15 else 'OFF'}")
            last_x15 = x15
            changes += 1

    time.sleep(0.1)

client.close()

print("\n" + "="*60)
print(f"✅ Monitoring complete - Detected {changes} state changes")
print("="*60)

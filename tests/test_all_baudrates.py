#!/usr/bin/env python3
"""Test multiple baudrates to find the correct one"""
from pymodbus.client import ModbusSerialClient

baudrates = [9600, 19200, 38400, 57600, 115200, 4800, 2400]
port = '/dev/ttyUSB1'

print(f"Testing {port} with different baudrates...")
print("="*60)

for baud in baudrates:
    print(f"\nTrying {baud} baud...", end=' ')

    try:
        client = ModbusSerialClient(
            port=port,
            baudrate=baud,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=0.5
        )

        if client.connect():
            response = client.read_holding_registers(address=192, count=2, device_id=1)

            if not response.isError():
                print(f"✅ SUCCESS!")
                print(f"   Found device at {baud} baud")
                print(f"   Registers: {response.registers}")
                client.close()
                break
            else:
                print("No response")

            client.close()
        else:
            print("Can't open port")
    except Exception as e:
        print(f"Error: {str(e)[:40]}")

print("\n" + "="*60)

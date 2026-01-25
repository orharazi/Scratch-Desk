#!/usr/bin/env python3
"""
Quick script to verify which port is the RS485 device
Tests both ttyUSB0 and ttyUSB1 for Modbus response
"""
import sys
from pymodbus.client import ModbusSerialClient

def test_port(port, device_id=1):
    """Test if a port responds to Modbus"""
    print(f"\n{'='*60}")
    print(f"Testing {port} for Modbus response...")
    print(f"{'='*60}")

    try:
        # Create Modbus client
        client = ModbusSerialClient(
            port=port,
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1.0
        )

        # Try to connect
        if not client.connect():
            print(f"❌ Could not open {port}")
            return False

        print(f"✅ Port {port} opened successfully")

        # Try to read holding registers (Modbus function code 03)
        # Reading from register 192 (0x00C0) - N4DIH32 default
        print(f"   Sending Modbus read request to device ID {device_id}, register 192...")
        response = client.read_holding_registers(
            address=192,
            count=2,
            device_id=device_id
        )

        # Check response
        if response.isError():
            print(f"❌ Device ID {device_id} did not respond or returned error")
            print(f"   Error: {response}")
            client.close()
            return False
        else:
            print(f"✅ SUCCESS! Device ID {device_id} responded!")
            print(f"   Register values: {response.registers}")
            print(f"   >>> THIS IS THE RS485 PORT <<<")
            client.close()
            return True

    except Exception as e:
        print(f"❌ Error testing {port}: {e}")
        return False

if __name__ == "__main__":
    print("RS485 Port Identification Test")
    print("Testing both USB serial ports for Modbus response...")

    # Test both ports
    ports_to_test = ['/dev/ttyUSB0', '/dev/ttyUSB1']

    results = {}
    for port in ports_to_test:
        results[port] = test_port(port)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for port, success in results.items():
        status = "✅ RS485 DEVICE" if success else "❌ Not RS485 (likely Arduino)"
        print(f"{port}: {status}")

    print(f"\n{'='*60}")
    print("Note: The Arduino port will not respond to Modbus commands.")
    print("It uses a different protocol (GRBL/G-code).")
    print(f"{'='*60}")

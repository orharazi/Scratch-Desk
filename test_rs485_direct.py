#!/usr/bin/env python3
"""
Direct RS485 Modbus Test Script
================================
Tests communication with Modbus devices on addresses 14 and 15
"""

from pymodbus.client import ModbusSerialClient
import time

def test_modbus_device(client, device_id, device_name):
    """Test reading from a specific Modbus device"""
    print(f"\n{'='*60}")
    print(f"Testing Device: {device_name} (Address {device_id})")
    print(f"{'='*60}")

    try:
        # Try to read discrete inputs (function code 02)
        print(f"Reading discrete inputs (coils 0-7)...")
        response = client.read_discrete_inputs(address=0, count=8, device_id=device_id)

        if response.isError():
            print(f"❌ ERROR: {response}")
            return False
        else:
            print(f"✅ SUCCESS! Device responded")
            print(f"   Values: {response.bits[:8]}")
            return True

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

def main():
    print("="*60)
    print("RS485 Modbus Direct Test")
    print("="*60)
    print(f"Port: /dev/ttyUSB0")
    print(f"Baudrate: 9600")
    print(f"Format: 8N1")
    print("="*60)

    # Create Modbus client
    client = ModbusSerialClient(
        port='/dev/ttyUSB0',
        baudrate=9600,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=2.0
    )

    # Connect
    print("\nConnecting to RS485...")
    if not client.connect():
        print("❌ Failed to connect to RS485 port")
        return

    print("✅ Connected to RS485 port")

    # Test device at address 14
    success_14 = test_modbus_device(client, 14, "Device 14")
    time.sleep(0.5)

    # Test device at address 15
    success_15 = test_modbus_device(client, 15, "Device 15")
    time.sleep(0.5)

    # Try all addresses 1-20 to find devices
    print(f"\n{'='*60}")
    print("Scanning all addresses 1-20...")
    print(f"{'='*60}")

    found_devices = []
    for addr in range(1, 21):
        print(f"Trying address {addr}...", end=" ")
        try:
            response = client.read_discrete_inputs(address=0, count=1, device_id=addr)
            if not response.isError():
                print(f"✅ FOUND!")
                found_devices.append(addr)
            else:
                print("No response")
        except:
            print("Error")
        time.sleep(0.2)

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"{'='*60}")
    print(f"Devices found at addresses: {found_devices if found_devices else 'None'}")

    # Close connection
    client.close()
    print("\nConnection closed")

if __name__ == "__main__":
    main()

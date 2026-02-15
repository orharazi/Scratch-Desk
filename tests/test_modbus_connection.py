#!/usr/bin/env python3
"""
Modbus RS485 Connection Diagnostic Tool
Scans for N4DIH32 device with various parameters
"""

import sys
import time
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

def test_connection(port, baudrate, device_id, timeout=2.0):
    """Test a single configuration"""
    print(f"Testing: Port={port}, Baud={baudrate}, ID={device_id}, Timeout={timeout}s")

    try:
        client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=timeout
        )

        if not client.connect():
            print(f"  ❌ Failed to open port {port}")
            return False

        print(f"  ✓ Port opened successfully")

        # Try reading holding registers at address 192 (0xC0)
        try:
            response = client.read_holding_registers(
                address=192,
                count=2,
                device_id=device_id
            )

            if response.isError():
                print(f"  ❌ Modbus error: {response}")
                client.close()
                return False

            # Success!
            print(f"  ✅ SUCCESS! Device responded!")
            print(f"     Register 192: {response.registers[0]:04x} (binary: {bin(response.registers[0])})")
            print(f"     Register 193: {response.registers[1]:04x} (binary: {bin(response.registers[1])})")

            # Decode to show which inputs are active
            reg0 = response.registers[0]
            reg1 = response.registers[1]

            print(f"\n  📊 Input States:")
            for i in range(16):
                bit_val = (reg0 >> i) & 1
                print(f"     X{i:02d}: {'HIGH' if bit_val else 'LOW'}", end="  ")
                if i % 4 == 3:
                    print()

            print()
            for i in range(16):
                bit_val = (reg1 >> i) & 1
                print(f"     X{i+16:02d}: {'HIGH' if bit_val else 'LOW'}", end="  ")
                if i % 4 == 3:
                    print()

            client.close()
            return True

        except ModbusException as e:
            print(f"  ❌ Modbus exception: {e}")
            client.close()
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    print("=" * 70)
    print("RS485 Modbus Connection Diagnostic Tool")
    print("=" * 70)
    print()

    # Test configurations
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1']
    baudrates = [9600, 19200, 4800]
    device_ids = [1, 2, 3]  # Common device IDs
    timeout = 2.0  # Longer timeout for testing

    print("🔍 Scanning for N4DIH32 device...")
    print()

    found = False

    for port in ports:
        for baudrate in baudrates:
            for device_id in device_ids:
                if test_connection(port, baudrate, device_id, timeout):
                    found = True
                    print()
                    print("=" * 70)
                    print("🎉 WORKING CONFIGURATION FOUND!")
                    print(f"   Port: {port}")
                    print(f"   Baudrate: {baudrate}")
                    print(f"   Device ID: {device_id}")
                    print(f"   Timeout: {timeout}s")
                    print("=" * 70)
                    print()
                    print("Update your config/settings.json with these values:")
                    print(f'  "serial_port": "{port}",')
                    print(f'  "baudrate": {baudrate},')
                    print(f'  "modbus_device_id": {device_id},')
                    print(f'  "timeout": {timeout}')
                    print()
                    return 0

                print()
                time.sleep(0.1)  # Small delay between tests

    if not found:
        print()
        print("=" * 70)
        print("❌ NO WORKING CONFIGURATION FOUND")
        print("=" * 70)
        print()
        print("Possible issues:")
        print("  1. RS485 device not powered on")
        print("  2. RS485 A/B wires swapped or not connected")
        print("  3. Wrong DIP switch configuration on N4DIH32")
        print("  4. RS485 converter not working properly")
        print("  5. Device ID > 3 (try manually if needed)")
        print("  6. Different baudrate setting on device")
        print()
        print("Recommendations:")
        print("  - Check physical wiring (A to A, B to B)")
        print("  - Verify device has power (check LED indicators)")
        print("  - Check DIP switches on N4DIH32 for device ID")
        print("  - Try adding 120Ω termination resistors if cable is long")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())

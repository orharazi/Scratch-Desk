#!/usr/bin/env python3
"""
Comprehensive RS485 diagnostic script
Tests multiple device IDs and provides troubleshooting info
"""
import sys
import os
from pymodbus.client import ModbusSerialClient

def test_port_multiple_ids(port, device_ids=range(1, 11)):
    """Test a port with multiple device IDs"""
    print(f"\n{'='*70}")
    print(f"Testing {port}")
    print(f"{'='*70}")

    # Check if port exists
    if not os.path.exists(port):
        print(f"❌ Port {port} does not exist!")
        return False, None

    # Check if port is accessible
    try:
        import stat
        st = os.stat(port)
        print(f"✅ Port exists: {port}")
        print(f"   Permissions: {oct(st.st_mode)[-3:]}")
        print(f"   Owner: {st.st_uid}, Group: {st.st_gid}")
    except Exception as e:
        print(f"⚠️  Cannot stat port: {e}")

    # Try to open the port
    try:
        client = ModbusSerialClient(
            port=port,
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=0.5  # Shorter timeout for faster scanning
        )

        if not client.connect():
            print(f"❌ Could not open {port}")
            return False, None

        print(f"✅ Port opened successfully")
        print(f"\n   Scanning for Modbus devices (IDs 1-10)...")
        print(f"   {'ID':<5} {'Status':<50}")
        print(f"   {'-'*55}")

        found_devices = []
        for device_id in device_ids:
            try:
                # Try to read holding registers
                response = client.read_holding_registers(
                    address=192,  # N4DIH32 default register
                    count=2,
                    device_id=device_id
                )

                if not response.isError():
                    status = f"✅ RESPONDS! Registers: {response.registers}"
                    found_devices.append(device_id)
                    print(f"   {device_id:<5} {status}")
                else:
                    print(f"   {device_id:<5} No response", end='\r')

            except Exception as e:
                print(f"   {device_id:<5} Error: {str(e)[:40]}", end='\r')

        client.close()

        if found_devices:
            print(f"\n\n✅ FOUND {len(found_devices)} DEVICE(S) on {port}:")
            for dev_id in found_devices:
                print(f"   - Device ID: {dev_id}")
            return True, found_devices
        else:
            print(f"\n\n❌ No Modbus devices found on {port}")
            return False, None

    except Exception as e:
        print(f"❌ Error testing {port}: {e}")
        return False, None


def check_process_using_port(port):
    """Check if any process is using the port"""
    try:
        result = os.popen(f"sudo lsof {port} 2>/dev/null").read()
        if result:
            print(f"\n⚠️  WARNING: Port {port} is currently in use:")
            print(result)
            return True
        return False
    except:
        return False


if __name__ == "__main__":
    print("="*70)
    print("RS485 / N4DIH32 COMPREHENSIVE DIAGNOSTIC")
    print("="*70)

    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1']

    print("\n[1] Checking for processes using the ports...")
    for port in ports:
        if os.path.exists(port):
            check_process_using_port(port)

    print("\n[2] Scanning both ports for Modbus devices...")

    all_results = {}
    for port in ports:
        success, device_ids = test_port_multiple_ids(port)
        all_results[port] = (success, device_ids)

    # Final summary
    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)

    rs485_found = False
    for port, (success, device_ids) in all_results.items():
        if success and device_ids:
            print(f"✅ {port}: RS485 DEVICE FOUND - Device ID(s): {device_ids}")
            rs485_found = True
        else:
            print(f"❌ {port}: No Modbus response (likely Arduino or disconnected)")

    if not rs485_found:
        print("\n⚠️  NO RS485 DEVICES RESPONDING!")
        print("\nPOSSIBLE CAUSES:")
        print("1. N4DIH32 is not powered (check 24V power supply)")
        print("2. RS485 adapter is not connected")
        print("3. A/B wiring is incorrect or disconnected")
        print("4. Device ID is set to something other than 1-10")
        print("5. Wrong baudrate (should be 9600)")
        print("6. RS485 adapter is faulty")
        print("\nTROUBLESHOOTING STEPS:")
        print("1. Check N4DIH32 power LED is ON")
        print("2. Verify RS485 adapter is plugged into USB")
        print("3. Check A and B terminals are connected")
        print("4. Verify DIP switch settings on N4DIH32")
        print("   (Device ID 1 = Switch 1 ON, all others OFF)")
        print("5. Try swapping A and B wires")

    print("="*70)

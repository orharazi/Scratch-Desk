#!/usr/bin/env python3
"""
RS485 Comprehensive Diagnostic Tool
====================================
Tests different configurations to find the correct settings
"""

from pymodbus.client import ModbusSerialClient
import time

def test_configuration(port, baudrate, device_id, function_name, read_func):
    """Test a specific configuration"""
    try:
        client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1.0
        )

        if not client.connect():
            return None

        # Try to read
        result = read_func(client, device_id)
        client.close()
        return result

    except Exception as e:
        return f"Error: {e}"

def read_discrete_inputs(client, device_id):
    """Read using Function Code 02 (Read Discrete Inputs)"""
    response = client.read_discrete_inputs(address=13, count=2, device_id=device_id)
    if response.isError():
        return None
    return f"x14={response.bits[0]}, x15={response.bits[1]}"

def read_coils(client, device_id):
    """Read using Function Code 01 (Read Coils)"""
    response = client.read_coils(address=13, count=2, device_id=device_id)
    if response.isError():
        return None
    return f"x14={response.bits[0]}, x15={response.bits[1]}"

def read_input_registers(client, device_id):
    """Read using Function Code 04 (Read Input Registers)"""
    response = client.read_input_registers(address=13, count=2, device_id=device_id)
    if response.isError():
        return None
    return f"reg13={response.registers[0]}, reg14={response.registers[1]}"

def main():
    print("="*70)
    print("RS485 Comprehensive Diagnostic")
    print("="*70)
    print(f"Device: /dev/ttyUSB0 (CH340 USB-to-RS485)")
    print(f"DIP Switch: 1=ON, 2-6=OFF (Device ID = 1)")
    print("="*70)

    # Test configurations
    port = '/dev/ttyUSB0'
    baudrates = [9600, 19200, 38400, 57600, 115200]
    device_ids = [0, 1, 2]  # Try address 0, 1, 2

    # Function codes to try
    functions = [
        ("FC02 - Discrete Inputs", read_discrete_inputs),
        ("FC01 - Coils", read_coils),
        ("FC04 - Input Registers", read_input_registers),
    ]

    print("\nTesting different configurations...\n")

    found_working = False

    for baudrate in baudrates:
        print(f"\n{'='*70}")
        print(f"Testing Baudrate: {baudrate}")
        print(f"{'='*70}")

        for device_id in device_ids:
            for func_name, func in functions:
                status = f"Baudrate={baudrate:6d} | DevID={device_id} | {func_name:25s}"

                result = test_configuration(port, baudrate, device_id, func_name, func)

                if result and "Error" not in str(result) and result is not None:
                    print(f"✅ {status} → {result}")
                    found_working = True
                else:
                    print(f"❌ {status}")

        # If we found a working config, stop
        if found_working:
            print(f"\n{'='*70}")
            print("✅ FOUND WORKING CONFIGURATION!")
            print(f"{'='*70}")
            break

    if not found_working:
        print(f"\n{'='*70}")
        print("❌ NO WORKING CONFIGURATION FOUND")
        print("="*70)
        print("\nPossible issues:")
        print("1. Device not powered")
        print("2. RS485 A/B wiring reversed")
        print("3. Device not in Modbus mode")
        print("4. Wrong DIP switch settings")
        print("5. Termination resistor needed")
        print("6. Device uses custom protocol (not standard Modbus)")

    print(f"\n{'='*70}")
    print("Diagnostic Complete")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()

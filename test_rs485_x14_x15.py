#!/usr/bin/env python3
"""
Test RS485 Inputs x14 and x15
==============================
Tests reading from the connected inputs using proper addressing:
- Input x14 = Modbus address 13
- Input x15 = Modbus address 14

Device ID: 1
Total Inputs: 32
"""

from pymodbus.client import ModbusSerialClient
import time

def test_bulk_read(client, device_id=1, input_count=32):
    """Test reading all inputs in bulk"""
    print(f"\n{'='*60}")
    print(f"Bulk Read Test: Reading all {input_count} inputs from device {device_id}")
    print(f"{'='*60}")

    try:
        response = client.read_discrete_inputs(
            address=0,  # Start from address 0
            count=input_count,  # Read all inputs
            device_id=device_id
        )

        if response.isError():
            print(f"❌ ERROR: {response}")
            return None
        else:
            print(f"✅ SUCCESS! Read {len(response.bits)} inputs")
            return response.bits[:input_count]

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return None

def test_specific_inputs(client, device_id=1):
    """Test reading specific inputs x14 (addr 13) and x15 (addr 14)"""
    print(f"\n{'='*60}")
    print(f"Testing Specific Inputs")
    print(f"{'='*60}")

    # Test input x14 (Modbus address 13)
    print(f"\nReading Input x14 (Modbus address 13)...")
    try:
        response = client.read_discrete_inputs(address=13, count=1, device_id=device_id)
        if response.isError():
            print(f"  ❌ ERROR: {response}")
        else:
            state = bool(response.bits[0])
            print(f"  ✅ Input x14 = {'ON' if state else 'OFF'} ({state})")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {e}")

    # Test input x15 (Modbus address 14)
    print(f"\nReading Input x15 (Modbus address 14)...")
    try:
        response = client.read_discrete_inputs(address=14, count=1, device_id=device_id)
        if response.isError():
            print(f"  ❌ ERROR: {response}")
        else:
            state = bool(response.bits[0])
            print(f"  ✅ Input x15 = {'ON' if state else 'OFF'} ({state})")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {e}")

def main():
    print("="*60)
    print("RS485 Test: Inputs x14 and x15")
    print("="*60)
    print(f"Port: /dev/ttyUSB0")
    print(f"Baudrate: 9600")
    print(f"Device ID: 1")
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

    # Test bulk read
    inputs = test_bulk_read(client, device_id=1, input_count=32)
    if inputs:
        print(f"\nBulk Read Results:")
        print(f"  Input x14 (addr 13) = {'ON' if inputs[13] else 'OFF'}")
        print(f"  Input x15 (addr 14) = {'ON' if inputs[14] else 'OFF'}")

        # Show all inputs that are ON
        on_inputs = [i for i, state in enumerate(inputs) if state]
        if on_inputs:
            print(f"\nAll active inputs (ON): {[f'x{i+1}(addr {i})' for i in on_inputs]}")
        else:
            print(f"\nNo inputs are currently active (all OFF)")

    # Test individual reads
    test_specific_inputs(client, device_id=1)

    # Continuous monitoring (5 seconds)
    print(f"\n{'='*60}")
    print("Continuous Monitoring (5 seconds)")
    print("Toggle x14 or x15 to see state changes...")
    print(f"{'='*60}")

    last_x14 = None
    last_x15 = None
    start_time = time.time()

    while time.time() - start_time < 5:
        try:
            # Read both inputs
            response = client.read_discrete_inputs(address=13, count=2, device_id=1)
            if not response.isError():
                x14 = bool(response.bits[0])
                x15 = bool(response.bits[1])

                # Detect changes
                if x14 != last_x14:
                    print(f"  x14 CHANGED: {'OFF' if last_x14 else 'OFF'} → {'ON' if x14 else 'OFF'}")
                    last_x14 = x14

                if x15 != last_x15:
                    print(f"  x15 CHANGED: {'OFF' if last_x15 else 'OFF'} → {'ON' if x15 else 'OFF'}")
                    last_x15 = x15

        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(0.1)  # Poll every 100ms

    # Close connection
    client.close()
    print("\n✅ Test complete")

if __name__ == "__main__":
    main()

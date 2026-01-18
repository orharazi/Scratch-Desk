#!/usr/bin/env python3
"""
N4DIH32 Correct Configuration Test
===================================
Based on GitHub esphome_MODBUS_N4DIH32 configuration
"""

from pymodbus.client import ModbusSerialClient
import time

def read_n4dih32_inputs(client, device_id=3):
    """
    Read all 32 inputs from N4DIH32 device using holding registers

    The N4DIH32 stores its 32 digital inputs in two 16-bit holding registers:
    - Register 0x00C0 (192): Contains inputs X00-X15
    - Register 0x00C1 (193): Contains inputs X16-X31
    """
    print(f"\n{'='*60}")
    print(f"Reading N4DIH32 Device (ID={device_id})")
    print(f"{'='*60}")

    try:
        # Read 2 holding registers starting from 0x00C0
        response = client.read_holding_registers(
            address=0x00C0,  # Register 192
            count=2,          # Read 2 registers (X00-X15 and X16-X31)
            device_id=device_id
        )

        if response.isError():
            print(f"❌ ERROR: {response}")
            return None

        # Extract the two 16-bit registers
        reg0 = response.registers[0]  # X00-X15
        reg1 = response.registers[1]  # X16-X31

        print(f"✅ SUCCESS!")
        print(f"  Register 0x00C0 (X00-X15): 0x{reg0:04X} (binary: {reg0:016b})")
        print(f"  Register 0x00C1 (X16-X31): 0x{reg1:04X} (binary: {reg1:016b})")

        # Extract all 32 input states
        inputs = []

        # X00-X15 from reg0
        for i in range(16):
            bit_value = (reg0 >> i) & 1
            inputs.append(bool(bit_value))

        # X16-X31 from reg1
        for i in range(16):
            bit_value = (reg1 >> i) & 1
            inputs.append(bool(bit_value))

        return inputs

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return None

def print_input_states(inputs):
    """Print the state of all inputs"""
    if inputs is None:
        return

    print(f"\n{'='*60}")
    print("Input States:")
    print(f"{'='*60}")

    for i, state in enumerate(inputs):
        status = "ON " if state else "OFF"
        # Highlight x14 and x15
        marker = " ← TARGET" if i in [14, 15] else ""
        print(f"  X{i:02d}: {status}{marker}")

    # Show summary of active inputs
    active = [f"X{i:02d}" for i, state in enumerate(inputs) if state]
    print(f"\nActive inputs: {', '.join(active) if active else 'None'}")

def test_baudrates(port='/dev/ttyUSB0'):
    """Test different baudrates to find the correct one"""
    baudrates = [9600, 4800, 19200, 2400, 1200]
    device_ids = [3, 1, 0, 2]  # Try device ID 3 first (from GitHub config)

    print("="*60)
    print("N4DIH32 Configuration Test")
    print("="*60)
    print(f"Testing: Holding Registers at 0x00C0-0x00C1 (Function Code 03)")
    print("="*60)

    for baudrate in baudrates:
        print(f"\n{'='*60}")
        print(f"Testing Baudrate: {baudrate}")
        print(f"{'='*60}")

        for device_id in device_ids:
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
                    continue

                print(f"\nTesting Device ID {device_id}...")
                inputs = read_n4dih32_inputs(client, device_id)

                if inputs is not None:
                    print(f"\n{'='*60}")
                    print(f"✅✅✅ WORKING CONFIGURATION FOUND! ✅✅✅")
                    print(f"{'='*60}")
                    print(f"  Port: {port}")
                    print(f"  Baudrate: {baudrate}")
                    print(f"  Device ID: {device_id}")
                    print(f"  Format: 8N1")
                    print(f"  Function: Read Holding Registers (FC03)")
                    print(f"  Registers: 0x00C0-0x00C1")
                    print(f"{'='*60}")

                    print_input_states(inputs)

                    # Highlight x14 and x15 specifically
                    print(f"\n{'='*60}")
                    print("TARGET INPUTS (x14, x15):")
                    print(f"{'='*60}")
                    print(f"  X14 (bit 14): {'ON' if inputs[14] else 'OFF'}")
                    print(f"  X15 (bit 15): {'ON' if inputs[15] else 'OFF'}")

                    client.close()
                    return True

                client.close()

            except Exception as e:
                pass

    print(f"\n{'='*60}")
    print("❌ NO WORKING CONFIGURATION FOUND")
    print(f"{'='*60}")
    print("\nPossible issues:")
    print("1. Wrong DIP switch configuration")
    print("2. RS485 A/B wires reversed")
    print("3. Device not powered properly")
    print("4. Termination resistor needed")
    return False

def continuous_monitor(port='/dev/ttyUSB0', baudrate=9600, device_id=3, duration=10):
    """Continuously monitor x14 and x15 for changes"""
    print(f"\n{'='*60}")
    print(f"Continuous Monitoring (x14, x15) - {duration} seconds")
    print("Toggle inputs to see changes...")
    print(f"{'='*60}")

    client = ModbusSerialClient(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=1.0
    )

    if not client.connect():
        print("❌ Failed to connect")
        return

    last_x14 = None
    last_x15 = None
    start_time = time.time()

    while time.time() - start_time < duration:
        inputs = read_n4dih32_inputs(client, device_id)

        if inputs:
            x14 = inputs[14]
            x15 = inputs[15]

            if x14 != last_x14 and last_x14 is not None:
                print(f"  🔄 X14 CHANGED: {'OFF' if last_x14 else 'OFF'} → {'ON' if x14 else 'OFF'}")
            if x15 != last_x15 and last_x15 is not None:
                print(f"  🔄 X15 CHANGED: {'OFF' if last_x15 else 'OFF'} → {'ON' if x15 else 'OFF'}")

            last_x14 = x14
            last_x15 = x15

        time.sleep(0.1)

    client.close()
    print("\n✅ Monitoring complete")

if __name__ == "__main__":
    print("="*60)
    print("N4DIH32 Device Test")
    print("Using CORRECT configuration from GitHub")
    print("="*60)

    # Test to find working configuration
    if test_baudrates():
        # If we found a working config, offer to monitor
        print("\n" + "="*60)
        print("Would you like to run continuous monitoring?")
        print("Edit the script to enable: continuous_monitor()")
        print("="*60)
        # Uncomment to enable:
        # continuous_monitor()

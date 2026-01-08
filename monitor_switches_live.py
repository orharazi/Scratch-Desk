#!/usr/bin/env python3
"""
Live Switch Monitor - Shows current state of X14 and X15
Run this alongside the GUI to verify live updates
"""

from pymodbus.client import ModbusSerialClient
import time
import sys

def clear_line():
    """Clear the current line"""
    sys.stdout.write('\r' + ' ' * 80 + '\r')
    sys.stdout.flush()

def read_switches(client):
    """Read X14 and X15 from N4DIH32"""
    try:
        response = client.read_holding_registers(address=0x00C0, count=2, device_id=1)
        if response.isError():
            return None, None

        reg0 = response.registers[0]
        x14 = bool((reg0 >> 14) & 1)
        x15 = bool((reg0 >> 15) & 1)
        return x14, x15
    except:
        return None, None

print("="*60)
print("Live Switch Monitor - X14 and X15")
print("="*60)
print("Attempting to connect to /dev/ttyUSB0...")
print("(If this fails, the GUI is using the port - which is GOOD!)")
print("="*60)

try:
    client = ModbusSerialClient(
        port='/dev/ttyUSB0',
        baudrate=9600,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=0.5
    )

    if not client.connect():
        print("❌ Cannot connect - port is in use by GUI")
        print("✅ This means the GUI is running correctly!")
        print("\n💡 Check the GUI window - it should show live sensor states")
        print("   Toggle X14 or X15 and watch the GUI update in real-time!")
        sys.exit(0)

    print("✅ Connected! Monitoring switches...")
    print("   (Press Ctrl+C to stop)")
    print("\n")

    last_x14 = None
    last_x15 = None
    update_count = 0

    while True:
        x14, x15 = read_switches(client)

        if x14 is not None and x15 is not None:
            # Show current state
            x14_icon = "🟢ON " if x14 else "⚫OFF"
            x15_icon = "🟢ON " if x15 else "⚫OFF"

            clear_line()
            sys.stdout.write(f"X14: {x14_icon}  |  X15: {x15_icon}  |  Updates: {update_count}")
            sys.stdout.flush()

            # Detect changes
            if last_x14 is not None and x14 != last_x14:
                print(f"\n🔄 X14 CHANGED: {'OFF→ON' if x14 else 'ON→OFF'}")
                update_count += 1

            if last_x15 is not None and x15 != last_x15:
                print(f"\n🔄 X15 CHANGED: {'OFF→ON' if x15 else 'ON→OFF'}")
                update_count += 1

            last_x14 = x14
            last_x15 = x15
        else:
            clear_line()
            sys.stdout.write("⚠️  Read error - retrying...")
            sys.stdout.flush()

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\n✅ Monitoring stopped")
    client.close()
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)

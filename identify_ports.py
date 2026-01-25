#!/usr/bin/env python3
"""Identify which USB port is which device"""

import subprocess

def main():
    print("="*70)
    print("USB PORT IDENTIFIER")
    print("="*70)

    for port in ['/dev/ttyUSB0', '/dev/ttyUSB1']:
        print(f"\n{port}:")
        try:
            result = subprocess.run(['udevadm', 'info', '-q', 'all', '-n', port],
                                  capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if any(x in line for x in ['ID_MODEL', 'ID_VENDOR', 'ID_SERIAL', 'usb']):
                    if '=' in line:
                        print(f"  {line.split('=')[0].strip()}: {line.split('=')[1].strip()}")
        except:
            pass

    print("\n" + "="*70)
    print("TO IDENTIFY WHICH IS RS485:")
    print("  1. Physically unplug the RS485 USB converter")
    print("  2. Run: ls -la /dev/ttyUSB*")
    print("  3. See which port disappeared")
    print("  4. That's your RS485 port!")
    print("="*70)

if __name__ == "__main__":
    main()

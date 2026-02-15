#!/usr/bin/env python3
"""Quick RS485 test after hardware fixes"""

import sys
from pymodbus.client import ModbusSerialClient

def quick_test(port, device_id=1, baudrate=9600):
    """Quick test of RS485 device"""
    print(f"\nQuick Test: {port}, ID={device_id}, Baud={baudrate}")
    print("-" * 50)
    
    try:
        client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=2.0
        )
        
        if not client.connect():
            print("❌ FAILED: Cannot open port")
            print(f"   Make sure {port} exists and nothing else is using it")
            return False
        
        print("✓ Port opened successfully")
        
        # Try reading
        response = client.read_holding_registers(
            address=192,
            count=2,
            device_id=device_id
        )
        
        client.close()
        
        if response.isError():
            print(f"❌ FAILED: Device not responding")
            print(f"   Error: {response}")
            print("\n   NEXT STEPS:")
            print("   1. Try swapping A and B wires")
            print("   2. Check DIP switches")
            print("   3. Try other USB port")
            return False
        
        # SUCCESS!
        print("✅ SUCCESS! Device is responding!")
        print(f"\n   Register 192: 0x{response.registers[0]:04x}")
        print(f"   Register 193: 0x{response.registers[1]:04x}")
        
        # Decode inputs
        reg0, reg1 = response.registers
        active = []
        for i in range(16):
            if (reg0 >> i) & 1:
                active.append(f"X{i:02d}")
        for i in range(16):
            if (reg1 >> i) & 1:
                active.append(f"X{i+16:02d}")
        
        if active:
            print(f"\n   Active inputs: {', '.join(active)}")
        else:
            print(f"\n   All inputs are LOW (inactive)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("="*50)
    print("QUICK RS485 TEST")
    print("="*50)
    
    # Test both ports with common configs
    configs = [
        ('/dev/ttyUSB0', 1, 9600),
        ('/dev/ttyUSB0', 2, 9600),
        ('/dev/ttyUSB1', 1, 9600),
        ('/dev/ttyUSB1', 2, 9600),
    ]
    
    for port, dev_id, baud in configs:
        if quick_test(port, dev_id, baud):
            print("\n" + "="*50)
            print("WORKING CONFIGURATION FOUND!")
            print("="*50)
            print(f"\nUpdate config/settings.json:")
            print(f'  "serial_port": "{port}",')
            print(f'  "baudrate": {baud},')
            print(f'  "modbus_device_id": {dev_id},')
            return 0
    
    print("\n" + "="*50)
    print("NO WORKING CONFIG FOUND")
    print("="*50)
    print("\nTry:")
    print("  1. Swap A/B wires")
    print("  2. Check DIP switches")
    print("  3. Run: sudo python3 ultra_rs485_scanner.py")
    return 1

if __name__ == "__main__":
    sys.exit(main())

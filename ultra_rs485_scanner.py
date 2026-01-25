#!/usr/bin/env python3
"""
Ultra-thorough RS485 Scanner
Tests both ports with extended configuration range
"""

import sys
import time
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

def test_config(port, baudrate, device_id, timeout=2.0, verbose=False):
    """Test a specific configuration"""
    if verbose:
        print(f"  Testing: Port={port}, Baud={baudrate}, ID={device_id}...", end='', flush=True)
    
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
            if verbose:
                print(" [Port locked]")
            return False
        
        # Try reading holding registers at address 192 (0xC0)
        response = client.read_holding_registers(
            address=192,
            count=2,
            device_id=device_id
        )
        
        client.close()
        
        if not response.isError():
            return response.registers
        
        if verbose:
            print(" [No response]")
        return False
        
    except ModbusException as e:
        if verbose:
            print(f" [Error: {str(e)[:30]}]")
        return False
    except Exception as e:
        if verbose:
            print(f" [Exception: {str(e)[:20]}]")
        return False

def scan_port_thoroughly(port, max_id=20):
    """Thoroughly scan a single port"""
    print(f"\n{'='*70}")
    print(f"SCANNING PORT: {port}")
    print(f"{'='*70}")
    
    baudrates = [9600, 19200, 4800, 38400, 57600, 115200]
    
    tested = 0
    found_configs = []
    
    for baudrate in baudrates:
        print(f"\n--- Testing at {baudrate} baud ---")
        
        # Quick test first 5 IDs
        for device_id in range(1, 6):
            result = test_config(port, baudrate, device_id, timeout=1.5, verbose=False)
            tested += 1
            
            if result:
                print(f"  ✅ FOUND! ID={device_id}, Registers: {[hex(r) for r in result]}")
                found_configs.append({
                    'port': port,
                    'baudrate': baudrate,
                    'device_id': device_id,
                    'registers': result
                })
                return found_configs
            
            # Show progress
            if device_id % 5 == 0:
                print(f"  Tested IDs 1-{device_id}... no response", end='\r', flush=True)
        
        # Extended scan if requested
        if max_id > 5:
            print(f"  Testing extended IDs 6-{max_id}...", end='', flush=True)
            for device_id in range(6, max_id + 1):
                result = test_config(port, baudrate, device_id, timeout=1.5, verbose=False)
                tested += 1
                
                if result:
                    print(f"\n  ✅ FOUND! ID={device_id}, Registers: {[hex(r) for r in result]}")
                    found_configs.append({
                        'port': port,
                        'baudrate': baudrate,
                        'device_id': device_id,
                        'registers': result
                    })
                    return found_configs
            print(" no response")
        
        print(f"  No device found at {baudrate} baud")
    
    print(f"\n❌ No working configuration found on {port} (tested {tested} configs)")
    return found_configs

def main():
    print("="*70)
    print("ULTRA-THOROUGH RS485 SCANNER")
    print("="*70)
    print("\nThis will test BOTH USB ports with multiple configurations")
    print("Testing Device IDs 1-20, Baudrates: 9600, 19200, 4800, 38400, 57600, 115200")
    print()
    
    # Check which ports exist
    import os
    available_ports = []
    for port in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2']:
        if os.path.exists(port):
            available_ports.append(port)
    
    if not available_ports:
        print("❌ ERROR: No /dev/ttyUSB* ports found!")
        print("Check if USB devices are connected")
        return 1
    
    print(f"Found ports: {', '.join(available_ports)}")
    print()
    
    # Scan each port thoroughly
    all_found = []
    
    for port in available_ports:
        configs = scan_port_thoroughly(port, max_id=20)
        all_found.extend(configs)
        
        if configs:
            # Found something, stop here
            break
    
    # Final report
    print("\n" + "="*70)
    print("SCAN COMPLETE")
    print("="*70)
    
    if all_found:
        print("\n✅✅✅ WORKING CONFIGURATION(S) FOUND! ✅✅✅\n")
        
        for idx, config in enumerate(all_found, 1):
            print(f"Configuration #{idx}:")
            print(f"  Port:        {config['port']}")
            print(f"  Baudrate:    {config['baudrate']}")
            print(f"  Device ID:   {config['device_id']}")
            print(f"  Registers:   {config['registers']}")
            print(f"  Reg 192:     0x{config['registers'][0]:04x} = {config['registers'][0]}")
            print(f"  Reg 193:     0x{config['registers'][1]:04x} = {config['registers'][1]}")
            print()
            
            # Decode inputs
            reg0 = config['registers'][0]
            reg1 = config['registers'][1]
            
            active_inputs = []
            for i in range(16):
                if (reg0 >> i) & 1:
                    active_inputs.append(f"X{i:02d}")
            for i in range(16):
                if (reg1 >> i) & 1:
                    active_inputs.append(f"X{i+16:02d}")
            
            if active_inputs:
                print(f"  Active inputs: {', '.join(active_inputs)}")
            else:
                print(f"  Active inputs: None (all LOW)")
            print()
        
        # Show config to update
        best = all_found[0]
        print("="*70)
        print("UPDATE YOUR config/settings.json:")
        print("="*70)
        print(f'''
In the "rs485" section, update these values:

  "serial_port": "{best['port']}",
  "baudrate": {best['baudrate']},
  "modbus_device_id": {best['device_id']},
        ''')
        return 0
    
    else:
        print("\n❌ NO WORKING CONFIGURATION FOUND ON ANY PORT")
        print("\nThis means:")
        print("  1. Device is not responding to Modbus requests")
        print("  2. Possible A/B wires swapped (try swapping physically)")
        print("  3. Device might be on a different baudrate not tested")
        print("  4. Device ID might be > 20 (very unusual)")
        print("  5. Hardware issue with RS485 converter or N4DIH32")
        print()
        print("NEXT STEPS:")
        print("  - Physically swap the A and B wires")
        print("  - Check DIP switches on N4DIH32 device")
        print("  - Verify which USB port is the RS485 (unplug to test)")
        print("  - Check if converter TX/RX LEDs flash when testing")
        return 1

if __name__ == "__main__":
    sys.exit(main())

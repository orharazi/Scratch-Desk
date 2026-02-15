#!/usr/bin/env python3
"""
Deep RS485 Modbus Diagnostic - Tests raw serial and Modbus
"""

import sys
import time
import serial
import subprocess
from pymodbus.client import ModbusSerialClient

def check_hardware():
    """Check hardware info"""
    print("="*70)
    print("HARDWARE CHECK")
    print("="*70)
    
    # USB devices
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        print("\nUSB Devices with Serial/UART:")
        for line in result.stdout.split('\n'):
            if 'CH340' in line or 'CH341' in line or 'Serial' in line:
                print(f"  {line}")
    except:
        pass
    
    # Serial ports
    print("\nSerial Ports:")
    try:
        result = subprocess.run(['ls', '-la', '/dev/ttyUSB*'], 
                              capture_output=True, text=True, shell=False,
                              stderr=subprocess.STDOUT)
        print(result.stdout)
    except:
        pass

def test_raw_serial(port, baudrate):
    """Test if port can send/receive ANY data"""
    print(f"\n--- Testing {port} at {baudrate} baud ---")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=2.0
        )
        
        print(f"  Port opened OK")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Send Modbus request: Device ID 1, FC 03, Addr 192, Count 2
        request = bytes([0x01, 0x03, 0x00, 0xC0, 0x00, 0x02, 0x44, 0x56])
        
        print(f"  Sending: {request.hex()}")
        ser.write(request)
        ser.flush()
        
        time.sleep(0.5)
        
        waiting = ser.in_waiting
        print(f"  Bytes in buffer: {waiting}")
        
        if waiting > 0:
            response = ser.read(waiting)
            print(f"  SUCCESS - Got response: {response.hex()}")
            ser.close()
            return True
        else:
            print(f"  NO RESPONSE")
            ser.close()
            return False
            
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_modbus(port, baudrate, device_id):
    """Test Modbus protocol"""
    print(f"  Testing Modbus: Port={port}, Baud={baudrate}, ID={device_id}")
    
    try:
        client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=3.0
        )
        
        if not client.connect():
            print(f"    Failed to open port")
            return False
        
        response = client.read_holding_registers(
            address=192,
            count=2,
            device_id=device_id
        )
        
        if not response.isError():
            print(f"    SUCCESS! Registers: {[hex(r) for r in response.registers]}")
            client.close()
            return True
        else:
            print(f"    Modbus error: {response}")
            client.close()
            return False
            
    except Exception as e:
        print(f"    Exception: {str(e)[:50]}")
        return False

def main():
    print("="*70)
    print("DEEP RS485 DIAGNOSTIC")
    print("="*70)
    
    # Phase 1: Hardware check
    check_hardware()
    
    # Phase 2: Raw serial test
    print("\n" + "="*70)
    print("PHASE 2: RAW SERIAL TEST")
    print("="*70)
    
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1']
    baudrates = [9600, 19200]
    
    raw_results = {}
    for port in ports:
        for baud in baudrates:
            key = f"{port}@{baud}"
            raw_results[key] = test_raw_serial(port, baud)
    
    # Phase 3: Modbus protocol test
    print("\n" + "="*70)
    print("PHASE 3: MODBUS PROTOCOL TEST")
    print("="*70)
    
    device_ids = [1, 2, 3]
    
    for port in ports:
        print(f"\nTesting port: {port}")
        for baud in [9600, 19200, 4800]:
            for dev_id in device_ids:
                if test_modbus(port, baud, dev_id):
                    print(f"\n{'='*70}")
                    print(f"FOUND WORKING CONFIG!")
                    print(f"  Port: {port}")
                    print(f"  Baudrate: {baud}")
                    print(f"  Device ID: {dev_id}")
                    print(f"{'='*70}")
                    return 0
                time.sleep(0.1)
    
    # Results
    print("\n" + "="*70)
    print("DIAGNOSTIC COMPLETE - NO WORKING CONFIG FOUND")
    print("="*70)
    
    print("\nRaw Serial Results:")
    got_any_data = False
    for config, result in raw_results.items():
        status = "GOT DATA" if result else "NO DATA"
        print(f"  {config}: {status}")
        if result:
            got_any_data = True
    
    print("\nRECOMMENDATIONS:")
    if not got_any_data:
        print("""
CRITICAL: No data received on ANY port at ANY baudrate!

This is a HARDWARE problem. Check:
  1. Is N4DIH32 powered on? (check LED)
  2. Are A/B wires connected correctly?
  3. Try swapping A and B wires
  4. Check if correct USB port (disconnect one device to test)
  5. Verify DIP switches for device ID
  6. Check RS485 converter TX/RX LEDs when sending
        """)
    else:
        print("""
Data received but Modbus protocol fails.

Possible issues:
  1. Wrong device ID (check DIP switches)
  2. Wrong baudrate setting on device
  3. Device may need different parity (E or O)
  4. Wrong register address
        """)
    
    return 1

if __name__ == "__main__":
    sys.exit(main())

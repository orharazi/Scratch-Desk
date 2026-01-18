#!/usr/bin/env python3
"""
Debug script to test edge sensor reading
"""

import sys
import time
sys.path.insert(0, '/home/orharazi/Scratch-Desk')

from hardware.implementations.real.real_hardware import RealHardware

def main():
    print("="*70)
    print("EDGE SENSOR DEBUG TEST")
    print("="*70)

    # Initialize hardware
    print("\n1. Initializing hardware...")
    hardware = RealHardware()

    if not hardware.initialize():
        print("✗ Failed to initialize hardware")
        return

    print("✓ Hardware initialized\n")

    # Wait for polling thread to initialize
    print("2. Waiting 2 seconds for polling thread to initialize...")
    time.sleep(2)

    # Check internal state
    if hasattr(hardware, 'gpio') and hardware.gpio:
        print("\n3. Checking internal switch_states dictionary:")
        switch_states = hardware.gpio.switch_states
        print(f"   Total keys: {len(switch_states)}")

        edge_sensors = ['x_left_edge', 'x_right_edge', 'y_top_edge', 'y_bottom_edge']
        print(f"\n   Edge sensor states:")
        for sensor in edge_sensors:
            if sensor in switch_states:
                state = switch_states[sensor]
                print(f"   ✓ {sensor}: {state} ({'TRIGGERED' if state else 'READY'})")
            else:
                print(f"   ✗ {sensor}: NOT FOUND in switch_states")

        print(f"\n   All switch_states keys:")
        for key in sorted(switch_states.keys()):
            print(f"      - {key}: {switch_states[key]}")

    # Test getter methods
    print("\n4. Testing hardware getter methods:")
    edge_methods = [
        ('get_x_left_edge_sensor', 'x_left_edge'),
        ('get_x_right_edge_sensor', 'x_right_edge'),
        ('get_y_top_edge_sensor', 'y_top_edge'),
        ('get_y_bottom_edge_sensor', 'y_bottom_edge')
    ]

    for method_name, sensor_name in edge_methods:
        if hasattr(hardware, method_name):
            state = getattr(hardware, method_name)()
            print(f"   ✓ {method_name}(): {state} ({'TRIGGERED' if state else 'READY'})")
        else:
            print(f"   ✗ {method_name}(): METHOD NOT FOUND")

    # Monitor for changes
    print("\n5. Monitoring for changes (10 seconds)...")
    print("   TRIGGER AN EDGE SENSOR NOW!\n")

    # Store initial states
    last_states = {}
    for method_name, sensor_name in edge_methods:
        if hasattr(hardware, method_name):
            last_states[sensor_name] = getattr(hardware, method_name)()

    start_time = time.time()
    poll_count = 0

    while time.time() - start_time < 10:
        poll_count += 1

        # Check for changes
        for method_name, sensor_name in edge_methods:
            if hasattr(hardware, method_name):
                current_state = getattr(hardware, method_name)()

                if sensor_name not in last_states or current_state != last_states[sensor_name]:
                    print(f"\n   🚨 CHANGE DETECTED! Poll #{poll_count}")
                    print(f"      Sensor: {sensor_name}")
                    print(f"      Changed from: {last_states.get(sensor_name, 'UNKNOWN')}")
                    print(f"      Changed to: {current_state}")
                    print(f"      Meaning: {'TRIGGERED' if current_state else 'READY'}\n")
                    last_states[sensor_name] = current_state

        time.sleep(0.1)  # 100ms = 10Hz

    print("\n6. Test complete")
    hardware.shutdown()
    print("="*70)

if __name__ == "__main__":
    main()

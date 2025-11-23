#!/usr/bin/env python3
import sys
import time
sys.path.insert(0, '/home/orharazi/Scratch-Desk')
from hardware.implementations.real.real_hardware import RealHardware

hw = RealHardware()
if not hw.initialize():
    print("Failed to init")
    sys.exit(1)

time.sleep(3)  # Wait for polling

print("\n=== Edge Sensor States ===")
for method in ['get_x_left_edge_sensor', 'get_x_right_edge_sensor', 'get_y_top_edge_sensor', 'get_y_bottom_edge_sensor']:
    state = getattr(hw, method)()
    print(f"{method}: {state}")

print("\n=== switch_states keys ===")
if hasattr(hw, 'gpio'):
    for key in sorted(hw.gpio.switch_states.keys()):
        print(f"  {key}: {hw.gpio.switch_states[key]}")

print("\n=== Monitoring for 5 seconds ===")
print("Trigger a sensor now!\n")

last = {}
for i in range(50):
    for method in ['get_x_left_edge_sensor', 'get_x_right_edge_sensor', 'get_y_top_edge_sensor', 'get_y_bottom_edge_sensor']:
        state = getattr(hw, method)()
        if method not in last or state != last[method]:
            print(f"CHANGE: {method} = {state}")
            last[method] = state
    time.sleep(0.1)

hw.shutdown()

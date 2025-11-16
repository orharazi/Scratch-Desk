#!/usr/bin/env python3
"""
Test script to verify multiplexer sensors are updating in the GUI.
This script helps debug the sensor state propagation from hardware to GUI.
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from hardware.implementations.real.real_hardware import RealHardware
from config.config import Config
from utils.logger_config import setup_logger

def test_mux_sensors():
    """Test multiplexer sensor reading and GUI updates"""

    # Setup logger
    logger = setup_logger(log_to_console=True, debug_mode=True)

    # Load config
    config = Config()

    # Create hardware instance
    hardware = RealHardware(logger=logger, config=config)

    print("\n" + "="*60)
    print("MULTIPLEXER SENSOR GUI UPDATE TEST")
    print("="*60)

    # Initialize hardware
    print("\n1. Initializing hardware...")
    if not hardware.initialize():
        print("ERROR: Failed to initialize hardware!")
        return False

    print("   ✓ Hardware initialized")
    print("   ✓ Polling thread should be running")

    # Give polling thread time to initialize all sensor states
    print("\n2. Waiting for sensor states to initialize (3 seconds)...")
    time.sleep(3)

    # Define multiplexer sensors to test
    mux_sensors = [
        "line_marker_up_sensor",
        "line_marker_down_sensor",
        "line_cutter_up_sensor",
        "line_cutter_down_sensor",
        "line_motor_left_up_sensor",
        "line_motor_left_down_sensor",
        "line_motor_right_up_sensor",
        "line_motor_right_down_sensor",
        "row_marker_up_sensor",
        "row_marker_down_sensor",
        "row_cutter_up_sensor",
        "row_cutter_down_sensor"
    ]

    print("\n3. Testing sensor getters (what GUI calls):")
    print("-" * 40)

    all_working = True
    for sensor in mux_sensors:
        getter_method = f"get_{sensor}"
        if hasattr(hardware, getter_method):
            try:
                state = getattr(hardware, getter_method)()
                state_str = "TRIGGERED" if state else "READY"
                print(f"   {sensor:<30} : {state_str}")

                # Check internal state
                if hasattr(hardware, 'gpio') and hardware.gpio:
                    switch_key = f"mux_{sensor}"
                    if switch_key in hardware.gpio.switch_states:
                        internal_state = hardware.gpio.switch_states[switch_key]
                        if internal_state != state:
                            print(f"      WARNING: Internal state mismatch! Internal={internal_state}, Getter={state}")
                            all_working = False
                    else:
                        print(f"      WARNING: No internal state found for {switch_key}")
                        print(f"      Available keys: {list(hardware.gpio.switch_states.keys())}")
                        all_working = False
            except Exception as e:
                print(f"   {sensor:<30} : ERROR - {str(e)}")
                all_working = False
        else:
            print(f"   {sensor:<30} : NO GETTER METHOD")
            all_working = False

    print("\n4. Monitoring for changes (press Ctrl+C to stop):")
    print("-" * 40)
    print("   Trigger sensors on the hardware to see state changes...")
    print("   The GUI should show these changes in real-time!\n")

    # Store last known states
    last_states = {}
    for sensor in mux_sensors:
        getter = f"get_{sensor}"
        if hasattr(hardware, getter):
            last_states[sensor] = getattr(hardware, getter)()

    try:
        while True:
            # Check for changes
            for sensor in mux_sensors:
                getter = f"get_{sensor}"
                if hasattr(hardware, getter):
                    current_state = getattr(hardware, getter)()
                    if sensor not in last_states or current_state != last_states[sensor]:
                        state_str = "TRIGGERED" if current_state else "READY"
                        old_str = "TRIGGERED" if last_states.get(sensor, False) else "READY"
                        print(f"   CHANGE: {sensor} : {old_str} → {state_str}")
                        last_states[sensor] = current_state

            time.sleep(0.025)  # Match optimized 40Hz polling rate

    except KeyboardInterrupt:
        print("\n\nTest stopped by user")

    print("\n" + "="*60)
    if all_working:
        print("✓ TEST PASSED: All sensors accessible and initialized")
        print("  The GUI should now show sensor state changes!")
    else:
        print("✗ TEST FAILED: Some sensors not properly initialized")
        print("  Check the warnings above for details")
    print("="*60)

    # Cleanup
    hardware.close()
    return all_working

if __name__ == "__main__":
    success = test_mux_sensors()
    sys.exit(0 if success else 1)
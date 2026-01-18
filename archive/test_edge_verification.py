#!/usr/bin/env python3
"""Quick test to verify edge sensors are working after fix"""

import sys
import time
sys.path.insert(0, '/home/orharazi/Scratch-Desk')

from hardware.implementations.real.raspberry_pi.raspberry_pi_gpio import RaspberryPiGPIO
from core.logger import get_logger

def main():
    logger = get_logger()

    logger.warning("\n" + "="*70)
    logger.warning("EDGE SENSOR VERIFICATION TEST - POST-FIX")
    logger.warning("="*70)
    logger.warning("This test verifies ALL 4 edge switches are now being monitored")
    logger.warning("")

    gpio = RaspberryPiGPIO()
    gpio.initialize()

    # Wait for polling thread
    logger.info("Waiting for polling thread to initialize...")
    time.sleep(1)

    # Check switch_states
    logger.warning("\nVerifying switch_states dictionary contains all 4 edge switches:")
    all_present = True
    for key in ['x_left_edge', 'x_right_edge', 'y_top_edge', 'y_bottom_edge']:
        if key in gpio.switch_states:
            state = gpio.switch_states[key]
            logger.success(f"  ✓ {key:15s}: PRESENT (current state: {'TRIGGERED' if state else 'READY'})")
        else:
            logger.error(f"  ✗ {key:15s}: MISSING from dictionary!")
            all_present = False

    if all_present:
        logger.success("\n✓✓✓ ALL 4 EDGE SWITCHES ARE BEING MONITORED! ✓✓✓")
    else:
        logger.error("\n✗✗✗ SOME EDGE SWITCHES ARE NOT BEING MONITORED! ✗✗✗")

    # Monitor for changes
    logger.warning("\nMonitoring for 10 seconds - PRESS EACH SWITCH TO TEST!")
    logger.warning("You should see state change messages when you press switches...")

    start_time = time.time()
    last_states = {k: gpio.switch_states.get(k) for k in ['x_left_edge', 'x_right_edge', 'y_top_edge', 'y_bottom_edge']}
    changes_detected = 0

    while time.time() - start_time < 10:
        for key in ['x_left_edge', 'x_right_edge', 'y_top_edge', 'y_bottom_edge']:
            current = gpio.switch_states.get(key)
            if current != last_states.get(key):
                changes_detected += 1
                logger.warning(f"\n>>> CHANGE #{changes_detected}: {key} changed from {last_states.get(key)} to {current}")
                last_states[key] = current
        time.sleep(0.025)  # 40Hz checking

    logger.info(f"\nTest complete. Detected {changes_detected} state changes.")

    gpio.cleanup()

    if changes_detected > 0:
        logger.success("✓ Edge switches are responding!")
    else:
        logger.warning("No changes detected - make sure to press the switches during the test")

if __name__ == "__main__":
    main()

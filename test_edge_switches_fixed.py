#!/usr/bin/env python3
"""
Test script to verify edge switches are being read and logged properly
"""

import time
import sys
from hardware.implementations.real.raspberry_pi.raspberry_pi_gpio import RaspberryPiGPIO
from core.logger import get_logger

logger = get_logger()

def main():
    logger.warning("="*80, category="test")
    logger.warning("EDGE SWITCH TEST - FIXED VERSION", category="test")
    logger.warning("="*80, category="test")
    logger.warning("This test will:", category="test")
    logger.warning("1. Initialize GPIO with BULLETPROOF logging", category="test")
    logger.warning("2. Show ALL edge switches being monitored", category="test")
    logger.warning("3. Log EVERY state change at WARNING level", category="test")
    logger.warning("4. Verify ALL 4 switches are polled every cycle", category="test")
    logger.warning("="*80, category="test")

    # Initialize GPIO
    gpio = RaspberryPiGPIO()

    try:
        if not gpio.initialize():
            logger.error("Failed to initialize GPIO!", category="test")
            return 1

        logger.warning("="*80, category="test")
        logger.warning("GPIO INITIALIZED - EDGE SWITCHES ACTIVE", category="test")
        logger.warning("="*80, category="test")

        # The polling thread is now running and will log at WARNING level
        logger.warning("PRESS ANY EDGE SWITCH NOW!", category="test")
        logger.warning("You should see WARNING level logs for EVERY press/release", category="test")
        logger.warning("="*80, category="test")

        # Monitor for 60 seconds
        test_duration = 60
        start_time = time.time()
        last_status_time = start_time

        while time.time() - start_time < test_duration:
            current_time = time.time()

            # Every 5 seconds, show current state
            if current_time - last_status_time > 5:
                last_status_time = current_time
                remaining = test_duration - (current_time - start_time)

                logger.warning(f"TEST STATUS: {remaining:.0f} seconds remaining", category="test")

                # Read and display all edge switch states
                states = []
                for sensor_name in ['x_left_edge', 'x_right_edge', 'y_top_edge', 'y_bottom_edge']:
                    state = gpio.read_sensor(sensor_name)
                    if state is not None:
                        states.append(f"{sensor_name}: {'TRIGGERED' if state else 'READY'}")
                    else:
                        states.append(f"{sensor_name}: ERROR")

                logger.warning(f"CURRENT STATES: {' | '.join(states)}", category="test")

                # Check polling thread health
                if gpio.polling_thread and gpio.polling_thread.is_alive():
                    logger.warning("POLLING THREAD: ACTIVE ✓", category="test")
                else:
                    logger.error("POLLING THREAD: DEAD ✗", category="test")

            time.sleep(0.1)

        logger.warning("="*80, category="test")
        logger.warning("TEST COMPLETE", category="test")
        logger.warning("="*80, category="test")

    finally:
        logger.warning("Cleaning up GPIO...", category="test")
        gpio.cleanup()
        logger.warning("Cleanup complete", category="test")

    return 0

if __name__ == "__main__":
    sys.exit(main())
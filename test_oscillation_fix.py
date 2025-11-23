#!/usr/bin/env python3
"""
Simple test to check if channels 6 and 11 are oscillating continuously
"""

import time
import sys
sys.path.insert(0, '/home/orharazi/Scratch-Desk')

from hardware.implementations.real.raspberry_pi.raspberry_pi_gpio import RaspberryPiGPIO
from core.logger import get_logger

def main():
    logger = get_logger()

    logger.info("="*70, category="test")
    logger.info("OSCILLATION FIX TEST - Monitoring channels 6 & 11", category="test")
    logger.info("="*70, category="test")

    # Initialize GPIO interface
    logger.info("Initializing GPIO interface...", category="test")
    gpio = RaspberryPiGPIO()

    try:
        if not gpio.initialize():
            logger.error("Failed to initialize GPIO", category="test")
            return 1

        # Wait for system to stabilize
        logger.info("Waiting 5 seconds for system to stabilize...", category="test")
        time.sleep(5)

        # Monitor channels 6 and 11 for oscillations
        logger.info("\nMonitoring channels 6 & 11 for oscillations (30 seconds)...", category="test")
        logger.info("If you see OSCILLATION DETECTED warnings, the fix is NOT working", category="test")
        logger.info("-"*70, category="test")

        # Get initial states
        initial_states = gpio.get_all_sensor_states()
        ch6_sensor = 'row_marker_down_sensor'
        ch11_sensor = 'line_motor_right_up_sensor'

        ch6_state = initial_states.get(ch6_sensor, False)
        ch11_state = initial_states.get(ch11_sensor, False)

        logger.info(f"Initial states:", category="test")
        logger.info(f"  Channel 6 ({ch6_sensor}): {'TRIGGERED' if ch6_state else 'READY'}", category="test")
        logger.info(f"  Channel 11 ({ch11_sensor}): {'TRIGGERED' if ch11_state else 'READY'}", category="test")
        logger.info("-"*70, category="test")

        # Track oscillations
        oscillations = {ch6_sensor: 0, ch11_sensor: 0}
        last_states = {ch6_sensor: ch6_state, ch11_sensor: ch11_state}

        start_time = time.time()
        check_count = 0

        while time.time() - start_time < 30:  # Monitor for 30 seconds
            check_count += 1
            current_states = gpio.get_all_sensor_states()

            # Check channel 6
            current_ch6 = current_states.get(ch6_sensor, False)
            if current_ch6 != last_states[ch6_sensor]:
                oscillations[ch6_sensor] += 1
                elapsed = time.time() - start_time
                logger.warning(
                    f"[{elapsed:.1f}s] Channel 6 oscillation #{oscillations[ch6_sensor]}: "
                    f"{'READY' if last_states[ch6_sensor] else 'TRIGGERED'} -> "
                    f"{'READY' if current_ch6 else 'TRIGGERED'}",
                    category="test"
                )
                last_states[ch6_sensor] = current_ch6

            # Check channel 11
            current_ch11 = current_states.get(ch11_sensor, False)
            if current_ch11 != last_states[ch11_sensor]:
                oscillations[ch11_sensor] += 1
                elapsed = time.time() - start_time
                logger.warning(
                    f"[{elapsed:.1f}s] Channel 11 oscillation #{oscillations[ch11_sensor]}: "
                    f"{'READY' if last_states[ch11_sensor] else 'TRIGGERED'} -> "
                    f"{'READY' if current_ch11 else 'TRIGGERED'}",
                    category="test"
                )
                last_states[ch11_sensor] = current_ch11

            time.sleep(0.1)  # Check every 100ms

        # Results
        logger.info("\n" + "="*70, category="test")
        logger.info("TEST RESULTS", category="test")
        logger.info("="*70, category="test")

        total_oscillations = sum(oscillations.values())
        logger.info(f"Channel 6 oscillations: {oscillations[ch6_sensor]}", category="test")
        logger.info(f"Channel 11 oscillations: {oscillations[ch11_sensor]}", category="test")
        logger.info(f"Total oscillations: {total_oscillations}", category="test")

        if total_oscillations > 5:  # Allow a few transitions during startup
            logger.error(f"\nFAILED: {total_oscillations} oscillations detected!", category="test")
            logger.error("The channels are still oscillating continuously", category="test")
            return 1
        else:
            logger.success(f"\nSUCCESS: Only {total_oscillations} transitions detected", category="test")
            logger.success("This is within normal limits - the fix appears to be working!", category="test")
            return 0

    except Exception as e:
        logger.error(f"Test failed with error: {e}", category="test")
        return 1
    finally:
        logger.info("\nCleaning up GPIO...", category="test")
        gpio.cleanup()
        logger.info("Test complete", category="test")

if __name__ == "__main__":
    sys.exit(main())
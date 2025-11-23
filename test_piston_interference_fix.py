#!/usr/bin/env python3
"""
COMPREHENSIVE TEST for the persistent false positive fix

This script specifically tests that channels 6 and 11 do NOT show
persistent oscillations after triggering the line_marker_piston.

The comprehensive fix includes:
1. Enhanced multiplexer reset with GPIO pin re-initialization
2. State dictionary cleanup to remove corrupted values
3. Burn-in reads to flush transients
4. Extended stabilization delays
"""

import time
import sys
sys.path.insert(0, '/home/orharazi/Scratch-Desk')

from hardware.implementations.real.raspberry_pi.raspberry_pi_gpio import RaspberryPiGPIO
from core.logger import get_logger

def main():
    logger = get_logger()

    logger.info("="*70, category="test")
    logger.info("COMPREHENSIVE PERSISTENT FALSE POSITIVE FIX TEST", category="test")
    logger.info("="*70, category="test")
    logger.info("Testing that channels 6 & 11 do NOT oscillate after piston ops", category="test")
    logger.info("", category="test")
    logger.info("THE COMPREHENSIVE FIX:", category="test")
    logger.info("- Reinitializes switch_states dictionary", category="test")
    logger.info("- Re-establishes GPIO pin modes", category="test")
    logger.info("- Performs burn-in reads on problematic channels", category="test")
    logger.info("- Uses extended stabilization delays", category="test")
    logger.info("="*70, category="test")

    # Initialize GPIO interface
    logger.info("\nInitializing GPIO interface...", category="test")
    gpio = RaspberryPiGPIO()

    try:
        if not gpio.initialize():
            logger.error("Failed to initialize GPIO", category="test")
            return 1

        # Give polling thread time to stabilize
        logger.info("Waiting for sensor polling to stabilize...", category="test")
        time.sleep(3)

        # Test all pistons
        pistons_to_test = [
            "line_marker_piston",
            "line_cutter_piston",
            "line_motor_piston",
            "row_marker_piston",
            "row_cutter_piston"
        ]

        logger.info("\n" + "="*70, category="test")
        logger.info("STARTING PISTON INTERFERENCE TESTS", category="test")
        logger.info("="*70, category="test")

        for piston_name in pistons_to_test:
            logger.info(f"\nTesting piston: {piston_name}", category="test")
            logger.info("-"*50, category="test")

            # Record initial sensor states
            initial_states = gpio.get_all_sensor_states()
            mux_sensors = {k: v for k, v in initial_states.items()
                          if k in gpio.multiplexer_config.get('channels', {})}

            logger.info(f"Initial multiplexer sensor states ({len(mux_sensors)} sensors):", category="test")
            for sensor, state in mux_sensors.items():
                logger.info(f"  {sensor:30s}: {'TRIGGERED' if state else 'READY'}", category="test")

            # Test piston DOWN
            logger.info(f"\nSetting {piston_name} DOWN...", category="test")
            gpio.set_piston(piston_name, "down")

            # Give time for any false changes to appear
            time.sleep(0.5)

            # Check for false positives
            after_down_states = gpio.get_all_sensor_states()
            mux_after_down = {k: v for k, v in after_down_states.items()
                             if k in gpio.multiplexer_config.get('channels', {})}

            false_positives_down = []
            for sensor in mux_sensors:
                if mux_sensors[sensor] != mux_after_down[sensor]:
                    false_positives_down.append(sensor)
                    logger.error(f"  FALSE POSITIVE: {sensor} changed from "
                               f"{'TRIGGERED' if mux_sensors[sensor] else 'READY'} to "
                               f"{'TRIGGERED' if mux_after_down[sensor] else 'READY'}",
                               category="test")

            if not false_positives_down:
                logger.success(f"  No false positives after {piston_name} DOWN", category="test")
            else:
                logger.error(f"  {len(false_positives_down)} FALSE POSITIVES detected!", category="test")

            # Test piston UP
            logger.info(f"\nSetting {piston_name} UP...", category="test")
            gpio.set_piston(piston_name, "up")

            # Give time for any false changes to appear
            time.sleep(0.5)

            # Check for false positives
            after_up_states = gpio.get_all_sensor_states()
            mux_after_up = {k: v for k, v in after_up_states.items()
                           if k in gpio.multiplexer_config.get('channels', {})}

            false_positives_up = []
            for sensor in mux_sensors:
                # Compare with initial state (before any piston movement)
                if mux_sensors[sensor] != mux_after_up[sensor]:
                    false_positives_up.append(sensor)
                    logger.error(f"  FALSE POSITIVE: {sensor} changed from "
                               f"{'TRIGGERED' if mux_sensors[sensor] else 'READY'} to "
                               f"{'TRIGGERED' if mux_after_up[sensor] else 'READY'}",
                               category="test")

            if not false_positives_up:
                logger.success(f"  No false positives after {piston_name} UP", category="test")
            else:
                logger.error(f"  {len(false_positives_up)} FALSE POSITIVES detected!", category="test")

            # Summary for this piston
            if not false_positives_down and not false_positives_up:
                logger.success(f"\n  PASSED: {piston_name} - No interference detected", category="test")
            else:
                total_errors = len(false_positives_down) + len(false_positives_up)
                logger.error(f"\n  FAILED: {piston_name} - {total_errors} false positives", category="test")

        # CRITICAL TEST: Monitor channels 6 & 11 for persistent oscillations
        logger.info("\n" + "="*70, category="test")
        logger.info("CRITICAL: PERSISTENT OSCILLATION TEST", category="test")
        logger.info("Monitoring channels 6 & 11 after line_marker_piston trigger", category="test")
        logger.info("="*70, category="test")

        # Get baseline for critical channels
        critical_channels = {
            'row_marker_down_sensor': 6,
            'line_motor_right_up_sensor': 11
        }

        logger.info("\nGetting baseline states for critical channels...", category="test")
        baseline_states = {}
        for sensor_name, channel in critical_channels.items():
            state = gpio.get_all_sensor_states().get(sensor_name, False)
            baseline_states[sensor_name] = state
            logger.info(f"  Channel {channel} ({sensor_name}): {'TRIGGERED' if state else 'READY'}", category="test")

        # Trigger the problematic piston
        logger.info("\nTriggering line_marker_piston (GPIO 11) - the problematic piston...", category="test")
        gpio.set_piston("line_marker_piston", "down")
        time.sleep(0.5)
        gpio.set_piston("line_marker_piston", "up")

        # Monitor for persistent oscillations
        logger.info("\nMonitoring for oscillations (20 seconds)...", category="test")
        oscillation_counts = {name: 0 for name in critical_channels.keys()}
        last_states = baseline_states.copy()

        start_time = time.time()
        check_count = 0

        while time.time() - start_time < 20:  # Monitor for 20 seconds
            check_count += 1
            current_states = {}

            for sensor_name in critical_channels.keys():
                current = gpio.get_all_sensor_states().get(sensor_name, False)
                current_states[sensor_name] = current

                if current != last_states[sensor_name]:
                    oscillation_counts[sensor_name] += 1
                    elapsed = time.time() - start_time
                    logger.warning(
                        f"  [{elapsed:.1f}s] Channel {critical_channels[sensor_name]} ({sensor_name}) "
                        f"oscillated: {'READY' if last_states[sensor_name] else 'TRIGGERED'} -> "
                        f"{'READY' if current else 'TRIGGERED'} (oscillation #{oscillation_counts[sensor_name]})",
                        category="test"
                    )

            last_states = current_states
            time.sleep(0.3)  # Check every 300ms

        # Analyze results
        logger.info("\n" + "="*70, category="test")
        logger.info("OSCILLATION TEST RESULTS", category="test")
        logger.info("="*70, category="test")

        total_oscillations = sum(oscillation_counts.values())
        for sensor_name, count in oscillation_counts.items():
            channel = critical_channels[sensor_name]
            if count > 0:
                logger.error(f"  Channel {channel} ({sensor_name}): {count} oscillations DETECTED", category="test")
            else:
                logger.success(f"  Channel {channel} ({sensor_name}): STABLE - no oscillations", category="test")

        if total_oscillations > 0:
            logger.error(f"\nFAILURE: {total_oscillations} total oscillations detected!", category="test")
            logger.error("The fix is NOT working - channels are still showing persistent false positives", category="test")
            rapid_errors = ["oscillations_detected"]
        else:
            logger.success("\nSUCCESS: No oscillations detected on critical channels!", category="test")
            logger.success("The comprehensive fix has eliminated the persistent false positives", category="test")
            rapid_errors = []

        # Final summary
        logger.info("\n" + "="*70, category="test")
        logger.info("TEST COMPLETE", category="test")
        logger.info("="*70, category="test")

        if rapid_errors:
            logger.error("RESULT: FIX NOT WORKING - False positives still occurring", category="test")
            logger.error("Check electrical connections and consider increasing delays", category="test")
            return 1
        else:
            logger.success("RESULT: FIX IS WORKING - No false positives detected!", category="test")
            logger.success("The multiplexer reset successfully prevents GPIO interference", category="test")
            return 0

    except Exception as e:
        logger.error(f"Test failed with error: {e}", category="test")
        return 1
    finally:
        logger.info("\nCleaning up GPIO...", category="test")
        gpio.cleanup()
        logger.info("Test script complete", category="test")

if __name__ == "__main__":
    sys.exit(main())
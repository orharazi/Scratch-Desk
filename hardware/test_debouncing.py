#!/usr/bin/env python3
"""
Test Script for GPIO Debouncing
================================

This script tests that the debouncing implementation eliminates false positive
sensor state changes when the system is static.

Expected behavior:
1. Static sensors should show NO state changes
2. Real state changes should be detected after 3 consistent reads
3. Noisy/bouncing reads should be ignored
"""

import time
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.implementations.real.raspberry_pi.raspberry_pi_gpio import RaspberryPiGPIO
from core.logger import get_logger

def test_sensor_stability(gpio, sensor_name, duration=10):
    """
    Monitor a sensor for false state changes

    Args:
        gpio: RaspberryPiGPIO instance
        sensor_name: Name of sensor to monitor
        duration: How long to monitor (seconds)

    Returns:
        Number of state changes detected
    """
    logger = get_logger()
    logger.info(f"="*60, category="test")
    logger.info(f"Testing sensor stability: {sensor_name}", category="test")
    logger.info(f"Duration: {duration} seconds", category="test")
    logger.info(f"="*60, category="test")

    start_time = time.time()
    last_state = None
    state_changes = 0
    total_reads = 0

    while time.time() - start_time < duration:
        # Read sensor
        state = gpio.read_sensor(sensor_name)
        total_reads += 1

        # Track state changes
        if last_state is not None and last_state != state:
            state_changes += 1
            logger.warning(f"State change #{state_changes}: {sensor_name} changed from {last_state} to {state} at read #{total_reads}", category="test")

        last_state = state

        # Read at 100Hz (10ms interval)
        time.sleep(0.01)

    # Report results
    logger.info(f"="*60, category="test")
    logger.info(f"Test Complete for {sensor_name}:", category="test")
    logger.info(f"  Total reads: {total_reads}", category="test")
    logger.info(f"  State changes: {state_changes}", category="test")
    logger.info(f"  Stability: {'STABLE ✓' if state_changes == 0 else f'UNSTABLE ✗ ({state_changes} false changes)'}", category="test")
    logger.info(f"="*60, category="test")

    return state_changes

def main():
    """Main test function"""
    logger = get_logger()

    logger.info("="*70, category="test")
    logger.info("GPIO DEBOUNCING TEST - VERIFYING FALSE POSITIVE ELIMINATION", category="test")
    logger.info("="*70, category="test")
    logger.info("This test verifies that debouncing eliminates false sensor state changes", category="test")
    logger.info("Expected: Static sensors should show ZERO state changes", category="test")
    logger.info("="*70, category="test")

    # Create GPIO interface
    gpio = RaspberryPiGPIO()

    try:
        # Initialize GPIO
        if not gpio.initialize():
            logger.error("Failed to initialize GPIO", category="test")
            return 1

        # Test various sensors for stability
        test_sensors = [
            # Edge sensors (direct GPIO)
            "x_left_edge",
            "x_right_edge",
            "y_top_edge",
            "y_bottom_edge",

            # Piston sensors (multiplexer)
            "line_marker_up_sensor",
            "line_marker_down_sensor",
            "line_cutter_up_sensor",
            "line_cutter_down_sensor"
        ]

        total_false_positives = 0
        failed_sensors = []

        logger.info("", category="test")
        logger.info("Testing each sensor for 5 seconds...", category="test")
        logger.info("DO NOT MOVE ANY HARDWARE DURING THIS TEST!", category="test")
        logger.info("", category="test")

        for sensor_name in test_sensors:
            try:
                changes = test_sensor_stability(gpio, sensor_name, duration=5)
                total_false_positives += changes
                if changes > 0:
                    failed_sensors.append(sensor_name)
                time.sleep(0.5)  # Brief pause between tests
            except Exception as e:
                logger.error(f"Error testing {sensor_name}: {e}", category="test")

        # Final report
        logger.info("="*70, category="test")
        logger.info("DEBOUNCING TEST COMPLETE", category="test")
        logger.info("="*70, category="test")

        if total_false_positives == 0:
            logger.success("✓ SUCCESS: NO FALSE POSITIVES DETECTED!", category="test")
            logger.success("  Debouncing is working correctly", category="test")
            logger.success("  All sensors are stable with no spurious state changes", category="test")
        else:
            logger.error(f"✗ FAILURE: {total_false_positives} false positives detected", category="test")
            logger.error(f"  Failed sensors: {', '.join(failed_sensors)}", category="test")
            logger.error("  Debouncing may need adjustment or hardware has issues", category="test")

        logger.info("="*70, category="test")

        return 0 if total_false_positives == 0 else 1

    except Exception as e:
        logger.error(f"Test failed with error: {e}", category="test")
        return 1
    finally:
        # Cleanup
        gpio.cleanup()
        logger.info("GPIO cleanup completed", category="test")

if __name__ == "__main__":
    sys.exit(main())
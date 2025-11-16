#!/usr/bin/env python3
"""
Edge Sensor Test Script
Tests edge sensor detection on real hardware with detailed diagnostics
"""

import sys
import time

# Add the project root to Python path
sys.path.insert(0, '/home/orharazi/Scratch-Desk')

from hardware.implementations.real.real_hardware import RealHardware
from hardware.tools.utils import get_logger

def test_edge_sensors():
    """Test edge sensor detection with detailed logging"""

    logger = get_logger()
    logger.info("="*80)
    logger.info("EDGE SENSOR DIAGNOSTIC TEST")
    logger.info("="*80)

    # Initialize hardware
    logger.info("Initializing hardware...")
    hardware = RealHardware()

    if not hardware.initialize():
        logger.error("Failed to initialize hardware!")
        return False

    logger.success("Hardware initialized successfully!")
    logger.info("="*80)

    # Test configuration
    logger.info("EDGE SENSOR CONFIGURATION:")
    logger.info("  - x_left_edge: GPIO pin 4")
    logger.info("  - x_right_edge: GPIO pin 17")
    logger.info("  - y_top_edge: GPIO pin 7")
    logger.info("  - y_bottom_edge: GPIO pin 8")
    logger.info("  - Pull resistor: PULL-DOWN (expects HIGH when triggered)")
    logger.info("="*80)

    logger.info("Starting edge sensor monitoring...")
    logger.info("INSTRUCTIONS:")
    logger.info("  1. Manually trigger each edge sensor on the machine")
    logger.info("  2. Watch for state changes in the logs")
    logger.info("  3. Press Ctrl+C to stop")
    logger.info("")

    # Monitor edge sensors
    last_states = {
        'x_left_edge': None,
        'x_right_edge': None,
        'y_top_edge': None,
        'y_bottom_edge': None
    }

    poll_count = 0
    last_status_time = time.time()

    try:
        while True:
            poll_count += 1

            # Read all edge sensors
            current_states = {
                'x_left_edge': hardware.get_x_left_edge_sensor(),
                'x_right_edge': hardware.get_x_right_edge_sensor(),
                'y_top_edge': hardware.get_y_top_edge_sensor(),
                'y_bottom_edge': hardware.get_y_bottom_edge_sensor()
            }

            # Check for changes
            for sensor_name, current_state in current_states.items():
                last_state = last_states[sensor_name]

                if last_state is not None and current_state != last_state:
                    # State changed!
                    logger.warning("="*60)
                    logger.warning(f"🚨 EDGE SENSOR CHANGE DETECTED! 🚨")
                    logger.warning(f"   Sensor: {sensor_name.upper()}")
                    logger.warning(f"   Changed from: {'TRIGGERED' if last_state else 'READY'}")
                    logger.warning(f"   Changed to: {'TRIGGERED' if current_state else 'READY'}")
                    logger.warning(f"   Poll count: {poll_count}")
                    logger.warning("="*60)

                last_states[sensor_name] = current_state

            # Print status every 3 seconds
            current_time = time.time()
            if current_time - last_status_time > 3.0:
                last_status_time = current_time
                logger.info("Current Edge Sensor States:")
                logger.info(f"  X-Left: {'TRIGGERED' if current_states['x_left_edge'] else 'READY'} | X-Right: {'TRIGGERED' if current_states['x_right_edge'] else 'READY'}")
                logger.info(f"  Y-Top: {'TRIGGERED' if current_states['y_top_edge'] else 'READY'} | Y-Bottom: {'TRIGGERED' if current_states['y_bottom_edge'] else 'READY'}")
                logger.info(f"  (Polls: {poll_count}, waiting for changes...)")

            # Small delay to avoid overwhelming the system
            time.sleep(0.025)  # 25ms = 40Hz polling

    except KeyboardInterrupt:
        logger.info("\nStopping edge sensor test...")

    # Cleanup
    hardware.cleanup()
    logger.success("Edge sensor test completed")
    return True

if __name__ == "__main__":
    test_edge_sensors()
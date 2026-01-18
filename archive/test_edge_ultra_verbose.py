#!/usr/bin/env python3

"""
ULTRA-VERBOSE Edge Switch Test
===============================

This script tests edge switch detection with MAXIMUM verbosity.
It will show EVERY GPIO read and help diagnose why changes aren't detected.

Run this and PRESS THE EDGE SWITCHES to see if they trigger!
"""

import sys
import time
from hardware.implementations.real.raspberry_pi.raspberry_pi_gpio import RaspberryPiGPIO
from core.logger import get_logger

def main():
    logger = get_logger()

    logger.warning("="*80)
    logger.warning("ULTRA-VERBOSE EDGE SWITCH TEST")
    logger.warning("="*80)
    logger.warning("This test will show EVERY GPIO read for edge switches")
    logger.warning("Press Ctrl+C to stop")
    logger.warning("="*80)

    # Initialize GPIO
    gpio = RaspberryPiGPIO()

    try:
        if not gpio.initialize():
            logger.error("Failed to initialize GPIO!")
            return 1

        logger.warning("\n" + "="*80)
        logger.warning("INITIALIZATION COMPLETE")
        logger.warning("The polling thread is now running with ULTRA-VERBOSE logging")
        logger.warning("="*80)
        logger.warning("INSTRUCTIONS:")
        logger.warning("1. Watch the logs for the first 20 poll cycles (ultra-detailed)")
        logger.warning("2. PRESS each edge switch one by one")
        logger.warning("3. Look for 'EDGE SWITCH STATE CHANGE DETECTED!' messages")
        logger.warning("4. If no changes detected, check the raw GPIO values")
        logger.warning("5. Press Ctrl+C to exit")
        logger.warning("="*80)

        # Keep running and let the polling thread do its work
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    finally:
        logger.info("Cleaning up GPIO...")
        gpio.cleanup()
        logger.info("Test complete!")

    return 0

if __name__ == "__main__":
    sys.exit(main())
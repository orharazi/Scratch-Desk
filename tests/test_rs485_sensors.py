#!/usr/bin/env python3
"""
Quick test script to verify RS485 sensor reads
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hardware.implementations.real.raspberry_pi.raspberry_pi_gpio import RaspberryPiGPIO
from core.logger import get_logger

logger = get_logger()

def main():
    logger.info("="*60, category="hardware")
    logger.info("RS485 Modbus Sensor Test", category="hardware")
    logger.info("="*60, category="hardware")

    # Initialize GPIO
    gpio = RaspberryPiGPIO()

    if not gpio.initialize():
        logger.error("Failed to initialize GPIO", category="hardware")
        return

    logger.info("GPIO initialized successfully!", category="hardware")
    logger.info("Monitoring RS485 sensors for 30 seconds...", category="hardware")
    logger.info("TRIGGER A SENSOR NOW to see the change!", category="hardware")
    logger.info("="*60, category="hardware")

    # Monitor for 30 seconds
    start_time = time.time()
    while time.time() - start_time < 30:
        time.sleep(0.5)  # Give polling thread time to work

    logger.info("="*60, category="hardware")
    logger.info("Test complete - check the logs above for sensor changes", category="hardware")
    logger.info("="*60, category="hardware")

    # Cleanup
    gpio.cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user", category="hardware")
    except Exception as e:
        logger.error(f"Test failed: {e}", category="hardware")

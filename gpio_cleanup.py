#!/usr/bin/env python3
"""
GPIO Cleanup Script
Releases all GPIO pins so tests can run
"""

try:
    import RPi.GPIO as GPIO
    print("Cleaning up GPIO...")
    GPIO.cleanup()
    print("✓ GPIO cleaned up successfully")
except Exception as e:
    print(f"GPIO cleanup: {e}")

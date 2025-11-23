#!/usr/bin/env python3
"""
Realtime Edge Switch Test - Direct GPIO Monitoring
This script reads edge switches directly every 25ms and shows state changes in realtime
"""

import time
import RPi.GPIO as GPIO

# Edge switch pins from settings.json
EDGE_SWITCHES = {
    "x_left_edge": 4,
    "x_right_edge": 17,
    "y_top_edge": 7,
    "y_bottom_edge": 8
}

print("="*70)
print("🔧 REALTIME EDGE SWITCH TEST 🔧")
print("="*70)
print("This script monitors edge switches in REALTIME with zero debouncing.")
print("Testing configuration:")
print("  - Pull-UP resistors (switches connect to GND when pressed)")
print("  - Inverted logic: LOW = pressed/triggered, HIGH = open/ready")
print("  - Poll rate: 40 Hz (every 25ms)")
print("="*70)

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup edge switch pins with pull-UP resistors
print("\nInitializing edge switches...")
for name, pin in EDGE_SWITCHES.items():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    print(f"  ✓ {name:20s} on GPIO pin {pin} (pull-UP)")

# Read initial states
print("\n" + "="*70)
print("INITIAL STATES:")
print("="*70)
states = {}
for name, pin in EDGE_SWITCHES.items():
    raw = GPIO.input(pin)
    inverted = not raw  # Invert: LOW = pressed
    states[name] = inverted
    print(f"  {name:20s}: raw={'HIGH' if raw else 'LOW '} → {'TRIGGERED ✓' if inverted else 'READY    '}")

print("\n" + "="*70)
print("🚨 MONITORING FOR CHANGES (Press Ctrl+C to stop) 🚨")
print("="*70)
print("Press each edge switch to test...")
print()

poll_count = 0
try:
    while True:
        poll_count += 1

        # Read all switches
        for name, pin in EDGE_SWITCHES.items():
            raw = GPIO.input(pin)
            inverted = not raw  # Invert: LOW = pressed

            # Check for state change
            old_state = states.get(name)
            if inverted != old_state:
                states[name] = inverted

                # Print BIG WARNING on change
                print("="*70)
                print(f"🚨🚨🚨 SWITCH CHANGED: {name.upper()} 🚨🚨🚨")
                print("="*70)
                print(f"  GPIO Pin: {pin}")
                print(f"  Raw GPIO: {'HIGH' if raw else 'LOW'}")
                print(f"  Previous: {'TRIGGERED' if old_state else 'READY'}")
                print(f"  Current:  {'TRIGGERED' if inverted else 'READY'}")
                print(f"  Poll #:   {poll_count}")
                print("="*70)
                print()

        # Status update every 2 seconds
        if poll_count % 80 == 0:  # 80 polls * 25ms = 2 seconds
            print(f"[Poll #{poll_count}] Current states:", end=" ")
            for name in EDGE_SWITCHES.keys():
                state = states.get(name, False)
                print(f"{name}={'T' if state else 'R'}", end=" ")
            print()

        time.sleep(0.025)  # 25ms = 40 Hz polling

except KeyboardInterrupt:
    print("\n\n" + "="*70)
    print("Test stopped by user")
    print("="*70)

finally:
    print("\nCleaning up GPIO...")
    GPIO.cleanup()
    print("✓ Done")

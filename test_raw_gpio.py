#!/usr/bin/env python3
"""
ULTRA-SIMPLE RAW GPIO TEST FOR EDGE SENSORS
============================================
Direct GPIO reads with NO abstraction, NO debouncing, NO threads
Just pure GPIO.input() calls to verify hardware works
"""

import time
import sys

# Try to import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    print("✓ RPi.GPIO imported successfully")
    print(f"  Module: {GPIO.__module__ if hasattr(GPIO, '__module__') else 'Unknown'}")
    print(f"  Type: {type(GPIO).__name__}")
except ImportError as e:
    print("✗ FAILED to import RPi.GPIO")
    print(f"  Error: {e}")
    print("  Are you running on a Raspberry Pi?")
    print("  Is RPi.GPIO installed? (sudo pip3 install RPi.GPIO)")
    sys.exit(1)

# Edge sensor pins from config
EDGE_PINS = {
    'x_left_edge': 4,
    'x_right_edge': 17,
    'y_top_edge': 7,
    'y_bottom_edge': 8
}

def main():
    print("\n" + "="*70)
    print("ULTRA-SIMPLE EDGE SENSOR GPIO TEST")
    print("="*70)
    print("This test reads GPIO pins 4, 17, 7, 8 directly every 100ms")
    print("NO debouncing, NO threads, NO abstraction - just raw GPIO.input()")
    print("="*70 + "\n")

    # Setup GPIO
    print("Configuring GPIO...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Test 1: PULL-DOWN configuration (expecting HIGH when triggered)
    print("\n" + "="*70)
    print("TEST 1: PULL-DOWN RESISTORS (Current Configuration)")
    print("Expecting: LOW (0) = Not triggered, HIGH (1) = Triggered")
    print("="*70)

    # Setup pins with pull-down
    for name, pin in EDGE_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        print(f"  {name:15s}: GPIO {pin:2d} configured with PULL-DOWN")

    print("\nInitial readings (5 samples per pin):")
    for name, pin in EDGE_PINS.items():
        readings = []
        for _ in range(5):
            readings.append(GPIO.input(pin))
            time.sleep(0.002)  # 2ms between reads

        unique = set(readings)
        if len(unique) == 1:
            state = readings[0]
            print(f"  {name:15s} [GPIO {pin:2d}]: {state} ({'HIGH' if state else 'LOW'}) - STABLE")
        else:
            print(f"  {name:15s} [GPIO {pin:2d}]: UNSTABLE! {readings}")

    print("\nCONTINUOUS MONITORING (100ms interval)")
    print("Press Ctrl+C to switch to PULL-UP test")
    print("-" * 50)

    last_states = {}
    for name, pin in EDGE_PINS.items():
        last_states[name] = GPIO.input(pin)

    poll_count = 0
    last_status_time = time.time()

    try:
        while True:
            poll_count += 1

            # Read all pins
            for name, pin in EDGE_PINS.items():
                current = GPIO.input(pin)

                # Check for change
                if current != last_states[name]:
                    print("\n" + "🚨"*30)
                    print(f"CHANGE DETECTED! Poll #{poll_count}")
                    print(f"  Sensor: {name.upper()}")
                    print(f"  GPIO Pin: {pin}")
                    print(f"  Changed from: {last_states[name]} ({'HIGH' if last_states[name] else 'LOW'})")
                    print(f"  Changed to:   {current} ({'HIGH' if current else 'LOW'})")
                    print(f"  Meaning: Sensor is now {'TRIGGERED' if current else 'NOT TRIGGERED'}")
                    print("🚨"*30 + "\n")
                    last_states[name] = current

            # Status every 2 seconds
            if time.time() - last_status_time > 2.0:
                last_status_time = time.time()
                print(f"[{poll_count:5d}] ", end="")
                for name, pin in EDGE_PINS.items():
                    state = GPIO.input(pin)
                    symbol = "■" if state else "□"
                    print(f"{name[0]}{name.split('_')[1][0].upper()}:{symbol} ", end="")
                print(f"(■=HIGH/TRIG □=LOW/READY)")

            time.sleep(0.1)  # 100ms = 10Hz

    except KeyboardInterrupt:
        print("\n\nStopping PULL-DOWN test...")

    # Test 2: PULL-UP configuration (maybe sensors are active-LOW?)
    print("\n" + "="*70)
    print("TEST 2: PULL-UP RESISTORS (Alternative Configuration)")
    print("Expecting: HIGH (1) = Not triggered, LOW (0) = Triggered")
    print("="*70)

    # Reconfigure with pull-up
    for name, pin in EDGE_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print(f"  {name:15s}: GPIO {pin:2d} reconfigured with PULL-UP")

    time.sleep(0.1)  # Let pins settle

    print("\nInitial readings with PULL-UP:")
    for name, pin in EDGE_PINS.items():
        readings = []
        for _ in range(5):
            readings.append(GPIO.input(pin))
            time.sleep(0.002)

        unique = set(readings)
        if len(unique) == 1:
            state = readings[0]
            print(f"  {name:15s} [GPIO {pin:2d}]: {state} ({'HIGH' if state else 'LOW'}) - STABLE")
        else:
            print(f"  {name:15s} [GPIO {pin:2d}]: UNSTABLE! {readings}")

    print("\nMonitoring with PULL-UP for 5 seconds...")
    print("Trigger a sensor to see if it goes LOW...")

    for name, pin in EDGE_PINS.items():
        last_states[name] = GPIO.input(pin)

    end_time = time.time() + 5.0
    while time.time() < end_time:
        for name, pin in EDGE_PINS.items():
            current = GPIO.input(pin)
            if current != last_states[name]:
                print(f"\n🚨 CHANGE: {name} went from {last_states[name]} to {current}")
                print(f"   Meaning: {'TRIGGERED' if not current else 'NOT TRIGGERED'} (inverted logic)")
                last_states[name] = current
        time.sleep(0.05)

    # Test 3: Floating test (NO pull resistors)
    print("\n" + "="*70)
    print("TEST 3: FLOATING PINS (No Pull Resistors)")
    print("This will show if pins are floating (bad wiring)")
    print("="*70)

    # Setup without pull resistors
    for name, pin in EDGE_PINS.items():
        GPIO.setup(pin, GPIO.IN)  # No pull-up or pull-down
        print(f"  {name:15s}: GPIO {pin:2d} configured as FLOATING input")

    time.sleep(0.1)

    print("\nFloating pin readings (should be stable if properly wired):")
    for name, pin in EDGE_PINS.items():
        readings = []
        for _ in range(20):
            readings.append(GPIO.input(pin))
            time.sleep(0.001)

        unique = set(readings)
        if len(unique) == 1:
            state = readings[0]
            print(f"  {name:15s}: STABLE at {state} - Good wiring!")
        else:
            high_count = readings.count(1)
            low_count = readings.count(0)
            print(f"  {name:15s}: FLOATING! {high_count} HIGH, {low_count} LOW")
            print(f"  {'':15s}  → Pin is not properly connected or missing pull resistor!")

    # Cleanup
    GPIO.cleanup()

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print("\nDIAGNOSIS GUIDE:")
    print("1. If pins are STABLE with PULL-DOWN and respond to triggers → Working correctly")
    print("2. If pins are STABLE with PULL-UP and respond to triggers → Need to invert logic")
    print("3. If pins are FLOATING → Wiring issue, check connections")
    print("4. If NO changes detected → Check sensor power, ground, and signal connections")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
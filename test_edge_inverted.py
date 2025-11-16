#!/usr/bin/env python3
"""
TEST EDGE SENSORS WITH INVERTED LOGIC
======================================
Tests if edge sensors are active-LOW (need pull-up resistors)
instead of active-HIGH (pull-down resistors)
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
    print("✓ RPi.GPIO imported")
except ImportError:
    print("✗ Failed to import RPi.GPIO")
    sys.exit(1)

# Edge sensor pins
EDGE_PINS = {
    'x_left_edge': 4,
    'x_right_edge': 17,
    'y_top_edge': 7,
    'y_bottom_edge': 8
}

def test_pull_configuration():
    """Test both pull-up and pull-down to determine correct configuration"""

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    print("="*70)
    print("EDGE SENSOR PULL RESISTOR CONFIGURATION TEST")
    print("="*70)
    print("This test will determine if sensors are active-HIGH or active-LOW\n")

    # Test 1: Pull-DOWN configuration
    print("TEST 1: PULL-DOWN RESISTORS (Current config)")
    print("-" * 50)
    print("If sensors are active-HIGH: Expect LOW when not triggered, HIGH when triggered")

    pull_down_states = {}
    for name, pin in EDGE_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        time.sleep(0.01)

        # Take 10 readings
        readings = []
        for _ in range(10):
            readings.append(GPIO.input(pin))
            time.sleep(0.001)

        avg = sum(readings) / len(readings)
        stable = len(set(readings)) == 1

        if stable:
            state = readings[0]
            pull_down_states[name] = state
            print(f"  {name:15s} [pin {pin:2d}]: {'HIGH' if state else 'LOW'} (stable)")
        else:
            pull_down_states[name] = avg
            print(f"  {name:15s} [pin {pin:2d}]: UNSTABLE (avg: {avg:.2f})")

    print("\n🔷 Now TRIGGER one sensor and press Enter...")
    input()

    print("Reading TRIGGERED state with PULL-DOWN:")
    for name, pin in EDGE_PINS.items():
        state = GPIO.input(pin)
        old_state = pull_down_states[name]
        if isinstance(old_state, bool):
            if state != old_state:
                print(f"  {name:15s}: CHANGED from {'HIGH' if old_state else 'LOW'} to {'HIGH' if state else 'LOW'} ✓")
            else:
                print(f"  {name:15s}: NO CHANGE (still {'HIGH' if state else 'LOW'})")
        else:
            print(f"  {name:15s}: Now {'HIGH' if state else 'LOW'} (was unstable)")

    # Test 2: Pull-UP configuration
    print("\n" + "="*70)
    print("TEST 2: PULL-UP RESISTORS (Alternative config)")
    print("-" * 50)
    print("If sensors are active-LOW: Expect HIGH when not triggered, LOW when triggered")

    pull_up_states = {}
    for name, pin in EDGE_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        time.sleep(0.01)

        # Take 10 readings
        readings = []
        for _ in range(10):
            readings.append(GPIO.input(pin))
            time.sleep(0.001)

        avg = sum(readings) / len(readings)
        stable = len(set(readings)) == 1

        if stable:
            state = readings[0]
            pull_up_states[name] = state
            print(f"  {name:15s} [pin {pin:2d}]: {'HIGH' if state else 'LOW'} (stable)")
        else:
            pull_up_states[name] = avg
            print(f"  {name:15s} [pin {pin:2d}]: UNSTABLE (avg: {avg:.2f})")

    print("\n🔷 Keep the same sensor TRIGGERED and press Enter...")
    input()

    print("Reading TRIGGERED state with PULL-UP:")
    for name, pin in EDGE_PINS.items():
        state = GPIO.input(pin)
        old_state = pull_up_states[name]
        if isinstance(old_state, bool):
            if state != old_state:
                print(f"  {name:15s}: CHANGED from {'HIGH' if old_state else 'LOW'} to {'HIGH' if state else 'LOW'} ✓")
            else:
                print(f"  {name:15s}: NO CHANGE (still {'HIGH' if state else 'LOW'})")
        else:
            print(f"  {name:15s}: Now {'HIGH' if state else 'LOW'} (was unstable)")

    # Analysis
    print("\n" + "="*70)
    print("ANALYSIS RESULTS")
    print("="*70)

    print("\nBased on the test results:")
    print("\n1. If PULL-DOWN showed changes (LOW→HIGH when triggered):")
    print("   → Sensors are ACTIVE-HIGH (correct config)")
    print("   → Keep using GPIO.PUD_DOWN")

    print("\n2. If PULL-UP showed changes (HIGH→LOW when triggered):")
    print("   → Sensors are ACTIVE-LOW (need to change)")
    print("   → Change to GPIO.PUD_UP and invert logic")

    print("\n3. If NEITHER showed changes:")
    print("   → Hardware connection issue")
    print("   → Check wiring, power, and ground connections")

    print("\n4. If readings are UNSTABLE:")
    print("   → Floating pins or electrical noise")
    print("   → Check for proper pull resistor connections")

    GPIO.cleanup()
    print("\n" + "="*70)

def continuous_monitor_inverted():
    """Monitor with inverted logic (pull-up, active-low)"""

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    print("\n" + "="*70)
    print("CONTINUOUS MONITORING WITH INVERTED LOGIC")
    print("="*70)
    print("Using PULL-UP resistors, expecting LOW when triggered\n")

    # Setup with pull-up
    for name, pin in EDGE_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    last_states = {}
    for name, pin in EDGE_PINS.items():
        last_states[name] = GPIO.input(pin)
        state = last_states[name]
        # Inverted logic: LOW = triggered, HIGH = not triggered
        status = "TRIGGERED" if not state else "READY"
        print(f"{name:15s}: {'HIGH' if state else 'LOW'} ({status})")

    print("\nMonitoring... (Ctrl+C to stop)")
    print("-" * 50)

    poll_count = 0
    try:
        while True:
            poll_count += 1

            for name, pin in EDGE_PINS.items():
                current = GPIO.input(pin)

                if current != last_states[name]:
                    # State changed with inverted logic
                    old_status = "TRIGGERED" if not last_states[name] else "READY"
                    new_status = "TRIGGERED" if not current else "READY"

                    print(f"\n🚨 CHANGE on {name}!")
                    print(f"   Raw: {'HIGH' if last_states[name] else 'LOW'} → {'HIGH' if current else 'LOW'}")
                    print(f"   Status: {old_status} → {new_status}")
                    print(f"   Poll: #{poll_count}\n")

                    last_states[name] = current

            if poll_count % 100 == 0:
                # Status every 100 polls
                statuses = []
                for name in EDGE_PINS:
                    state = GPIO.input(EDGE_PINS[name])
                    symbol = "■" if not state else "□"  # Inverted: LOW=triggered
                    statuses.append(f"{name[0]}{name.split('_')[1][0].upper()}:{symbol}")
                print(f"[{poll_count:5d}] " + " ".join(statuses) + " (■=TRIG □=READY)")

            time.sleep(0.05)  # 50ms = 20Hz

    except KeyboardInterrupt:
        print("\nStopping...")

    GPIO.cleanup()

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Configuration Test (determine if active-HIGH or active-LOW)")
    print("2. Continuous Monitor with Inverted Logic")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "1":
        test_pull_configuration()
    elif choice == "2":
        continuous_monitor_inverted()
    else:
        print("Invalid choice")
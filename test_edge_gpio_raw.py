#!/usr/bin/env python3
"""
Raw GPIO Test for Edge Sensors
Direct GPIO access to test edge sensor pins without any abstraction
"""

import time

try:
    import RPi.GPIO as GPIO
    print("✓ Real RPi.GPIO imported")
except ImportError:
    print("✗ Failed to import RPi.GPIO - not on Raspberry Pi")
    exit(1)

# Edge sensor pin configuration
EDGE_SENSOR_PINS = {
    'x_left_edge': 4,
    'x_right_edge': 17,
    'y_top_edge': 7,
    'y_bottom_edge': 8
}

def test_raw_gpio():
    """Test edge sensor GPIO pins directly"""

    print("="*60)
    print("RAW GPIO EDGE SENSOR TEST")
    print("="*60)

    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    print("\nTesting with PULL-DOWN resistors (expecting HIGH when triggered)...")

    # Setup all edge sensor pins with pull-down resistors
    for sensor_name, pin in EDGE_SENSOR_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        print(f"  {sensor_name}: GPIO pin {pin} configured with PULL-DOWN")

    print("\n" + "="*60)
    print("INITIAL PIN READINGS:")
    print("="*60)

    # Read initial states
    for sensor_name, pin in EDGE_SENSOR_PINS.items():
        # Take multiple readings
        readings = []
        for _ in range(10):
            readings.append(GPIO.input(pin))
            time.sleep(0.001)

        # Check if stable
        if len(set(readings)) == 1:
            state = readings[0]
            print(f"{sensor_name:15s} [GPIO {pin:2d}]: {'HIGH' if state else 'LOW'} (stable)")
        else:
            high_count = readings.count(1)
            low_count = readings.count(0)
            print(f"{sensor_name:15s} [GPIO {pin:2d}]: UNSTABLE! {high_count} HIGH, {low_count} LOW")
            print(f"{'':15s} Readings: {readings}")

    print("\n" + "="*60)
    print("MONITORING FOR CHANGES (Press Ctrl+C to stop)")
    print("Trigger edge sensors to see state changes...")
    print("="*60 + "\n")

    # Track last states
    last_states = {}
    for sensor_name, pin in EDGE_SENSOR_PINS.items():
        last_states[sensor_name] = GPIO.input(pin)

    poll_count = 0
    last_report_time = time.time()

    try:
        while True:
            poll_count += 1
            changed = False

            # Check each sensor
            for sensor_name, pin in EDGE_SENSOR_PINS.items():
                current_state = GPIO.input(pin)

                if current_state != last_states[sensor_name]:
                    # State changed!
                    print("🚨" * 20)
                    print(f"CHANGE DETECTED on {sensor_name.upper()}!")
                    print(f"  GPIO Pin: {pin}")
                    print(f"  Old State: {'HIGH' if last_states[sensor_name] else 'LOW'}")
                    print(f"  New State: {'HIGH' if current_state else 'LOW'}")
                    print(f"  Poll #: {poll_count}")
                    print(f"  Interpretation: Sensor is now {'TRIGGERED' if current_state else 'READY'}")
                    print("🚨" * 20 + "\n")

                    last_states[sensor_name] = current_state
                    changed = True

            # Periodic status report every 5 seconds
            current_time = time.time()
            if current_time - last_report_time > 5.0:
                last_report_time = current_time
                print(f"[Poll #{poll_count}] Current states:")
                for sensor_name, pin in EDGE_SENSOR_PINS.items():
                    state = GPIO.input(pin)
                    print(f"  {sensor_name:15s}: {'HIGH (TRIGGERED)' if state else 'LOW (READY)'}")
                print("")

            # Small delay to avoid CPU overload
            time.sleep(0.01)  # 10ms = 100Hz polling

    except KeyboardInterrupt:
        print("\n\nStopping test...")

    # Test with PULL-UP resistors to see if sensors are active-low
    print("\n" + "="*60)
    print("TESTING WITH PULL-UP RESISTORS (expecting LOW when triggered)...")
    print("="*60)

    # Reconfigure with pull-up resistors
    for sensor_name, pin in EDGE_SENSOR_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print(f"  {sensor_name}: GPIO pin {pin} reconfigured with PULL-UP")

    time.sleep(0.1)  # Let pins settle

    print("\nREADINGS WITH PULL-UP:")
    for sensor_name, pin in EDGE_SENSOR_PINS.items():
        state = GPIO.input(pin)
        print(f"  {sensor_name:15s}: {'HIGH' if state else 'LOW'}")

    print("\nTrigger a sensor to see if it goes LOW...")
    time.sleep(3)

    print("\nFINAL READINGS:")
    for sensor_name, pin in EDGE_SENSOR_PINS.items():
        state = GPIO.input(pin)
        print(f"  {sensor_name:15s}: {'HIGH' if state else 'LOW'}")

    # Cleanup
    GPIO.cleanup()
    print("\nGPIO cleaned up. Test complete.")

if __name__ == "__main__":
    test_raw_gpio()
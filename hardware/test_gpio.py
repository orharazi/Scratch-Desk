#!/usr/bin/env python3

"""
GPIO Test
=========

Tests Raspberry Pi GPIO control for pistons and sensors.
"""

import sys
import time
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.raspberry_pi_gpio import RaspberryPiGPIO


def test_piston_control(gpio: RaspberryPiGPIO):
    """Test all piston controls"""
    print("\n" + "="*60)
    print("Test 1: Piston Control")
    print("="*60)

    pistons = [
        "line_marker_piston",
        "line_cutter_piston",
        "line_motor_piston",
        "row_marker_piston",
        "row_cutter_piston"
    ]

    for piston in pistons:
        print(f"\nTesting {piston}...")

        # Down
        print(f"  Moving {piston} DOWN...")
        if gpio.piston_down(piston):
            print("  ✓ DOWN successful")
            time.sleep(1)
        else:
            print("  ✗ DOWN failed")
            return False

        # Up
        print(f"  Moving {piston} UP...")
        if gpio.piston_up(piston):
            print("  ✓ UP successful")
            time.sleep(1)
        else:
            print("  ✗ UP failed")
            return False

    print("\n✓ All piston tests passed")
    return True


def test_sensor_reading(gpio: RaspberryPiGPIO):
    """Test sensor reading"""
    print("\n" + "="*60)
    print("Test 2: Sensor Reading")
    print("="*60)

    sensors = [
        "line_marker_state",
        "line_cutter_state",
        "line_motor_piston_sensor",
        "row_marker_state",
        "row_cutter_state",
        "x_left_edge",
        "x_right_edge",
        "y_top_edge",
        "y_bottom_edge"
    ]

    print("\nReading all sensors...")
    for sensor in sensors:
        state = gpio.read_sensor(sensor)
        if state is not None:
            status = "TRIGGERED" if state else "READY"
            print(f"  {sensor:30s}: {status}")
        else:
            print(f"  {sensor:30s}: ERROR")

    return True


def test_limit_switches(gpio: RaspberryPiGPIO):
    """Test limit switch reading"""
    print("\n" + "="*60)
    print("Test 3: Limit Switch Reading")
    print("="*60)

    switches = ["rows_door"]

    print("\nReading limit switches...")
    for switch in switches:
        state = gpio.read_limit_switch(switch)
        if state is not None:
            status = "ACTIVATED" if state else "INACTIVE"
            print(f"  {switch:30s}: {status}")
        else:
            print(f"  {switch:30s}: ERROR")

    return True


def test_piston_sensor_sync(gpio: RaspberryPiGPIO):
    """Test piston control synchronized with sensor reading"""
    print("\n" + "="*60)
    print("Test 4: Piston-Sensor Synchronization")
    print("="*60)

    piston_sensor_pairs = [
        ("line_marker_piston", "line_marker_state"),
        ("line_cutter_piston", "line_cutter_state"),
        ("line_motor_piston", "line_motor_piston_sensor"),
        ("row_marker_piston", "row_marker_state"),
        ("row_cutter_piston", "row_cutter_state"),
    ]

    for piston, sensor in piston_sensor_pairs:
        print(f"\nTesting {piston} with {sensor}...")

        # Move down and check sensor
        print(f"  Moving {piston} DOWN...")
        gpio.piston_down(piston)
        time.sleep(0.5)

        sensor_state = gpio.read_sensor(sensor)
        print(f"  Sensor {sensor}: {'TRIGGERED' if sensor_state else 'READY'}")

        # Move up and check sensor
        print(f"  Moving {piston} UP...")
        gpio.piston_up(piston)
        time.sleep(0.5)

        sensor_state = gpio.read_sensor(sensor)
        print(f"  Sensor {sensor}: {'TRIGGERED' if sensor_state else 'READY'}")

    print("\n✓ Synchronization test complete")
    return True


def test_rapid_cycling(gpio: RaspberryPiGPIO):
    """Test rapid piston cycling"""
    print("\n" + "="*60)
    print("Test 5: Rapid Piston Cycling")
    print("="*60)

    print("\nRapidly cycling line_marker_piston 10 times...")

    for i in range(10):
        print(f"  Cycle {i+1}/10...")
        gpio.piston_down("line_marker_piston")
        time.sleep(0.2)
        gpio.piston_up("line_marker_piston")
        time.sleep(0.2)

    print("\n✓ Rapid cycling complete")
    return True


def test_all_pistons_simultaneous(gpio: RaspberryPiGPIO):
    """Test all pistons moving simultaneously"""
    print("\n" + "="*60)
    print("Test 6: All Pistons Simultaneous")
    print("="*60)

    pistons = [
        "line_marker_piston",
        "line_cutter_piston",
        "line_motor_piston",
        "row_marker_piston",
        "row_cutter_piston"
    ]

    print("\nMoving all pistons DOWN simultaneously...")
    for piston in pistons:
        gpio.piston_down(piston)
    time.sleep(2)

    print("Moving all pistons UP simultaneously...")
    for piston in pistons:
        gpio.piston_up(piston)
    time.sleep(2)

    print("\n✓ Simultaneous movement test complete")
    return True


def interactive_sensor_test(gpio: RaspberryPiGPIO):
    """Interactive sensor testing - trigger sensors manually"""
    print("\n" + "="*60)
    print("Test 7: Interactive Sensor Test")
    print("="*60)

    print("\nThis test will continuously read sensors.")
    print("Manually trigger sensors (e.g., wave hand in front of sensor)")
    print("Press Ctrl+C to exit")

    try:
        while True:
            # Read all sensors
            sensor_states = gpio.get_all_sensor_states()

            # Clear screen and display
            print("\n" * 2)
            print("="*60)
            print("Sensor States (live)")
            print("="*60)

            for sensor, state in sorted(sensor_states.items()):
                status = "🔴 TRIGGERED" if state else "🟢 READY"
                print(f"  {sensor:30s}: {status}")

            print("\nPress Ctrl+C to exit")
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\n✓ Interactive test ended")
        return True


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("Raspberry Pi GPIO Test Suite")
    print("="*60)
    print("\nThis will test GPIO pins for pistons and sensors.")
    print("Make sure:")
    print("  1. Raspberry Pi is connected")
    print("  2. All GPIO connections are secure")
    print("  3. Power supply is adequate")
    print("  4. Emergency stop is accessible")
    print("\n⚠ WARNING: Pistons will actuate! Ensure safety first.")

    response = input("\nProceed with GPIO tests? (yes/no): ")
    if response.lower() != "yes":
        print("Test cancelled")
        return

    # Create and initialize GPIO
    print("\nInitializing GPIO...")
    gpio = RaspberryPiGPIO()

    if not gpio.initialize():
        print("✗ Failed to initialize GPIO")
        print("\nTroubleshooting:")
        print("  1. Check Raspberry Pi GPIO connections")
        print("  2. Verify GPIO pins in settings.json")
        print("  3. Ensure proper permissions (may need sudo)")
        return

    try:
        # Run test suite
        tests = [
            ("Piston Control", test_piston_control),
            ("Sensor Reading", test_sensor_reading),
            ("Limit Switches", test_limit_switches),
            ("Piston-Sensor Sync", test_piston_sensor_sync),
            ("Rapid Cycling", test_rapid_cycling),
            ("All Pistons Simultaneous", test_all_pistons_simultaneous),
            ("Interactive Sensor Test", interactive_sensor_test),
        ]

        results = []
        for test_name, test_func in tests:
            response = input(f"\nRun test: {test_name}? (yes/no/quit): ")
            if response.lower() == "quit":
                print("Test suite terminated by user")
                break
            elif response.lower() != "yes":
                print(f"Skipping {test_name}")
                continue

            try:
                result = test_func(gpio)
                results.append((test_name, result))
                if result:
                    print(f"\n✓ {test_name} passed")
                else:
                    print(f"\n✗ {test_name} failed")
            except KeyboardInterrupt:
                print("\n\n⚠ Test interrupted by user")
                break
            except Exception as e:
                print(f"\n✗ Test error: {e}")
                results.append((test_name, False))

        # Print summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        for test_name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {test_name}")

        passed = sum(1 for _, result in results if result)
        total = len(results)
        print(f"\nTotal: {passed}/{total} tests passed")
        print("="*60 + "\n")

    finally:
        # Cleanup GPIO
        print("\nCleaning up GPIO...")
        gpio.cleanup()
        print("✓ Test complete")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Test suite interrupted by user")
        sys.exit(0)

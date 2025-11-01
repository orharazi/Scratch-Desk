#!/usr/bin/env python3

"""
Motor Movement Test
===================

Tests Arduino GRBL motor control with various movement patterns.
"""

import sys
import time
from hardware.arduino_grbl import ArduinoGRBL


def test_basic_movements(grbl: ArduinoGRBL):
    """Test basic motor movements"""
    print("\n" + "="*60)
    print("Test 1: Basic Movements")
    print("="*60)

    movements = [
        (10, 0, "Move to X=10cm, Y=0cm"),
        (10, 10, "Move to X=10cm, Y=10cm"),
        (0, 10, "Move to X=0cm, Y=10cm"),
        (0, 0, "Return to origin"),
    ]

    for x, y, description in movements:
        print(f"\n{description}...")
        if grbl.move_to(x, y):
            print("✓ Movement successful")
            time.sleep(2)
        else:
            print("✗ Movement failed")
            return False

    return True


def test_square_pattern(grbl: ArduinoGRBL):
    """Test square movement pattern"""
    print("\n" + "="*60)
    print("Test 2: Square Pattern (20cm x 20cm)")
    print("="*60)

    square = [
        (0, 0),
        (20, 0),
        (20, 20),
        (0, 20),
        (0, 0)
    ]

    for i, (x, y) in enumerate(square):
        print(f"\nCorner {i+1}: ({x}cm, {y}cm)")
        if grbl.move_to(x, y):
            print("✓ Movement successful")
            time.sleep(1)
        else:
            print("✗ Movement failed")
            return False

    return True


def test_diagonal_movements(grbl: ArduinoGRBL):
    """Test diagonal movements"""
    print("\n" + "="*60)
    print("Test 3: Diagonal Movements")
    print("="*60)

    diagonals = [
        (0, 0, "Origin"),
        (15, 15, "Diagonal to (15, 15)"),
        (30, 10, "Diagonal to (30, 10)"),
        (10, 30, "Diagonal to (10, 30)"),
        (0, 0, "Return to origin"),
    ]

    for x, y, description in diagonals:
        print(f"\n{description}...")
        if grbl.move_to(x, y):
            print("✓ Movement successful")
            time.sleep(1.5)
        else:
            print("✗ Movement failed")
            return False

    return True


def test_rapid_vs_feed(grbl: ArduinoGRBL):
    """Test rapid movement vs feed rate movement"""
    print("\n" + "="*60)
    print("Test 4: Rapid Movement vs Feed Rate")
    print("="*60)

    print("\nMoving to (50, 0) with feed rate...")
    start = time.time()
    grbl.move_to(50, 0, rapid=False)
    feed_time = time.time() - start
    print(f"Time taken: {feed_time:.2f}s")
    time.sleep(1)

    print("\nMoving to (0, 0) with rapid movement...")
    start = time.time()
    grbl.move_to(0, 0, rapid=True)
    rapid_time = time.time() - start
    print(f"Time taken: {rapid_time:.2f}s")

    print(f"\nSpeed comparison: Rapid is {feed_time/rapid_time:.1f}x faster")
    return True


def test_axis_limits(grbl: ArduinoGRBL):
    """Test movement to axis limits"""
    print("\n" + "="*60)
    print("Test 5: Axis Limits (be careful!)")
    print("="*60)

    # Read limits from settings
    import json
    try:
        with open("settings.json", 'r') as f:
            config = json.load(f)
        max_x = config.get("hardware_limits", {}).get("max_x_position", 120)
        max_y = config.get("hardware_limits", {}).get("max_y_position", 80)
    except:
        max_x = 120
        max_y = 80

    print(f"\nMax limits: X={max_x}cm, Y={max_y}cm")
    print("Testing movement to maximum positions...")

    limits = [
        (max_x, 0, f"X limit ({max_x}cm, 0cm)"),
        (max_x, max_y, f"Both limits ({max_x}cm, {max_y}cm)"),
        (0, max_y, f"Y limit (0cm, {max_y}cm)"),
        (0, 0, "Return to origin"),
    ]

    for x, y, description in limits:
        print(f"\n{description}...")
        response = input("Press Enter to continue or 's' to skip: ")
        if response.lower() == 's':
            print("Skipped")
            continue

        if grbl.move_to(x, y):
            print("✓ Movement successful")
            time.sleep(2)
        else:
            print("✗ Movement failed")
            return False

    return True


def test_status_monitoring(grbl: ArduinoGRBL):
    """Test status monitoring during movement"""
    print("\n" + "="*60)
    print("Test 6: Status Monitoring")
    print("="*60)

    print("\nMonitoring status during movement to (30, 30)...")

    # Start movement
    print("Starting movement...")
    grbl.move_to(30, 30, rapid=False)

    # Monitor status for 5 seconds
    start = time.time()
    while time.time() - start < 5:
        status = grbl.get_status()
        if status:
            print(f"State: {status.get('state', 'Unknown'):8s} | "
                  f"Position: X={status.get('x', 0):6.2f}cm, Y={status.get('y', 0):6.2f}cm")
        time.sleep(0.5)

    # Return to origin
    print("\nReturning to origin...")
    grbl.move_to(0, 0)

    return True


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("Arduino GRBL Motor Movement Test Suite")
    print("="*60)
    print("\nThis will test motor movements with the real hardware.")
    print("Make sure:")
    print("  1. Arduino is connected and powered")
    print("  2. Motors are properly connected")
    print("  3. Work area is clear of obstacles")
    print("  4. Emergency stop is accessible")
    print("\n⚠ WARNING: Motors will move! Ensure safety first.")

    response = input("\nProceed with motor tests? (yes/no): ")
    if response.lower() != "yes":
        print("Test cancelled")
        return

    # Create and connect to GRBL
    print("\nConnecting to GRBL...")
    grbl = ArduinoGRBL()

    if not grbl.connect():
        print("✗ Failed to connect to GRBL")
        print("\nTroubleshooting:")
        print("  1. Check Arduino is connected via USB")
        print("  2. Verify serial port in settings.json")
        print("  3. Ensure GRBL firmware is uploaded to Arduino")
        return

    try:
        # Run test suite
        tests = [
            ("Basic Movements", test_basic_movements),
            ("Square Pattern", test_square_pattern),
            ("Diagonal Movements", test_diagonal_movements),
            ("Rapid vs Feed Rate", test_rapid_vs_feed),
            ("Axis Limits", test_axis_limits),
            ("Status Monitoring", test_status_monitoring),
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
                result = test_func(grbl)
                results.append((test_name, result))
                if result:
                    print(f"\n✓ {test_name} passed")
                else:
                    print(f"\n✗ {test_name} failed")
            except KeyboardInterrupt:
                print("\n\n⚠ Test interrupted by user")
                grbl.stop()
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
        # Always return to origin and disconnect
        print("\nReturning to origin...")
        grbl.move_to(0, 0)
        time.sleep(2)

        print("Disconnecting...")
        grbl.disconnect()
        print("✓ Test complete")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Test suite interrupted by user")
        sys.exit(0)

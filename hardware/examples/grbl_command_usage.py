#!/usr/bin/env python3

"""
GRBL Command Library Usage Examples
====================================

Examples showing how to use the GRBL command library for GUI development.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hardware.grbl_commands import (
    generate_gcode,
    generate_jog_command,
    get_commands_by_category,
    get_all_commands,
    MOTION_COMMANDS,
    SYSTEM_COMMANDS,
    REALTIME_COMMANDS,
    COMMAND_SEQUENCES,
    PRESET_POSITIONS
)


def example_basic_movement():
    """Example: Basic movement commands"""
    print("\n" + "="*60)
    print("Example 1: Basic Movement Commands")
    print("="*60)

    # Rapid positioning
    cmd = generate_gcode('G0', X=50, Y=35)
    print(f"Rapid move:    {cmd}")

    # Linear move with feed rate
    cmd = generate_gcode('G1', X=100, Y=50, F=1000)
    print(f"Linear move:   {cmd}")

    # Arc (clockwise)
    cmd = generate_gcode('G2', X=10, Y=10, I=5, J=0, F=500)
    print(f"Arc CW:        {cmd}")

    # Return to origin
    cmd = generate_gcode('G0', X=0, Y=0)
    print(f"Go to origin:  {cmd}")


def example_jogging():
    """Example: Jogging commands for manual control"""
    print("\n" + "="*60)
    print("Example 2: Jogging Commands")
    print("="*60)

    # Incremental jog commands
    print("Incremental jogging (relative):")
    print(f"  X+ 10mm:  {generate_jog_command('X', 10, 500)}")
    print(f"  X- 10mm:  {generate_jog_command('X', -10, 500)}")
    print(f"  Y+ 5mm:   {generate_jog_command('Y', 5, 1000)}")
    print(f"  Y- 5mm:   {generate_jog_command('Y', -5, 1000)}")

    # Absolute jog
    print("\nAbsolute jogging:")
    print(f"  Go to X50: {generate_jog_command('X', 50, 1000, absolute=True)}")
    print(f"  Go to Y35: {generate_jog_command('Y', 35, 1000, absolute=True)}")

    # Machine coordinates
    print("\nJog in machine coordinates:")
    print(f"  Home X:    {generate_jog_command('X', 0, 1000, absolute=True, machine_coords=True)}")


def example_coordinate_setup():
    """Example: Setting up work coordinates"""
    print("\n" + "="*60)
    print("Example 3: Work Coordinate Setup")
    print("="*60)

    print("Zero current position as work zero:")
    print(f"  {generate_gcode('G10 L20', P=1, X=0, Y=0)}")

    print("\nTemporary offset:")
    print(f"  {generate_gcode('G92', X=0, Y=0)}")

    print("\nSelect work coordinate systems:")
    print(f"  WCS 1: G54")
    print(f"  WCS 2: G55")
    print(f"  WCS 3: G56")


def example_initialization():
    """Example: Machine initialization sequence"""
    print("\n" + "="*60)
    print("Example 4: Machine Initialization")
    print("="*60)

    sequence = COMMAND_SEQUENCES['initialize']
    print(f"{sequence['name']}:")
    print(f"Description: {sequence['description']}")
    print("\nCommands:")
    for i, cmd in enumerate(sequence['commands'], 1):
        print(f"  {i}. {cmd}")


def example_command_lookup():
    """Example: Looking up command information"""
    print("\n" + "="*60)
    print("Example 5: Command Information Lookup")
    print("="*60)

    # Get specific command info
    cmd_info = MOTION_COMMANDS['G0']
    print(f"Command: {cmd_info['code']}")
    print(f"Name: {cmd_info['name']}")
    print(f"Description: {cmd_info['description']}")
    print(f"Parameters: {', '.join(cmd_info['parameters'])}")
    print(f"Example: {cmd_info['example']}")


def example_category_listing():
    """Example: List all commands in a category"""
    print("\n" + "="*60)
    print("Example 6: Commands by Category")
    print("="*60)

    # Get motion commands
    motion_cmds = get_commands_by_category('Motion')
    print(f"Motion Commands ({len(motion_cmds)}):")
    for code, cmd in motion_cmds.items():
        print(f"  {code:8} - {cmd['name']}")

    # Get system commands
    print(f"\nSystem Commands:")
    system_cmds = get_commands_by_category('System')
    for code, cmd in list(system_cmds.items())[:5]:
        print(f"  {code:8} - {cmd['name']}")


def example_preset_positions():
    """Example: Using preset positions"""
    print("\n" + "="*60)
    print("Example 7: Preset Positions")
    print("="*60)

    print("Available presets:")
    for key, preset in PRESET_POSITIONS.items():
        x, y = preset['X'], preset['Y']
        cmd = generate_gcode('G0', X=x, Y=y)
        print(f"  {preset['name']:15} → {cmd}")


def example_gui_buttons():
    """Example: Creating GUI button commands"""
    print("\n" + "="*60)
    print("Example 8: GUI Quick Action Buttons")
    print("="*60)

    buttons = {
        "Home": "$H",
        "Unlock": "$X",
        "Status": "?",
        "Set Zero": "G10 L20 P1 X0 Y0",
        "Go to Zero": "G90 G0 X0 Y0",
        "Emergency Stop": "!",
        "Resume": "~",
    }

    print("Quick action button mappings:")
    for name, cmd in buttons.items():
        print(f"  {name:15} → {cmd}")


def example_status_parsing():
    """Example: Parsing GRBL status response"""
    print("\n" + "="*60)
    print("Example 9: Status Response Parsing")
    print("="*60)

    # Example status response
    status_response = "<Idle|MPos:10.000,20.000,0.000|WPos:10.000,20.000,0.000>"

    print(f"Status query command: ?")
    print(f"\nExample response:")
    print(f"  {status_response}")

    print("\nParsed information:")
    print("  State: Idle")
    print("  Machine Position: X=10.000, Y=20.000, Z=0.000")
    print("  Work Position: X=10.000, Y=20.000, Z=0.000")


def example_drawing_pattern():
    """Example: Drawing a square pattern"""
    print("\n" + "="*60)
    print("Example 10: Drawing a Square (50x50mm)")
    print("="*60)

    commands = [
        ("Initialize", "G90"),
        ("Start position", generate_gcode('G0', X=0, Y=0)),
        ("Draw right", generate_gcode('G1', X=50, Y=0, F=1000)),
        ("Draw up", generate_gcode('G1', X=50, Y=50)),
        ("Draw left", generate_gcode('G1', X=0, Y=50)),
        ("Draw down", generate_gcode('G1', X=0, Y=0)),
    ]

    print("G-code sequence:")
    for i, (desc, cmd) in enumerate(commands, 1):
        print(f"  {i}. {cmd:25} ; {desc}")


def example_error_handling():
    """Example: Error and alarm codes"""
    print("\n" + "="*60)
    print("Example 11: Error Handling")
    print("="*60)

    print("Common GRBL responses:")
    print("  'ok'      → Command successful")
    print("  'error:2' → Bad number format")
    print("  'error:9' → G-code not supported")
    print("  'ALARM:1' → Hard limit triggered")
    print("  'ALARM:2' → Soft limit triggered")

    print("\nRecovery commands:")
    print("  $X        → Unlock after alarm")
    print("  Ctrl-X    → Soft reset (emergency)")


def example_feed_rate_control():
    """Example: Feed rate variations"""
    print("\n" + "="*60)
    print("Example 12: Feed Rate Control")
    print("="*60)

    feed_rates = {
        "Slow": 500,
        "Normal": 1000,
        "Fast": 2000,
        "Rapid": 3000
    }

    print("Movement at different feed rates:")
    for name, rate in feed_rates.items():
        cmd = generate_gcode('G1', X=50, Y=35, F=rate)
        print(f"  {name:8} ({rate:4} mm/min): {cmd}")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print(" "*15 + "GRBL Command Library Examples")
    print("="*70)

    # Run all examples
    example_basic_movement()
    example_jogging()
    example_coordinate_setup()
    example_initialization()
    example_command_lookup()
    example_category_listing()
    example_preset_positions()
    example_gui_buttons()
    example_status_parsing()
    example_drawing_pattern()
    example_error_handling()
    example_feed_rate_control()

    print("\n" + "="*70)
    print("Examples completed!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()

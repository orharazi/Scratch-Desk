#!/usr/bin/env python3

"""
CNC SCRATCH DESK - Hardware Abstraction Layer
==============================================

This module provides a virtual mock of the physical CNC Scratch Desk hardware.
All variables here represent real hardware components that will be connected in production.

MACHINE STRUCTURE:
==================

MOTORS & POSITIONING:
- X Motor (Rows Motor): Horizontal movement (0-100cm) - moves marking/cutting tools left-right
- Y Motor (Lines Motor): Vertical movement (0-100cm) - moves marking/cutting tools up-down

LIMIT SWITCHES (Safety sensors):
- y_top: Top Y-axis limit switch (detects top boundary)
- y_bottom: Bottom Y-axis limit switch (detects bottom boundary)
- x_right: Right X-axis limit switch (detects right boundary)
- x_left: Left X-axis limit switch (detects left boundary)
- rows: Door safety limit switch (prevents operation when door open)

LINES TOOLS (Y-axis operations - horizontal marking/cutting):
- line_marker_piston: Pneumatic piston that lifts/lowers the X-axis marker assembly
- line_marker_state: Sensor detecting marker tool position (UP/DOWN)
- line_cutter_piston: Pneumatic piston that lifts/lowers the X-axis cutter assembly
- line_cutter_state: Sensor detecting cutter tool position (UP/DOWN)
- line_motor_piston: Pneumatic piston that lifts/lowers the entire Y motor assembly during movement
- line_motor_piston_sensor: Sensor detecting Y motor piston position (UP/DOWN)

ROWS TOOLS (X-axis operations - vertical marking/cutting):
- row_marker_piston: Pneumatic piston that lifts/lowers the Y-axis marker assembly
- row_marker_state: Sensor detecting marker tool position (UP/DOWN)
- row_marker_limit_switch: Physical sensor detecting actual row marker position (UP/DOWN)
- row_cutter_piston: Pneumatic piston that lifts/lowers the Y-axis cutter assembly
- row_cutter_state: Sensor detecting cutter tool position (UP/DOWN)

EDGE DETECTION SENSORS:
- x_left/x_right sensors: Detect paper edges during horizontal (lines) operations
- y_top/y_bottom sensors: Detect paper edges during vertical (rows) operations

All state changes are reflected in the Hardware Status panel in real-time.
"""

import time
import threading
import json
import os
from threading import Event

# Hardware state variables - optimized for Raspberry Pi (simple variables)
current_x_position = 0.0  # cm - X motor (rows motor) position
current_y_position = 0.0  # cm - Y motor (lines motor) position

# Load settings from settings.json
def load_settings():
    """Load hardware settings from settings.json"""
    try:
        with open('settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Default settings if file not found
        return {
            "hardware_limits": {
                "max_x_position": 100.0,
                "max_y_position": 100.0,
                "min_x_position": 0.0,
                "min_y_position": 0.0,
                "paper_start_x": 15.0
            }
        }

# Load settings
settings = load_settings()
hardware_limits = settings.get("hardware_limits", {})
timing_settings = settings.get("timing", {})

# System constraints from settings
MAX_X_POSITION = hardware_limits.get("max_x_position", 100.0)  # cm
MAX_Y_POSITION = hardware_limits.get("max_y_position", 100.0)  # cm
MIN_X_POSITION = hardware_limits.get("min_x_position", 0.0)    # cm
MIN_Y_POSITION = hardware_limits.get("min_y_position", 0.0)    # cm
PAPER_START_X = hardware_limits.get("paper_start_x", 15.0)     # cm from left edge

# === ACTUAL HARDWARE STATE VARIABLES ===
# These variables directly represent physical hardware components

# LINES TOOLS (Y-axis / horizontal operations)
line_marker_state = "up"           # Marking tool for horizontal lines: "up" (inactive) or "down" (marking)
line_marker_piston = "up"          # Piston that lifts X-axis marker assembly: "up" (default) or "down" (for operations)
line_cutter_state = "up"           # Cutting tool for horizontal cuts: "up" (inactive) or "down" (cutting)
line_cutter_piston = "up"          # Piston that lifts X-axis cutter assembly: "up" (default) or "down" (for operations)
line_motor_piston = "down"         # Piston that lifts Y motor assembly: "down" (default) or "up" (during upward Y movement)
line_motor_piston_sensor = "down"  # Sensor detecting Y motor piston position: "down" (default) or "up" (lifted)

# ROWS TOOLS (X-axis / vertical operations)
row_marker_piston = "up"           # Piston that lifts Y-axis marker assembly: "up" (default) or "down" (for operations)
row_marker_state = "up"            # Sensor detecting marker tool position: "up" or "down"
row_marker_limit_switch = "up"     # Physical sensor detecting row marker position: "up" or "down"
row_cutter_piston = "up"           # Piston that lifts Y-axis cutter assembly: "up" (default) or "down" (for operations)
row_cutter_state = "up"            # Sensor detecting cutter tool position: "up" (inactive) or "down" (cutting)

# Sensor events for manual triggering
sensor_events = {
    'x_left': Event(),
    'x_right': Event(),
    'y_top': Event(),
    'y_bottom': Event()
}

# Sensor results
sensor_results = {
    'x_sensor': None,
    'y_sensor': None
}

# Sensor trigger states (for live monitoring)
sensor_trigger_states = {
    'x_left': False,
    'x_right': False,
    'y_top': False,
    'y_bottom': False
}

# Sensor trigger timers (for auto-reset after display)
sensor_trigger_timers = {
    'x_left': 0,
    'x_right': 0,
    'y_top': 0,
    'y_bottom': 0
}

# Limit switch states (simulated hardware limit switches)
limit_switch_states = {
    'y_top': False,      # Top Y-axis limit switch
    'y_bottom': False,   # Bottom Y-axis limit switch
    'x_right': False,    # Right X-axis limit switch
    'x_left': False,     # Left X-axis limit switch
    'rows': False        # Rows limit switch - default UP
}

def reset_hardware():
    """Reset all hardware to initial state"""
    global current_x_position, current_y_position
    global line_marker_state, line_marker_piston, line_cutter_state, line_cutter_piston
    global line_motor_piston, line_motor_piston_sensor
    global row_marker_piston, row_marker_state, row_marker_limit_switch
    global row_cutter_piston, row_cutter_state

    current_x_position = 0.0
    current_y_position = 0.0
    line_marker_state = "up"
    line_marker_piston = "up"           # Default state is UP
    line_cutter_state = "up"
    line_cutter_piston = "up"           # Default state is UP
    line_motor_piston = "down"          # Default state is DOWN
    line_motor_piston_sensor = "down"   # Default state is DOWN (not lifted)
    row_marker_piston = "up"            # Default state is UP
    row_marker_state = "up"
    row_marker_limit_switch = "up"      # Default limit switch position
    row_cutter_piston = "up"            # Default state is UP
    row_cutter_state = "up"

    # Clear all sensor events
    for event in sensor_events.values():
        event.clear()
    
    sensor_results['x_sensor'] = None
    sensor_results['y_sensor'] = None
    
    print("Hardware reset to initial state")

# Movement functions
def move_x(position):
    """Move X motor to specified position within limits"""
    global current_x_position, line_marker_piston
    
    print(f"MOCK: move_x({position:.1f})")
    
    if position < MIN_X_POSITION:
        print(f"Warning: X position {position:.1f} below minimum {MIN_X_POSITION:.1f}, clamping")
        position = MIN_X_POSITION
    elif position > MAX_X_POSITION:
        print(f"Warning: X position {position:.1f} above maximum {MAX_X_POSITION:.1f}, clamping")
        position = MAX_X_POSITION
    
    if position != current_x_position:
        print(f"Moving X motor from {current_x_position:.1f}cm to {position:.1f}cm")

        # Simulate movement delay (keep short for responsiveness)
        move_distance = abs(position - current_x_position)
        delay_per_cm = timing_settings.get("motor_movement_delay_per_cm", 0.01)
        max_delay = timing_settings.get("max_motor_movement_delay", 0.5)
        delay = min(move_distance * delay_per_cm, max_delay)
        time.sleep(delay)

        current_x_position = position
        print(f"X motor positioned at {current_x_position:.1f}cm")
    else:
        print(f"X motor already at {position:.1f}cm")

def move_y(position):
    """Move Y motor to specified position within limits"""
    global current_y_position, line_motor_piston

    print(f"MOCK: move_y({position:.1f})")

    if position < MIN_Y_POSITION:
        print(f"Warning: Y position {position:.1f} below minimum {MIN_Y_POSITION:.1f}, clamping")
        position = MIN_Y_POSITION
    elif position > MAX_Y_POSITION:
        print(f"Warning: Y position {position:.1f} above maximum {MAX_Y_POSITION:.1f}, clamping")
        position = MAX_Y_POSITION

    if position != current_y_position:
        print(f"Moving Y motor from {current_y_position:.1f}cm to {position:.1f}cm")

        # Simulate movement delay (keep short for responsiveness)
        move_distance = abs(position - current_y_position)
        delay_per_cm = timing_settings.get("motor_movement_delay_per_cm", 0.01)
        max_delay = timing_settings.get("max_motor_movement_delay", 0.5)
        delay = min(move_distance * delay_per_cm, max_delay)
        time.sleep(delay)

        current_y_position = position
        print(f"Y motor positioned at {current_y_position:.1f}cm")
    else:
        print(f"Y motor already at {position:.1f}cm")

def get_current_x():
    """Get current X motor position"""
    print(f"MOCK: get_current_x() -> {current_x_position:.1f}")
    return current_x_position

def get_current_y():
    """Get current Y motor position"""
    print(f"MOCK: get_current_y() -> {current_y_position:.1f}")
    return current_y_position

# Line tools (Y-axis operations)
def line_marker_down():
    """Lower line marker to marking position"""
    global line_marker_state, line_marker_piston
    print("MOCK: line_marker_down()")
    if line_marker_state != "down":
        # First lower the piston (bring marker assembly down)
        if line_marker_piston != "down":
            print("Lowering line marker piston - bringing marker assembly down")
            time.sleep(timing_settings.get("tool_action_delay", 0.1))
            line_marker_piston = "down"
            print("Line marker piston DOWN - assembly lowered")

        # Then activate the marker
        print("Lowering line marker")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_state = "down"
        print("Line marker down - ready to mark")
    else:
        print("Line marker already down")

def line_marker_up():
    """Raise line marker from marking position"""
    global line_marker_state, line_marker_piston
    print("MOCK: line_marker_up()")
    if line_marker_state != "up":
        # First deactivate the marker
        print("Raising line marker")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_state = "up"
        print("Line marker up")

        # Then raise the piston (lift marker assembly up to default position)
        if line_marker_piston != "up":
            print("Raising line marker piston - returning to default position")
            time.sleep(timing_settings.get("tool_action_delay", 0.1))
            line_marker_piston = "up"
            print("Line marker piston UP - default position")
    else:
        print("Line marker already up")

def line_cutter_down():
    """Lower line cutter to cutting position"""
    global line_cutter_state, line_cutter_piston
    print("MOCK: line_cutter_down()")
    if line_cutter_state != "down":
        # First lower the piston (bring cutter assembly down)
        if line_cutter_piston != "down":
            print("Lowering line cutter piston - bringing cutter assembly down")
            time.sleep(timing_settings.get("tool_action_delay", 0.1))
            line_cutter_piston = "down"
            print("Line cutter piston DOWN - assembly lowered")

        # Then activate the cutter
        print("Lowering line cutter")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_state = "down"
        print("Line cutter down - ready to cut")
    else:
        print("Line cutter already down")

def line_cutter_up():
    """Raise line cutter from cutting position"""
    global line_cutter_state, line_cutter_piston
    print("MOCK: line_cutter_up()")
    if line_cutter_state != "up":
        # First deactivate the cutter
        print("Raising line cutter")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_state = "up"
        print("Line cutter up")

        # Then raise the piston (lift cutter assembly up to default position)
        if line_cutter_piston != "up":
            print("Raising line cutter piston - returning to default position")
            time.sleep(timing_settings.get("tool_action_delay", 0.1))
            line_cutter_piston = "up"
            print("Line cutter piston UP - default position")
    else:
        print("Line cutter already up")

# Row tools (X-axis operations)
def row_marker_down():
    """Lower row marker to marking position (does NOT affect motor door limit switch)"""
    global row_marker_state, row_marker_piston
    print("MOCK: row_marker_down()")
    if row_marker_state != "down":
        # First lower the piston (bring marker assembly down)
        if row_marker_piston != "down":
            print("Lowering row marker piston - bringing marker assembly down")
            time.sleep(timing_settings.get("tool_action_delay", 0.1))
            row_marker_piston = "down"
            print("Row marker piston DOWN - assembly lowered")

        # Then activate the marker
        print("Lowering row marker")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_state = "down"
        print("Row marker down - ready to mark")
    else:
        print("Row marker already down")

def row_marker_up():
    """Raise row marker from marking position (does NOT affect motor door limit switch)"""
    global row_marker_state, row_marker_piston
    print("MOCK: row_marker_up()")
    if row_marker_state != "up":
        # First deactivate the marker
        print("Raising row marker")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_state = "up"
        print("Row marker up")

        # Then raise the piston (lift marker assembly up to default position)
        if row_marker_piston != "up":
            print("Raising row marker piston - returning to default position")
            time.sleep(timing_settings.get("tool_action_delay", 0.1))
            row_marker_piston = "up"
            print("Row marker piston UP - default position")
    else:
        print("Row marker already up")

def row_cutter_down():
    """Lower row cutter to cutting position"""
    global row_cutter_state, row_cutter_piston
    print("MOCK: row_cutter_down()")
    if row_cutter_state != "down":
        # First lower the piston (bring cutter assembly down)
        if row_cutter_piston != "down":
            print("Lowering row cutter piston - bringing cutter assembly down")
            time.sleep(timing_settings.get("tool_action_delay", 0.1))
            row_cutter_piston = "down"
            print("Row cutter piston DOWN - assembly lowered")

        # Then activate the cutter
        print("Lowering row cutter")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_state = "down"
        print("Row cutter down - ready to cut")
    else:
        print("Row cutter already down")

def row_cutter_up():
    """Raise row cutter from cutting position"""
    global row_cutter_state, row_cutter_piston
    print("MOCK: row_cutter_up()")
    if row_cutter_state != "up":
        # First deactivate the cutter
        print("Raising row cutter")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_state = "up"
        print("Row cutter up")

        # Then raise the piston (lift cutter assembly up to default position)
        if row_cutter_piston != "up":
            print("Raising row cutter piston - returning to default position")
            time.sleep(timing_settings.get("tool_action_delay", 0.1))
            row_cutter_piston = "up"
            print("Row cutter piston UP - default position")
    else:
        print("Row cutter already up")

# Global reference to execution engine for sensor positioning
current_execution_engine = None

# Sensor functions with manual triggering and timing control
def wait_for_x_left_sensor():
    """Wait for LEFT X sensor specifically. Ignores premature triggers and safety pauses."""
    print("MOCK: wait_for_x_left_sensor()")
    print("Waiting for LEFT X sensor... (Use trigger_x_left_sensor())")
    print("In GUI mode, click 'Left Edge' button")
    
    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['x_left'].clear()
    
    # Wait specifically for left sensor
    while True:
        if sensor_events['x_left'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                print("🚫 X LEFT sensor trigger ignored - execution paused due to safety violation")
                sensor_events['x_left'].clear()  # Flush the trigger
                continue  # Keep waiting
            
            sensor_events['x_left'].clear()
            sensor_results['x_sensor'] = 'left'
            print("X LEFT sensor triggered: LEFT edge detected")
            
            # Move pointer to sensor location if execution engine available
            _move_to_sensor_location('x_left')
            
            return 'left'

def wait_for_x_right_sensor():
    """Wait for RIGHT X sensor specifically. Ignores premature triggers and safety pauses."""
    print("MOCK: wait_for_x_right_sensor()")
    print("Waiting for RIGHT X sensor... (Use trigger_x_right_sensor())")
    print("In GUI mode, click 'Right Edge' button")
    
    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['x_right'].clear()
    
    # Wait specifically for right sensor
    while True:
        if sensor_events['x_right'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                print("🚫 X RIGHT sensor trigger ignored - execution paused due to safety violation")
                sensor_events['x_right'].clear()  # Flush the trigger
                continue  # Keep waiting
            
            sensor_events['x_right'].clear()
            sensor_results['x_sensor'] = 'right'
            print("X RIGHT sensor triggered: RIGHT edge detected")
            
            # Move pointer to sensor location if execution engine available
            _move_to_sensor_location('x_right')
            
            return 'right'

def wait_for_y_top_sensor():
    """Wait for TOP Y sensor specifically. Ignores premature triggers and safety pauses."""
    print("MOCK: wait_for_y_top_sensor()")
    print("Waiting for TOP Y sensor... (Use trigger_y_top_sensor())")
    print("In GUI mode, click 'Top Edge' button")
    
    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['y_top'].clear()
    
    # Wait specifically for top sensor
    while True:
        if sensor_events['y_top'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                print("🚫 Y TOP sensor trigger ignored - execution paused due to safety violation")
                sensor_events['y_top'].clear()  # Flush the trigger
                continue  # Keep waiting
            
            sensor_events['y_top'].clear()
            sensor_results['y_sensor'] = 'top'
            print("Y TOP sensor triggered: TOP edge detected")
            
            # Move pointer to sensor location if execution engine available
            _move_to_sensor_location('y_top')
            
            return 'top'

def wait_for_y_bottom_sensor():
    """Wait for BOTTOM Y sensor specifically. Ignores premature triggers and safety pauses."""
    print("MOCK: wait_for_y_bottom_sensor()")
    print("Waiting for BOTTOM Y sensor... (Use trigger_y_bottom_sensor())")
    print("In GUI mode, click 'Bottom Edge' button")
    
    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['y_bottom'].clear()
    
    # Wait specifically for bottom sensor
    while True:
        if sensor_events['y_bottom'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                print("🚫 Y BOTTOM sensor trigger ignored - execution paused due to safety violation")
                sensor_events['y_bottom'].clear()  # Flush the trigger
                continue  # Keep waiting
            
            sensor_events['y_bottom'].clear()
            sensor_results['y_sensor'] = 'bottom'
            print("Y BOTTOM sensor triggered: BOTTOM edge detected")
            
            # Move pointer to sensor location if execution engine available
            _move_to_sensor_location('y_bottom')
            
            return 'bottom'

# Legacy sensor functions for backward compatibility
def wait_for_x_sensor():
    """Wait for X sensor to be triggered manually. Returns 'left' or 'right'. Ignores triggers during safety pauses."""
    print("MOCK: wait_for_x_sensor()")
    print("Waiting for X sensor... (Use trigger_x_left_sensor() or trigger_x_right_sensor())")
    print("In GUI mode, click 'Left Edge' or 'Right Edge' buttons")
    
    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['x_left'].clear()
    sensor_events['x_right'].clear()
    
    # Wait for either left or right sensor
    while True:
        if sensor_events['x_left'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                print("🚫 X LEFT sensor trigger ignored - execution paused due to safety violation")
                sensor_events['x_left'].clear()  # Flush the trigger
                continue  # Keep waiting
            
            sensor_events['x_left'].clear()
            sensor_results['x_sensor'] = 'left'
            print("X sensor triggered: LEFT edge detected")
            return 'left'
        elif sensor_events['x_right'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                print("🚫 X RIGHT sensor trigger ignored - execution paused due to safety violation")
                sensor_events['x_right'].clear()  # Flush the trigger
                continue  # Keep waiting
            
            sensor_events['x_right'].clear()
            sensor_results['x_sensor'] = 'right'
            print("X sensor triggered: RIGHT edge detected")
            return 'right'

def wait_for_y_sensor():
    """Wait for Y sensor to be triggered manually. Returns 'top' or 'bottom'. Ignores triggers during safety pauses."""
    print("MOCK: wait_for_y_sensor()")
    print("Waiting for Y sensor... (Use trigger_y_top_sensor() or trigger_y_bottom_sensor())")
    print("In GUI mode, click 'Top Edge' or 'Bottom Edge' buttons")
    
    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['y_top'].clear()
    sensor_events['y_bottom'].clear()
    
    # Wait for either top or bottom sensor
    while True:
        if sensor_events['y_top'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                print("🚫 Y TOP sensor trigger ignored - execution paused due to safety violation")
                sensor_events['y_top'].clear()  # Flush the trigger
                continue  # Keep waiting
            
            sensor_events['y_top'].clear()
            sensor_results['y_sensor'] = 'top'
            print("Y sensor triggered: TOP edge detected")
            return 'top'
        elif sensor_events['y_bottom'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                print("🚫 Y BOTTOM sensor trigger ignored - execution paused due to safety violation")
                sensor_events['y_bottom'].clear()  # Flush the trigger
                continue  # Keep waiting
            
            sensor_events['y_bottom'].clear()
            sensor_results['y_sensor'] = 'bottom'
            print("Y sensor triggered: BOTTOM edge detected")
            return 'bottom'

# Sensor buffer management for safety system
def flush_all_sensor_buffers():
    """Clear all sensor event buffers - used when resuming from safety pauses"""
    print("🧹 FLUSH: Clearing all sensor buffers (removing triggers from safety pause)")
    for sensor_name, event in sensor_events.items():
        if event.is_set():
            print(f"    Flushing {sensor_name} sensor buffer")
        event.clear()
    print("✅ All sensor buffers cleared - ready for post-resume triggers")

# Manual sensor triggers for testing
def trigger_x_left_sensor():
    """Manually trigger left X sensor"""
    global sensor_trigger_states, sensor_trigger_timers
    print("MOCK: trigger_x_left_sensor()")
    sensor_events['x_left'].set()
    sensor_trigger_states['x_left'] = True
    sensor_trigger_timers['x_left'] = time.time()
    print("Manual trigger: X LEFT sensor activated")

def trigger_x_right_sensor():
    """Manually trigger right X sensor"""
    global sensor_trigger_states, sensor_trigger_timers
    print("MOCK: trigger_x_right_sensor()")
    sensor_events['x_right'].set()
    sensor_trigger_states['x_right'] = True
    sensor_trigger_timers['x_right'] = time.time()
    print("Manual trigger: X RIGHT sensor activated")

def trigger_y_top_sensor():
    """Manually trigger top Y sensor"""
    global sensor_trigger_states, sensor_trigger_timers
    print("MOCK: trigger_y_top_sensor()")
    sensor_events['y_top'].set()
    sensor_trigger_states['y_top'] = True
    sensor_trigger_timers['y_top'] = time.time()
    print("Manual trigger: Y TOP sensor activated")

def trigger_y_bottom_sensor():
    """Manually trigger bottom Y sensor"""
    global sensor_trigger_states, sensor_trigger_timers
    print("MOCK: trigger_y_bottom_sensor()")
    sensor_events['y_bottom'].set()
    sensor_trigger_states['y_bottom'] = True
    sensor_trigger_timers['y_bottom'] = time.time()
    print("Manual trigger: Y BOTTOM sensor activated")

# Tool positioning functions (convenience functions for test controls)
def lift_line_tools():
    """Lift line tools off surface (convenience function for manual testing)"""
    print("MOCK: lift_line_tools()")
    print("Lifting line tools off surface")
    line_marker_up()
    line_cutter_up()
    time.sleep(timing_settings.get("row_marker_stable_delay", 0.2))
    print("Line tools lifted")

def lower_line_tools():
    """Lower line tools to surface (convenience function for manual testing)"""
    print("MOCK: lower_line_tools()")
    print("Lowering line tools to surface")
    time.sleep(timing_settings.get("row_marker_stable_delay", 0.2))
    print("Line tools lowered to surface")

def move_line_tools_to_top():
    """Move line tools to maximum Y position"""
    print("MOCK: move_line_tools_to_top()")
    print("Moving line tools to top position")
    lift_line_tools()
    move_y(MAX_Y_POSITION)
    print("Line tools moved to top")

# Line marker piston control functions
def line_marker_piston_up():
    """Raise line marker piston (default state)"""
    global line_marker_piston
    print("MOCK: line_marker_piston_up()")
    if line_marker_piston != "up":
        print("Raising line marker piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_piston = "up"
        print("Line marker piston UP - default position")
    else:
        print("Line marker piston already UP")

def line_marker_piston_down():
    """Lower line marker piston (for operations)"""
    global line_marker_piston
    print("MOCK: line_marker_piston_down()")
    if line_marker_piston != "down":
        print("Lowering line marker piston - preparing for operations")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_piston = "down"
        print("Line marker piston DOWN - ready for operations")
    else:
        print("Line marker piston already DOWN")

# Line cutter piston control functions
def line_cutter_piston_up():
    """Raise line cutter piston (default state)"""
    global line_cutter_piston
    print("MOCK: line_cutter_piston_up()")
    if line_cutter_piston != "up":
        print("Raising line cutter piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_piston = "up"
        print("Line cutter piston UP - default position")
    else:
        print("Line cutter piston already UP")

def line_cutter_piston_down():
    """Lower line cutter piston (for operations)"""
    global line_cutter_piston
    print("MOCK: line_cutter_piston_down()")
    if line_cutter_piston != "down":
        print("Lowering line cutter piston - preparing for operations")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_piston = "down"
        print("Line cutter piston DOWN - ready for operations")
    else:
        print("Line cutter piston already DOWN")

# Line motor piston control functions
def line_motor_piston_up():
    """Lift line motor piston (raises entire Y motor assembly)"""
    global line_motor_piston, line_motor_piston_sensor
    print("MOCK: line_motor_piston_up()")
    if line_motor_piston != "up":
        print("Raising line motor piston - lifting Y motor assembly")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_motor_piston = "up"
        line_motor_piston_sensor = "up"  # Sensor detects lifted position
        print("Line motor piston UP - Y motor assembly raised")
    else:
        print("Line motor piston already UP")

def line_motor_piston_down():
    """Lower line motor piston (lowers entire Y motor assembly)"""
    global line_motor_piston, line_motor_piston_sensor
    print("MOCK: line_motor_piston_down()")
    if line_motor_piston != "down":
        print("Lowering line motor piston - lowering Y motor assembly")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_motor_piston = "down"
        line_motor_piston_sensor = "down"  # Sensor detects lowered position
        print("Line motor piston DOWN - Y motor assembly lowered")
    else:
        print("Line motor piston already DOWN")

# Row marker piston control functions
def row_marker_piston_up():
    """Raise row marker piston (default state)"""
    global row_marker_piston
    print("MOCK: row_marker_piston_up()")
    if row_marker_piston != "up":
        print("Raising row marker piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "up"
        print("Row marker piston UP - default position")
    else:
        print("Row marker piston already UP")

def row_marker_piston_down():
    """Lower row marker piston (for operations)"""
    global row_marker_piston
    print("MOCK: row_marker_piston_down()")
    if row_marker_piston != "down":
        print("Lowering row marker piston - preparing for operations")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "down"
        print("Row marker piston DOWN - ready for operations")
    else:
        print("Row marker piston already DOWN")

# Row cutter piston control functions
def row_cutter_piston_up():
    """Raise row cutter piston (default state)"""
    global row_cutter_piston
    print("MOCK: row_cutter_piston_up()")
    if row_cutter_piston != "up":
        print("Raising row cutter piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "up"
        print("Row cutter piston UP - default position")
    else:
        print("Row cutter piston already UP")

def row_cutter_piston_down():
    """Lower row cutter piston (for operations)"""
    global row_cutter_piston
    print("MOCK: row_cutter_piston_down()")
    if row_cutter_piston != "down":
        print("Lowering row cutter piston - preparing for operations")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "down"
        print("Row cutter piston DOWN - ready for operations")
    else:
        print("Row cutter piston already DOWN")

# Status and diagnostic functions
def get_hardware_status():
    """Get current hardware status for debugging"""
    status = {
        'x_position': current_x_position,
        'y_position': current_y_position,
        'line_marker': line_marker_state,
        'line_marker_piston': line_marker_piston,
        'line_cutter': line_cutter_state,
        'line_cutter_piston': line_cutter_piston,
        'line_motor_piston': line_motor_piston,
        'line_motor_piston_sensor': line_motor_piston_sensor,
        'row_marker_piston': row_marker_piston,
        'row_marker': row_marker_state,
        'row_marker_limit_switch': row_marker_limit_switch,
        'row_cutter_piston': row_cutter_piston,
        'row_cutter': row_cutter_state
    }
    return status

def print_hardware_status():
    """Print current hardware status"""
    print("\n=== Hardware Status ===")
    print(f"X Position: {current_x_position:.1f}cm")
    print(f"Y Position: {current_y_position:.1f}cm")
    print(f"Line Marker: {line_marker_state}")
    print(f"Line Marker Piston: {line_marker_piston}")
    print(f"Line Cutter: {line_cutter_state}")
    print(f"Line Cutter Piston: {line_cutter_piston}")
    print(f"Line Motor Piston: {line_motor_piston}")
    print(f"Line Motor Piston Sensor: {line_motor_piston_sensor}")
    print(f"Row Marker Piston: {row_marker_piston}")
    print(f"Row Marker: {row_marker_state}")
    print(f"Row Marker Limit Switch: {row_marker_limit_switch}")
    print(f"Row Cutter Piston: {row_cutter_piston}")
    print(f"Row Cutter: {row_cutter_state}")
    print("=====================\n")

if __name__ == "__main__":
    print("Mock Hardware System Test")
    print("========================")
    
    # Test movement
    print("\nTesting movement:")
    move_x(25.0)
    move_y(30.0)
    
    # Test tools
    print("\nTesting line tools:")
    line_marker_down()
    line_marker_up()
    
    print("\nTesting row tools:")
    row_marker_down()
    row_marker_up()
    
    # Show status
    print_hardware_status()
    
    print("Mock hardware test complete!")

def set_execution_engine_reference(execution_engine):
    """Set reference to execution engine for sensor positioning"""
    global current_execution_engine
    current_execution_engine = execution_engine

def _move_to_sensor_location(sensor_type):
    """Trigger visual sensor update in canvas when triggered during wait_sensor steps.
    NOTE: This does NOT move motors - only updates canvas display!
    Motors only move during actual execution steps (move_x, move_y commands).
    """
    global current_execution_engine

    if not current_execution_engine:
        print(f"No execution engine reference - sensor {sensor_type} triggered but no GUI update")
        return

    # Check if execution engine is currently running and in a wait_sensor step
    if not current_execution_engine.is_running:
        print(f"Execution engine not running - sensor {sensor_type} triggered but ignoring (not part of current execution plan)")
        return

    # Check if current step is a wait_sensor step
    if (current_execution_engine.current_step_index < len(current_execution_engine.steps)):
        current_step = current_execution_engine.steps[current_execution_engine.current_step_index]
        if current_step.get('operation') != 'wait_sensor':
            print(f"Current step is not wait_sensor - sensor {sensor_type} triggered but ignoring (not part of current execution plan)")
            return

        # Verify the sensor type matches the expected sensor in the current step
        expected_sensor = current_step.get('parameters', {}).get('sensor')
        sensor_match = False

        if expected_sensor == 'x' and sensor_type in ['x_left', 'x_right']:
            sensor_match = True
        elif expected_sensor == 'y' and sensor_type in ['y_top', 'y_bottom']:
            sensor_match = True
        elif expected_sensor == sensor_type:
            sensor_match = True

        if not sensor_match:
            print(f"Sensor {sensor_type} doesn't match expected sensor {expected_sensor} - ignoring trigger")
            return

    if not hasattr(current_execution_engine, 'canvas_manager') or not current_execution_engine.canvas_manager:
        print(f"No canvas manager available - sensor {sensor_type} triggered but no GUI update")
        return

    canvas_manager = current_execution_engine.canvas_manager

    if not canvas_manager.main_app.current_program:
        print(f"No current program loaded - sensor {sensor_type} triggered but no program context")
        return

    # IMPORTANT: Only update visual display, do NOT move motors!
    # The canvas_sensors.trigger_sensor_visualization() will handle visual updates
    # Motors should only move during actual execution steps (move_x, move_y commands)
    print(f"📍 Sensor {sensor_type} triggered - updating canvas display only (motors remain at current position)")

    # Trigger canvas visualization update without moving motors
    if hasattr(canvas_manager, 'canvas_sensors'):
        canvas_manager.canvas_sensors.trigger_sensor_visualization(sensor_type)
    else:
        # Fallback - just update position display
        canvas_manager.update_position_display()

# Tool state getter functions
def get_line_marker_state():
    """Get current line marker state"""
    return line_marker_state

def get_line_marker_piston_state():
    """Get current line marker piston state"""
    return line_marker_piston

def get_line_cutter_piston_state():
    """Get current line cutter piston state"""
    return line_cutter_piston

def get_line_motor_piston_state():
    """Get current line motor piston state (lifts entire Y motor assembly)"""
    return line_motor_piston

def get_line_motor_piston_sensor_state():
    """Get current line motor piston sensor state (detects piston position)"""
    return line_motor_piston_sensor

def get_line_cutter_state():
    """Get current line cutter state"""
    return line_cutter_state

def get_row_marker_state():
    """Get current row marker state"""
    return row_marker_state

def get_row_marker_piston_state():
    """Get current row marker piston state"""
    return row_marker_piston

def get_row_cutter_state():
    """Get current row cutter state"""
    return row_cutter_state

def get_row_cutter_piston_state():
    """Get current row cutter piston state"""
    return row_cutter_piston

def get_row_motor_limit_switch():
    """Get current row marker limit switch state - reads from limit_switch_states['rows']"""
    # Map boolean limit switch state to "up"/"down" string
    # True (checked/ON) = DOWN, False (unchecked/OFF) = UP
    return "down" if limit_switch_states.get('rows', False) else "up"

def set_row_marker_limit_switch(state):
    """Manually set row marker limit switch state (operator control)"""
    global row_marker_limit_switch
    if state in ["up", "down"]:
        row_marker_limit_switch = state
        print(f"Row marker limit switch manually set to: {state.upper()}")

def get_sensor_trigger_states():
    """Get current sensor trigger states with auto-reset after 1 second"""
    global sensor_trigger_states, sensor_trigger_timers
    current_time = time.time()

    # Auto-reset sensors that have been triggered for more than 1 second
    for sensor_name in sensor_trigger_states:
        if sensor_trigger_states[sensor_name] and (current_time - sensor_trigger_timers[sensor_name] > 1.0):
            sensor_trigger_states[sensor_name] = False

    return sensor_trigger_states.copy()

def reset_sensor_trigger_state(sensor_name):
    """Manually reset a specific sensor trigger state"""
    global sensor_trigger_states
    if sensor_name in sensor_trigger_states:
        sensor_trigger_states[sensor_name] = False

def toggle_row_marker_limit_switch():
    """Toggle row marker limit switch state (for manual operator control)"""
    global row_marker_limit_switch
    new_state = "down" if row_marker_limit_switch == "up" else "up"
    row_marker_limit_switch = new_state
    print(f"Row marker limit switch toggled to: {new_state.upper()}")
    return new_state

# Limit switch control functions
def toggle_limit_switch(switch_name):
    """Toggle a limit switch state (motor door sensor - independent from marker piston)"""
    global limit_switch_states
    if switch_name in limit_switch_states:
        limit_switch_states[switch_name] = not limit_switch_states[switch_name]
        state = "ON" if limit_switch_states[switch_name] else "OFF"
        print(f"Limit switch {switch_name} toggled to: {state}")
        # Note: This is motor door sensor, NOT marker piston position
        return limit_switch_states[switch_name]
    return False

def get_limit_switch_state(switch_name):
    """Get a limit switch state"""
    return limit_switch_states.get(switch_name, False)

def set_limit_switch_state(switch_name, state):
    """Set a limit switch state"""
    global limit_switch_states
    if switch_name in limit_switch_states:
        limit_switch_states[switch_name] = state
        print(f"Limit switch {switch_name} set to: {'ON' if state else 'OFF'}")
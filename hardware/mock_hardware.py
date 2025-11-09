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

# Load settings from config/settings.json
def load_settings():
    """Load hardware settings from config/settings.json"""
    try:
        with open('config/settings.json', 'r') as f:
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
# NOTE: Each piston/tool has TWO sensors (up sensor + down sensor)
# Sensor logic: When piston UP → up_sensor=True, down_sensor=False
#               When piston DOWN → up_sensor=False, down_sensor=True

# LINES TOOLS (Y-axis / horizontal operations)
# Line Marker - single piston with dual sensors
line_marker_piston = "up"          # Piston control: "up" (default) or "down" (for operations)
line_marker_up_sensor = True       # Sensor: True when piston is UP (default)
line_marker_down_sensor = False    # Sensor: True when piston is DOWN

# Line Cutter - single piston with dual sensors
line_cutter_piston = "up"          # Piston control: "up" (default) or "down" (for operations)
line_cutter_up_sensor = True       # Sensor: True when piston is UP (default)
line_cutter_down_sensor = False    # Sensor: True when piston is DOWN

# Line Motor - Single piston (left and right connected to same port)
line_motor_piston = "down"         # Piston control: "down" (default) or "up" (during upward Y movement)
line_motor_up_sensor = False       # Sensor: True when piston is UP
line_motor_down_sensor = True      # Sensor: True when piston is DOWN (default)

# ROWS TOOLS (X-axis / vertical operations)
# Row Marker - single piston with dual sensors
row_marker_piston = "up"           # Piston control: "up" (default) or "down" (for operations)
row_marker_up_sensor = True        # Sensor: True when piston is UP (default)
row_marker_down_sensor = False     # Sensor: True when piston is DOWN

# Row Cutter - single piston with dual sensors
row_cutter_piston = "up"           # Piston control: "up" (default) or "down" (for operations)
row_cutter_up_sensor = True        # Sensor: True when piston is UP (default)
row_cutter_down_sensor = False     # Sensor: True when piston is DOWN

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

# Edge sensor states (hardware sensors that detect paper edges)
x_left_edge = False      # X left edge sensor
x_right_edge = False     # X right edge sensor
y_top_edge = False       # Y top edge sensor
y_bottom_edge = False    # Y bottom edge sensor

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
    global line_marker_piston, line_marker_up_sensor, line_marker_down_sensor
    global line_cutter_piston, line_cutter_up_sensor, line_cutter_down_sensor
    global line_motor_piston_left, line_motor_left_up_sensor, line_motor_left_down_sensor
    global line_motor_piston_right, line_motor_right_up_sensor, line_motor_right_down_sensor
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    global limit_switch_states
    global x_left_edge, x_right_edge, y_top_edge, y_bottom_edge

    current_x_position = 0.0
    current_y_position = 0.0

    # Line marker - default UP
    line_marker_piston = "up"
    line_marker_up_sensor = True
    line_marker_down_sensor = False

    # Line cutter - default UP
    line_cutter_piston = "up"
    line_cutter_up_sensor = True
    line_cutter_down_sensor = False

    # Line motor left piston - default DOWN
    line_motor_piston_left = "down"
    line_motor_left_up_sensor = False
    line_motor_left_down_sensor = True

    # Line motor right piston - default DOWN
    line_motor_piston_right = "down"
    line_motor_right_up_sensor = False
    line_motor_right_down_sensor = True

    # Row marker - default UP
    row_marker_piston = "up"
    row_marker_up_sensor = True
    row_marker_down_sensor = False

    # Row cutter - default UP
    row_cutter_piston = "up"
    row_cutter_up_sensor = True
    row_cutter_down_sensor = False

    # Edge sensors - default off
    x_left_edge = False
    x_right_edge = False
    y_top_edge = False
    y_bottom_edge = False

    limit_switch_states['rows'] = False # Default is False (UP)

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
    global line_marker_piston, line_marker_up_sensor, line_marker_down_sensor
    print("MOCK: line_marker_down()")
    if line_marker_piston != "down":
        print("Lowering line marker piston - bringing marker assembly down")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_piston = "down"
        # Update sensors: up sensor OFF, down sensor ON
        line_marker_up_sensor = False
        line_marker_down_sensor = True
        print("Line marker piston DOWN - assembly lowered (up_sensor=False, down_sensor=True)")
    else:
        print("Line marker already down")

def line_marker_up():
    """Raise line marker from marking position"""
    global line_marker_piston, line_marker_up_sensor, line_marker_down_sensor
    print("MOCK: line_marker_up()")
    if line_marker_piston != "up":
        print("Raising line marker piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_piston = "up"
        # Update sensors: up sensor ON, down sensor OFF
        line_marker_up_sensor = True
        line_marker_down_sensor = False
        print("Line marker piston UP - default position (up_sensor=True, down_sensor=False)")
    else:
        print("Line marker already up")

def line_cutter_down():
    """Lower line cutter to cutting position"""
    global line_cutter_piston, line_cutter_up_sensor, line_cutter_down_sensor
    print("MOCK: line_cutter_down()")
    if line_cutter_piston != "down":
        print("Lowering line cutter piston - bringing cutter assembly down")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_piston = "down"
        # Update sensors: up sensor OFF, down sensor ON
        line_cutter_up_sensor = False
        line_cutter_down_sensor = True
        print("Line cutter piston DOWN - assembly lowered (up_sensor=False, down_sensor=True)")
    else:
        print("Line cutter already down")

def line_cutter_up():
    """Raise line cutter from cutting position"""
    global line_cutter_piston, line_cutter_up_sensor, line_cutter_down_sensor
    print("MOCK: line_cutter_up()")
    if line_cutter_piston != "up":
        print("Raising line cutter piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_piston = "up"
        # Update sensors: up sensor ON, down sensor OFF
        line_cutter_up_sensor = True
        line_cutter_down_sensor = False
        print("Line cutter piston UP - default position (up_sensor=True, down_sensor=False)")
    else:
        print("Line cutter already up")

# Row tools (X-axis operations)
def row_marker_down():
    """Lower row marker to marking position (does NOT affect motor door limit switch)"""
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    print("MOCK: row_marker_down()")
    if row_marker_piston != "down":
        print("Lowering row marker piston - bringing marker assembly down")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "down"
        # Update sensors: up sensor OFF, down sensor ON
        row_marker_up_sensor = False
        row_marker_down_sensor = True
        print("Row marker piston DOWN - assembly lowered (up_sensor=False, down_sensor=True)")
    else:
        print("Row marker already down")

def row_marker_up():
    """Raise row marker from marking position (does NOT affect motor door limit switch)"""
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    print("MOCK: row_marker_up()")
    if row_marker_piston != "up":
        print("Raising row marker piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "up"
        # Update sensors: up sensor ON, down sensor OFF
        row_marker_up_sensor = True
        row_marker_down_sensor = False
        print("Row marker piston UP - default position (up_sensor=True, down_sensor=False)")
    else:
        print("Row marker already up")

def row_cutter_down():
    """Lower row cutter to cutting position"""
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    print("MOCK: row_cutter_down()")
    if row_cutter_piston != "down":
        print("Lowering row cutter piston - bringing cutter assembly down")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "down"
        # Update sensors: up sensor OFF, down sensor ON
        row_cutter_up_sensor = False
        row_cutter_down_sensor = True
        print("Row cutter piston DOWN - assembly lowered (up_sensor=False, down_sensor=True)")
    else:
        print("Row cutter already down")

def row_cutter_up():
    """Raise row cutter from cutting position"""
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    print("MOCK: row_cutter_up()")
    if row_cutter_piston != "up":
        print("Raising row cutter piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "up"
        # Update sensors: up sensor ON, down sensor OFF
        row_cutter_up_sensor = True
        row_cutter_down_sensor = False
        print("Row cutter piston UP - default position (up_sensor=True, down_sensor=False)")
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
    global sensor_trigger_states, sensor_trigger_timers, x_left_edge
    print("MOCK: trigger_x_left_sensor()")
    sensor_events['x_left'].set()
    sensor_trigger_states['x_left'] = True
    sensor_trigger_timers['x_left'] = time.time()
    x_left_edge = True  # Set edge sensor state
    print("Manual trigger: X LEFT sensor activated")

def trigger_x_right_sensor():
    """Manually trigger right X sensor"""
    global sensor_trigger_states, sensor_trigger_timers, x_right_edge
    print("MOCK: trigger_x_right_sensor()")
    sensor_events['x_right'].set()
    sensor_trigger_states['x_right'] = True
    sensor_trigger_timers['x_right'] = time.time()
    x_right_edge = True  # Set edge sensor state
    print("Manual trigger: X RIGHT sensor activated")

def trigger_y_top_sensor():
    """Manually trigger top Y sensor"""
    global sensor_trigger_states, sensor_trigger_timers, y_top_edge
    print("MOCK: trigger_y_top_sensor()")
    sensor_events['y_top'].set()
    sensor_trigger_states['y_top'] = True
    sensor_trigger_timers['y_top'] = time.time()
    y_top_edge = True  # Set edge sensor state
    print("Manual trigger: Y TOP sensor activated")

def trigger_y_bottom_sensor():
    """Manually trigger bottom Y sensor"""
    global sensor_trigger_states, sensor_trigger_timers, y_bottom_edge
    print("MOCK: trigger_y_bottom_sensor()")
    sensor_events['y_bottom'].set()
    sensor_trigger_states['y_bottom'] = True
    sensor_trigger_timers['y_bottom'] = time.time()
    y_bottom_edge = True  # Set edge sensor state
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
# Line motor dual pistons (left + right) control functions
def line_motor_piston_up():
    """Lift line motor piston (raises entire Y motor assembly)"""
    global line_motor_piston, line_motor_up_sensor, line_motor_down_sensor
    print("MOCK: line_motor_piston_up()")
    if line_motor_piston != "up":
        print("Raising line motor piston - lifting Y motor assembly")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_motor_piston = "up"
        # Update sensors: up sensor ON, down sensor OFF
        line_motor_up_sensor = True
        line_motor_down_sensor = False
        print("Line motor piston UP (up_sensor=True, down_sensor=False)")
    else:
        print("Line motor piston already UP")

def line_motor_piston_down():
    """Lower line motor piston (lowers entire Y motor assembly)"""
    global line_motor_piston, line_motor_up_sensor, line_motor_down_sensor
    print("MOCK: line_motor_piston_down()")
    if line_motor_piston != "down":
        print("Lowering line motor piston - lowering Y motor assembly")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_motor_piston = "down"
        # Update sensors: up sensor OFF, down sensor ON
        line_motor_up_sensor = False
        line_motor_down_sensor = True
        print("Line motor piston DOWN (up_sensor=False, down_sensor=True)")
    else:
        print("Line motor piston already DOWN")

# Row marker piston control functions
def row_marker_piston_up():
    """Raise row marker piston (default state)"""
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    print("MOCK: row_marker_piston_up()")
    if row_marker_piston != "up":
        print("Raising row marker piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "up"
        row_marker_up_sensor = True
        row_marker_down_sensor = False
        print("Row marker piston UP - default position (up_sensor=True, down_sensor=False)")
    else:
        print("Row marker piston already UP")

def row_marker_piston_down():
    """Lower row marker piston (for operations)"""
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    print("MOCK: row_marker_piston_down()")
    if row_marker_piston != "down":
        print("Lowering row marker piston - preparing for operations")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "down"
        row_marker_up_sensor = False
        row_marker_down_sensor = True
        print("Row marker piston DOWN - ready for operations (up_sensor=False, down_sensor=True)")
    else:
        print("Row marker piston already DOWN")

# Row cutter piston control functions
def row_cutter_piston_up():
    """Raise row cutter piston (default state)"""
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    print("MOCK: row_cutter_piston_up()")
    if row_cutter_piston != "up":
        print("Raising row cutter piston - returning to default position")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "up"
        row_cutter_up_sensor = True
        row_cutter_down_sensor = False
        print("Row cutter piston UP - default position (up_sensor=True, down_sensor=False)")
    else:
        print("Row cutter piston already UP")

def row_cutter_piston_down():
    """Lower row cutter piston (for operations)"""
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    print("MOCK: row_cutter_piston_down()")
    if row_cutter_piston != "down":
        print("Lowering row cutter piston - preparing for operations")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "down"
        row_cutter_up_sensor = False
        row_cutter_down_sensor = True
        print("Row cutter piston DOWN - ready for operations (up_sensor=False, down_sensor=True)")
    else:
        print("Row cutter piston already DOWN")

# Status and diagnostic functions
def get_hardware_status():
    """Get current hardware status for debugging"""
    status = {
        'x_position': current_x_position,
        'y_position': current_y_position,
        # Line marker
        'line_marker_piston': line_marker_piston,
        'line_marker_up_sensor': line_marker_up_sensor,
        'line_marker_down_sensor': line_marker_down_sensor,
        # Line cutter
        'line_cutter_piston': line_cutter_piston,
        'line_cutter_up_sensor': line_cutter_up_sensor,
        'line_cutter_down_sensor': line_cutter_down_sensor,
        # Line motor left piston
        'line_motor_piston_left': line_motor_piston_left,
        'line_motor_left_up_sensor': line_motor_left_up_sensor,
        'line_motor_left_down_sensor': line_motor_left_down_sensor,
        # Line motor right piston
        'line_motor_piston_right': line_motor_piston_right,
        'line_motor_right_up_sensor': line_motor_right_up_sensor,
        'line_motor_right_down_sensor': line_motor_right_down_sensor,
        # Row marker
        'row_marker_piston': row_marker_piston,
        'row_marker_up_sensor': row_marker_up_sensor,
        'row_marker_down_sensor': row_marker_down_sensor,
        # Row cutter
        'row_cutter_piston': row_cutter_piston,
        'row_cutter_up_sensor': row_cutter_up_sensor,
        'row_cutter_down_sensor': row_cutter_down_sensor,
        # Limit switch
        'row_marker_limit_switch': "down" if limit_switch_states.get('rows', False) else "up"
    }
    return status

def print_hardware_status():
    """Print current hardware status"""
    print("\n=== Hardware Status ===")
    print(f"X Position: {current_x_position:.1f}cm")
    print(f"Y Position: {current_y_position:.1f}cm")
    print(f"\nLine Marker:")
    print(f"  Piston: {line_marker_piston}")
    print(f"  Up Sensor: {line_marker_up_sensor}")
    print(f"  Down Sensor: {line_marker_down_sensor}")
    print(f"\nLine Cutter:")
    print(f"  Piston: {line_cutter_piston}")
    print(f"  Up Sensor: {line_cutter_up_sensor}")
    print(f"  Down Sensor: {line_cutter_down_sensor}")
    print(f"\nLine Motor Left Piston:")
    print(f"  Piston: {line_motor_piston_left}")
    print(f"  Up Sensor: {line_motor_left_up_sensor}")
    print(f"  Down Sensor: {line_motor_left_down_sensor}")
    print(f"\nLine Motor Right Piston:")
    print(f"  Piston: {line_motor_piston_right}")
    print(f"  Up Sensor: {line_motor_right_up_sensor}")
    print(f"  Down Sensor: {line_motor_right_down_sensor}")
    print(f"\nRow Marker:")
    print(f"  Piston: {row_marker_piston}")
    print(f"  Up Sensor: {row_marker_up_sensor}")
    print(f"  Down Sensor: {row_marker_down_sensor}")
    print(f"\nRow Cutter:")
    print(f"  Piston: {row_cutter_piston}")
    print(f"  Up Sensor: {row_cutter_up_sensor}")
    print(f"  Down Sensor: {row_cutter_down_sensor}")
    print(f"\nRow Marker Limit Switch: {'down' if limit_switch_states.get('rows', False) else 'up'}")
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
# Line Marker getters
def get_line_marker_piston_state():
    """Get current line marker piston state"""
    return line_marker_piston

def get_line_marker_up_sensor():
    """Get line marker up sensor state"""
    return line_marker_up_sensor

def get_line_marker_down_sensor():
    """Get line marker down sensor state"""
    return line_marker_down_sensor

# Line Cutter getters
def get_line_cutter_piston_state():
    """Get current line cutter piston state"""
    return line_cutter_piston

def get_line_cutter_up_sensor():
    """Get line cutter up sensor state"""
    return line_cutter_up_sensor

def get_line_cutter_down_sensor():
    """Get line cutter down sensor state"""
    return line_cutter_down_sensor

# Line Motor Left Piston getters
def get_line_motor_piston_state():
    """Get current line motor piston state"""
    return line_motor_piston

def get_line_motor_up_sensor():
    """Get line motor up sensor state"""
    return line_motor_up_sensor

def get_line_motor_down_sensor():
    """Get line motor down sensor state"""
    return line_motor_down_sensor

# Row Marker getters
def get_row_marker_piston_state():
    """Get current row marker piston state"""
    return row_marker_piston

def get_row_marker_up_sensor():
    """Get row marker up sensor state"""
    return row_marker_up_sensor

def get_row_marker_down_sensor():
    """Get row marker down sensor state"""
    return row_marker_down_sensor

# Row Cutter getters
def get_row_cutter_piston_state():
    """Get current row cutter piston state"""
    return row_cutter_piston

def get_row_cutter_up_sensor():
    """Get row cutter up sensor state"""
    return row_cutter_up_sensor

def get_row_cutter_down_sensor():
    """Get row cutter down sensor state"""
    return row_cutter_down_sensor

# Legacy compatibility getters (for old code that expects single sensor)
def get_line_marker_state():
    """Get current line marker state (legacy - returns 'up' if up_sensor True, else 'down')"""
    return "up" if line_marker_up_sensor else "down"

def get_line_cutter_state():
    """Get current line cutter state (legacy - returns 'up' if up_sensor True, else 'down')"""
    return "up" if line_cutter_up_sensor else "down"

def get_row_marker_state():
    """Get current row marker state (legacy - returns 'up' if up_sensor True, else 'down')"""
    return "up" if row_marker_up_sensor else "down"

def get_row_cutter_state():
    """Get current row cutter state (legacy - returns 'up' if up_sensor True, else 'down')"""
    return "up" if row_cutter_up_sensor else "down"

# Edge sensor getters
def get_x_left_edge():
    """Get X left edge sensor state"""
    return x_left_edge

def get_x_right_edge():
    """Get X right edge sensor state"""
    return x_right_edge

def get_y_top_edge():
    """Get Y top edge sensor state"""
    return y_top_edge

def get_y_bottom_edge():
    """Get Y bottom edge sensor state"""
    return y_bottom_edge

def get_row_motor_limit_switch():
    """Get current row marker limit switch state - reads from limit_switch_states['rows']"""
    # Map boolean limit switch state to "up"/"down" string
    # True (checked/ON) = DOWN, False (unchecked/OFF) = UP
    return "down" if limit_switch_states.get('rows', False) else "up"

def set_row_marker_limit_switch(state):
    """Manually set row marker limit switch state (operator control)"""
    global limit_switch_states
    if state in ["up", "down"]:
        # True (ON) = DOWN, False (OFF) = UP
        limit_switch_states['rows'] = (state == "down")
        print(f"Row marker limit switch manually set to: {state.upper()}")

def get_sensor_trigger_states():
    """Get current sensor trigger states with auto-reset after 1 second"""
    global sensor_trigger_states, sensor_trigger_timers
    global x_left_edge, x_right_edge, y_top_edge, y_bottom_edge
    current_time = time.time()

    # Auto-reset sensors that have been triggered for more than 1 second
    for sensor_name in sensor_trigger_states:
        if sensor_trigger_states[sensor_name] and (current_time - sensor_trigger_timers[sensor_name] > 1.0):
            sensor_trigger_states[sensor_name] = False
            # Also reset edge sensor states
            if sensor_name == 'x_left':
                x_left_edge = False
            elif sensor_name == 'x_right':
                x_right_edge = False
            elif sensor_name == 'y_top':
                y_top_edge = False
            elif sensor_name == 'y_bottom':
                y_bottom_edge = False

    return sensor_trigger_states.copy()

def reset_sensor_trigger_state(sensor_name):
    """Manually reset a specific sensor trigger state"""
    global sensor_trigger_states
    if sensor_name in sensor_trigger_states:
        sensor_trigger_states[sensor_name] = False

def toggle_row_marker_limit_switch():
    """Toggle row marker limit switch state (for manual operator control)"""
    global limit_switch_states
    # Toggle the boolean state
    limit_switch_states['rows'] = not limit_switch_states['rows']
    new_state = "down" if limit_switch_states['rows'] else "up"
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


# ============================================================================
# CLASS-BASED WRAPPER FOR FACTORY PATTERN
# ============================================================================

class MockHardware:
    """
    Class-based wrapper for mock hardware functions.
    Provides same interface as RealHardware for factory pattern.
    """

    def __init__(self, config_path: str = "config/settings.json"):
        """Initialize mock hardware"""
        self.config_path = config_path
        self.is_initialized = False
        print("\n✓ Mock Hardware initialized\n")

    def initialize(self) -> bool:
        """Initialize mock hardware (always succeeds)"""
        self.is_initialized = True
        return True

    # ========== MOTOR CONTROL ==========
    def move_x(self, position: float) -> bool:
        return move_x(position)

    def move_y(self, position: float) -> bool:
        return move_y(position)

    def move_to(self, x: float, y: float) -> bool:
        move_x(x)
        move_y(y)
        return True

    def home_motors(self) -> bool:
        move_x(0.0)
        move_y(0.0)
        return True

    # ========== POSITION GETTERS ==========
    def get_current_x(self) -> float:
        return get_current_x()

    def get_current_y(self) -> float:
        return get_current_y()

    # ========== PISTON CONTROL ==========
    def line_marker_piston_down(self) -> bool:
        return line_marker_piston_down()

    def line_marker_piston_up(self) -> bool:
        return line_marker_piston_up()

    def line_cutter_piston_down(self) -> bool:
        return line_cutter_piston_down()

    def line_cutter_piston_up(self) -> bool:
        return line_cutter_piston_up()

    def line_motor_piston_down(self) -> bool:
        return line_motor_piston_down()

    def line_motor_piston_up(self) -> bool:
        return line_motor_piston_up()

    def row_marker_piston_down(self) -> bool:
        return row_marker_piston_down()

    def row_marker_piston_up(self) -> bool:
        return row_marker_piston_up()

    def row_cutter_piston_down(self) -> bool:
        return row_cutter_piston_down()

    def row_cutter_piston_up(self) -> bool:
        return row_cutter_piston_up()

    # ========== TOOL ACTION WRAPPERS ==========
    def line_marker_down(self) -> bool:
        return line_marker_down()

    def line_marker_up(self) -> bool:
        return line_marker_up()

    def line_cutter_down(self) -> bool:
        return line_cutter_down()

    def line_cutter_up(self) -> bool:
        return line_cutter_up()

    def row_marker_down(self) -> bool:
        return row_marker_down()

    def row_marker_up(self) -> bool:
        return row_marker_up()

    def row_cutter_down(self) -> bool:
        return row_cutter_down()

    def row_cutter_up(self) -> bool:
        return row_cutter_up()

    def lift_line_tools(self) -> bool:
        return lift_line_tools()

    def lower_line_tools(self) -> bool:
        return lower_line_tools()

    def move_line_tools_to_top(self) -> bool:
        return move_line_tools_to_top()

    # ========== SENSOR GETTERS ==========
    def get_line_marker_up_sensor(self) -> bool:
        return get_line_marker_up_sensor()

    def get_line_marker_down_sensor(self) -> bool:
        return get_line_marker_down_sensor()

    def get_line_cutter_up_sensor(self) -> bool:
        return get_line_cutter_up_sensor()

    def get_line_cutter_down_sensor(self) -> bool:
        return get_line_cutter_down_sensor()

    def get_line_motor_up_sensor(self) -> bool:
        return get_line_motor_up_sensor()

    def get_line_motor_down_sensor(self) -> bool:
        return get_line_motor_down_sensor()

    def get_row_marker_up_sensor(self) -> bool:
        return get_row_marker_up_sensor()

    def get_row_marker_down_sensor(self) -> bool:
        return get_row_marker_down_sensor()

    def get_row_cutter_up_sensor(self) -> bool:
        return get_row_cutter_up_sensor()

    def get_row_cutter_down_sensor(self) -> bool:
        return get_row_cutter_down_sensor()

    # ========== STATE GETTERS ==========
    def get_line_marker_state(self) -> str:
        return get_line_marker_state()

    def get_line_cutter_state(self) -> str:
        return get_line_cutter_state()

    def get_row_marker_state(self) -> str:
        return get_row_marker_state()

    def get_row_cutter_state(self) -> str:
        return get_row_cutter_state()

    def get_line_marker_piston_state(self) -> str:
        return get_line_marker_piston_state()

    def get_line_cutter_piston_state(self) -> str:
        return get_line_cutter_piston_state()

    def get_line_motor_piston_state(self) -> str:
        return get_line_motor_piston_state()

    def get_row_marker_piston_state(self) -> str:
        return get_row_marker_piston_state()

    def get_row_cutter_piston_state(self) -> str:
        return get_row_cutter_piston_state()

    # ========== EDGE SENSORS ==========
    def get_x_left_edge_sensor(self) -> bool:
        return get_x_left_edge()

    def get_x_right_edge_sensor(self) -> bool:
        return get_x_right_edge()

    def get_y_top_edge_sensor(self) -> bool:
        return get_y_top_edge()

    def get_y_bottom_edge_sensor(self) -> bool:
        return get_y_bottom_edge()

    def get_x_left_edge(self) -> bool:
        return get_x_left_edge()

    def get_x_right_edge(self) -> bool:
        return get_x_right_edge()

    def get_y_top_edge(self) -> bool:
        return get_y_top_edge()

    def get_y_bottom_edge(self) -> bool:
        return get_y_bottom_edge()

    def read_edge_sensors(self):
        return {
            'x_left': get_x_left_edge(),
            'x_right': get_x_right_edge(),
            'y_top': get_y_top_edge(),
            'y_bottom': get_y_bottom_edge()
        }

    # ========== LIMIT SWITCHES ==========
    def get_door_switch(self) -> bool:
        return get_limit_switch_state("rows_door")

    def get_rows_door_switch(self) -> bool:
        return get_limit_switch_state("rows_door")

    def get_limit_switch_state(self, switch_name: str) -> bool:
        return get_limit_switch_state(switch_name)

    def get_row_motor_limit_switch(self) -> str:
        return get_row_motor_limit_switch()

    def set_limit_switch_state(self, switch_name: str, state: bool):
        set_limit_switch_state(switch_name, state)

    def set_row_marker_limit_switch(self, state: bool):
        set_limit_switch_state("rows_door", state)

    def toggle_limit_switch(self, switch_name: str):
        return toggle_limit_switch(switch_name)

    def toggle_row_marker_limit_switch(self):
        toggle_limit_switch("rows_door")

    # ========== SENSOR TRIGGERS ==========
    def trigger_x_left_sensor(self):
        trigger_x_left_sensor()

    def trigger_x_right_sensor(self):
        trigger_x_right_sensor()

    def trigger_y_top_sensor(self):
        trigger_y_top_sensor()

    def trigger_y_bottom_sensor(self):
        trigger_y_bottom_sensor()

    def get_sensor_trigger_states(self):
        return get_sensor_trigger_states()

    # ========== WAIT FOR SENSORS ==========
    def wait_for_x_sensor(self):
        wait_for_x_sensor()

    def wait_for_y_sensor(self):
        wait_for_y_sensor()

    def wait_for_x_left_sensor(self):
        wait_for_x_left_sensor()

    def wait_for_x_right_sensor(self):
        wait_for_x_right_sensor()

    def wait_for_y_top_sensor(self):
        wait_for_y_top_sensor()

    def wait_for_y_bottom_sensor(self):
        wait_for_y_bottom_sensor()

    # ========== STATUS & CONTROL ==========
    def get_hardware_status(self):
        return get_hardware_status()

    def reset_hardware(self):
        reset_hardware()

    def emergency_stop(self) -> bool:
        print("MOCK: Emergency stop")
        return True

    def resume_operation(self) -> bool:
        print("MOCK: Resume operation")
        return True

    # ========== EXECUTION ENGINE INTEGRATION ==========
    def set_execution_engine_reference(self, engine):
        """Set execution engine reference for sensor waiting"""
        set_execution_engine_reference(engine)

    def flush_all_sensor_buffers(self):
        """Flush all sensor buffers"""
        flush_all_sensor_buffers()

    def shutdown(self):
        """Shutdown mock hardware"""
        print("MOCK: Shutdown")
        self.is_initialized = False
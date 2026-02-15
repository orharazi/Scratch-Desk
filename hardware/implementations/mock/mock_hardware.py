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
from core.logger import get_logger

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

# Line Motor - Single piston control for both sides, but separate sensors
line_motor_piston = "down"                # Piston control: "down" (default) or "up" (shared for both sides)
line_motor_left_up_sensor = False         # Left sensor: True when left side is UP
line_motor_left_down_sensor = True        # Left sensor: True when left side is DOWN (default)
line_motor_right_up_sensor = False        # Right sensor: True when right side is UP
line_motor_right_down_sensor = True       # Right sensor: True when right side is DOWN (default)

# ROWS TOOLS (X-axis / vertical operations)
# Row Marker - single piston with dual sensors
row_marker_piston = "up"           # Piston control: "up" (default) or "down" (for operations)
row_marker_up_sensor = True        # Sensor: True when piston is UP (default)
row_marker_down_sensor = False     # Sensor: True when piston is DOWN

# Row Cutter - single piston with dual sensors
row_cutter_piston = "up"           # Piston control: "up" (default) or "down" (for operations)
row_cutter_up_sensor = True        # Sensor: True when piston is UP (default)
row_cutter_down_sensor = False     # Sensor: True when piston is DOWN

# AIR PRESSURE SYSTEM
# Air pressure valve - controls airflow to all pneumatic pistons
air_pressure_valve = "up"          # Valve control: "up" (closed/no air) or "down" (open/air flowing)

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
    'rows_door': False   # Rows door limit switch - default UP
}

def reset_hardware():
    """Reset all hardware to initial state"""
    global current_x_position, current_y_position
    global line_marker_piston, line_marker_up_sensor, line_marker_down_sensor
    global line_cutter_piston, line_cutter_up_sensor, line_cutter_down_sensor
    global line_motor_piston, line_motor_left_up_sensor, line_motor_left_down_sensor
    global line_motor_right_up_sensor, line_motor_right_down_sensor
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    global air_pressure_valve
    global limit_switch_states
    global x_left_edge, x_right_edge, y_top_edge, y_bottom_edge
    global sensor_trigger_states, sensor_trigger_timers, execution_engine_reference

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

    # Line motor piston (shared control) - default DOWN
    line_motor_piston = "down"
    line_motor_left_up_sensor = False
    line_motor_left_down_sensor = True
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

    # Air pressure valve - default UP (closed)
    air_pressure_valve = "up"

    # Edge sensors - default off
    x_left_edge = False
    x_right_edge = False
    y_top_edge = False
    y_bottom_edge = False

    limit_switch_states['rows_door'] = False  # Default is False (UP)
    # At position (0,0), x_right and y_bottom limit switches are active (at home)
    limit_switch_states['x_right'] = True
    limit_switch_states['x_left'] = False
    limit_switch_states['y_bottom'] = True
    limit_switch_states['y_top'] = False

    # Clear all sensor events
    for event in sensor_events.values():
        event.clear()

    sensor_results['x_sensor'] = None
    sensor_results['y_sensor'] = None

    # Reset sensor trigger states (for live monitoring visualization)
    for key in sensor_trigger_states:
        sensor_trigger_states[key] = False

    # Reset sensor trigger timers
    for key in sensor_trigger_timers:
        sensor_trigger_timers[key] = 0

    # Clear execution engine reference to prevent stale callbacks
    execution_engine_reference = None

    logger = get_logger()
    logger.info("Hardware reset to initial state", category="hardware")

# Movement functions
def move_x(position):
    """Move X motor to specified position within limits"""
    global current_x_position, line_marker_piston

    logger = get_logger()
    logger.debug(f"move_x({position:.1f})", category="hardware")

    if position < MIN_X_POSITION:
        logger.warning(f"X position {position:.1f} below minimum {MIN_X_POSITION:.1f}, clamping", category="hardware")
        position = MIN_X_POSITION
    elif position > MAX_X_POSITION:
        logger.warning(f"X position {position:.1f} above maximum {MAX_X_POSITION:.1f}, clamping", category="hardware")
        position = MAX_X_POSITION

    if position != current_x_position:
        logger.info(f"Moving X motor from {current_x_position:.1f}cm to {position:.1f}cm", category="hardware")

        # Simulate movement delay (keep short for responsiveness)
        move_distance = abs(position - current_x_position)
        delay_per_cm = timing_settings.get("motor_movement_delay_per_cm", 0.01)
        max_delay = timing_settings.get("max_motor_movement_delay", 0.5)
        delay = min(move_distance * delay_per_cm, max_delay)
        time.sleep(delay)

        current_x_position = position

        # Update limit switch states based on position
        limit_switch_states['x_right'] = (current_x_position <= MIN_X_POSITION)
        limit_switch_states['x_left'] = (current_x_position >= MAX_X_POSITION)

        logger.info(f"X motor positioned at {current_x_position:.1f}cm", category="hardware")
    else:
        logger.debug(f"X motor already at {position:.1f}cm", category="hardware")

def move_y(position):
    """Move Y motor to specified position within limits"""
    global current_y_position, line_motor_piston

    logger = get_logger()
    logger.debug(f"move_y({position:.1f})", category="hardware")

    if position < MIN_Y_POSITION:
        logger.warning(f"Y position {position:.1f} below minimum {MIN_Y_POSITION:.1f}, clamping", category="hardware")
        position = MIN_Y_POSITION
    elif position > MAX_Y_POSITION:
        logger.warning(f"Y position {position:.1f} above maximum {MAX_Y_POSITION:.1f}, clamping", category="hardware")
        position = MAX_Y_POSITION

    if position != current_y_position:
        logger.info(f"Moving Y motor from {current_y_position:.1f}cm to {position:.1f}cm", category="hardware")

        # Simulate movement delay (keep short for responsiveness)
        move_distance = abs(position - current_y_position)
        delay_per_cm = timing_settings.get("motor_movement_delay_per_cm", 0.01)
        max_delay = timing_settings.get("max_motor_movement_delay", 0.5)
        delay = min(move_distance * delay_per_cm, max_delay)
        time.sleep(delay)

        current_y_position = position

        # Update limit switch states based on position
        limit_switch_states['y_bottom'] = (current_y_position <= MIN_Y_POSITION)
        limit_switch_states['y_top'] = (current_y_position >= MAX_Y_POSITION)

        logger.info(f"Y motor positioned at {current_y_position:.1f}cm", category="hardware")
    else:
        logger.debug(f"Y motor already at {position:.1f}cm", category="hardware")

def get_current_x():
    """Get current X motor position"""
    logger = get_logger()
    logger.debug(f"get_current_x() -> {current_x_position:.1f}", category="hardware")
    return current_x_position

def get_current_y():
    """Get current Y motor position"""
    logger = get_logger()
    logger.debug(f"get_current_y() -> {current_y_position:.1f}", category="hardware")
    return current_y_position

# Line tools (Y-axis operations)
def line_marker_down():
    """Lower line marker to marking position"""
    global line_marker_piston, line_marker_up_sensor, line_marker_down_sensor
    logger = get_logger()
    logger.debug("line_marker_down()", category="hardware")
    if line_marker_piston != "down":
        logger.info("Lowering line marker piston - bringing marker assembly down", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_piston = "down"
        # Update sensors: up sensor OFF, down sensor ON
        line_marker_up_sensor = False
        line_marker_down_sensor = True
        logger.success("Line marker piston DOWN - assembly lowered (up_sensor=False, down_sensor=True)", category="hardware")
    else:
        logger.debug("Line marker already down", category="hardware")

def line_marker_up():
    """Raise line marker from marking position"""
    global line_marker_piston, line_marker_up_sensor, line_marker_down_sensor
    logger = get_logger()
    logger.debug("line_marker_up()", category="hardware")
    if line_marker_piston != "up":
        logger.info("Raising line marker piston - returning to default position", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_piston = "up"
        # Update sensors: up sensor ON, down sensor OFF
        line_marker_up_sensor = True
        line_marker_down_sensor = False
        logger.success("Line marker piston UP - default position (up_sensor=True, down_sensor=False)", category="hardware")
    else:
        logger.debug("Line marker already up", category="hardware")

def line_cutter_down():
    """Lower line cutter to cutting position"""
    global line_cutter_piston, line_cutter_up_sensor, line_cutter_down_sensor
    logger = get_logger()
    logger.debug("line_cutter_down()", category="hardware")
    if line_cutter_piston != "down":
        logger.info("Lowering line cutter piston - bringing cutter assembly down", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_piston = "down"
        # Update sensors: up sensor OFF, down sensor ON
        line_cutter_up_sensor = False
        line_cutter_down_sensor = True
        logger.success("Line cutter piston DOWN - assembly lowered (up_sensor=False, down_sensor=True)", category="hardware")
    else:
        logger.debug("Line cutter already down", category="hardware")

def line_cutter_up():
    """Raise line cutter from cutting position"""
    global line_cutter_piston, line_cutter_up_sensor, line_cutter_down_sensor
    logger = get_logger()
    logger.debug("line_cutter_up()", category="hardware")
    if line_cutter_piston != "up":
        logger.info("Raising line cutter piston - returning to default position", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_piston = "up"
        # Update sensors: up sensor ON, down sensor OFF
        line_cutter_up_sensor = True
        line_cutter_down_sensor = False
        logger.success("Line cutter piston UP - default position (up_sensor=True, down_sensor=False)", category="hardware")
    else:
        logger.debug("Line cutter already up", category="hardware")

# Row tools (X-axis operations)
def row_marker_down():
    """Lower row marker to marking position (does NOT affect motor door limit switch)"""
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    logger = get_logger()
    logger.debug("row_marker_down()", category="hardware")
    if row_marker_piston != "down":
        logger.info("Lowering row marker piston - bringing marker assembly down", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "down"
        # Update sensors: up sensor OFF, down sensor ON
        row_marker_up_sensor = False
        row_marker_down_sensor = True
        logger.success("Row marker piston DOWN - assembly lowered (up_sensor=False, down_sensor=True)", category="hardware")
    else:
        logger.debug("Row marker already down", category="hardware")

def row_marker_up():
    """Raise row marker from marking position (does NOT affect motor door limit switch)"""
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    logger = get_logger()
    logger.debug("row_marker_up()", category="hardware")
    if row_marker_piston != "up":
        logger.info("Raising row marker piston - returning to default position", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "up"
        # Update sensors: up sensor ON, down sensor OFF
        row_marker_up_sensor = True
        row_marker_down_sensor = False
        logger.success("Row marker piston UP - default position (up_sensor=True, down_sensor=False)", category="hardware")
    else:
        logger.debug("Row marker already up", category="hardware")

def row_cutter_down():
    """Lower row cutter to cutting position"""
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    logger = get_logger()
    logger.debug("row_cutter_down()", category="hardware")
    if row_cutter_piston != "down":
        logger.info("Lowering row cutter piston - bringing cutter assembly down", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "down"
        # Update sensors: up sensor OFF, down sensor ON
        row_cutter_up_sensor = False
        row_cutter_down_sensor = True
        logger.success("Row cutter piston DOWN - assembly lowered (up_sensor=False, down_sensor=True)", category="hardware")
    else:
        logger.debug("Row cutter already down", category="hardware")

def row_cutter_up():
    """Raise row cutter from cutting position"""
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    logger = get_logger()
    logger.debug("row_cutter_up()", category="hardware")
    if row_cutter_piston != "up":
        logger.info("Raising row cutter piston - returning to default position", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "up"
        # Update sensors: up sensor ON, down sensor OFF
        row_cutter_up_sensor = True
        row_cutter_down_sensor = False
        logger.success("Row cutter piston UP - default position (up_sensor=True, down_sensor=False)", category="hardware")
    else:
        logger.debug("Row cutter already up", category="hardware")

# Global reference to execution engine for sensor positioning
current_execution_engine = None

# Sensor functions with manual triggering and timing control
def wait_for_x_left_sensor():
    """Wait for left lines sensor specifically. Ignores premature triggers and safety pauses."""
    logger = get_logger()
    logger.debug("wait_for_x_left_sensor()", category="hardware")
    logger.info("Waiting for left lines sensor... (Use trigger_x_left_sensor())", category="hardware")
    logger.info("In GUI mode, click 'Left Edge' button", category="hardware")

    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['x_left'].clear()

    # Track start time for timeout
    start_time = time.time()
    max_timeout = timing_settings.get("sensor_wait_timeout", 300.0)

    # Wait specifically for left sensor
    while True:
        # Check for stop event FIRST (critical for proper stop/reset)
        if current_execution_engine and hasattr(current_execution_engine, 'stop_event'):
            if current_execution_engine.stop_event.is_set():
                logger.warning("Left lines sensor wait aborted - stop requested", category="hardware")
                return None

        # Check for timeout
        if time.time() - start_time > max_timeout:
            logger.warning(f"Left lines sensor wait timeout after {max_timeout}s", category="hardware")
            return None

        if sensor_events['x_left'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                logger.warning("Left lines sensor trigger ignored - execution paused due to safety violation", category="hardware")
                sensor_events['x_left'].clear()  # Flush the trigger
                continue  # Keep waiting

            sensor_events['x_left'].clear()
            sensor_results['x_sensor'] = 'left'
            logger.info("Left lines sensor triggered: LEFT edge detected", category="hardware")

            # Move pointer to sensor location if execution engine available
            _move_to_sensor_location('x_left')

            return 'left'

def wait_for_x_right_sensor():
    """Wait for right lines sensor specifically. Ignores premature triggers and safety pauses."""
    logger = get_logger()
    logger.debug("wait_for_x_right_sensor()", category="hardware")
    logger.info("Waiting for right lines sensor... (Use trigger_x_right_sensor())", category="hardware")
    logger.info("In GUI mode, click 'Right Edge' button", category="hardware")

    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['x_right'].clear()

    # Track start time for timeout
    start_time = time.time()
    max_timeout = timing_settings.get("sensor_wait_timeout", 300.0)

    # Wait specifically for right sensor
    while True:
        # Check for stop event FIRST (critical for proper stop/reset)
        if current_execution_engine and hasattr(current_execution_engine, 'stop_event'):
            if current_execution_engine.stop_event.is_set():
                logger.warning("Right lines sensor wait aborted - stop requested", category="hardware")
                return None

        # Check for timeout
        if time.time() - start_time > max_timeout:
            logger.warning(f"Right lines sensor wait timeout after {max_timeout}s", category="hardware")
            return None

        if sensor_events['x_right'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                logger.warning("Right lines sensor trigger ignored - execution paused due to safety violation", category="hardware")
                sensor_events['x_right'].clear()  # Flush the trigger
                continue  # Keep waiting

            sensor_events['x_right'].clear()
            sensor_results['x_sensor'] = 'right'
            logger.info("Right lines sensor triggered: RIGHT edge detected", category="hardware")

            # Move pointer to sensor location if execution engine available
            _move_to_sensor_location('x_right')

            return 'right'

def wait_for_y_top_sensor():
    """Wait for top rows sensor specifically. Ignores premature triggers and safety pauses."""
    logger = get_logger()
    logger.debug("wait_for_y_top_sensor()", category="hardware")
    logger.info("Waiting for top rows sensor... (Use trigger_y_top_sensor())", category="hardware")
    logger.info("In GUI mode, click 'Top Edge' button", category="hardware")

    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['y_top'].clear()

    # Track start time for timeout
    start_time = time.time()
    max_timeout = timing_settings.get("sensor_wait_timeout", 300.0)

    # Wait specifically for top sensor
    while True:
        # Check for stop event FIRST (critical for proper stop/reset)
        if current_execution_engine and hasattr(current_execution_engine, 'stop_event'):
            if current_execution_engine.stop_event.is_set():
                logger.warning("Top rows sensor wait aborted - stop requested", category="hardware")
                return None

        # Check for timeout
        if time.time() - start_time > max_timeout:
            logger.warning(f"Top rows sensor wait timeout after {max_timeout}s", category="hardware")
            return None

        if sensor_events['y_top'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                logger.warning("Top rows sensor trigger ignored - execution paused due to safety violation", category="hardware")
                sensor_events['y_top'].clear()  # Flush the trigger
                continue  # Keep waiting

            sensor_events['y_top'].clear()
            sensor_results['y_sensor'] = 'top'
            logger.info("Top rows sensor triggered: TOP edge detected", category="hardware")

            # Move pointer to sensor location if execution engine available
            _move_to_sensor_location('y_top')

            return 'top'

def wait_for_y_bottom_sensor():
    """Wait for bottom rows sensor specifically. Ignores premature triggers and safety pauses."""
    logger = get_logger()
    logger.debug("wait_for_y_bottom_sensor()", category="hardware")
    logger.info("Waiting for bottom rows sensor... (Use trigger_y_bottom_sensor())", category="hardware")
    logger.info("In GUI mode, click 'Bottom Edge' button", category="hardware")

    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['y_bottom'].clear()

    # Track start time for timeout
    start_time = time.time()
    max_timeout = timing_settings.get("sensor_wait_timeout", 300.0)

    # Wait specifically for bottom sensor
    while True:
        # Check for stop event FIRST (critical for proper stop/reset)
        if current_execution_engine and hasattr(current_execution_engine, 'stop_event'):
            if current_execution_engine.stop_event.is_set():
                logger.warning("Bottom rows sensor wait aborted - stop requested", category="hardware")
                return None

        # Check for timeout
        if time.time() - start_time > max_timeout:
            logger.warning(f"Bottom rows sensor wait timeout after {max_timeout}s", category="hardware")
            return None

        if sensor_events['y_bottom'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                logger.warning("Bottom rows sensor trigger ignored - execution paused due to safety violation", category="hardware")
                sensor_events['y_bottom'].clear()  # Flush the trigger
                continue  # Keep waiting

            sensor_events['y_bottom'].clear()
            sensor_results['y_sensor'] = 'bottom'
            logger.info("Bottom rows sensor triggered: BOTTOM edge detected", category="hardware")

            # Move pointer to sensor location if execution engine available
            _move_to_sensor_location('y_bottom')

            return 'bottom'

# Legacy sensor functions for backward compatibility
def wait_for_x_sensor():
    """Wait for rows sensor to be triggered manually. Returns 'left' or 'right'. Ignores triggers during safety pauses."""
    logger = get_logger()
    logger.debug("wait_for_x_sensor()", category="hardware")
    logger.info("Waiting for lines sensor... (Use trigger_x_left_sensor() or trigger_x_right_sensor())", category="hardware")
    logger.info("In GUI mode, click 'Left Edge' or 'Right Edge' buttons", category="hardware")

    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['x_left'].clear()
    sensor_events['x_right'].clear()

    # Track start time for timeout
    start_time = time.time()
    max_timeout = timing_settings.get("sensor_wait_timeout", 300.0)

    # Wait for either left or right sensor
    while True:
        # Check for stop event FIRST (critical for proper stop/reset)
        if current_execution_engine and hasattr(current_execution_engine, 'stop_event'):
            if current_execution_engine.stop_event.is_set():
                logger.warning("Lines sensor wait aborted - stop requested", category="hardware")
                return None

        # Check for timeout
        if time.time() - start_time > max_timeout:
            logger.warning(f"Lines sensor wait timeout after {max_timeout}s", category="hardware")
            return None

        if sensor_events['x_left'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                logger.warning("Left lines sensor trigger ignored - execution paused due to safety violation", category="hardware")
                sensor_events['x_left'].clear()  # Flush the trigger
                continue  # Keep waiting

            sensor_events['x_left'].clear()
            sensor_results['x_sensor'] = 'left'
            logger.info("Lines sensor triggered: LEFT edge detected", category="hardware")
            return 'left'
        elif sensor_events['x_right'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                logger.warning("Right lines sensor trigger ignored - execution paused due to safety violation", category="hardware")
                sensor_events['x_right'].clear()  # Flush the trigger
                continue  # Keep waiting

            sensor_events['x_right'].clear()
            sensor_results['x_sensor'] = 'right'
            logger.info("Lines sensor triggered: RIGHT edge detected", category="hardware")
            return 'right'

def wait_for_y_sensor():
    """Wait for rows sensor to be triggered manually. Returns 'top' or 'bottom'. Ignores triggers during safety pauses."""
    logger = get_logger()
    logger.debug("wait_for_y_sensor()", category="hardware")
    logger.info("Waiting for rows sensor... (Use trigger_y_top_sensor() or trigger_y_bottom_sensor())", category="hardware")
    logger.info("In GUI mode, click 'Top Edge' or 'Bottom Edge' buttons", category="hardware")

    # Clear any existing triggers first (ignore premature triggers and safety pause triggers)
    sensor_events['y_top'].clear()
    sensor_events['y_bottom'].clear()

    # Track start time for timeout
    start_time = time.time()
    max_timeout = timing_settings.get("sensor_wait_timeout", 300.0)

    # Wait for either top or bottom sensor
    while True:
        # Check for stop event FIRST (critical for proper stop/reset)
        if current_execution_engine and hasattr(current_execution_engine, 'stop_event'):
            if current_execution_engine.stop_event.is_set():
                logger.warning("Rows sensor wait aborted - stop requested", category="hardware")
                return None

        # Check for timeout
        if time.time() - start_time > max_timeout:
            logger.warning(f"Rows sensor wait timeout after {max_timeout}s", category="hardware")
            return None

        if sensor_events['y_top'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                logger.warning("Top rows sensor trigger ignored - execution paused due to safety violation", category="hardware")
                sensor_events['y_top'].clear()  # Flush the trigger
                continue  # Keep waiting

            sensor_events['y_top'].clear()
            sensor_results['y_sensor'] = 'top'
            logger.info("Rows sensor triggered: TOP edge detected", category="hardware")
            return 'top'
        elif sensor_events['y_bottom'].wait(timeout=timing_settings.get("sensor_poll_timeout", 0.1)):
            # Check if execution is paused due to safety violation - ignore triggers during pause
            if current_execution_engine and current_execution_engine.is_paused:
                logger.warning("Bottom rows sensor trigger ignored - execution paused due to safety violation", category="hardware")
                sensor_events['y_bottom'].clear()  # Flush the trigger
                continue  # Keep waiting

            sensor_events['y_bottom'].clear()
            sensor_results['y_sensor'] = 'bottom'
            logger.info("Rows sensor triggered: BOTTOM edge detected", category="hardware")
            return 'bottom'

# Sensor buffer management for safety system
def flush_all_sensor_buffers():
    """Clear all sensor event buffers - used when resuming from safety pauses"""
    logger = get_logger()
    logger.info("FLUSH: Clearing all sensor buffers (removing triggers from safety pause)", category="hardware")
    for sensor_name, event in sensor_events.items():
        if event.is_set():
            logger.debug(f"    Flushing {sensor_name} sensor buffer", category="hardware")
        event.clear()
    logger.success("All sensor buffers cleared - ready for post-resume triggers", category="hardware")

def signal_all_sensor_events():
    """Signal all sensor events to unblock waiting threads during stop"""
    logger = get_logger()
    logger.info("SIGNAL: Waking all sensor wait threads for stop", category="hardware")
    for event in sensor_events.values():
        event.set()

# Manual sensor triggers for testing
def trigger_x_left_sensor():
    """Manually trigger left lines sensor"""
    global sensor_trigger_states, sensor_trigger_timers, x_left_edge
    logger = get_logger()
    logger.debug("trigger_x_left_sensor()", category="hardware")
    sensor_events['x_left'].set()
    sensor_trigger_states['x_left'] = True
    sensor_trigger_timers['x_left'] = time.time()
    x_left_edge = True  # Set edge sensor state
    logger.info("Manual trigger: Left lines sensor activated", category="hardware")

def trigger_x_right_sensor():
    """Manually trigger right lines sensor"""
    global sensor_trigger_states, sensor_trigger_timers, x_right_edge
    logger = get_logger()
    logger.debug("trigger_x_right_sensor()", category="hardware")
    sensor_events['x_right'].set()
    sensor_trigger_states['x_right'] = True
    sensor_trigger_timers['x_right'] = time.time()
    x_right_edge = True  # Set edge sensor state
    logger.info("Manual trigger: Right lines sensor activated", category="hardware")

def trigger_y_top_sensor():
    """Manually trigger top rows sensor"""
    global sensor_trigger_states, sensor_trigger_timers, y_top_edge
    logger = get_logger()
    logger.debug("trigger_y_top_sensor()", category="hardware")
    sensor_events['y_top'].set()
    sensor_trigger_states['y_top'] = True
    sensor_trigger_timers['y_top'] = time.time()
    y_top_edge = True  # Set edge sensor state
    logger.info("Manual trigger: Top rows sensor activated", category="hardware")

def trigger_y_bottom_sensor():
    """Manually trigger bottom rows sensor"""
    global sensor_trigger_states, sensor_trigger_timers, y_bottom_edge
    logger = get_logger()
    logger.debug("trigger_y_bottom_sensor()", category="hardware")
    sensor_events['y_bottom'].set()
    sensor_trigger_states['y_bottom'] = True
    sensor_trigger_timers['y_bottom'] = time.time()
    y_bottom_edge = True  # Set edge sensor state
    logger.info("Manual trigger: Bottom rows sensor activated", category="hardware")

# Tool positioning functions (convenience functions for test controls)
def lift_line_tools():
    """Lift line tools off surface (convenience function for manual testing)"""
    logger = get_logger()
    logger.debug("lift_line_tools()", category="hardware")
    logger.info("Lifting line tools off surface", category="hardware")
    line_marker_up()
    line_cutter_up()
    time.sleep(timing_settings.get("row_marker_stable_delay", 0.2))
    logger.success("Line tools lifted", category="hardware")

def lower_line_tools():
    """Lower line tools to surface (convenience function for manual testing)"""
    logger = get_logger()
    logger.debug("lower_line_tools()", category="hardware")
    logger.info("Lowering line tools to surface", category="hardware")
    time.sleep(timing_settings.get("row_marker_stable_delay", 0.2))
    logger.success("Line tools lowered to surface", category="hardware")

def move_line_tools_to_top():
    """Move line tools to maximum Y position"""
    logger = get_logger()
    logger.debug("move_line_tools_to_top()", category="hardware")
    logger.info("Moving line tools to top position", category="hardware")
    lift_line_tools()
    move_y(MAX_Y_POSITION)
    logger.success("Line tools moved to top", category="hardware")

# Line marker piston control functions
def line_marker_piston_up():
    """Raise line marker piston (default state)"""
    global line_marker_piston
    logger = get_logger()
    logger.debug("line_marker_piston_up()", category="hardware")
    if line_marker_piston != "up":
        logger.info("Raising line marker piston - returning to default position", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_piston = "up"
        logger.success("Line marker piston UP - default position", category="hardware")
    else:
        logger.debug("Line marker piston already UP", category="hardware")

def line_marker_piston_down():
    """Lower line marker piston (for operations)"""
    global line_marker_piston
    logger = get_logger()
    logger.debug("line_marker_piston_down()", category="hardware")
    if line_marker_piston != "down":
        logger.info("Lowering line marker piston - preparing for operations", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_marker_piston = "down"
        logger.success("Line marker piston DOWN - ready for operations", category="hardware")
    else:
        logger.debug("Line marker piston already DOWN", category="hardware")

# Line cutter piston control functions
def line_cutter_piston_up():
    """Raise line cutter piston (default state)"""
    global line_cutter_piston
    logger = get_logger()
    logger.debug("line_cutter_piston_up()", category="hardware")
    if line_cutter_piston != "up":
        logger.info("Raising line cutter piston - returning to default position", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_piston = "up"
        logger.success("Line cutter piston UP - default position", category="hardware")
    else:
        logger.debug("Line cutter piston already UP", category="hardware")

def line_cutter_piston_down():
    """Lower line cutter piston (for operations)"""
    global line_cutter_piston
    logger = get_logger()
    logger.debug("line_cutter_piston_down()", category="hardware")
    if line_cutter_piston != "down":
        logger.info("Lowering line cutter piston - preparing for operations", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_cutter_piston = "down"
        logger.success("Line cutter piston DOWN - ready for operations", category="hardware")
    else:
        logger.debug("Line cutter piston already DOWN", category="hardware")

# Line motor piston control functions
# Line motor dual pistons (left + right) control functions
def line_motor_piston_up():
    """Lift line motor piston (raises entire Y motor assembly - both sides move together)"""
    global line_motor_piston, line_motor_left_up_sensor, line_motor_left_down_sensor
    global line_motor_right_up_sensor, line_motor_right_down_sensor
    logger = get_logger()
    logger.debug("line_motor_piston_up()", category="hardware")
    if line_motor_piston != "up":
        logger.info("Raising line motor piston - lifting both sides of Y motor assembly", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_motor_piston = "up"
        # Update both left and right sensors: up sensors ON, down sensors OFF
        line_motor_left_up_sensor = True
        line_motor_left_down_sensor = False
        line_motor_right_up_sensor = True
        line_motor_right_down_sensor = False
        logger.success("Line motor piston UP (left & right up_sensors=True, down_sensors=False)", category="hardware")
    else:
        logger.debug("Line motor piston already UP", category="hardware")

def line_motor_piston_down():
    """Lower line motor piston (lowers entire Y motor assembly - both sides move together)"""
    global line_motor_piston, line_motor_left_up_sensor, line_motor_left_down_sensor
    global line_motor_right_up_sensor, line_motor_right_down_sensor
    logger = get_logger()
    logger.debug("line_motor_piston_down()", category="hardware")
    if line_motor_piston != "down":
        logger.info("Lowering line motor piston - lowering both sides of Y motor assembly", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        line_motor_piston = "down"
        # Update both left and right sensors: up sensors OFF, down sensors ON
        line_motor_left_up_sensor = False
        line_motor_left_down_sensor = True
        line_motor_right_up_sensor = False
        line_motor_right_down_sensor = True
        logger.success("Line motor piston DOWN (left & right up_sensors=False, down_sensors=True)", category="hardware")
    else:
        logger.debug("Line motor piston already DOWN", category="hardware")

# Row marker piston control functions
def row_marker_piston_up():
    """Raise row marker piston (default state)"""
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    logger = get_logger()
    logger.debug("row_marker_piston_up()", category="hardware")
    if row_marker_piston != "up":
        logger.info("Raising row marker piston - returning to default position", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "up"
        row_marker_up_sensor = True
        row_marker_down_sensor = False
        logger.success("Row marker piston UP - default position (up_sensor=True, down_sensor=False)", category="hardware")
    else:
        logger.debug("Row marker piston already UP", category="hardware")

def row_marker_piston_down():
    """Lower row marker piston (for operations)"""
    global row_marker_piston, row_marker_up_sensor, row_marker_down_sensor
    logger = get_logger()
    logger.debug("row_marker_piston_down()", category="hardware")
    if row_marker_piston != "down":
        logger.info("Lowering row marker piston - preparing for operations", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_marker_piston = "down"
        row_marker_up_sensor = False
        row_marker_down_sensor = True
        logger.success("Row marker piston DOWN - ready for operations (up_sensor=False, down_sensor=True)", category="hardware")
    else:
        logger.debug("Row marker piston already DOWN", category="hardware")

# Row cutter piston control functions
def row_cutter_piston_up():
    """Raise row cutter piston (default state)"""
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    logger = get_logger()
    logger.debug("row_cutter_piston_up()", category="hardware")
    if row_cutter_piston != "up":
        logger.info("Raising row cutter piston - returning to default position", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "up"
        row_cutter_up_sensor = True
        row_cutter_down_sensor = False
        logger.success("Row cutter piston UP - default position (up_sensor=True, down_sensor=False)", category="hardware")
    else:
        logger.debug("Row cutter piston already UP", category="hardware")

def row_cutter_piston_down():
    """Lower row cutter piston (for operations)"""
    global row_cutter_piston, row_cutter_up_sensor, row_cutter_down_sensor
    logger = get_logger()
    logger.debug("row_cutter_piston_down()", category="hardware")
    if row_cutter_piston != "down":
        logger.info("Lowering row cutter piston - preparing for operations", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        row_cutter_piston = "down"
        row_cutter_up_sensor = False
        row_cutter_down_sensor = True
        logger.success("Row cutter piston DOWN - ready for operations (up_sensor=False, down_sensor=True)", category="hardware")
    else:
        logger.debug("Row cutter piston already DOWN", category="hardware")

# Air Pressure Valve functions
def air_pressure_valve_down():
    """Open air pressure valve (air flows to pistons)"""
    global air_pressure_valve
    logger = get_logger()
    logger.debug("air_pressure_valve_down()", category="hardware")
    if air_pressure_valve != "down":
        logger.info("Opening air pressure valve - air flowing to pistons", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        air_pressure_valve = "down"
        logger.success("Air pressure valve OPEN (down) - air flowing", category="hardware")
    else:
        logger.debug("Air pressure valve already OPEN", category="hardware")

def air_pressure_valve_up():
    """Close air pressure valve (no air to pistons)"""
    global air_pressure_valve
    logger = get_logger()
    logger.debug("air_pressure_valve_up()", category="hardware")
    if air_pressure_valve != "up":
        logger.info("Closing air pressure valve - stopping air flow", category="hardware")
        time.sleep(timing_settings.get("tool_action_delay", 0.1))
        air_pressure_valve = "up"
        logger.success("Air pressure valve CLOSED (up) - no air flow", category="hardware")
    else:
        logger.debug("Air pressure valve already CLOSED", category="hardware")

def get_air_pressure_valve_state():
    """Get current air pressure valve state"""
    return air_pressure_valve

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
        # Line motor piston (shared control, separate sensors)
        'line_motor_piston': line_motor_piston,
        'line_motor_left_up_sensor': line_motor_left_up_sensor,
        'line_motor_left_down_sensor': line_motor_left_down_sensor,
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
        'row_marker_limit_switch': "down" if limit_switch_states.get('rows', False) else "up",
        # Air pressure valve
        'air_pressure_valve': air_pressure_valve
    }
    return status

def print_hardware_status():
    """Print current hardware status"""
    logger = get_logger()
    logger.info("=== Hardware Status ===", category="hardware")
    logger.info(f"X Position: {current_x_position:.1f}cm", category="hardware")
    logger.info(f"Y Position: {current_y_position:.1f}cm", category="hardware")
    logger.info(f"Line Marker:", category="hardware")
    logger.info(f"  Piston: {line_marker_piston}", category="hardware")
    logger.info(f"  Up Sensor: {line_marker_up_sensor}", category="hardware")
    logger.info(f"  Down Sensor: {line_marker_down_sensor}", category="hardware")
    logger.info(f"Line Cutter:", category="hardware")
    logger.info(f"  Piston: {line_cutter_piston}", category="hardware")
    logger.info(f"  Up Sensor: {line_cutter_up_sensor}", category="hardware")
    logger.info(f"  Down Sensor: {line_cutter_down_sensor}", category="hardware")
    logger.info(f"Line Motor Piston (Shared Control):", category="hardware")
    logger.info(f"  Piston: {line_motor_piston}", category="hardware")
    logger.info(f"  Left Up Sensor: {line_motor_left_up_sensor}", category="hardware")
    logger.info(f"  Left Down Sensor: {line_motor_left_down_sensor}", category="hardware")
    logger.info(f"  Right Up Sensor: {line_motor_right_up_sensor}", category="hardware")
    logger.info(f"  Right Down Sensor: {line_motor_right_down_sensor}", category="hardware")
    logger.info(f"Row Marker:", category="hardware")
    logger.info(f"  Piston: {row_marker_piston}", category="hardware")
    logger.info(f"  Up Sensor: {row_marker_up_sensor}", category="hardware")
    logger.info(f"  Down Sensor: {row_marker_down_sensor}", category="hardware")
    logger.info(f"Row Cutter:", category="hardware")
    logger.info(f"  Piston: {row_cutter_piston}", category="hardware")
    logger.info(f"  Up Sensor: {row_cutter_up_sensor}", category="hardware")
    logger.info(f"  Down Sensor: {row_cutter_down_sensor}", category="hardware")
    logger.info(f"Row Marker Limit Switch: {'down' if limit_switch_states.get('rows', False) else 'up'}", category="hardware")
    logger.info(f"Air Pressure Valve: {air_pressure_valve}", category="hardware")
    logger.info("=====================", category="hardware")

if __name__ == "__main__":
    logger = get_logger()
    logger.info("Mock Hardware System Test", category="hardware")
    logger.info("========================", category="hardware")

    # Test movement
    logger.info("Testing movement:", category="hardware")
    move_x(25.0)
    move_y(30.0)

    # Test tools
    logger.info("Testing line tools:", category="hardware")
    line_marker_down()
    line_marker_up()

    logger.info("Testing row tools:", category="hardware")
    row_marker_down()
    row_marker_up()

    # Show status
    print_hardware_status()

    logger.success("Mock hardware test complete!", category="hardware")

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
    logger = get_logger()

    if not current_execution_engine:
        logger.debug(f"No execution engine reference - sensor {sensor_type} triggered but no GUI update", category="hardware")
        return

    # Check if execution engine is currently running and in a wait_sensor step
    if not current_execution_engine.is_running:
        logger.debug(f"Execution engine not running - sensor {sensor_type} triggered but ignoring (not part of current execution plan)", category="hardware")
        return

    # Check if current step is a wait_sensor step
    if (current_execution_engine.current_step_index < len(current_execution_engine.steps)):
        current_step = current_execution_engine.steps[current_execution_engine.current_step_index]
        if current_step.get('operation') != 'wait_sensor':
            logger.debug(f"Current step is not wait_sensor - sensor {sensor_type} triggered but ignoring (not part of current execution plan)", category="hardware")
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
            logger.debug(f"Sensor {sensor_type} doesn't match expected sensor {expected_sensor} - ignoring trigger", category="hardware")
            return

    if not hasattr(current_execution_engine, 'canvas_manager') or not current_execution_engine.canvas_manager:
        logger.debug(f"No canvas manager available - sensor {sensor_type} triggered but no GUI update", category="hardware")
        return

    canvas_manager = current_execution_engine.canvas_manager

    if not canvas_manager.main_app.current_program:
        logger.debug(f"No current program loaded - sensor {sensor_type} triggered but no program context", category="hardware")
        return

    # IMPORTANT: Only update visual display, do NOT move motors!
    # The canvas_sensors.trigger_sensor_visualization() will handle visual updates
    # Motors should only move during actual execution steps (move_x, move_y commands)
    logger.info(f"Sensor {sensor_type} triggered - updating canvas display only (motors remain at current position)", category="hardware")

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
    """Get current line motor piston state (shared control)"""
    return line_motor_piston

def get_line_motor_left_up_sensor():
    """Get line motor left up sensor state"""
    return line_motor_left_up_sensor

def get_line_motor_left_down_sensor():
    """Get line motor left down sensor state"""
    return line_motor_left_down_sensor

def get_line_motor_right_up_sensor():
    """Get line motor right up sensor state"""
    return line_motor_right_up_sensor

def get_line_motor_right_down_sensor():
    """Get line motor right down sensor state"""
    return line_motor_right_down_sensor

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
    """Get current row marker limit switch state - reads from limit_switch_states['rows_door']"""
    # Map boolean limit switch state to "up"/"down" string
    # True (checked/ON) = DOWN, False (unchecked/OFF) = UP
    return "down" if limit_switch_states.get('rows_door', False) else "up"

def set_row_marker_limit_switch(state):
    """Manually set row marker limit switch state (operator control)"""
    global limit_switch_states
    logger = get_logger()
    if state in ["up", "down"]:
        # True (ON) = DOWN, False (OFF) = UP
        limit_switch_states['rows_door'] = (state == "down")
        logger.info(f"Row marker limit switch manually set to: {state.upper()}", category="hardware")

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
    logger = get_logger()
    # Toggle the boolean state
    limit_switch_states['rows_door'] = not limit_switch_states['rows_door']
    new_state = "down" if limit_switch_states['rows_door'] else "up"
    logger.info(f"Row marker limit switch toggled to: {new_state.upper()}", category="hardware")
    return new_state

# Limit switch control functions
def toggle_limit_switch(switch_name):
    """Toggle a limit switch state (motor door sensor - independent from marker piston)"""
    global limit_switch_states
    logger = get_logger()
    if switch_name in limit_switch_states:
        limit_switch_states[switch_name] = not limit_switch_states[switch_name]
        state = "ON" if limit_switch_states[switch_name] else "OFF"
        logger.info(f"Limit switch {switch_name} toggled to: {state}", category="hardware")
        # Note: This is motor door sensor, NOT marker piston position
        return limit_switch_states[switch_name]
    return False

def get_limit_switch_state(switch_name):
    """Get a limit switch state"""
    return limit_switch_states.get(switch_name, False)

def set_limit_switch_state(switch_name, state):
    """Set a limit switch state"""
    global limit_switch_states
    logger = get_logger()
    if switch_name in limit_switch_states:
        limit_switch_states[switch_name] = state
        logger.info(f"Limit switch {switch_name} set to: {'ON' if state else 'OFF'}", category="hardware")


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
        self.logger = get_logger()
        self.logger.success("Mock Hardware initialized", category="hardware")

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

    def perform_complete_homing_sequence(self, progress_callback=None) -> tuple[bool, str]:
        """
        Perform complete homing sequence (mock implementation)

        Mock version simulates the full sequence without real hardware.

        Args:
            progress_callback: Optional callback function(step_number, step_name, status, message=None)

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        self.logger.info("="*60, category="hardware")
        self.logger.info("MOCK: Starting complete homing sequence", category="hardware")
        self.logger.info("="*60, category="hardware")

        # Simulate configuration
        if progress_callback:
            progress_callback(1, "Apply GRBL configuration", "running")
        self.logger.info("Step 1: (Simulated) Applying GRBL configuration", category="hardware")
        time.sleep(0.2)
        if progress_callback:
            progress_callback(1, "Apply GRBL configuration", "done")

        # Simulate door check
        if progress_callback:
            progress_callback(2, "Check door is open", "running")
        self.logger.info("Step 2: (Simulated) Checking door sensor - OK", category="hardware")
        time.sleep(0.1)
        if progress_callback:
            progress_callback(2, "Check door is open", "done")

        # Simulate lifting pistons
        if progress_callback:
            progress_callback(3, "Lift line motor pistons", "running")
        self.logger.info("Step 3: (Simulated) Lifting line motor pistons", category="hardware")
        line_motor_piston_up()
        time.sleep(0.5)
        if progress_callback:
            progress_callback(3, "Lift line motor pistons", "done")

        # Simulate homing
        if progress_callback:
            progress_callback(4, "Run GRBL homing ($H)", "running")
        self.logger.info("Step 4: (Simulated) Running GRBL homing", category="hardware")
        move_x(0.0)
        move_y(0.0)
        time.sleep(1.0)
        if progress_callback:
            progress_callback(4, "Run GRBL homing ($H)", "done")

        # Simulate coordinate reset
        if progress_callback:
            progress_callback(5, "Reset work coordinates to (0,0)", "running")
        self.logger.info("Step 5: (Simulated) Resetting work coordinates to (0, 0)", category="hardware")
        time.sleep(0.2)
        if progress_callback:
            progress_callback(5, "Reset work coordinates to (0,0)", "done")

        # Simulate lowering pistons
        if progress_callback:
            progress_callback(6, "Lower line motor pistons", "running")
        self.logger.info("Step 6: (Simulated) Lowering line motor pistons", category="hardware")
        line_motor_piston_down()
        time.sleep(0.5)
        if progress_callback:
            progress_callback(6, "Lower line motor pistons", "done")

        self.logger.success("MOCK: Complete homing sequence finished", category="hardware")
        self.logger.info("="*60, category="hardware")
        return True, ""

    def apply_grbl_configuration(self) -> bool:
        """Apply GRBL configuration (mock implementation)"""
        self.logger.info("MOCK: Applying GRBL configuration (simulation)", category="hardware")
        return True

    def get_grbl_status(self):
        """Get GRBL status (mock implementation)"""
        return {
            'state': 'Idle',
            'x': get_current_x(),
            'y': get_current_y()
        }

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

    def air_pressure_valve_down(self) -> bool:
        return air_pressure_valve_down()

    def air_pressure_valve_up(self) -> bool:
        return air_pressure_valve_up()

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

    def get_line_motor_left_up_sensor(self) -> bool:
        return get_line_motor_left_up_sensor()

    def get_line_motor_left_down_sensor(self) -> bool:
        return get_line_motor_left_down_sensor()

    def get_line_motor_right_up_sensor(self) -> bool:
        return get_line_motor_right_up_sensor()

    def get_line_motor_right_down_sensor(self) -> bool:
        return get_line_motor_right_down_sensor()

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

    def get_air_pressure_valve_state(self) -> str:
        return get_air_pressure_valve_state()

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

    def get_door_sensor(self) -> bool:
        """Alias for get_door_switch for consistency with other sensors"""
        return get_limit_switch_state("rows_door")

    def get_rows_door_switch(self) -> bool:
        return get_limit_switch_state("rows_door")

    def get_limit_switch_state(self, switch_name: str) -> bool:
        return get_limit_switch_state(switch_name)

    def get_top_limit_switch(self) -> bool:
        return get_limit_switch_state('y_top')

    def get_bottom_limit_switch(self) -> bool:
        return get_limit_switch_state('y_bottom')

    def get_left_limit_switch(self) -> bool:
        return get_limit_switch_state('x_left')

    def get_right_limit_switch(self) -> bool:
        return get_limit_switch_state('x_right')

    def get_row_motor_limit_switch(self) -> str:
        return get_row_motor_limit_switch()

    def get_rows_limit_switch(self) -> bool:
        """Get rows limit switch state"""
        return get_limit_switch_state('rows')

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
        self.logger.error("EMERGENCY STOP activated", category="hardware")
        return True

    def resume_operation(self) -> bool:
        self.logger.info("Resume operation", category="hardware")
        return True

    # ========== EXECUTION ENGINE INTEGRATION ==========
    def set_execution_engine_reference(self, engine):
        """Set execution engine reference for sensor waiting"""
        set_execution_engine_reference(engine)

    def flush_all_sensor_buffers(self):
        """Flush all sensor buffers"""
        flush_all_sensor_buffers()

    def signal_all_sensor_events(self):
        """Signal all sensor events to unblock waiting threads during stop"""
        signal_all_sensor_events()

    def shutdown(self):
        """Shutdown mock hardware"""
        self.logger.info("Shutdown", category="hardware")
        self.is_initialized = False
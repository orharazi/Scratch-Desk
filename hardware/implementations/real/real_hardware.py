#!/usr/bin/env python3

"""
Real Hardware Implementation
=============================

Combines Raspberry Pi GPIO and Arduino GRBL into single interface.
This class contains ONLY real hardware implementation.
"""

import json
from typing import Optional, Dict
from hardware.implementations.real.raspberry_pi.raspberry_pi_gpio import RaspberryPiGPIO
from hardware.implementations.real.arduino_grbl.arduino_grbl import ArduinoGRBL
from core.logger import get_logger

# Module-level logger for main section
module_logger = get_logger()


class RealHardware:
    """
    Real Hardware Implementation
    Manages both Raspberry Pi GPIO and Arduino GRBL
    """

    def __init__(self, config_path: str = "config/settings.json"):
        """
        Initialize hardware interface

        Args:
            config_path: Path to config/settings.json configuration file
        """
        self.logger = get_logger()
        self.config_path = config_path
        self.config = self._load_config(config_path)

        # Initialize components
        self.gpio: Optional[RaspberryPiGPIO] = None
        self.grbl: Optional[ArduinoGRBL] = None
        self.is_initialized = False
        self.initialization_error = None

        self.logger.info("="*60, category="hardware")
        self.logger.info("Real Hardware Interface Configuration", category="hardware")
        self.logger.info("="*60, category="hardware")
        self.logger.info("Mode: REAL HARDWARE", category="hardware")
        self.logger.info("="*60, category="hardware")

        # Attempt to initialize hardware
        if not self.initialize():
            self.initialization_error = "Failed to initialize hardware. Check connections and try again."

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from config/settings.json"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Error loading config: {e}", category="hardware")
            return {}

    def initialize(self) -> bool:
        """
        Initialize all hardware components

        Returns:
            True if initialization successful, False otherwise
        """
        if self.is_initialized:
            self.logger.debug("Hardware already initialized", category="hardware")
            return True

        errors = []

        # Initialize Raspberry Pi GPIO
        self.logger.info("Initializing Raspberry Pi GPIO...", category="hardware")
        try:
            self.gpio = RaspberryPiGPIO(self.config_path)
            if not self.gpio.initialize():
                error_msg = "GPIO initialization failed"
                self.logger.error(error_msg, category="hardware")
                errors.append(error_msg)
            else:
                self.logger.success("GPIO initialized successfully", category="hardware")
        except Exception as e:
            error_msg = f"GPIO error: {str(e)}"
            self.logger.error(error_msg, category="hardware")
            errors.append(error_msg)

        # Initialize Arduino GRBL
        self.logger.info("Initializing Arduino GRBL...", category="hardware")
        try:
            self.grbl = ArduinoGRBL(self.config_path)
            if not self.grbl.connect():
                error_msg = "GRBL connection failed - check Arduino port and connection"
                self.logger.error(error_msg, category="hardware")
                errors.append(error_msg)
            else:
                self.logger.success("GRBL connected successfully", category="hardware")
        except Exception as e:
            error_msg = f"GRBL error: {str(e)}"
            self.logger.error(error_msg, category="hardware")
            errors.append(error_msg)

        if not errors:
            self.is_initialized = True
            self.initialization_error = None
            self.logger.success("All hardware initialized successfully", category="hardware")
            return True
        else:
            self.initialization_error = "; ".join(errors)
            self.logger.error(f"Hardware initialization failed: {self.initialization_error}", category="hardware")
            return False

    # ========== MOTOR CONTROL (via GRBL) ==========

    def move_x(self, position: float) -> bool:
        """
        Move X motor to absolute position

        Args:
            position: Target position in cm

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized or not self.grbl:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        # Move only X axis, keep Y at current position
        return self.grbl.move_to(position, self.grbl.current_y)

    def move_y(self, position: float) -> bool:
        """
        Move Y motor to absolute position

        Args:
            position: Target position in cm

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized or not self.grbl:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        # Move only Y axis, keep X at current position
        return self.grbl.move_to(self.grbl.current_x, position)

    def move_to(self, x: float, y: float) -> bool:
        """
        Move to absolute position

        Args:
            x: Target X position in cm
            y: Target Y position in cm

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized or not self.grbl:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.grbl.move_to(x, y)

    def home_motors(self) -> bool:
        """
        Home all motors

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized or not self.grbl:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.grbl.home()

    # ========== PISTON CONTROL (via GPIO) ==========

    def line_marker_piston_down(self) -> bool:
        """Lower line marker piston"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.piston_down("line_marker_piston")

    def line_marker_piston_up(self) -> bool:
        """Raise line marker piston"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.piston_up("line_marker_piston")

    def line_cutter_piston_down(self) -> bool:
        """Lower line cutter piston"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.piston_down("line_cutter_piston")

    def line_cutter_piston_up(self) -> bool:
        """Raise line cutter piston"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.piston_up("line_cutter_piston")

    def line_motor_piston_down(self) -> bool:
        """Lower line motor piston (both sides move together - single GPIO control)"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.line_motor_piston_down()

    def line_motor_piston_up(self) -> bool:
        """Raise line motor piston (both sides move together - single GPIO control)"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.line_motor_piston_up()

    def row_marker_piston_down(self) -> bool:
        """Lower row marker piston"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.piston_down("row_marker_piston")

    def row_marker_piston_up(self) -> bool:
        """Raise row marker piston"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.piston_up("row_marker_piston")

    def row_cutter_piston_down(self) -> bool:
        """Lower row cutter piston"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.piston_down("row_cutter_piston")

    def row_cutter_piston_up(self) -> bool:
        """Raise row cutter piston"""
        if not self.is_initialized or not self.gpio:
            self.logger.error("Hardware not initialized", category="hardware")
            return False

        return self.gpio.piston_up("row_cutter_piston")

    # ========== SENSOR READING (via GPIO) - DUAL SENSORS PER TOOL ==========

    # Line Marker Sensors
    def get_line_marker_up_sensor(self) -> bool:
        """Read line marker UP sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_line_marker_up_sensor()
        return state if state is not None else False

    def get_line_marker_down_sensor(self) -> bool:
        """Read line marker DOWN sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_line_marker_down_sensor()
        return state if state is not None else False

    # Line Cutter Sensors
    def get_line_cutter_up_sensor(self) -> bool:
        """Read line cutter UP sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_line_cutter_up_sensor()
        return state if state is not None else False

    def get_line_cutter_down_sensor(self) -> bool:
        """Read line cutter DOWN sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_line_cutter_down_sensor()
        return state if state is not None else False

    # Line Motor Left Piston Sensors
    def get_line_motor_left_up_sensor(self) -> bool:
        """Read line motor LEFT piston UP sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_line_motor_left_up_sensor()
        return state if state is not None else False

    def get_line_motor_left_down_sensor(self) -> bool:
        """Read line motor LEFT piston DOWN sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_line_motor_left_down_sensor()
        return state if state is not None else False

    # Line Motor Right Piston Sensors
    def get_line_motor_right_up_sensor(self) -> bool:
        """Read line motor RIGHT piston UP sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_line_motor_right_up_sensor()
        return state if state is not None else False

    def get_line_motor_right_down_sensor(self) -> bool:
        """Read line motor RIGHT piston DOWN sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_line_motor_right_down_sensor()
        return state if state is not None else False

    # Row Marker Sensors
    def get_row_marker_up_sensor(self) -> bool:
        """Read row marker UP sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_row_marker_up_sensor()
        return state if state is not None else False

    def get_row_marker_down_sensor(self) -> bool:
        """Read row marker DOWN sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_row_marker_down_sensor()
        return state if state is not None else False

    # Row Cutter Sensors
    def get_row_cutter_up_sensor(self) -> bool:
        """Read row cutter UP sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_row_cutter_up_sensor()
        return state if state is not None else False

    def get_row_cutter_down_sensor(self) -> bool:
        """Read row cutter DOWN sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_row_cutter_down_sensor()
        return state if state is not None else False

    # ========== EDGE SENSORS ==========

    def get_x_left_edge_sensor(self) -> bool:
        """Read X-axis LEFT edge sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_x_left_edge_sensor()
        return state if state is not None else False

    def get_x_right_edge_sensor(self) -> bool:
        """Read X-axis RIGHT edge sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_x_right_edge_sensor()
        return state if state is not None else False

    def get_y_top_edge_sensor(self) -> bool:
        """Read Y-axis TOP edge sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_y_top_edge_sensor()
        return state if state is not None else False

    def get_y_bottom_edge_sensor(self) -> bool:
        """Read Y-axis BOTTOM edge sensor state"""
        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.get_y_bottom_edge_sensor()
        return state if state is not None else False

    def read_edge_sensors(self) -> Dict[str, bool]:
        """
        Read all edge detection sensors (convenience method)

        Returns:
            Dictionary with sensor states: {'x_left': bool, 'x_right': bool, 'y_top': bool, 'y_bottom': bool}
        """
        return {
            'x_left': self.get_x_left_edge_sensor(),
            'x_right': self.get_x_right_edge_sensor(),
            'y_top': self.get_y_top_edge_sensor(),
            'y_bottom': self.get_y_bottom_edge_sensor()
        }

    # ========== LIMIT SWITCHES ==========

    def get_door_switch(self) -> bool:
        """
        Read door limit switch state (from Arduino GRBL)

        Returns:
            True if door is closed, False if open
        """
        if not self.is_initialized or not self.grbl:
            return False

        state = self.grbl.get_door_switch_state()
        return state if state is not None else False

    def get_rows_door_switch(self) -> bool:
        """
        Read rows door limit switch state (legacy method - now routes to Arduino)

        DEPRECATED: Use get_door_switch() instead
        """
        return self.get_door_switch()

    # ========== EMERGENCY CONTROLS ==========

    def emergency_stop(self) -> bool:
        """Emergency stop all motors"""
        if not self.is_initialized or not self.grbl:
            return False

        return self.grbl.stop()

    def resume_operation(self) -> bool:
        """Resume operation after emergency stop"""
        if not self.is_initialized or not self.grbl:
            return False

        return self.grbl.resume()

    # ========== POSITION GETTERS ==========

    def get_current_x(self) -> float:
        """Get current X motor position in cm"""
        if not self.is_initialized or not self.grbl:
            return 0.0

        return self.grbl.current_x

    def get_current_y(self) -> float:
        """Get current Y motor position in cm"""
        if not self.is_initialized or not self.grbl:
            return 0.0

        return self.grbl.current_y

    # ========== TOOL ACTION METHODS ==========

    def line_marker_down(self) -> bool:
        """Lower line marker tool"""
        return self.line_marker_piston_down()

    def line_marker_up(self) -> bool:
        """Raise line marker tool"""
        return self.line_marker_piston_up()

    def line_cutter_down(self) -> bool:
        """Lower line cutter tool"""
        return self.line_cutter_piston_down()

    def line_cutter_up(self) -> bool:
        """Raise line cutter tool"""
        return self.line_cutter_piston_up()

    def row_marker_down(self) -> bool:
        """Lower row marker tool"""
        return self.row_marker_piston_down()

    def row_marker_up(self) -> bool:
        """Raise row marker tool"""
        return self.row_marker_piston_up()

    def row_cutter_down(self) -> bool:
        """Lower row cutter tool"""
        return self.row_cutter_piston_down()

    def row_cutter_up(self) -> bool:
        """Raise row cutter tool"""
        return self.row_cutter_piston_up()

    def lift_line_tools(self) -> bool:
        """Lift all line tools (marker, cutter, motor pistons)"""
        marker_ok = self.line_marker_up()
        cutter_ok = self.line_cutter_up()
        motor_ok = self.line_motor_piston_up()
        return marker_ok and cutter_ok and motor_ok

    def lower_line_tools(self) -> bool:
        """Lower all line tools (marker, cutter, motor pistons)"""
        marker_ok = self.line_marker_down()
        cutter_ok = self.line_cutter_down()
        motor_ok = self.line_motor_piston_down()
        return marker_ok and cutter_ok and motor_ok

    def move_line_tools_to_top(self) -> bool:
        """Move line motor to top position and lift all tools"""
        # First lift tools
        tools_lifted = self.lift_line_tools()
        # Then move to max Y position (top)
        max_y = self.config.get("hardware_limits", {}).get("max_y_position", 100.0)
        moved = self.move_y(max_y)
        return tools_lifted and moved

    # ========== STATE GETTERS ==========

    def get_line_marker_state(self) -> str:
        """Get line marker tool state"""
        up = self.get_line_marker_up_sensor()
        down = self.get_line_marker_down_sensor()
        if up and not down:
            return "up"
        elif down and not up:
            return "down"
        else:
            return "unknown"

    def get_line_cutter_state(self) -> str:
        """Get line cutter tool state"""
        up = self.get_line_cutter_up_sensor()
        down = self.get_line_cutter_down_sensor()
        if up and not down:
            return "up"
        elif down and not up:
            return "down"
        else:
            return "unknown"

    def get_row_marker_state(self) -> str:
        """Get row marker tool state"""
        up = self.get_row_marker_up_sensor()
        down = self.get_row_marker_down_sensor()
        if up and not down:
            return "up"
        elif down and not up:
            return "down"
        else:
            return "unknown"

    def get_row_cutter_state(self) -> str:
        """Get row cutter tool state"""
        up = self.get_row_cutter_up_sensor()
        down = self.get_row_cutter_down_sensor()
        if up and not down:
            return "up"
        elif down and not up:
            return "down"
        else:
            return "unknown"

    def get_line_marker_piston_state(self) -> str:
        """Get line marker piston state"""
        return self.get_line_marker_state()

    def get_line_cutter_piston_state(self) -> str:
        """Get line cutter piston state"""
        return self.get_line_cutter_state()

    def get_line_motor_piston_state(self) -> str:
        """Get line motor piston state (both sides move together, check both sensors)"""
        left_up = self.get_line_motor_left_up_sensor()
        left_down = self.get_line_motor_left_down_sensor()
        right_up = self.get_line_motor_right_up_sensor()
        right_down = self.get_line_motor_right_down_sensor()

        # Both sides should be in same state (single piston control)
        if left_up and right_up:
            return "up"
        elif left_down and right_down:
            return "down"
        else:
            return "unknown"  # Mismatch - possible sensor error

    def get_row_marker_piston_state(self) -> str:
        """Get row marker piston state"""
        return self.get_row_marker_state()

    def get_row_cutter_piston_state(self) -> str:
        """Get row cutter piston state"""
        return self.get_row_cutter_state()

    # ========== EDGE SENSOR GETTERS (compatibility wrappers) ==========

    def get_x_left_edge(self) -> bool:
        """Get X left edge sensor state"""
        return self.get_x_left_edge_sensor()

    def get_x_right_edge(self) -> bool:
        """Get X right edge sensor state"""
        return self.get_x_right_edge_sensor()

    def get_y_top_edge(self) -> bool:
        """Get Y top edge sensor state"""
        return self.get_y_top_edge_sensor()

    def get_y_bottom_edge(self) -> bool:
        """Get Y bottom edge sensor state"""
        return self.get_y_bottom_edge_sensor()

    # ========== LIMIT SWITCH METHODS ==========

    def get_limit_switch_state(self, switch_name: str) -> bool:
        """Get limit switch state by name"""
        if switch_name == "rows_door" or switch_name == "door":
            return self.get_door_switch()
        return False

    def get_row_motor_limit_switch(self) -> bool:
        """Get row motor limit switch (door) state"""
        return self.get_door_switch()

    def set_limit_switch_state(self, switch_name: str, state: bool):
        """Set limit switch state (not supported in real hardware mode)"""
        pass

    def set_row_marker_limit_switch(self, state: bool):
        """Set row marker limit switch state (not supported in real hardware mode)"""
        pass

    def toggle_limit_switch(self, switch_name: str):
        """Toggle limit switch state (not supported in real hardware mode)"""
        pass

    def toggle_row_marker_limit_switch(self):
        """Toggle row marker limit switch (not supported in real hardware mode)"""
        pass

    # ========== SENSOR TRIGGER METHODS (not supported in real hardware mode) ==========

    def trigger_x_left_sensor(self):
        """Trigger X left sensor (not supported in real hardware mode)"""
        pass

    def trigger_x_right_sensor(self):
        """Trigger X right sensor (not supported in real hardware mode)"""
        pass

    def trigger_y_top_sensor(self):
        """Trigger Y top sensor (not supported in real hardware mode)"""
        pass

    def trigger_y_bottom_sensor(self):
        """Trigger Y bottom sensor (not supported in real hardware mode)"""
        pass

    def get_sensor_trigger_states(self):
        """Get sensor trigger states (not supported in real hardware mode)"""
        return {}

    # ========== WAIT FOR SENSOR METHODS ==========

    def wait_for_x_sensor(self):
        """Wait for X sensor trigger (not supported in real hardware mode)"""
        pass

    def wait_for_y_sensor(self):
        """Wait for Y sensor trigger (not supported in real hardware mode)"""
        pass

    def wait_for_x_left_sensor(self):
        """Wait for X left sensor trigger (not supported in real hardware mode)"""
        pass

    def wait_for_x_right_sensor(self):
        """Wait for X right sensor trigger (not supported in real hardware mode)"""
        pass

    def wait_for_y_top_sensor(self):
        """Wait for Y top sensor trigger (not supported in real hardware mode)"""
        pass

    def wait_for_y_bottom_sensor(self):
        """Wait for Y bottom sensor trigger (not supported in real hardware mode)"""
        pass

    # ========== HARDWARE STATUS ==========

    def get_hardware_status(self):
        """Get complete hardware status dictionary with all sensors"""
        if not self.is_initialized or not self.gpio:
            return {
                'error': self.initialization_error or 'Hardware not initialized',
                'is_initialized': False,
                'x_position': 0,
                'y_position': 0
            }

        return {
            # Motor positions
            'x_position': self.get_current_x(),
            'y_position': self.get_current_y(),

            # Tool piston states
            'line_marker_piston': self.get_line_marker_state(),
            'line_cutter_piston': self.get_line_cutter_state(),
            'line_motor_piston': self.get_line_motor_piston_state(),
            'row_marker_piston': self.get_row_marker_state(),
            'row_cutter_piston': self.get_row_cutter_state(),

            # Tool sensors - Lines
            'line_marker_up_sensor': self.gpio.get_line_marker_up_sensor() if self.gpio else False,
            'line_marker_down_sensor': self.gpio.get_line_marker_down_sensor() if self.gpio else False,
            'line_cutter_up_sensor': self.gpio.get_line_cutter_up_sensor() if self.gpio else False,
            'line_cutter_down_sensor': self.gpio.get_line_cutter_down_sensor() if self.gpio else False,
            'line_motor_left_up_sensor': self.gpio.get_line_motor_left_up_sensor() if self.gpio else False,
            'line_motor_left_down_sensor': self.gpio.get_line_motor_left_down_sensor() if self.gpio else False,
            'line_motor_right_up_sensor': self.gpio.get_line_motor_right_up_sensor() if self.gpio else False,
            'line_motor_right_down_sensor': self.gpio.get_line_motor_right_down_sensor() if self.gpio else False,

            # Tool sensors - Rows
            'row_marker_up_sensor': self.gpio.get_row_marker_up_sensor() if self.gpio else False,
            'row_marker_down_sensor': self.gpio.get_row_marker_down_sensor() if self.gpio else False,
            'row_cutter_up_sensor': self.gpio.get_row_cutter_up_sensor() if self.gpio else False,
            'row_cutter_down_sensor': self.gpio.get_row_cutter_down_sensor() if self.gpio else False,

            # Edge sensors
            'x_left_edge': self.get_x_left_edge(),
            'x_right_edge': self.get_x_right_edge(),
            'y_top_edge': self.get_y_top_edge(),
            'y_bottom_edge': self.get_y_bottom_edge(),

            # Limit switches
            'row_marker_limit_switch': self.get_door_switch(),

            # Status
            'is_initialized': self.is_initialized
        }

    def reset_hardware(self):
        """Reset hardware to initial state"""
        if self.is_initialized:
            # Home motors
            self.home_motors()
            # Raise all tools
            self.lift_line_tools()

    # ========== MOCK-SPECIFIC METHODS (no-op for real hardware) ==========

    def set_execution_engine_reference(self, engine):
        """Set execution engine reference (only used by mock hardware for sensor waiting)"""
        pass

    def flush_all_sensor_buffers(self):
        """Flush sensor buffers (only used by mock hardware)"""
        pass

    # ========== CLEANUP ==========

    def shutdown(self):
        """Shutdown and cleanup all hardware"""
        self.logger.info("Shutting down hardware...", category="hardware")

        if self.grbl:
            self.grbl.disconnect()
        if self.gpio:
            self.gpio.cleanup()

        self.is_initialized = False
        self.logger.success("Hardware shutdown complete", category="hardware")


if __name__ == "__main__":
    """Test hardware interface"""
    module_logger.info("="*60, category="hardware")
    module_logger.info("Real Hardware Interface Test", category="hardware")
    module_logger.info("="*60, category="hardware")

    # Create hardware interface
    hardware = RealHardware()

    # Initialize
    if hardware.initialize():
        module_logger.info("Testing motor control...", category="hardware")
        hardware.move_to(10, 10)
        hardware.move_to(0, 0)

        module_logger.info("Testing piston control...", category="hardware")
        hardware.line_marker_piston_down()
        hardware.line_marker_piston_up()

        module_logger.info("Reading sensors...", category="hardware")
        edge_sensors = hardware.read_edge_sensors()
        module_logger.debug(f"Edge sensors: {edge_sensors}", category="hardware")

        # Shutdown
        hardware.shutdown()
    else:
        module_logger.error("Failed to initialize hardware", category="hardware")

    module_logger.info("="*60, category="hardware")
    module_logger.info("Test completed", category="hardware")
    module_logger.info("="*60, category="hardware")

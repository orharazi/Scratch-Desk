#!/usr/bin/env python3

"""
Real Hardware Implementation
=============================

Combines Raspberry Pi GPIO and Arduino GRBL into single interface.
This class contains ONLY real hardware implementation.
"""

import json
import time
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
        self.grbl_connected = False
        self.gpio_connected = False
        self.initialization_error = None

        # Internal position tracking (used when GRBL is not connected)
        self._fallback_x = 0.0
        self._fallback_y = 0.0

        # Internal piston state tracking (used when GPIO is not connected)
        self._fallback_piston_states = {
            'line_marker_piston': 'up',
            'line_cutter_piston': 'up',
            'line_motor_piston': 'down',
            'row_marker_piston': 'up',
            'row_cutter_piston': 'up',
            'air_pressure_valve': 'up',
        }
        self._fallback_sensor_states = {
            'line_marker_up': True, 'line_marker_down': False,
            'line_cutter_up': True, 'line_cutter_down': False,
            'line_motor_left_up': False, 'line_motor_left_down': True,
            'line_motor_right_up': False, 'line_motor_right_down': True,
            'row_marker_up': True, 'row_marker_down': False,
            'row_cutter_up': True, 'row_cutter_down': False,
        }

        # Execution engine reference for pause checking during sensor waits
        self.execution_engine = None

        # Timing settings for sensor polling
        timing_config = self.config.get("timing", {})
        self.sensor_poll_interval = timing_config.get("sensor_poll_timeout", 0.05)  # 50ms default
        self.sensor_wait_timeout = timing_config.get("sensor_wait_timeout", 300.0)  # 5 minutes max wait

        self.logger.info("="*60, category="hardware")
        self.logger.info("Real Hardware Interface Configuration", category="hardware")
        self.logger.info("="*60, category="hardware")
        self.logger.info("Mode: REAL HARDWARE", category="hardware")
        self.logger.info("="*60, category="hardware")

        # Attempt to initialize hardware - always mark as initialized so system can run
        self.initialize()
        # Always set is_initialized=True so system operates (with fallback tracking)
        self.is_initialized = True
        if self.initialization_error:
            self.logger.warning(f"Hardware partially initialized: {self.initialization_error}", category="hardware")
            self.logger.warning("System will operate with fallback position/state tracking", category="hardware")

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
        Initialize all hardware components.
        Even if some components fail, the system will operate with fallback tracking.

        Returns:
            True if all components initialized, False if any failed
        """
        errors = []

        # Initialize Raspberry Pi GPIO
        self.logger.info("Initializing Raspberry Pi GPIO...", category="hardware")
        try:
            self.gpio = RaspberryPiGPIO(self.config_path)
            if not self.gpio.initialize():
                error_msg = "GPIO initialization failed"
                self.logger.error(error_msg, category="hardware")
                errors.append(error_msg)
                self.gpio = None
            else:
                self.gpio_connected = True
                self.logger.success("GPIO initialized successfully", category="hardware")
        except Exception as e:
            error_msg = f"GPIO error: {str(e)}"
            self.logger.error(error_msg, category="hardware")
            errors.append(error_msg)
            self.gpio = None

        # Initialize Arduino GRBL (conditional based on config)
        start_with_grbl = self.config.get('hardware_config', {}).get('start_with_grbl', True)

        if start_with_grbl:
            self.logger.info("Initializing Arduino GRBL...", category="hardware")
            try:
                self.grbl = ArduinoGRBL(self.config_path)
                if not self.grbl.connect():
                    error_msg = "GRBL connection failed - check Arduino port and connection"
                    self.logger.error(error_msg, category="hardware")
                    errors.append(error_msg)
                    self.grbl = None
                else:
                    self.grbl_connected = True
                    self.logger.success("GRBL connected successfully", category="hardware")
            except Exception as e:
                error_msg = f"GRBL error: {str(e)}"
                self.logger.error(error_msg, category="hardware")
                errors.append(error_msg)
                self.grbl = None
        else:
            self.logger.info("GRBL initialization skipped (start_with_grbl=false)", category="hardware")
            self.logger.warning("Motor control will not be available without GRBL", category="hardware")
            self.grbl = None

        if not errors:
            self.initialization_error = None
            self.logger.success("All hardware initialized successfully", category="hardware")
            return True
        else:
            self.initialization_error = "; ".join(errors)
            self.logger.error(f"Hardware init errors: {self.initialization_error}", category="hardware")
            self.logger.warning("Using fallback position/state tracking for missing components", category="hardware")
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
        if self.grbl:
            result = self.grbl.move_to(position, self.grbl.current_y)
            self._fallback_x = position
            return result
        else:
            # Fallback: track position internally, log error
            self.logger.warning(f"GRBL not connected - tracking X={position:.1f}cm internally", category="hardware")
            self._fallback_x = position
            return True

    def move_y(self, position: float) -> bool:
        """
        Move Y motor to absolute position

        Args:
            position: Target position in cm

        Returns:
            True if successful, False otherwise
        """
        if self.grbl:
            result = self.grbl.move_to(self.grbl.current_x, position)
            self._fallback_y = position
            return result
        else:
            # Fallback: track position internally, log error
            self.logger.warning(f"GRBL not connected - tracking Y={position:.1f}cm internally", category="hardware")
            self._fallback_y = position
            return True

    def move_to(self, x: float, y: float) -> bool:
        """
        Move to absolute position

        Args:
            x: Target X position in cm
            y: Target Y position in cm

        Returns:
            True if successful, False otherwise
        """
        if self.grbl:
            result = self.grbl.move_to(x, y)
            self._fallback_x = x
            self._fallback_y = y
            return result
        else:
            self.logger.warning(f"GRBL not connected - tracking position ({x:.1f}, {y:.1f}) internally", category="hardware")
            self._fallback_x = x
            self._fallback_y = y
            return True

    def home_motors(self) -> bool:
        """
        Home all motors (basic $H command)

        Returns:
            True if successful, False otherwise
        """
        if self.grbl:
            result = self.grbl.home()
            self._fallback_x = 0.0
            self._fallback_y = 0.0
            return result
        else:
            self.logger.warning("GRBL not connected - resetting fallback position to (0,0)", category="hardware")
            self._fallback_x = 0.0
            self._fallback_y = 0.0
            return True

    def perform_complete_homing_sequence(self, progress_callback=None) -> tuple[bool, str]:
        """
        Perform complete homing sequence with configuration and safety checks

        This is the comprehensive homing procedure that:
        1. Applies GRBL configuration from settings.json
        2. Checks door is open
        3. Lifts line motor pistons
        4. Runs GRBL homing ($H)
        5. Resets work coordinates to (0, 0)
        6. Lowers line motor pistons

        Args:
            progress_callback: Optional callback function(step_number, step_name, status, message=None)

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        if not self.grbl:
            error_msg = "GRBL not connected - cannot perform homing"
            self.logger.error(error_msg, category="hardware")
            self._fallback_x = 0.0
            self._fallback_y = 0.0
            return False, error_msg

        # Pass self as hardware_interface so GRBL can control pistons and check door
        result = self.grbl.perform_complete_homing_sequence(hardware_interface=self, progress_callback=progress_callback)
        if result[0]:
            self._fallback_x = 0.0
            self._fallback_y = 0.0
        return result

    def apply_grbl_configuration(self) -> bool:
        """
        Apply GRBL configuration from settings.json

        Returns:
            True if successful, False otherwise
        """
        if not self.grbl:
            self.logger.warning("GRBL not connected - cannot apply configuration", category="hardware")
            return False

        return self.grbl.apply_grbl_configuration()

    def get_grbl_status(self) -> Optional[Dict]:
        """
        Get current GRBL status including position and state

        Returns:
            Dictionary with status info (state, x, y) or None if not available
        """
        if self.grbl:
            return self.grbl.get_status()

        # Fallback status when GRBL not connected
        return {
            'state': 'Disconnected',
            'x': self._fallback_x,
            'y': self._fallback_y
        }

    # ========== PISTON CONTROL (via GPIO) ==========

    def _piston_action(self, piston_name: str, direction: str) -> bool:
        """Generic piston action with fallback when GPIO not connected"""
        if self.gpio:
            if direction == 'down':
                return self.gpio.piston_down(piston_name)
            else:
                return self.gpio.piston_up(piston_name)
        else:
            self.logger.warning(f"GPIO not connected - tracking {piston_name} {direction} internally", category="hardware")
            self._fallback_piston_states[piston_name] = direction
            # Update sensor fallback states
            base = piston_name.replace('_piston', '')
            if direction == 'down':
                self._fallback_sensor_states[f'{base}_up'] = False
                self._fallback_sensor_states[f'{base}_down'] = True
            else:
                self._fallback_sensor_states[f'{base}_up'] = True
                self._fallback_sensor_states[f'{base}_down'] = False
            return True

    def line_marker_piston_down(self) -> bool:
        """Lower line marker piston"""
        return self._piston_action("line_marker_piston", "down")

    def line_marker_piston_up(self) -> bool:
        """Raise line marker piston"""
        return self._piston_action("line_marker_piston", "up")

    def line_cutter_piston_down(self) -> bool:
        """Lower line cutter piston"""
        return self._piston_action("line_cutter_piston", "down")

    def line_cutter_piston_up(self) -> bool:
        """Raise line cutter piston"""
        return self._piston_action("line_cutter_piston", "up")

    def line_motor_piston_down(self) -> bool:
        """Lower line motor piston (both sides move together - single GPIO control)"""
        if self.gpio:
            return self.gpio.line_motor_piston_down()
        else:
            self.logger.warning("GPIO not connected - tracking line_motor_piston down internally", category="hardware")
            self._fallback_piston_states['line_motor_piston'] = 'down'
            self._fallback_sensor_states['line_motor_left_up'] = False
            self._fallback_sensor_states['line_motor_left_down'] = True
            self._fallback_sensor_states['line_motor_right_up'] = False
            self._fallback_sensor_states['line_motor_right_down'] = True
            return True

    def line_motor_piston_up(self) -> bool:
        """Raise line motor piston (both sides move together - single GPIO control)"""
        if self.gpio:
            return self.gpio.line_motor_piston_up()
        else:
            self.logger.warning("GPIO not connected - tracking line_motor_piston up internally", category="hardware")
            self._fallback_piston_states['line_motor_piston'] = 'up'
            self._fallback_sensor_states['line_motor_left_up'] = True
            self._fallback_sensor_states['line_motor_left_down'] = False
            self._fallback_sensor_states['line_motor_right_up'] = True
            self._fallback_sensor_states['line_motor_right_down'] = False
            return True

    def row_marker_piston_down(self) -> bool:
        """Lower row marker piston"""
        return self._piston_action("row_marker_piston", "down")

    def row_marker_piston_up(self) -> bool:
        """Raise row marker piston"""
        return self._piston_action("row_marker_piston", "up")

    def row_cutter_piston_down(self) -> bool:
        """Lower row cutter piston"""
        return self._piston_action("row_cutter_piston", "down")

    def row_cutter_piston_up(self) -> bool:
        """Raise row cutter piston"""
        return self._piston_action("row_cutter_piston", "up")

    def air_pressure_valve_down(self) -> bool:
        """Open air pressure valve (air flows to pistons)"""
        return self._piston_action("air_pressure_valve", "down")

    def air_pressure_valve_up(self) -> bool:
        """Close air pressure valve (no air to pistons)"""
        return self._piston_action("air_pressure_valve", "up")

    def get_air_pressure_valve_state(self) -> str:
        """Get air pressure valve state"""
        if self.gpio:
            return self.gpio.get_piston_pin_state("air_pressure_valve")
        return self._fallback_piston_states.get('air_pressure_valve', 'up')

    # ========== SENSOR READING (via GPIO) - DUAL SENSORS PER TOOL ==========

    def _get_sensor(self, gpio_method_name: str, fallback_key: str) -> bool:
        """Generic sensor getter with fallback"""
        if self.gpio:
            method = getattr(self.gpio, gpio_method_name, None)
            if method:
                state = method()
                return state if state is not None else False
        return self._fallback_sensor_states.get(fallback_key, False)

    # Line Marker Sensors
    def get_line_marker_up_sensor(self) -> bool:
        return self._get_sensor('get_line_marker_up_sensor', 'line_marker_up')

    def get_line_marker_down_sensor(self) -> bool:
        return self._get_sensor('get_line_marker_down_sensor', 'line_marker_down')

    # Line Cutter Sensors
    def get_line_cutter_up_sensor(self) -> bool:
        return self._get_sensor('get_line_cutter_up_sensor', 'line_cutter_up')

    def get_line_cutter_down_sensor(self) -> bool:
        return self._get_sensor('get_line_cutter_down_sensor', 'line_cutter_down')

    # Line Motor Left Piston Sensors
    def get_line_motor_left_up_sensor(self) -> bool:
        return self._get_sensor('get_line_motor_left_up_sensor', 'line_motor_left_up')

    def get_line_motor_left_down_sensor(self) -> bool:
        return self._get_sensor('get_line_motor_left_down_sensor', 'line_motor_left_down')

    # Line Motor Right Piston Sensors
    def get_line_motor_right_up_sensor(self) -> bool:
        return self._get_sensor('get_line_motor_right_up_sensor', 'line_motor_right_up')

    def get_line_motor_right_down_sensor(self) -> bool:
        return self._get_sensor('get_line_motor_right_down_sensor', 'line_motor_right_down')

    # Row Marker Sensors
    def get_row_marker_up_sensor(self) -> bool:
        return self._get_sensor('get_row_marker_up_sensor', 'row_marker_up')

    def get_row_marker_down_sensor(self) -> bool:
        return self._get_sensor('get_row_marker_down_sensor', 'row_marker_down')

    # Row Cutter Sensors
    def get_row_cutter_up_sensor(self) -> bool:
        return self._get_sensor('get_row_cutter_up_sensor', 'row_cutter_up')

    def get_row_cutter_down_sensor(self) -> bool:
        return self._get_sensor('get_row_cutter_down_sensor', 'row_cutter_down')

    # ========== EDGE SENSORS ==========

    def get_x_left_edge_sensor(self) -> bool:
        """Read X-axis LEFT edge sensor state"""
        if not self.gpio:
            return False
        state = self.gpio.get_x_left_edge_sensor()
        return state if state is not None else False

    def get_x_right_edge_sensor(self) -> bool:
        """Read X-axis RIGHT edge sensor state"""
        if not self.gpio:
            return False
        state = self.gpio.get_x_right_edge_sensor()
        return state if state is not None else False

    def get_y_top_edge_sensor(self) -> bool:
        """Read Y-axis TOP edge sensor state"""
        if not self.gpio:
            return False
        state = self.gpio.get_y_top_edge_sensor()
        return state if state is not None else False

    def get_y_bottom_edge_sensor(self) -> bool:
        """Read Y-axis BOTTOM edge sensor state"""
        if not self.gpio:
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
        Read door sensor state (from RS485 via GPIO interface)

        Returns:
            True if door is closed, False if open
        """
        if not self.gpio:
            return False
        state = self.gpio.get_door_sensor()
        return state if state is not None else False

    def get_door_sensor(self) -> bool:
        """
        Read door sensor state (alias for get_door_switch for consistency with other sensors)

        Returns:
            True if door is closed, False if open
        """
        return self.get_door_switch()

    def get_rows_door_switch(self) -> bool:
        """
        Read rows door switch state (legacy method)

        DEPRECATED: Use get_door_switch() instead
        """
        return self.get_door_switch()

    # ========== EMERGENCY CONTROLS ==========

    def emergency_stop(self) -> bool:
        """Emergency stop all motors - feed hold then soft reset to clear queue"""
        if not self.grbl:
            self.logger.warning("GRBL not connected - emergency stop (no motors to stop)", category="hardware")
            return True

        result = self.grbl.stop()       # Feed hold "!" - immediate stop
        time.sleep(0.1)
        self.grbl.reset()               # Soft reset Ctrl-X - clears queue
        return result

    def resume_operation(self) -> bool:
        """Resume operation after emergency stop"""
        if not self.grbl:
            self.logger.warning("GRBL not connected - resume (no motors to resume)", category="hardware")
            return True

        return self.grbl.resume()

    # ========== POSITION GETTERS ==========

    def get_current_x(self) -> float:
        """Get current X motor position in cm"""
        if self.grbl:
            return self.grbl.current_x
        return self._fallback_x

    def get_current_y(self) -> float:
        """Get current Y motor position in cm"""
        if self.grbl:
            return self.grbl.current_y
        return self._fallback_y

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

    def _get_tool_state_from_sensors(self, up: bool, down: bool) -> str:
        """Determine tool state from up/down sensor pair"""
        if up and not down:
            return "up"
        elif down and not up:
            return "down"
        elif not up and not down:
            return "moving"
        else:
            return "error"

    def get_line_marker_state(self) -> str:
        """Get line marker tool state"""
        return self._get_tool_state_from_sensors(
            self.get_line_marker_up_sensor(), self.get_line_marker_down_sensor())

    def get_line_cutter_state(self) -> str:
        """Get line cutter tool state"""
        return self._get_tool_state_from_sensors(
            self.get_line_cutter_up_sensor(), self.get_line_cutter_down_sensor())

    def get_row_marker_state(self) -> str:
        """Get row marker tool state"""
        return self._get_tool_state_from_sensors(
            self.get_row_marker_up_sensor(), self.get_row_marker_down_sensor())

    def get_row_cutter_state(self) -> str:
        """Get row cutter tool state"""
        return self._get_tool_state_from_sensors(
            self.get_row_cutter_up_sensor(), self.get_row_cutter_down_sensor())

    def _get_piston_state(self, piston_name: str) -> str:
        """Get piston state with GPIO fallback"""
        if self.gpio:
            return self.gpio.get_piston_pin_state(piston_name)
        return self._fallback_piston_states.get(piston_name, "unknown")

    def get_line_marker_piston_state(self) -> str:
        """Get line marker piston actual GPIO pin state (not sensor state)"""
        return self._get_piston_state("line_marker_piston")

    def get_line_cutter_piston_state(self) -> str:
        """Get line cutter piston actual GPIO pin state (not sensor state)"""
        return self._get_piston_state("line_cutter_piston")

    def get_line_motor_piston_state(self) -> str:
        """Get line motor piston actual GPIO pin state (not sensor state)"""
        return self._get_piston_state("line_motor_piston")

    def get_row_marker_piston_state(self) -> str:
        """Get row marker piston actual GPIO pin state (not sensor state)"""
        return self._get_piston_state("row_marker_piston")

    def get_row_cutter_piston_state(self) -> str:
        """Get row cutter piston actual GPIO pin state (not sensor state)"""
        return self._get_piston_state("row_cutter_piston")

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
        if switch_name in ("rows_door", "door"):
            return self.get_door_switch()
        if self.grbl:
            return self.grbl.get_limit_switch(switch_name)
        return False

    def get_top_limit_switch(self) -> bool:
        """Get Y-axis top limit switch state"""
        return self.get_limit_switch_state('y_top')

    def get_bottom_limit_switch(self) -> bool:
        """Get Y-axis bottom limit switch state"""
        return self.get_limit_switch_state('y_bottom')

    def get_left_limit_switch(self) -> bool:
        """Get X-axis left limit switch state"""
        return self.get_limit_switch_state('x_left')

    def get_right_limit_switch(self) -> bool:
        """Get X-axis right limit switch state"""
        return self.get_limit_switch_state('x_right')

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
        """
        Wait for lines sensor trigger (either left or right edge).
        Blocks until sensor is triggered.

        Returns:
            'left' if left edge triggered, 'right' if right edge triggered
        """
        self.logger.info("Waiting for lines sensor (left or right edge)...", category="hardware")
        start_time = time.time()

        while True:
            # Check if execution is paused
            if self.execution_engine and hasattr(self.execution_engine, 'is_paused') and self.execution_engine.is_paused:
                time.sleep(self.sensor_poll_interval)
                continue

            # Check for stop signal
            if self.execution_engine and hasattr(self.execution_engine, 'stop_event'):
                if self.execution_engine.stop_event.is_set():
                    self.logger.warning("Lines sensor wait aborted - stop requested", category="hardware")
                    return None

            # Check left edge sensor
            if self.get_x_left_edge_sensor():
                self.logger.info("Lines sensor triggered: LEFT edge detected", category="hardware")
                return 'left'

            # Check right edge sensor
            if self.get_x_right_edge_sensor():
                self.logger.info("Lines sensor triggered: RIGHT edge detected", category="hardware")
                return 'right'

            # Check timeout
            if time.time() - start_time > self.sensor_wait_timeout:
                self.logger.warning(f"Lines sensor wait timeout after {self.sensor_wait_timeout}s", category="hardware")
                return None

            # Small delay before next poll
            time.sleep(self.sensor_poll_interval)

    def wait_for_y_sensor(self):
        """
        Wait for rows sensor trigger (either top or bottom edge).
        Blocks until sensor is triggered.

        Returns:
            'top' if top edge triggered, 'bottom' if bottom edge triggered
        """
        self.logger.info("Waiting for rows sensor (top or bottom edge)...", category="hardware")
        start_time = time.time()

        while True:
            # Check if execution is paused
            if self.execution_engine and hasattr(self.execution_engine, 'is_paused') and self.execution_engine.is_paused:
                time.sleep(self.sensor_poll_interval)
                continue

            # Check for stop signal
            if self.execution_engine and hasattr(self.execution_engine, 'stop_event'):
                if self.execution_engine.stop_event.is_set():
                    self.logger.warning("Rows sensor wait aborted - stop requested", category="hardware")
                    return None

            # Check top edge sensor
            if self.get_y_top_edge_sensor():
                self.logger.info("Rows sensor triggered: TOP edge detected", category="hardware")
                return 'top'

            # Check bottom edge sensor
            if self.get_y_bottom_edge_sensor():
                self.logger.info("Rows sensor triggered: BOTTOM edge detected", category="hardware")
                return 'bottom'

            # Check timeout
            if time.time() - start_time > self.sensor_wait_timeout:
                self.logger.warning(f"Rows sensor wait timeout after {self.sensor_wait_timeout}s", category="hardware")
                return None

            # Small delay before next poll
            time.sleep(self.sensor_poll_interval)

    def wait_for_x_left_sensor(self):
        """
        Wait specifically for Left lines edge sensor.
        Blocks until sensor is triggered.

        Returns:
            'left' when triggered, None on timeout
        """
        self.logger.info("Waiting for Left lines edge sensor...", category="hardware")
        start_time = time.time()

        while True:
            # Check if execution is paused
            if self.execution_engine and hasattr(self.execution_engine, 'is_paused') and self.execution_engine.is_paused:
                time.sleep(self.sensor_poll_interval)
                continue

            # Check for stop signal
            if self.execution_engine and hasattr(self.execution_engine, 'stop_event'):
                if self.execution_engine.stop_event.is_set():
                    self.logger.warning("X left sensor wait aborted - stop requested", category="hardware")
                    return None

            # Check left edge sensor
            if self.get_x_left_edge_sensor():
                self.logger.info("Left lines edge sensor triggered", category="hardware")
                return 'left'

            # Check timeout
            if time.time() - start_time > self.sensor_wait_timeout:
                self.logger.warning(f"X left sensor wait timeout after {self.sensor_wait_timeout}s", category="hardware")
                return None

            # Small delay before next poll
            time.sleep(self.sensor_poll_interval)

    def wait_for_x_right_sensor(self):
        """
        Wait specifically for Right lines edge sensor.
        Blocks until sensor is triggered.

        Returns:
            'right' when triggered, None on timeout
        """
        self.logger.info("Waiting for Right lines edge sensor...", category="hardware")
        start_time = time.time()

        while True:
            # Check if execution is paused
            if self.execution_engine and hasattr(self.execution_engine, 'is_paused') and self.execution_engine.is_paused:
                time.sleep(self.sensor_poll_interval)
                continue

            # Check for stop signal
            if self.execution_engine and hasattr(self.execution_engine, 'stop_event'):
                if self.execution_engine.stop_event.is_set():
                    self.logger.warning("X right sensor wait aborted - stop requested", category="hardware")
                    return None

            # Check right edge sensor
            if self.get_x_right_edge_sensor():
                self.logger.info("Right lines edge sensor triggered", category="hardware")
                return 'right'

            # Check timeout
            if time.time() - start_time > self.sensor_wait_timeout:
                self.logger.warning(f"X right sensor wait timeout after {self.sensor_wait_timeout}s", category="hardware")
                return None

            # Small delay before next poll
            time.sleep(self.sensor_poll_interval)

    def wait_for_y_top_sensor(self):
        """
        Wait specifically for Top rows edge sensor.
        Blocks until sensor is triggered.

        Returns:
            'top' when triggered, None on timeout
        """
        self.logger.info("Waiting for Top rows edge sensor...", category="hardware")
        start_time = time.time()

        while True:
            # Check if execution is paused
            if self.execution_engine and hasattr(self.execution_engine, 'is_paused') and self.execution_engine.is_paused:
                time.sleep(self.sensor_poll_interval)
                continue

            # Check for stop signal
            if self.execution_engine and hasattr(self.execution_engine, 'stop_event'):
                if self.execution_engine.stop_event.is_set():
                    self.logger.warning("Y top sensor wait aborted - stop requested", category="hardware")
                    return None

            # Check top edge sensor
            if self.get_y_top_edge_sensor():
                self.logger.info("Top rows edge sensor triggered", category="hardware")
                return 'top'

            # Check timeout
            if time.time() - start_time > self.sensor_wait_timeout:
                self.logger.warning(f"Y top sensor wait timeout after {self.sensor_wait_timeout}s", category="hardware")
                return None

            # Small delay before next poll
            time.sleep(self.sensor_poll_interval)

    def wait_for_y_bottom_sensor(self):
        """
        Wait specifically for Bottom rows edge sensor.
        Blocks until sensor is triggered.

        Returns:
            'bottom' when triggered, None on timeout
        """
        self.logger.info("Waiting for Bottom rows edge sensor...", category="hardware")
        start_time = time.time()

        while True:
            # Check if execution is paused
            if self.execution_engine and hasattr(self.execution_engine, 'is_paused') and self.execution_engine.is_paused:
                time.sleep(self.sensor_poll_interval)
                continue

            # Check for stop signal
            if self.execution_engine and hasattr(self.execution_engine, 'stop_event'):
                if self.execution_engine.stop_event.is_set():
                    self.logger.warning("Y bottom sensor wait aborted - stop requested", category="hardware")
                    return None

            # Check bottom edge sensor
            if self.get_y_bottom_edge_sensor():
                self.logger.info("Bottom rows edge sensor triggered", category="hardware")
                return 'bottom'

            # Check timeout
            if time.time() - start_time > self.sensor_wait_timeout:
                self.logger.warning(f"Y bottom sensor wait timeout after {self.sensor_wait_timeout}s", category="hardware")
                return None

            # Small delay before next poll
            time.sleep(self.sensor_poll_interval)

    # ========== HARDWARE STATUS ==========

    def get_hardware_status(self):
        """Get complete hardware status dictionary with all sensors (uses fallback when GPIO not connected)"""
        status = {
            # Motor positions (uses fallback when GRBL not connected)
            'x_position': self.get_current_x(),
            'y_position': self.get_current_y(),

            # Tool piston states (uses fallback when GPIO not connected)
            'line_marker_piston': self.get_line_marker_state(),
            'line_cutter_piston': self.get_line_cutter_state(),
            'line_motor_piston': self.get_line_motor_piston_state(),
            'row_marker_piston': self.get_row_marker_state(),
            'row_cutter_piston': self.get_row_cutter_state(),

            # Tool sensors (uses fallback when GPIO not connected)
            'line_marker_up_sensor': self.get_line_marker_up_sensor(),
            'line_marker_down_sensor': self.get_line_marker_down_sensor(),
            'line_cutter_up_sensor': self.get_line_cutter_up_sensor(),
            'line_cutter_down_sensor': self.get_line_cutter_down_sensor(),
            'line_motor_left_up_sensor': self.get_line_motor_left_up_sensor(),
            'line_motor_left_down_sensor': self.get_line_motor_left_down_sensor(),
            'line_motor_right_up_sensor': self.get_line_motor_right_up_sensor(),
            'line_motor_right_down_sensor': self.get_line_motor_right_down_sensor(),

            # Tool sensors - Rows
            'row_marker_up_sensor': self.get_row_marker_up_sensor(),
            'row_marker_down_sensor': self.get_row_marker_down_sensor(),
            'row_cutter_up_sensor': self.get_row_cutter_up_sensor(),
            'row_cutter_down_sensor': self.get_row_cutter_down_sensor(),

            # Edge sensors
            'x_left_edge': self.get_x_left_edge(),
            'x_right_edge': self.get_x_right_edge(),
            'y_top_edge': self.get_y_top_edge(),
            'y_bottom_edge': self.get_y_bottom_edge(),

            # Limit switches
            'row_marker_limit_switch': self.get_door_switch(),

            # Air pressure valve
            'air_pressure_valve': self.get_air_pressure_valve_state(),

            # Status
            'is_initialized': self.is_initialized
        }

        # Add connection info
        if self.initialization_error:
            status['connection_error'] = self.initialization_error
            status['grbl_connected'] = self.grbl_connected
            status['gpio_connected'] = self.gpio_connected

        return status

    def reset_hardware(self):
        """Reset hardware to initial state"""
        # Home motors (uses fallback if GRBL not connected)
        self.home_motors()
        # Raise all tools (uses fallback if GPIO not connected)
        self.lift_line_tools()

    # ========== MOCK-SPECIFIC METHODS (no-op for real hardware) ==========

    def set_execution_engine_reference(self, engine):
        """
        Set execution engine reference for sensor waiting.
        Used to check pause/stop state during blocking sensor waits.
        """
        self.execution_engine = engine
        self.logger.debug("Execution engine reference set", category="hardware")

    def flush_all_sensor_buffers(self):
        """Flush sensor buffers (only used by mock hardware)"""
        pass

    def signal_all_sensor_events(self):
        """Signal all sensor events to unblock waiting threads during stop (only used by mock hardware)"""
        pass

    # ========== CLEANUP ==========

    def shutdown(self):
        """Shutdown and cleanup all hardware"""
        self.logger.info("Shutting down hardware...", category="hardware")

        # Close air pressure valve before GPIO cleanup
        try:
            self.air_pressure_valve_up()
        except Exception:
            pass

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

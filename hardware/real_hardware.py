#!/usr/bin/env python3

"""
Real Hardware Implementation
=============================

Combines Raspberry Pi GPIO and Arduino GRBL into single interface.
This class contains ONLY real hardware implementation.
"""

import json
from typing import Optional, Dict
from hardware.raspberry_pi_gpio import RaspberryPiGPIO
from hardware.arduino_grbl import ArduinoGRBL


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
        self.config_path = config_path
        self.config = self._load_config(config_path)

        # Initialize components
        self.gpio: Optional[RaspberryPiGPIO] = None
        self.grbl: Optional[ArduinoGRBL] = None
        self.is_initialized = False
        self.initialization_error = None

        print(f"\n{'='*60}")
        print("Real Hardware Interface Configuration")
        print(f"{'='*60}")
        print(f"Mode: REAL HARDWARE")
        print(f"{'='*60}\n")

        # Attempt to initialize hardware
        if not self.initialize():
            self.initialization_error = "Failed to initialize hardware. Check connections and try again."

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from config/settings.json"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading config: {e}")
            return {}

    def initialize(self) -> bool:
        """
        Initialize all hardware components

        Returns:
            True if initialization successful, False otherwise
        """
        if self.is_initialized:
            print("Hardware already initialized")
            return True

        errors = []

        # Initialize Raspberry Pi GPIO
        print("\nInitializing Raspberry Pi GPIO...")
        try:
            self.gpio = RaspberryPiGPIO(self.config_path)
            if not self.gpio.initialize():
                error_msg = "GPIO initialization failed"
                print(f"✗ {error_msg}")
                errors.append(error_msg)
            else:
                print("✓ GPIO initialized successfully")
        except Exception as e:
            error_msg = f"GPIO error: {str(e)}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)

        # Initialize Arduino GRBL
        print("\nInitializing Arduino GRBL...")
        try:
            self.grbl = ArduinoGRBL(self.config_path)
            if not self.grbl.connect():
                error_msg = "GRBL connection failed - check Arduino port and connection"
                print(f"✗ {error_msg}")
                errors.append(error_msg)
            else:
                print("✓ GRBL connected successfully")
        except Exception as e:
            error_msg = f"GRBL error: {str(e)}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)

        if not errors:
            self.is_initialized = True
            self.initialization_error = None
            print("\n✓ All hardware initialized successfully\n")
            return True
        else:
            self.initialization_error = "; ".join(errors)
            print(f"\n✗ Hardware initialization failed: {self.initialization_error}\n")
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
            print("Hardware not initialized")
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
            print("Hardware not initialized")
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
            print("Hardware not initialized")
            return False

        return self.grbl.move_to(x, y)

    def home_motors(self) -> bool:
        """
        Home all motors

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized or not self.grbl:
            print("Hardware not initialized")
            return False

        return self.grbl.home()

    # ========== PISTON CONTROL (via GPIO) ==========

    def line_marker_piston_down(self) -> bool:
        """Lower line marker piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_down("line_marker_piston")

    def line_marker_piston_up(self) -> bool:
        """Raise line marker piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_up("line_marker_piston")

    def line_cutter_piston_down(self) -> bool:
        """Lower line cutter piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_down("line_cutter_piston")

    def line_cutter_piston_up(self) -> bool:
        """Raise line cutter piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_up("line_cutter_piston")

    def line_motor_piston_down(self) -> bool:
        """Lower BOTH line motor pistons (left and right)"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.line_motor_piston_down()

    def line_motor_piston_up(self) -> bool:
        """Raise BOTH line motor pistons (left and right)"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.line_motor_piston_up()

    def line_motor_piston_left_down(self) -> bool:
        """Lower line motor LEFT piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.line_motor_piston_left_down()

    def line_motor_piston_left_up(self) -> bool:
        """Raise line motor LEFT piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.line_motor_piston_left_up()

    def line_motor_piston_right_down(self) -> bool:
        """Lower line motor RIGHT piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.line_motor_piston_right_down()

    def line_motor_piston_right_up(self) -> bool:
        """Raise line motor RIGHT piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.line_motor_piston_right_up()

    def row_marker_piston_down(self) -> bool:
        """Lower row marker piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_down("row_marker_piston")

    def row_marker_piston_up(self) -> bool:
        """Raise row marker piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_up("row_marker_piston")

    def row_cutter_piston_down(self) -> bool:
        """Lower row cutter piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_down("row_cutter_piston")

    def row_cutter_piston_up(self) -> bool:
        """Raise row cutter piston"""
        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
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
        """Get line motor piston state (combined left+right)"""
        left_up = self.get_line_motor_left_up_sensor()
        left_down = self.get_line_motor_left_down_sensor()
        right_up = self.get_line_motor_right_up_sensor()
        right_down = self.get_line_motor_right_down_sensor()

        if left_up and right_up:
            return "up"
        elif left_down and right_down:
            return "down"
        else:
            return "unknown"

    def get_line_motor_piston_left_state(self) -> str:
        """Get line motor LEFT piston state"""
        up = self.get_line_motor_left_up_sensor()
        down = self.get_line_motor_left_down_sensor()
        if up and not down:
            return "up"
        elif down and not up:
            return "down"
        else:
            return "unknown"

    def get_line_motor_piston_right_state(self) -> str:
        """Get line motor RIGHT piston state"""
        up = self.get_line_motor_right_up_sensor()
        down = self.get_line_motor_right_down_sensor()
        if up and not down:
            return "up"
        elif down and not up:
            return "down"
        else:
            return "unknown"

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
        print("\nShutting down hardware...")

        if self.grbl:
            self.grbl.disconnect()
        if self.gpio:
            self.gpio.cleanup()

        self.is_initialized = False
        print("✓ Hardware shutdown complete\n")


if __name__ == "__main__":
    """Test hardware interface"""
    print("\n" + "="*60)
    print("Real Hardware Interface Test")
    print("="*60 + "\n")

    # Create hardware interface
    hardware = RealHardware()

    # Initialize
    if hardware.initialize():
        print("\nTesting motor control...")
        hardware.move_to(10, 10)
        hardware.move_to(0, 0)

        print("\nTesting piston control...")
        hardware.line_marker_piston_down()
        hardware.line_marker_piston_up()

        print("\nReading sensors...")
        edge_sensors = hardware.read_edge_sensors()
        print(f"Edge sensors: {edge_sensors}")

        # Shutdown
        hardware.shutdown()
    else:
        print("✗ Failed to initialize hardware")

    print("\n" + "="*60)
    print("Test completed")
    print("="*60 + "\n")

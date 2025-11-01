#!/usr/bin/env python3

"""
Unified Hardware Interface
===========================

Combines Raspberry Pi GPIO and Arduino GRBL into single interface.
Automatically switches between real hardware and mock based on settings.json.
"""

import json
from typing import Optional, Dict
from hardware.raspberry_pi_gpio import RaspberryPiGPIO
from hardware.arduino_grbl import ArduinoGRBL


class HardwareInterface:
    """
    Unified interface for all hardware control
    Manages both Raspberry Pi GPIO and Arduino GRBL
    """

    def __init__(self, config_path: str = "settings.json"):
        """
        Initialize hardware interface

        Args:
            config_path: Path to settings.json configuration file
        """
        self.config_path = config_path
        self.config = self._load_config(config_path)

        # Check if real hardware should be used
        self.use_real_hardware = self.config.get("hardware_config", {}).get("use_real_hardware", False)

        # Initialize components
        self.gpio: Optional[RaspberryPiGPIO] = None
        self.grbl: Optional[ArduinoGRBL] = None
        self.is_initialized = False

        print(f"\n{'='*60}")
        print("Hardware Interface Configuration")
        print(f"{'='*60}")
        print(f"Mode: {'REAL HARDWARE' if self.use_real_hardware else 'MOCK/SIMULATION'}")
        print(f"{'='*60}\n")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from settings.json"""
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

        if not self.use_real_hardware:
            print("⚠ Running in MOCK mode - no real hardware will be used")
            print("  To enable real hardware, set 'use_real_hardware': true in settings.json")
            self.is_initialized = True
            return True

        success = True

        # Initialize Raspberry Pi GPIO
        print("\nInitializing Raspberry Pi GPIO...")
        self.gpio = RaspberryPiGPIO(self.config_path)
        if not self.gpio.initialize():
            print("✗ Failed to initialize GPIO")
            success = False

        # Initialize Arduino GRBL
        print("\nInitializing Arduino GRBL...")
        self.grbl = ArduinoGRBL(self.config_path)
        if not self.grbl.connect():
            print("✗ Failed to connect to GRBL")
            success = False

        if success:
            self.is_initialized = True
            print("\n✓ All hardware initialized successfully\n")
        else:
            print("\n✗ Hardware initialization failed\n")

        return success

    # ========== MOTOR CONTROL (via GRBL) ==========

    def move_x(self, position: float) -> bool:
        """
        Move X motor to absolute position

        Args:
            position: Target position in cm

        Returns:
            True if successful, False otherwise
        """
        if not self.use_real_hardware:
            print(f"MOCK: move_x({position:.2f}cm)")
            return True

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
        if not self.use_real_hardware:
            print(f"MOCK: move_y({position:.2f}cm)")
            return True

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
        if not self.use_real_hardware:
            print(f"MOCK: move_to(x={x:.2f}cm, y={y:.2f}cm)")
            return True

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
        if not self.use_real_hardware:
            print("MOCK: home_motors()")
            return True

        if not self.is_initialized or not self.grbl:
            print("Hardware not initialized")
            return False

        return self.grbl.home()

    # ========== PISTON CONTROL (via GPIO) ==========

    def line_marker_piston_down(self) -> bool:
        """Lower line marker piston"""
        if not self.use_real_hardware:
            print("MOCK: line_marker_piston_down()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_down("line_marker_piston")

    def line_marker_piston_up(self) -> bool:
        """Raise line marker piston"""
        if not self.use_real_hardware:
            print("MOCK: line_marker_piston_up()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_up("line_marker_piston")

    def line_cutter_piston_down(self) -> bool:
        """Lower line cutter piston"""
        if not self.use_real_hardware:
            print("MOCK: line_cutter_piston_down()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_down("line_cutter_piston")

    def line_cutter_piston_up(self) -> bool:
        """Raise line cutter piston"""
        if not self.use_real_hardware:
            print("MOCK: line_cutter_piston_up()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_up("line_cutter_piston")

    def line_motor_piston_down(self) -> bool:
        """Lower line motor piston"""
        if not self.use_real_hardware:
            print("MOCK: line_motor_piston_down()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_down("line_motor_piston")

    def line_motor_piston_up(self) -> bool:
        """Raise line motor piston"""
        if not self.use_real_hardware:
            print("MOCK: line_motor_piston_up()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_up("line_motor_piston")

    def row_marker_piston_down(self) -> bool:
        """Lower row marker piston"""
        if not self.use_real_hardware:
            print("MOCK: row_marker_piston_down()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_down("row_marker_piston")

    def row_marker_piston_up(self) -> bool:
        """Raise row marker piston"""
        if not self.use_real_hardware:
            print("MOCK: row_marker_piston_up()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_up("row_marker_piston")

    def row_cutter_piston_down(self) -> bool:
        """Lower row cutter piston"""
        if not self.use_real_hardware:
            print("MOCK: row_cutter_piston_down()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_down("row_cutter_piston")

    def row_cutter_piston_up(self) -> bool:
        """Raise row cutter piston"""
        if not self.use_real_hardware:
            print("MOCK: row_cutter_piston_up()")
            return True

        if not self.is_initialized or not self.gpio:
            print("Hardware not initialized")
            return False

        return self.gpio.piston_up("row_cutter_piston")

    # ========== SENSOR READING (via GPIO) ==========

    def read_line_marker_state(self) -> bool:
        """Read line marker sensor state"""
        if not self.use_real_hardware:
            print("MOCK: read_line_marker_state() -> False")
            return False

        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.read_sensor("line_marker_state")
        return state if state is not None else False

    def read_line_cutter_state(self) -> bool:
        """Read line cutter sensor state"""
        if not self.use_real_hardware:
            print("MOCK: read_line_cutter_state() -> False")
            return False

        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.read_sensor("line_cutter_state")
        return state if state is not None else False

    def read_line_motor_piston_sensor(self) -> bool:
        """Read line motor piston sensor state"""
        if not self.use_real_hardware:
            print("MOCK: read_line_motor_piston_sensor() -> False")
            return False

        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.read_sensor("line_motor_piston_sensor")
        return state if state is not None else False

    def read_row_marker_state(self) -> bool:
        """Read row marker sensor state"""
        if not self.use_real_hardware:
            print("MOCK: read_row_marker_state() -> False")
            return False

        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.read_sensor("row_marker_state")
        return state if state is not None else False

    def read_row_cutter_state(self) -> bool:
        """Read row cutter sensor state"""
        if not self.use_real_hardware:
            print("MOCK: read_row_cutter_state() -> False")
            return False

        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.read_sensor("row_cutter_state")
        return state if state is not None else False

    def read_edge_sensors(self) -> Dict[str, bool]:
        """
        Read all edge detection sensors

        Returns:
            Dictionary with sensor states: {'x_left': bool, 'x_right': bool, 'y_top': bool, 'y_bottom': bool}
        """
        if not self.use_real_hardware:
            print("MOCK: read_edge_sensors()")
            return {'x_left': False, 'x_right': False, 'y_top': False, 'y_bottom': False}

        if not self.is_initialized or not self.gpio:
            return {'x_left': False, 'x_right': False, 'y_top': False, 'y_bottom': False}

        return {
            'x_left': self.gpio.read_sensor("x_left_edge") or False,
            'x_right': self.gpio.read_sensor("x_right_edge") or False,
            'y_top': self.gpio.read_sensor("y_top_edge") or False,
            'y_bottom': self.gpio.read_sensor("y_bottom_edge") or False
        }

    def read_rows_door_limit_switch(self) -> bool:
        """Read rows door limit switch state"""
        if not self.use_real_hardware:
            print("MOCK: read_rows_door_limit_switch() -> False")
            return False

        if not self.is_initialized or not self.gpio:
            return False

        state = self.gpio.read_limit_switch("rows_door")
        return state if state is not None else False

    # ========== EMERGENCY CONTROLS ==========

    def emergency_stop(self) -> bool:
        """Emergency stop all motors"""
        if not self.use_real_hardware:
            print("MOCK: emergency_stop()")
            return True

        if not self.is_initialized or not self.grbl:
            return False

        return self.grbl.stop()

    def resume_operation(self) -> bool:
        """Resume operation after emergency stop"""
        if not self.use_real_hardware:
            print("MOCK: resume_operation()")
            return True

        if not self.is_initialized or not self.grbl:
            return False

        return self.grbl.resume()

    # ========== CLEANUP ==========

    def shutdown(self):
        """Shutdown and cleanup all hardware"""
        print("\nShutting down hardware...")

        if self.use_real_hardware:
            if self.grbl:
                self.grbl.disconnect()
            if self.gpio:
                self.gpio.cleanup()

        self.is_initialized = False
        print("✓ Hardware shutdown complete\n")


if __name__ == "__main__":
    """Test hardware interface"""
    print("\n" + "="*60)
    print("Unified Hardware Interface Test")
    print("="*60 + "\n")

    # Create hardware interface
    hardware = HardwareInterface()

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

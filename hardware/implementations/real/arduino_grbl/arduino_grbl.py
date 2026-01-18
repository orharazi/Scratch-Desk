#!/usr/bin/env python3

"""
Arduino GRBL Interface
======================

Handles G-code communication with Arduino running GRBL firmware.
Controls X and Y motors via serial communication.
"""

import json
import time
import re
from typing import Optional, Tuple, Dict
from threading import Lock
from core.logger import get_logger

# Try to import pyserial, fall back to mock if not available
try:
    import serial
    SERIAL_AVAILABLE = True
    _module_logger = get_logger()
    _module_logger.debug("pyserial library loaded successfully", category="grbl")
except ImportError:
    SERIAL_AVAILABLE = False
    _module_logger = get_logger()
    _module_logger.debug("pyserial not available - Arduino GRBL will run in mock mode", category="grbl")
    _module_logger.debug("Install with: pip3 install pyserial", category="grbl")
    # Create mock serial class
    class MockSerial:
        def __init__(self, port, baudrate, timeout):
            self.port = port
            self.baudrate = baudrate
            self.timeout = timeout
            self.in_waiting = 0
            self.logger = get_logger()
            self.logger.debug(f"MOCK SERIAL: Opened {port} at {baudrate} baud", category="grbl")

        def write(self, data):
            self.logger.debug(f"MOCK SERIAL >> {data.decode().strip()}", category="grbl")

        def readline(self):
            return b"ok\n"

        def close(self):
            self.logger.debug("MOCK SERIAL: Connection closed", category="grbl")

        def flushInput(self):
            pass

    serial = type('serial', (), {
        'Serial': MockSerial,
        'SerialException': Exception
    })()


class ArduinoGRBL:
    """
    Interface for Arduino GRBL motor control via G-code
    """

    def __init__(self, config_path: str = "config/settings.json"):
        """
        Initialize GRBL interface

        Args:
            config_path: Path to config/settings.json configuration file
        """
        self.logger = get_logger()
        self.config = self._load_config(config_path)
        self.grbl_config = self.config.get("hardware_config", {}).get("arduino_grbl", {})

        self.serial_port = self.grbl_config.get("serial_port", "/dev/ttyACM0")
        self.baud_rate = self.grbl_config.get("baud_rate", 115200)
        self.connection_timeout = self.grbl_config.get("connection_timeout", 5.0)
        self.command_timeout = self.grbl_config.get("command_timeout", 10.0)

        self.grbl_settings = self.grbl_config.get("grbl_settings", {})
        self.feed_rate = self.grbl_settings.get("feed_rate", 1000)  # mm/min
        self.rapid_rate = self.grbl_settings.get("rapid_rate", 3000)  # mm/min

        # Limit switches configuration
        self.limit_switches = self.grbl_config.get("limit_switches", {})
        self.door_switch_config = self.limit_switches.get("door", {})

        # Load timing configuration values
        timing_config = self.config.get("timing", {})
        self._grbl_init_delay = timing_config.get("grbl_initialization_delay", 2)
        self._grbl_serial_poll_delay = timing_config.get("grbl_serial_poll_delay", 0.01)
        self._grbl_reset_delay = timing_config.get("grbl_reset_delay", 2)

        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        self.command_lock = Lock()  # Thread safety for serial commands

        self.current_x = 0.0  # Current X position in mm
        self.current_y = 0.0  # Current Y position in mm

        self.logger.info(
            f"Arduino GRBL Configuration - Port: {self.serial_port}, Baud: {self.baud_rate}, "
            f"Feed Rate: {self.feed_rate} mm/min, Rapid Rate: {self.rapid_rate} mm/min",
            category="grbl"
        )
        if self.door_switch_config:
            self.logger.info(f"Door Switch: Pin {self.door_switch_config.get('pin', 'N/A')}", category="grbl")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from config/settings.json"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Error loading config: {e}", category="grbl")
            return {}

    def connect(self) -> bool:
        """
        Connect to Arduino GRBL via serial

        Returns:
            True if connection successful, False otherwise
        """
        if self.is_connected:
            self.logger.info("Already connected to GRBL", category="grbl")
            return True

        # First check if port is configured
        if not self.serial_port or self.serial_port == "None":
            error_msg = "ARDUINO PORT NOT CONFIGURED - No serial port specified in settings"
            self.logger.error(error_msg, category="grbl")
            self.logger.error("Please configure the Arduino port in Hardware Settings panel", category="grbl")
            self.logger.error("Select the correct port from the dropdown and click Apply & Save", category="grbl")
            raise RuntimeError(error_msg)

        try:
            self.logger.info(f"Attempting to connect to Arduino GRBL...", category="grbl")
            self.logger.debug(f"Port: {self.serial_port}", category="grbl")
            self.logger.debug(f"Baud rate: {self.baud_rate}", category="grbl")
            self.logger.debug(f"Timeout: {self.connection_timeout}s", category="grbl")

            # Check if port exists (list available ports)
            import serial.tools.list_ports
            available_ports = [port.device for port in serial.tools.list_ports.comports()]
            self.logger.debug(f"Available ports: {available_ports if available_ports else 'None found'}", category="grbl")

            if self.serial_port not in available_ports:
                error_msg = f"PORT NOT FOUND - '{self.serial_port}' is not available"
                self.logger.error(error_msg, category="grbl")
                self.logger.error(f"Available ports: {', '.join(available_ports) if available_ports else 'None'}", category="grbl")
                self.logger.error("Check Arduino is connected and port is correct in Hardware Settings", category="grbl")
                raise RuntimeError(error_msg)

            # Open serial connection
            try:
                self.serial_connection = serial.Serial(
                    port=self.serial_port,
                    baudrate=self.baud_rate,
                    timeout=self.connection_timeout
                )
                self.logger.debug("Serial port opened", category="grbl")
            except serial.SerialException as e:
                if "Permission denied" in str(e):
                    error_msg = f"PERMISSION DENIED - Cannot access port '{self.serial_port}'"
                    self.logger.error(error_msg, category="grbl")
                    self.logger.error("Try: sudo usermod -a -G dialout $USER", category="grbl")
                    self.logger.error("Then logout and login again", category="grbl")
                elif "Device is busy" in str(e) or "Resource busy" in str(e):
                    error_msg = f"PORT IN USE - '{self.serial_port}' is already open by another program"
                    self.logger.error(error_msg, category="grbl")
                    self.logger.error("Close other programs using the Arduino (Arduino IDE, screen, minicom, etc.)", category="grbl")
                else:
                    error_msg = f"SERIAL ERROR - {str(e)}"
                    self.logger.error(error_msg, category="grbl")
                raise RuntimeError(error_msg)

            # Wait for GRBL to initialize (it sends startup message)
            self.logger.debug("Waiting for GRBL to initialize...", category="grbl")
            time.sleep(self._grbl_init_delay)

            # Flush any startup messages
            self.serial_connection.flushInput()

            # Send a simple command to verify connection
            self.logger.debug("Sending status query to GRBL...", category="grbl")
            response = self._send_command("?")
            self.logger.debug(f"Response: {response}", category="grbl")  # Status query

            if response:
                self.is_connected = True
                self.logger.debug("GRBL responded successfully", category="grbl")
                self.logger.success("Connected to Arduino GRBL", category="grbl")

                # Initialize GRBL
                self._initialize_grbl()
                return True
            else:
                error_msg = "NO RESPONSE FROM GRBL - Device not responding or wrong baud rate"
                self.logger.error(error_msg, category="grbl")
                self.logger.error("Check:", category="grbl")
                self.logger.error("1. Arduino has GRBL firmware installed", category="grbl")
                self.logger.error("2. Correct baud rate (usually 115200)", category="grbl")
                self.logger.error("3. USB cable supports data (not charge-only)", category="grbl")
                self.disconnect()
                raise RuntimeError(error_msg)

        except RuntimeError:
            # Re-raise our detailed errors
            raise
        except serial.SerialException as e:
            error_msg = f"SERIAL EXCEPTION - {type(e).__name__}: {str(e)}"
            self.logger.error(error_msg, category="grbl")
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"UNEXPECTED ARDUINO ERROR - {type(e).__name__}: {str(e)}"
            self.logger.error(error_msg, category="grbl")
            raise RuntimeError(error_msg)

    def _initialize_grbl(self):
        """Initialize GRBL with required settings"""
        self.logger.info("Initializing GRBL...", category="grbl")

        # Set positioning mode (absolute/relative)
        positioning_mode = self.grbl_settings.get("positioning_mode", "G90")
        self._send_command(positioning_mode)

        # Set units (mm/inch)
        units_mode = "G21" if self.grbl_settings.get("units", "mm") == "mm" else "G20"
        self._send_command(units_mode)

        # Home the machine (if homing is enabled)
        self.logger.info("Homing machine... (This may take a few seconds)", category="grbl")
        homing_timeout = self.grbl_config.get("homing_timeout", 30.0)
        response = self._send_command("$H", timeout=homing_timeout)
        if response and "ok" in response.lower():
            self.logger.success("Homing completed", category="grbl")
        else:
            self.logger.debug("Homing may have failed or is not configured", category="grbl")

        # Reset work coordinates to (0, 0)
        self._send_command("G92 X0 Y0")

        self.current_x = 0.0
        self.current_y = 0.0

        self.logger.success("GRBL initialized", category="grbl")

    def _send_command(self, command: str, timeout: Optional[float] = None) -> Optional[str]:
        """
        Send G-code command to GRBL and wait for response

        Args:
            command: G-code command to send
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            Response from GRBL, or None on error
        """
        # Allow commands if serial connection exists (even if not fully connected yet)
        if not self.serial_connection:
            self.logger.debug("No serial connection available", category="grbl")
            return None

        if timeout is None:
            timeout = self.command_timeout

        try:
            with self.command_lock:
                # Send command
                command = command.strip()
                self.logger.debug(f"GRBL >> {command}", category="grbl")
                self.serial_connection.write(f"{command}\n".encode())

                # Read response
                start_time = time.time()
                response_lines = []
                is_status_query = command == "?"

                while time.time() - start_time < timeout:
                    if self.serial_connection.in_waiting > 0:
                        line = self.serial_connection.readline().decode().strip()
                        if line:
                            response_lines.append(line)
                            self.logger.debug(f"GRBL << {line}", category="grbl")

                            # Status queries return immediately with <...> format
                            if is_status_query and line.startswith("<") and line.endswith(">"):
                                response = "\n".join(response_lines)
                                return response

                            # Regular commands wait for ok or error
                            if "ok" in line.lower() or "error" in line.lower():
                                response = "\n".join(response_lines)
                                return response

                    time.sleep(self._grbl_serial_poll_delay)

                self.logger.debug(f"Command timeout after {timeout}s", category="grbl")
                return "\n".join(response_lines) if response_lines else None

        except Exception as e:
            self.logger.error(f"Error sending command: {e}", category="grbl")
            return None

    def move_to(self, x: float, y: float, rapid: bool = False) -> bool:
        """
        Move to absolute position

        Args:
            x: Target X position in cm (will be converted to mm)
            y: Target Y position in cm (will be converted to mm)
            rapid: Use rapid movement (G0) instead of feed rate (G1)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            self.logger.debug("Not connected to GRBL", category="grbl")
            return False

        # Convert cm to mm
        x_mm = x * 10.0
        y_mm = y * 10.0

        try:
            # Choose movement command
            if rapid:
                # G0 = rapid positioning (no feed rate)
                command = f"G0 X{x_mm:.3f} Y{y_mm:.3f}"
            else:
                # G1 = linear interpolation with feed rate
                command = f"G1 X{x_mm:.3f} Y{y_mm:.3f} F{self.feed_rate}"

            response = self._send_command(command)

            if response and "ok" in response.lower():
                self.current_x = x
                self.current_y = y
                self.logger.debug(f"Moved to X={x:.2f}cm, Y={y:.2f}cm", category="grbl")
                return True
            else:
                self.logger.debug("Move command failed", category="grbl")
                return False

        except Exception as e:
            self.logger.error(f"Error moving to position: {e}", category="grbl")
            return False

    def move_relative(self, dx: float, dy: float) -> bool:
        """
        Move relative to current position

        Args:
            dx: Delta X in cm
            dy: Delta Y in cm

        Returns:
            True if successful, False otherwise
        """
        target_x = self.current_x + dx
        target_y = self.current_y + dy
        return self.move_to(target_x, target_y)

    def home(self) -> bool:
        """
        Home the machine (move to origin)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            self.logger.debug("Not connected to GRBL", category="grbl")
            return False

        try:
            self.logger.info("Homing machine...", category="grbl")
            homing_timeout = self.grbl_config.get("homing_timeout", 30.0)
            response = self._send_command("$H", timeout=homing_timeout)

            if response and "ok" in response.lower():
                self.current_x = 0.0
                self.current_y = 0.0
                self.logger.success("Homing completed", category="grbl")
                return True
            else:
                self.logger.debug("Homing failed", category="grbl")
                return False

        except Exception as e:
            self.logger.error(f"Error homing: {e}", category="grbl")
            return False

    def get_status(self) -> Optional[Dict]:
        """
        Get current GRBL status

        Returns:
            Dictionary with status information, or None on error
        """
        if not self.is_connected:
            return None

        try:
            response = self._send_command("?", timeout=1.0)

            if response:
                # Parse GRBL status response
                # Format: <Idle|MPos:0.000,0.000,0.000|WPos:0.000,0.000,0.000>
                status = {}

                # Extract state (Idle, Run, Hold, etc.)
                state_match = re.search(r'<([^|]+)', response)
                if state_match:
                    status['state'] = state_match.group(1)

                # Extract work position
                wpos_match = re.search(r'WPos:([\d.-]+),([\d.-]+)', response)
                if wpos_match:
                    status['x'] = float(wpos_match.group(1)) / 10.0  # Convert mm to cm
                    status['y'] = float(wpos_match.group(2)) / 10.0  # Convert mm to cm

                return status

            return None

        except Exception as e:
            self.logger.error(f"Error getting status: {e}", category="grbl")
            return None

    def stop(self) -> bool:
        """
        Emergency stop (feed hold)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            # Send feed hold character (!)
            self.serial_connection.write(b"!")
            self.logger.info("EMERGENCY STOP activated", category="grbl")
            return True
        except Exception as e:
            self.logger.error(f"Error sending stop: {e}", category="grbl")
            return False

    def resume(self) -> bool:
        """
        Resume from feed hold

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            # Send cycle start character (~)
            self.serial_connection.write(b"~")
            self.logger.info("Resuming operation", category="grbl")
            return True
        except Exception as e:
            self.logger.error(f"Error sending resume: {e}", category="grbl")
            return False

    def reset(self) -> bool:
        """
        Soft reset GRBL

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            # Send reset character (Ctrl-X)
            self.serial_connection.write(b"\x18")
            time.sleep(self._grbl_reset_delay)  # Wait for reset
            self.logger.success("GRBL reset", category="grbl")
            return True
        except Exception as e:
            self.logger.error(f"Error sending reset: {e}", category="grbl")
            return False

    def read_door_switch(self) -> Optional[bool]:
        """
        Read door limit switch state from Arduino digital pin

        Returns:
            True if door is closed (switch activated), False if open, None on error
        """
        if not self.is_connected:
            self.logger.debug("Not connected to Arduino", category="grbl")
            return None

        if not self.door_switch_config:
            self.logger.debug("Door switch not configured", category="grbl")
            return None

        try:
            # Send custom M-code to read digital pin
            # This requires custom firmware on Arduino to support reading digital pins
            # Format: M119 for GRBL built-in limit switch status
            door_switch_timeout = self.grbl_config.get("door_switch_read_timeout", 1.0)
            response = self._send_command("M119", timeout=door_switch_timeout)

            if response:
                # Parse door switch status from response
                # GRBL M119 format: "Door:X" where X is 0 (open) or 1 (closed)
                door_match = re.search(r'Door:(\d)', response, re.IGNORECASE)
                if door_match:
                    state = int(door_match.group(1))
                    return bool(state)  # True = closed, False = open

                # Alternative: Check for "Door" keyword in response
                if "door" in response.lower():
                    return "closed" in response.lower() or "triggered" in response.lower()

            # If no specific door status, assume open (safe default)
            return False

        except Exception as e:
            self.logger.error(f"Error reading door switch: {e}", category="grbl")
            return None

    def get_door_switch_state(self) -> Optional[bool]:
        """
        Get door limit switch state

        Returns:
            True if door is closed, False if open, None on error
        """
        return self.read_door_switch()

    def disconnect(self):
        """
        Disconnect from GRBL
        """
        if self.serial_connection:
            try:
                self.serial_connection.close()
                self.is_connected = False
                self.logger.info("Disconnected from GRBL", category="grbl")
            except Exception as e:
                self.logger.error(f"Error disconnecting: {e}", category="grbl")


if __name__ == "__main__":
    """Test GRBL interface"""
    test_logger = get_logger()
    test_logger.info("="*60, category="grbl")
    test_logger.info("Arduino GRBL Interface Test", category="grbl")
    test_logger.info("="*60, category="grbl")

    # Create GRBL interface
    grbl = ArduinoGRBL()

    # Try to connect
    if grbl.connect():
        test_logger.info("Testing motor movements...", category="grbl")

        # Test movement sequence
        test_logger.info("1. Moving to (10cm, 10cm)", category="grbl")
        grbl.move_to(10, 10)
        time.sleep(2)

        test_logger.info("2. Moving to (20cm, 15cm)", category="grbl")
        grbl.move_to(20, 15)
        time.sleep(2)

        test_logger.info("3. Moving back to origin", category="grbl")
        grbl.move_to(0, 0)
        time.sleep(2)

        # Get status
        test_logger.info("Getting status...", category="grbl")
        status = grbl.get_status()
        if status:
            test_logger.info(f"State: {status.get('state', 'Unknown')}", category="grbl")
            test_logger.info(f"Position: X={status.get('x', 0):.2f}cm, Y={status.get('y', 0):.2f}cm", category="grbl")

        # Disconnect
        grbl.disconnect()
    else:
        test_logger.error("Failed to connect to GRBL", category="grbl")
        test_logger.info("Note: This is expected if Arduino is not connected.", category="grbl")
        test_logger.info("The interface will work correctly when connected to real hardware.", category="grbl")

    test_logger.info("="*60, category="grbl")
    test_logger.info("Test completed", category="grbl")
    test_logger.info("="*60, category="grbl")

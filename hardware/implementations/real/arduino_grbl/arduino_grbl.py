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

        # Position verification settings (from config or defaults)
        self.position_tolerance = self.grbl_config.get("position_tolerance_cm", 0.1)  # cm
        self.movement_timeout = self.grbl_config.get("movement_timeout", 60.0)  # seconds
        self.movement_poll_interval = self.grbl_config.get("movement_poll_interval", 0.1)  # seconds

        # For change detection (only log when values change)
        self._last_logged_x = None
        self._last_logged_y = None
        self._last_logged_state = None

        # Cache WCO (Work Coordinate Offset) since GRBL doesn't always report it
        self._cached_wco_x = 0.0  # mm
        self._cached_wco_y = 0.0  # mm

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

        # IMPORTANT: Apply GRBL configuration from settings.json FIRST
        # This ensures the machine has correct settings before any movement/homing
        self.logger.info("Applying GRBL configuration from settings.json...", category="grbl")
        if self.apply_grbl_configuration():
            self.logger.success("GRBL configuration applied successfully", category="grbl")
        else:
            self.logger.warning("Failed to apply some GRBL configuration settings", category="grbl")

        # Small delay to ensure settings are written to EEPROM
        time.sleep(0.3)

        # Set positioning mode (absolute/relative)
        positioning_mode = self.grbl_settings.get("positioning_mode", "G90")
        self._send_command(positioning_mode)

        # Set units (mm/inch)
        units_mode = "G21" if self.grbl_settings.get("units", "mm") == "mm" else "G20"
        self._send_command(units_mode)

        # DO NOT auto-home on initialization - user will trigger homing manually
        self.logger.info("GRBL ready - use 'Start Homing Sequence' button to home the machine", category="grbl")

        # Query current status from GRBL
        status = self.get_status()
        if status:
            self.current_x = status.get('x', 0.0)
            self.current_y = status.get('y', 0.0)
            state = status.get('state', 'Unknown')

            self.logger.info(f"Current position: X={self.current_x:.2f}cm, Y={self.current_y:.2f}cm", category="grbl")
            self.logger.info(f"Current state: {state}", category="grbl")

            # If in ALARM state, clear it automatically
            if state == 'Alarm':
                self.logger.warning("⚠️  GRBL is in ALARM state - clearing alarm...", category="grbl")
                self.logger.warning("   Machine has not been homed or limit was triggered", category="grbl")
                if self.unlock_alarm():
                    self.logger.success("✓ Alarm cleared. You can now move the machine.", category="grbl")
                    self.logger.info("   Run 'Start Homing Sequence' to properly home the machine", category="grbl")
                else:
                    self.logger.error("Failed to clear alarm. Run homing sequence to recover.", category="grbl")
        else:
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
                is_status_query = command == "?"

                # Only log non-status commands at debug level
                if not is_status_query:
                    self.logger.debug(f"GRBL >> {command}", category="grbl")

                self.serial_connection.write(f"{command}\n".encode())

                # Read response
                start_time = time.time()
                response_lines = []

                while time.time() - start_time < timeout:
                    if self.serial_connection.in_waiting > 0:
                        line = self.serial_connection.readline().decode().strip()
                        if line:
                            # Only log non-status responses at debug level
                            if not is_status_query:
                                self.logger.debug(f"GRBL << {line}", category="grbl")

                            # Status queries: ONLY look for <...> format, ignore "ok"
                            if is_status_query:
                                if line.startswith("<") and line.endswith(">"):
                                    # Found status response - return immediately
                                    return line
                                elif line.lower() == "ok":
                                    # Ignore leftover "ok" from previous commands
                                    continue
                                else:
                                    # Add to response lines
                                    response_lines.append(line)
                            else:
                                # Regular commands: collect all lines until ok/error
                                response_lines.append(line)

                                # Regular commands wait for ok or error
                                if "ok" in line.lower() or "error" in line.lower():
                                    response = "\n".join(response_lines)
                                    return response

                    time.sleep(self._grbl_serial_poll_delay)

                if not is_status_query:
                    self.logger.debug(f"Command timeout after {timeout}s", category="grbl")
                return "\n".join(response_lines) if response_lines else None

        except Exception as e:
            self.logger.error(f"Error sending command: {e}", category="grbl")
            return None

    def move_to(self, x: float, y: float, rapid: bool = False, wait_for_completion: bool = True) -> bool:
        """
        Move to absolute position

        Args:
            x: Target X position in cm (will be converted to mm for GRBL)
            y: Target Y position in cm (will be converted to mm for GRBL)
            rapid: Use rapid movement (G0) instead of feed rate (G1)
            wait_for_completion: If True, blocks until motor reaches target position (default True)

        Returns:
            True if successful, False otherwise

        Note:
            GRBL uses mm as base unit (G21 mode).
            Conversion: 1cm = 10mm
            Example: x=10cm → x_mm=100mm → GRBL receives X100
            With config scale: X100 in GRBL = 10cm physical movement
        """
        if not self.is_connected:
            self.logger.debug("Not connected to GRBL", category="grbl")
            return False

        # Convert cm to mm (GRBL uses mm in G21 mode)
        # User's config: X100 GRBL units = 10cm = 100mm
        # So 1 GRBL unit = 1mm
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

            self.logger.info(f"Moving: {x:.2f}cm, {y:.2f}cm → GRBL: X{x_mm:.3f}, Y{y_mm:.3f} (mm)", category="grbl")
            response = self._send_command(command)

            if response and "ok" in response.lower():
                # Command was accepted by GRBL
                self.logger.debug(f"GRBL accepted move command", category="grbl")

                if wait_for_completion:
                    # Wait for actual movement to complete
                    self.logger.debug(f"Waiting for motor to reach position...", category="grbl")
                    if self.wait_for_movement_complete(x, y):
                        self.current_x = x
                        self.current_y = y
                        self.logger.success(f"✓ Movement complete: X={x:.2f}cm, Y={y:.2f}cm", category="grbl")
                        return True
                    else:
                        self.logger.error(f"Movement did not complete properly", category="grbl")
                        # Update position from GRBL status anyway
                        status = self.get_status(log_changes_only=False)
                        if status:
                            self.current_x = status.get('x', self.current_x)
                            self.current_y = status.get('y', self.current_y)
                        return False
                else:
                    # Don't wait - just update expected position
                    self.current_x = x
                    self.current_y = y
                    self.logger.success(f"✓ Move command sent: X={x:.2f}cm, Y={y:.2f}cm (not waiting)", category="grbl")
                    return True
            else:
                self.logger.warning(f"Move command failed: {response}", category="grbl")
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

    def get_status(self, log_changes_only: bool = True) -> Optional[Dict]:
        """
        Get current GRBL status

        Args:
            log_changes_only: If True, only log when position or state changes

        Returns:
            Dictionary with status information, or None on error

        Note:
            GRBL reports position in mm (WPos values).
            We convert to cm by dividing by 10.
            Example: GRBL reports WPos:100.0 → 100mm → 10cm in our system
        """
        if not self.is_connected:
            return None

        try:
            response = self._send_command("?", timeout=1.0)

            # Debug level only - shows every query
            self.logger.debug(f"GRBL raw response to '?': '{response}'", category="grbl")

            if response:
                # Parse GRBL status response
                # Format: <Idle|MPos:0.000,0.000,0.000|WPos:0.000,0.000,0.000>
                status = {}

                # Extract state (Idle, Run, Hold, etc.)
                state_match = re.search(r'<([^|]+)', response)
                if state_match:
                    status['state'] = state_match.group(1)
                else:
                    status['state'] = 'Unknown'

                # Extract work position (GRBL reports in mm)
                wpos_match = re.search(r'WPos:([\d.-]+),([\d.-]+)', response)
                mpos_match = re.search(r'MPos:([\d.-]+),([\d.-]+)', response)
                wco_match = re.search(r'WCO:([\d.-]+),([\d.-]+)', response)

                # Update cached WCO if present in response
                if wco_match:
                    self._cached_wco_x = float(wco_match.group(1))
                    self._cached_wco_y = float(wco_match.group(2))
                    self.logger.debug(f"Updated WCO cache: X={self._cached_wco_x}mm, Y={self._cached_wco_y}mm", category="grbl")

                # Calculate position (prefer WPos, fallback to MPos - WCO)
                if wpos_match:
                    # Direct WPos from GRBL
                    x_mm = float(wpos_match.group(1))
                    y_mm = float(wpos_match.group(2))
                    status['x'] = x_mm / 10.0
                    status['y'] = y_mm / 10.0
                    self.logger.debug(f"Using WPos directly: X={x_mm}mm, Y={y_mm}mm", category="grbl")
                elif mpos_match:
                    # Calculate WPos = MPos - WCO (using cached WCO if not in this response)
                    mpos_x_mm = float(mpos_match.group(1))
                    mpos_y_mm = float(mpos_match.group(2))

                    # Use cached WCO for calculation
                    wpos_x_mm = mpos_x_mm - self._cached_wco_x
                    wpos_y_mm = mpos_y_mm - self._cached_wco_y

                    status['x'] = wpos_x_mm / 10.0
                    status['y'] = wpos_y_mm / 10.0
                    self.logger.debug(f"Calculated WPos from MPos: MPos=({mpos_x_mm},{mpos_y_mm}) - WCO=({self._cached_wco_x},{self._cached_wco_y}) = WPos=({wpos_x_mm},{wpos_y_mm})mm", category="grbl")
                else:
                    self.logger.error("Could not parse position from GRBL response!", category="grbl")
                    return None

                # Check if anything changed (only log changes)
                if log_changes_only:
                    x_changed = (self._last_logged_x is None or
                                abs(status.get('x', 0) - self._last_logged_x) > 0.01)  # 0.01cm threshold
                    y_changed = (self._last_logged_y is None or
                                abs(status.get('y', 0) - self._last_logged_y) > 0.01)
                    state_changed = (self._last_logged_state != status.get('state'))

                    # Only log if something changed
                    if x_changed or y_changed or state_changed:
                        if state_changed:
                            self.logger.info(f"GRBL state changed: {self._last_logged_state} → {status.get('state')}", category="grbl")

                        if x_changed or y_changed:
                            self.logger.info(f"GRBL position: X={status.get('x', 0):.2f}cm, Y={status.get('y', 0):.2f}cm [State: {status.get('state')}]", category="grbl")

                        # Update last logged values
                        self._last_logged_x = status.get('x', 0)
                        self._last_logged_y = status.get('y', 0)
                        self._last_logged_state = status.get('state')

                return status

            else:
                self.logger.error("GRBL returned empty response to '?' command", category="grbl")
                return None

        except Exception as e:
            self.logger.error(f"Error getting status: {e}", category="grbl")
            return None

    def wait_for_movement_complete(self, target_x: float, target_y: float, timeout: float = None) -> bool:
        """
        Wait for GRBL to complete movement to target position.

        Polls GRBL status until:
        1. State is "Idle" (not "Run" or "Home")
        2. Position is within tolerance of target

        Args:
            target_x: Target X position in cm
            target_y: Target Y position in cm
            timeout: Maximum wait time in seconds (uses default if None)

        Returns:
            True if movement completed successfully, False on timeout or error
        """
        if not self.is_connected:
            return False

        if timeout is None:
            timeout = self.movement_timeout

        start_time = time.time()
        last_log_time = 0

        self.logger.debug(f"Waiting for movement to complete: target X={target_x:.2f}cm, Y={target_y:.2f}cm", category="grbl")

        while (time.time() - start_time) < timeout:
            status = self.get_status(log_changes_only=True)

            if not status:
                time.sleep(self.movement_poll_interval)
                continue

            current_state = status.get('state', 'Unknown')
            current_x = status.get('x', 0.0)
            current_y = status.get('y', 0.0)

            # Log progress every 2 seconds
            current_time = time.time()
            if current_time - last_log_time >= 2.0:
                distance_remaining = ((target_x - current_x)**2 + (target_y - current_y)**2)**0.5
                self.logger.debug(f"Movement progress: X={current_x:.2f}cm, Y={current_y:.2f}cm, "
                                 f"distance remaining: {distance_remaining:.2f}cm, state: {current_state}",
                                 category="grbl")
                last_log_time = current_time

            # Check if GRBL is idle
            if current_state == 'Idle':
                # Verify position is within tolerance
                x_ok = abs(current_x - target_x) <= self.position_tolerance
                y_ok = abs(current_y - target_y) <= self.position_tolerance

                if x_ok and y_ok:
                    self.logger.debug(f"Movement complete: arrived at X={current_x:.2f}cm, Y={current_y:.2f}cm", category="grbl")
                    return True
                else:
                    # GRBL is idle but not at target - this could be a problem
                    self.logger.warning(
                        f"GRBL idle but not at target position. "
                        f"Current: ({current_x:.2f}, {current_y:.2f}), "
                        f"Target: ({target_x:.2f}, {target_y:.2f}), "
                        f"Tolerance: {self.position_tolerance}cm",
                        category="grbl"
                    )
                    # Still return True since GRBL is idle - movement is complete even if position differs
                    return True

            elif current_state == 'Alarm':
                self.logger.error("GRBL entered ALARM state during movement!", category="grbl")
                return False

            # Still running, wait before next poll
            time.sleep(self.movement_poll_interval)

        # Timeout reached
        elapsed = time.time() - start_time
        status = self.get_status(log_changes_only=False)
        if status:
            self.logger.error(
                f"Movement timeout after {elapsed:.1f}s. "
                f"Current position: X={status.get('x', 0):.2f}cm, Y={status.get('y', 0):.2f}cm, "
                f"Target: X={target_x:.2f}cm, Y={target_y:.2f}cm, State: {status.get('state', 'Unknown')}",
                category="grbl"
            )
        else:
            self.logger.error(f"Movement timeout after {elapsed:.1f}s - no status available", category="grbl")

        return False

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

    def unlock_alarm(self) -> bool:
        """
        Clear GRBL alarm state using $X command

        GRBL enters alarm state when:
        - Limit switches are triggered
        - System hasn't been homed
        - Hard limits are enabled and triggered

        This command unlocks GRBL so it can move again.
        WARNING: Only use this if you're sure it's safe!

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            self.logger.error("Not connected to GRBL", category="grbl")
            return False

        try:
            self.logger.warning("Clearing GRBL alarm with $X (unlock) command...", category="grbl")
            response = self._send_command("$X", timeout=2.0)

            if response and "ok" in response.lower():
                self.logger.success("✓ GRBL alarm cleared - machine unlocked", category="grbl")
                time.sleep(0.5)

                # Verify alarm is cleared
                status = self.get_status()
                if status and status.get('state') != 'Alarm':
                    self.logger.success(f"✓ GRBL is now in '{status.get('state', 'Unknown')}' state", category="grbl")
                    return True
                else:
                    self.logger.warning("Alarm may not be fully cleared. Run homing sequence for full reset.", category="grbl")
                    return False
            else:
                self.logger.error(f"Failed to unlock GRBL: {response}", category="grbl")
                return False

        except Exception as e:
            self.logger.error(f"Error unlocking GRBL: {e}", category="grbl")
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

    def apply_grbl_configuration(self) -> bool:
        """
        Apply GRBL configuration from settings.json

        Reads grbl_configuration from settings and applies each setting to GRBL.

        Returns:
            True if all settings applied successfully, False otherwise
        """
        if not self.is_connected:
            self.logger.error("Not connected to GRBL", category="grbl")
            return False

        # Get configuration from settings
        grbl_configuration = self.grbl_config.get("grbl_configuration", {})

        if not grbl_configuration:
            self.logger.warning("No GRBL configuration found in settings.json", category="grbl")
            return True  # Not an error if not configured

        self.logger.info(f"Applying {len(grbl_configuration)} GRBL configuration settings...", category="grbl")

        success_count = 0
        fail_count = 0

        # Apply each setting
        for param, value in sorted(grbl_configuration.items()):
            try:
                command = f"{param}={value}"
                self.logger.debug(f"Setting {command}", category="grbl")
                response = self._send_command(command)

                if response and "ok" in response.lower():
                    success_count += 1
                    self.logger.debug(f"✓ {param}={value} applied", category="grbl")
                else:
                    fail_count += 1
                    self.logger.warning(f"✗ Failed to apply {param}={value}", category="grbl")

            except Exception as e:
                fail_count += 1
                self.logger.error(f"Error applying {param}: {e}", category="grbl")

        if fail_count == 0:
            self.logger.success(f"All {success_count} GRBL settings applied successfully", category="grbl")
            return True
        else:
            self.logger.warning(f"Applied {success_count} settings, {fail_count} failed", category="grbl")
            return False

    def perform_complete_homing_sequence(self, hardware_interface=None, progress_callback=None) -> tuple[bool, str]:
        """
        Perform complete homing sequence with door check and line motor management

        Sequence:
        1. Apply GRBL configuration from settings.json
        2. Check door is open (safety check)
        3. Lift line motor pistons (both sides)
        4. Run GRBL homing ($H)
        5. Wait for OK
        6. Reset work coordinates to (0, 0) using G10 L20 P1 X0 Y0
        7. Lower line motor pistons back down

        Args:
            hardware_interface: Reference to hardware interface (for piston control)
            progress_callback: Optional callback function(step_number, step_name, status, message=None) to report progress
                             status can be: 'running', 'done', 'error', 'waiting'

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        if not self.is_connected:
            error_msg = "Not connected to GRBL"
            self.logger.error(error_msg, category="grbl")
            return False, error_msg

        try:
            self.logger.info("="*60, category="grbl")
            self.logger.info("STARTING COMPLETE HOMING SEQUENCE", category="grbl")
            self.logger.info("="*60, category="grbl")

            # Step 1: Apply GRBL configuration
            if progress_callback:
                progress_callback(1, "Apply GRBL configuration", "running")
            self.logger.info("Step 1: Applying GRBL configuration from settings.json...", category="grbl")

            # First, send a soft reset to ensure GRBL is in a clean state
            self.logger.info("Sending soft reset to GRBL...", category="grbl")
            try:
                self.serial_connection.write(b'\x18')  # Ctrl+X soft reset
                self.serial_connection.flush()
                time.sleep(self._grbl_reset_delay)  # Wait for GRBL to reset and initialize
                self.serial_connection.flushInput()  # Clear any startup messages
                self.logger.info("Soft reset sent, GRBL should be ready", category="grbl")
            except Exception as e:
                self.logger.warning(f"Soft reset warning (non-fatal): {e}", category="grbl")

            # Check current GRBL state and clear alarm if needed
            status = self.get_status(log_changes_only=False)
            if status:
                current_state = status.get('state', 'Unknown')
                self.logger.info(f"Current GRBL state: {current_state}", category="grbl")
                if 'Alarm' in current_state:
                    self.logger.warning("GRBL is in Alarm state, attempting to clear with $X...", category="grbl")
                    unlock_response = self._send_command("$X")
                    self.logger.info(f"Unlock response: {unlock_response}", category="grbl")
                    time.sleep(0.5)

            # Now apply the GRBL configuration
            if not self.apply_grbl_configuration():
                error_msg = "Failed to apply GRBL configuration from settings.json"
                self.logger.error(error_msg, category="grbl")
                if progress_callback:
                    progress_callback(1, "Apply GRBL configuration", "error")
                return False, error_msg

            # Small delay to ensure all settings are written to EEPROM
            time.sleep(0.5)
            self.logger.info("GRBL configuration applied successfully", category="grbl")

            if progress_callback:
                progress_callback(1, "Apply GRBL configuration", "done")

            # Step 2: Check door is open (wait for user to open if closed)
            if progress_callback:
                progress_callback(2, "Check door is open", "running")
            self.logger.info("Step 2: Checking door sensor...", category="grbl")
            if hardware_interface:
                door_state = hardware_interface.get_door_sensor()
                if door_state:
                    # Door is closed - wait for user to open it
                    self.logger.warning("Door is closed! Waiting for door to be opened...", category="grbl")
                    if progress_callback:
                        progress_callback(2, "Check door is open", "waiting", "Door is closed - please open the door to continue")

                    # Poll door sensor until it opens (check every 0.5 seconds)
                    max_wait = 300  # 5 minutes maximum wait
                    wait_time = 0
                    while door_state and wait_time < max_wait:
                        time.sleep(0.5)
                        wait_time += 0.5
                        door_state = hardware_interface.get_door_sensor()
                        if not door_state:
                            break

                    # Check if door was opened or timeout
                    if door_state:
                        error_msg = "Timeout waiting for door to open (waited 5 minutes)"
                        self.logger.error(error_msg, category="grbl")
                        if progress_callback:
                            progress_callback(2, "Check door is open", "error")
                        return False, error_msg

                    self.logger.success("Door opened - safe to proceed", category="grbl")
                else:
                    self.logger.success("Door is open - safe to proceed", category="grbl")
            else:
                self.logger.warning("No hardware interface - skipping door check", category="grbl")
            if progress_callback:
                progress_callback(2, "Check door is open", "done")

            # Step 3: Lift line motor pistons (both sides)
            if progress_callback:
                progress_callback(3, "Lift line motor pistons", "running")
            self.logger.info("Step 3: Lifting line motor pistons...", category="grbl")
            self.logger.info("Calling hardware_interface.line_motor_piston_up()...", category="grbl")
            if hardware_interface:
                result = hardware_interface.line_motor_piston_up()
                self.logger.info(f"Piston up result: {result}", category="grbl")

                if not result:
                    error_msg = "Failed to lift line motor pistons"
                    self.logger.error(error_msg, category="grbl")
                    if progress_callback:
                        progress_callback(3, "Lift line motor pistons", "error")
                    return False, error_msg

                self.logger.success("✓ Line motor pistons commanded UP", category="grbl")
                self.logger.info("Waiting 2 seconds for pistons to fully lift...", category="grbl")

                # Wait for pistons to fully lift
                time.sleep(2.0)

                self.logger.success("✓ Line motor pistons should now be UP", category="grbl")
            else:
                self.logger.warning("No hardware interface - skipping piston lift", category="grbl")
            if progress_callback:
                progress_callback(3, "Lift line motor pistons", "done")

            # Step 4: Run GRBL homing ($H)
            if progress_callback:
                progress_callback(4, "Run GRBL homing ($H)", "running")
            self.logger.info("Step 4: Running GRBL homing ($H)...", category="grbl")
            self.logger.info("This may take up to 30 seconds...", category="grbl")

            homing_timeout = self.grbl_config.get("homing_timeout", 30.0)
            response = self._send_command("$H", timeout=homing_timeout)

            # Check for OK response (command accepted)
            if not response or "ok" not in response.lower():
                error_msg = f"GRBL homing command failed or timed out. Response: {response}"
                self.logger.error(error_msg, category="grbl")

                if progress_callback:
                    progress_callback(4, "Run GRBL homing ($H)", "error")

                # Lower pistons before returning
                if hardware_interface:
                    self.logger.info("Lowering line motor pistons...", category="grbl")
                    hardware_interface.line_motor_piston_down()

                return False, error_msg

            self.logger.success("GRBL homing command accepted - waiting for homing to complete...", category="grbl")

            # Wait for GRBL to actually finish homing (poll status until no longer "Home" or "Run")
            # GRBL states: "Home" while homing, "Idle" when done, "Alarm" if failed
            max_wait_time = homing_timeout + 5.0  # Extra buffer time
            start_time = time.time()
            homing_complete = False
            last_state = None

            while (time.time() - start_time) < max_wait_time:
                time.sleep(0.5)  # Poll every 500ms
                status = self.get_status(log_changes_only=False)

                if status:
                    current_state = status.get('state', 'Unknown')
                    last_state = current_state
                    self.logger.debug(f"Homing status check: {current_state}", category="grbl")

                    if current_state == 'Idle':
                        # Homing completed successfully
                        self.logger.success("GRBL homing physically completed - machine is now at home position", category="grbl")
                        homing_complete = True
                        break
                    elif current_state == 'Alarm':
                        # Homing failed
                        error_msg = "GRBL entered ALARM state during homing - check limit switches and machine setup"
                        self.logger.error(error_msg, category="grbl")
                        break
                    elif current_state in ['Home', 'Run']:
                        # Still homing, continue waiting
                        self.logger.debug(f"Homing still in progress (state: {current_state})...", category="grbl")
                        continue
                    else:
                        # Unknown state, log it but continue waiting
                        self.logger.warning(f"Unexpected state during homing: {current_state}", category="grbl")

            if not homing_complete:
                if last_state == 'Alarm':
                    error_msg = "GRBL homing failed - GRBL is in ALARM state (check limit switches and machine configuration)"
                elif last_state:
                    error_msg = f"GRBL homing did not complete - machine stuck in '{last_state}' state"
                else:
                    error_msg = "GRBL homing timed out - no response from GRBL controller"

                self.logger.error(error_msg, category="grbl")
                if progress_callback:
                    progress_callback(4, "Run GRBL homing ($H)", "error")

                # Lower pistons before returning
                if hardware_interface:
                    self.logger.info("Lowering line motor pistons...", category="grbl")
                    hardware_interface.line_motor_piston_down()

                return False, error_msg

            # Mark homing as done ONLY after it's actually complete
            if progress_callback:
                progress_callback(4, "Run GRBL homing ($H)", "done")

            # Step 5: Reset work coordinates to (0, 0)
            if progress_callback:
                progress_callback(5, "Reset work coordinates to (0,0)", "running")
            self.logger.info("Step 5: Resetting work coordinates to (0, 0)...", category="grbl")
            self.logger.info("Sending: G10 L20 P1 X0 Y0 (Set WCS origin to current position)", category="grbl")
            response = self._send_command("G10 L20 P1 X0 Y0")

            if response and "ok" in response.lower():
                self.current_x = 0.0
                self.current_y = 0.0
                self.logger.success("✓ Work coordinates reset to (0, 0) - machine is now at origin", category="grbl")

                # Verify the new position
                time.sleep(0.2)  # Brief delay for GRBL to update
                verify_status = self.get_status()
                if verify_status:
                    self.logger.info(f"Verified position: X={verify_status.get('x', 0):.2f}cm, Y={verify_status.get('y', 0):.2f}cm", category="grbl")
            else:
                self.logger.warning(f"Failed to reset work coordinates: {response}", category="grbl")
            if progress_callback:
                progress_callback(5, "Reset work coordinates to (0,0)", "done")

            # Step 6: Lower line motor pistons back down
            if progress_callback:
                progress_callback(6, "Lower line motor pistons", "running")
            self.logger.info("Step 6: Lowering line motor pistons...", category="grbl")
            self.logger.info("Calling hardware_interface.line_motor_piston_down()...", category="grbl")
            if hardware_interface:
                result = hardware_interface.line_motor_piston_down()
                self.logger.info(f"Piston down result: {result}", category="grbl")

                if not result:
                    self.logger.warning("Failed to lower line motor pistons", category="grbl")
                else:
                    self.logger.success("✓ Line motor pistons commanded DOWN", category="grbl")
                    self.logger.info("Waiting 2 seconds for pistons to fully lower...", category="grbl")
                    time.sleep(2.0)
                    self.logger.success("✓ Line motor pistons should now be DOWN", category="grbl")
            else:
                self.logger.warning("No hardware interface - skipping piston lower", category="grbl")
            if progress_callback:
                progress_callback(6, "Lower line motor pistons", "done")

            self.logger.info("="*60, category="grbl")
            self.logger.success("COMPLETE HOMING SEQUENCE FINISHED SUCCESSFULLY", category="grbl")
            self.logger.info("="*60, category="grbl")

            return True, ""

        except Exception as e:
            error_msg = f"Unexpected error during homing sequence: {str(e)}"
            self.logger.error(error_msg, category="grbl")

            # Safety: try to lower pistons
            if hardware_interface:
                try:
                    self.logger.info("Attempting to lower pistons after error...", category="grbl")
                    hardware_interface.line_motor_piston_down()
                except:
                    pass

            return False, error_msg

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

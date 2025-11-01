#!/usr/bin/env python3

"""
Arduino GRBL Interface
======================

Handles G-code communication with Arduino running GRBL firmware.
Controls X and Y motors via serial communication.
"""

import json
import serial
import time
import re
from typing import Optional, Tuple, Dict
from threading import Lock


class ArduinoGRBL:
    """
    Interface for Arduino GRBL motor control via G-code
    """

    def __init__(self, config_path: str = "settings.json"):
        """
        Initialize GRBL interface

        Args:
            config_path: Path to settings.json configuration file
        """
        self.config = self._load_config(config_path)
        self.grbl_config = self.config.get("hardware_config", {}).get("arduino_grbl", {})

        self.serial_port = self.grbl_config.get("serial_port", "/dev/ttyACM0")
        self.baud_rate = self.grbl_config.get("baud_rate", 115200)
        self.connection_timeout = self.grbl_config.get("connection_timeout", 5.0)
        self.command_timeout = self.grbl_config.get("command_timeout", 10.0)

        self.grbl_settings = self.grbl_config.get("grbl_settings", {})
        self.feed_rate = self.grbl_settings.get("feed_rate", 1000)  # mm/min
        self.rapid_rate = self.grbl_settings.get("rapid_rate", 3000)  # mm/min

        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        self.command_lock = Lock()  # Thread safety for serial commands

        self.current_x = 0.0  # Current X position in mm
        self.current_y = 0.0  # Current Y position in mm

        print(f"\n{'='*60}")
        print("Arduino GRBL Configuration")
        print(f"{'='*60}")
        print(f"Serial Port: {self.serial_port}")
        print(f"Baud Rate: {self.baud_rate}")
        print(f"Feed Rate: {self.feed_rate} mm/min")
        print(f"Rapid Rate: {self.rapid_rate} mm/min")
        print(f"{'='*60}\n")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from settings.json"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading config: {e}")
            return {}

    def connect(self) -> bool:
        """
        Connect to Arduino GRBL via serial

        Returns:
            True if connection successful, False otherwise
        """
        if self.is_connected:
            print("Already connected to GRBL")
            return True

        try:
            print(f"Connecting to GRBL on {self.serial_port} at {self.baud_rate} baud...")

            # Open serial connection
            self.serial_connection = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=self.connection_timeout
            )

            # Wait for GRBL to initialize (it sends startup message)
            time.sleep(2)

            # Flush any startup messages
            self.serial_connection.flushInput()

            # Send a simple command to verify connection
            response = self._send_command("?")  # Status query

            if response:
                self.is_connected = True
                print("✓ Connected to GRBL successfully")

                # Initialize GRBL
                self._initialize_grbl()
                return True
            else:
                print("✗ No response from GRBL")
                self.disconnect()
                return False

        except serial.SerialException as e:
            print(f"✗ Serial connection error: {e}")
            return False
        except Exception as e:
            print(f"✗ Error connecting to GRBL: {e}")
            return False

    def _initialize_grbl(self):
        """Initialize GRBL with required settings"""
        print("Initializing GRBL...")

        # Set to absolute positioning mode
        self._send_command("G90")

        # Set units to mm
        self._send_command("G21")

        # Home the machine (if homing is enabled)
        print("Homing machine... (This may take a few seconds)")
        response = self._send_command("$H", timeout=30.0)
        if response and "ok" in response.lower():
            print("✓ Homing completed")
        else:
            print("⚠ Homing may have failed or is not configured")

        # Reset work coordinates to (0, 0)
        self._send_command("G92 X0 Y0")

        self.current_x = 0.0
        self.current_y = 0.0

        print("✓ GRBL initialized")

    def _send_command(self, command: str, timeout: Optional[float] = None) -> Optional[str]:
        """
        Send G-code command to GRBL and wait for response

        Args:
            command: G-code command to send
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            Response from GRBL, or None on error
        """
        if not self.is_connected or not self.serial_connection:
            print("Not connected to GRBL")
            return None

        if timeout is None:
            timeout = self.command_timeout

        try:
            with self.command_lock:
                # Send command
                command = command.strip()
                print(f"GRBL >> {command}")
                self.serial_connection.write(f"{command}\n".encode())

                # Read response
                start_time = time.time()
                response_lines = []

                while time.time() - start_time < timeout:
                    if self.serial_connection.in_waiting > 0:
                        line = self.serial_connection.readline().decode().strip()
                        if line:
                            response_lines.append(line)
                            print(f"GRBL << {line}")

                            # Check for completion indicators
                            if "ok" in line.lower() or "error" in line.lower():
                                response = "\n".join(response_lines)
                                return response

                    time.sleep(0.01)

                print(f"⚠ Command timeout after {timeout}s")
                return "\n".join(response_lines) if response_lines else None

        except Exception as e:
            print(f"Error sending command: {e}")
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
            print("Not connected to GRBL")
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
                print(f"✓ Moved to X={x:.2f}cm, Y={y:.2f}cm")
                return True
            else:
                print(f"✗ Move command failed")
                return False

        except Exception as e:
            print(f"Error moving to position: {e}")
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
            print("Not connected to GRBL")
            return False

        try:
            print("Homing machine...")
            response = self._send_command("$H", timeout=30.0)

            if response and "ok" in response.lower():
                self.current_x = 0.0
                self.current_y = 0.0
                print("✓ Homing completed")
                return True
            else:
                print("✗ Homing failed")
                return False

        except Exception as e:
            print(f"Error homing: {e}")
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
            print(f"Error getting status: {e}")
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
            print("⚠ EMERGENCY STOP activated")
            return True
        except Exception as e:
            print(f"Error sending stop: {e}")
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
            print("✓ Resuming operation")
            return True
        except Exception as e:
            print(f"Error sending resume: {e}")
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
            time.sleep(2)  # Wait for reset
            print("✓ GRBL reset")
            return True
        except Exception as e:
            print(f"Error sending reset: {e}")
            return False

    def disconnect(self):
        """
        Disconnect from GRBL
        """
        if self.serial_connection:
            try:
                self.serial_connection.close()
                self.is_connected = False
                print("✓ Disconnected from GRBL")
            except Exception as e:
                print(f"Error disconnecting: {e}")


if __name__ == "__main__":
    """Test GRBL interface"""
    print("\n" + "="*60)
    print("Arduino GRBL Interface Test")
    print("="*60 + "\n")

    # Create GRBL interface
    grbl = ArduinoGRBL()

    # Try to connect
    if grbl.connect():
        print("\nTesting motor movements...")

        # Test movement sequence
        print("\n1. Moving to (10cm, 10cm)")
        grbl.move_to(10, 10)
        time.sleep(2)

        print("\n2. Moving to (20cm, 15cm)")
        grbl.move_to(20, 15)
        time.sleep(2)

        print("\n3. Moving back to origin")
        grbl.move_to(0, 0)
        time.sleep(2)

        # Get status
        print("\nGetting status...")
        status = grbl.get_status()
        if status:
            print(f"  State: {status.get('state', 'Unknown')}")
            print(f"  Position: X={status.get('x', 0):.2f}cm, Y={status.get('y', 0):.2f}cm")

        # Disconnect
        grbl.disconnect()
    else:
        print("✗ Failed to connect to GRBL")
        print("\nNote: This is expected if Arduino is not connected.")
        print("The interface will work correctly when connected to real hardware.")

    print("\n" + "="*60)
    print("Test completed")
    print("="*60 + "\n")

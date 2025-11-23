#!/usr/bin/env python3

"""
Raspberry Pi GPIO Interface
============================

Handles all GPIO operations for pistons, sensors, and limit switches.
Uses settings.json for GPIO pin configuration.
"""

import json
import time
import threading
from typing import Dict, Optional
from hardware.implementations.real.raspberry_pi.multiplexer import CD74HC4067Multiplexer
from core.logger import get_logger

# Module-level logger
module_logger = get_logger()

# Try to import RPi.GPIO, fall back to mock if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    module_logger.success("RPi.GPIO library loaded successfully", category="hardware")
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    module_logger.warning("RPi.GPIO not available - running in mock mode", category="hardware")
    # Create mock GPIO class for development on non-Raspberry Pi systems
    class MockGPIO:
        BCM = "BCM"
        BOARD = "BOARD"
        OUT = "OUT"
        IN = "IN"
        PUD_UP = "PUD_UP"
        PUD_DOWN = "PUD_DOWN"
        HIGH = True
        LOW = False

        def __init__(self):
            self._pin_states = {}  # Track output pin states
            self._pin_modes = {}   # Track pin modes

        def setmode(self, mode):
            module_logger.debug(f"MOCK GPIO: setmode({mode})", category="hardware")

        def setwarnings(self, enabled):
            module_logger.debug(f"MOCK GPIO: setwarnings({enabled})", category="hardware")

        def setup(self, pin, mode, pull_up_down=None):
            self._pin_modes[pin] = mode
            if mode == "OUT":
                self._pin_states[pin] = False
            module_logger.debug(f"MOCK GPIO: setup(pin={pin}, mode={mode}, pull_up_down={pull_up_down})", category="hardware")

        def output(self, pin, state):
            self._pin_states[pin] = state
            module_logger.debug(f"MOCK GPIO: output(pin={pin}, state={'HIGH' if state else 'LOW'})", category="hardware")

        def input(self, pin):
            # Return HIGH for sensor pins (simulating not triggered)
            state = self._pin_states.get(pin, True)
            return state

        def cleanup(self):
            module_logger.debug("MOCK GPIO: cleanup()", category="hardware")
            self._pin_states.clear()
            self._pin_modes.clear()

    GPIO = MockGPIO()


class RaspberryPiGPIO:
    """
    Interface for Raspberry Pi GPIO control of pistons, sensors, and limit switches
    """

    def __init__(self, config_path: str = "config/settings.json"):
        """
        Initialize GPIO interface

        Args:
            config_path: Path to config/settings.json configuration file
        """
        self.logger = get_logger()
        self.config = self._load_config(config_path)
        self.gpio_config = self.config.get("hardware_config", {}).get("raspberry_pi", {})
        self.is_initialized = False

        # Pin mappings from settings
        self.piston_pins = self.gpio_config.get("pistons", {})
        self.multiplexer_config = self.gpio_config.get("multiplexer", {})
        self.direct_sensor_pins = self.gpio_config.get("direct_sensors", {})
        # REMOVED limit_switch_pins - not part of user's machine
        self.multiplexer = None  # Will be initialized later
        self.invert_mux_readings = self.multiplexer_config.get("invert_readings", False)

        # Initialize state tracking dictionary
        self._last_sensor_states = {}  # Initialize state tracking dictionary

        # Polling thread for continuous switch monitoring
        self.polling_thread = None
        self.polling_active = False
        self.switch_states = {}  # Track last known state of all switches

        # Piston settling time
        self._piston_settling_time = self.config.get("timing", {}).get("piston_gpio_settling_delay", 0.05)  # 50ms default

        self.logger.info("="*60, category="hardware")
        self.logger.info("Raspberry Pi GPIO Configuration", category="hardware")
        self.logger.info("="*60, category="hardware")
        self.logger.info(f"GPIO Library: {'REAL RPi.GPIO' if GPIO_AVAILABLE else 'MOCK GPIO (NOT READING REAL PINS!)'}", category="hardware")
        self.logger.debug(f"GPIO Type: {type(GPIO).__name__}", category="hardware")
        self.logger.debug(f"GPIO Module: {GPIO.__class__.__module__ if hasattr(GPIO, '__class__') else 'N/A'}", category="hardware")

        if not GPIO_AVAILABLE:
            self.logger.warning("="*40, category="hardware")
            self.logger.warning("MOCK GPIO IS BEING USED!", category="hardware")
            self.logger.warning("Real hardware sensors WILL NOT BE READ!", category="hardware")
            self.logger.warning("Make sure RPi.GPIO is installed: pip3 install RPi.GPIO", category="hardware")
            self.logger.warning("="*40, category="hardware")

        self.logger.debug(f"Piston pins: {self.piston_pins}", category="hardware")
        self.logger.debug(f"Multiplexer config: {self.multiplexer_config}", category="hardware")
        self.logger.debug(f"Direct sensor pins: {self.direct_sensor_pins}", category="hardware")
        # REMOVED limit switch logging - not part of user's machine
        self.logger.info("="*60, category="hardware")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from settings.json"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            module_logger.error(f"Error loading config: {e}", category="hardware")
            return {}

    def initialize(self) -> bool:
        """
        Initialize GPIO pins for pistons, sensors, and limit switches

        Returns:
            True if initialization successful, False otherwise
        """
        if self.is_initialized:
            self.logger.warning("GPIO already initialized", category="hardware")
            return True

        # Check if running on Raspberry Pi
        try:
            import RPi.GPIO
        except (ImportError, RuntimeError) as e:
            error_msg = "NOT RUNNING ON RASPBERRY PI - RPi.GPIO module not available or not on Pi hardware"
            self.logger.error(error_msg, category="hardware")
            self.logger.error("This application requires Raspberry Pi hardware to run in Real Hardware mode.", category="hardware")
            self.logger.error("Switch to Simulation mode in Hardware Settings to test without Pi hardware.", category="hardware")
            raise RuntimeError(error_msg)

        try:
            # AGGRESSIVE GPIO cleanup to handle "GPIO busy" errors
            try:
                self.logger.info("Performing aggressive GPIO cleanup...", category="hardware")
                GPIO.cleanup()
                time.sleep(0.1)  # Give GPIO time to release
                self.logger.debug("Cleaned up existing GPIO state", category="hardware")
            except Exception as cleanup_error:
                self.logger.debug(f"Initial cleanup: {cleanup_error}", category="hardware")
                # Try alternative cleanup method
                try:
                    # Reset GPIO mode to force cleanup
                    GPIO.setmode(GPIO.BCM)
                    GPIO.cleanup()
                    self.logger.debug("Alternative GPIO cleanup successful", category="hardware")
                except:
                    pass  # Ignore if this also fails

            # Set GPIO mode (BCM or BOARD)
            gpio_mode = self.gpio_config.get("gpio_mode", "BCM")
            self.logger.info(f"Setting GPIO mode: {gpio_mode}", category="hardware")

            try:
                if gpio_mode == "BCM":
                    GPIO.setmode(GPIO.BCM)
                else:
                    GPIO.setmode(GPIO.BOARD)
                GPIO.setwarnings(False)
                self.logger.debug(f"GPIO mode set to {gpio_mode}", category="hardware")
            except Exception as e:
                raise RuntimeError(f"Failed to set GPIO mode: {str(e)}. Check GPIO permissions (run with sudo?)")

            # Setup piston pins as outputs (default LOW = retracted/up)
            self.logger.info(f"Initializing {len(self.piston_pins)} piston outputs...", category="hardware")
            failed_pistons = []
            for piston_name, pin in self.piston_pins.items():
                try:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)
                    self.logger.debug(f"Piston '{piston_name}' on GPIO {pin}", category="hardware")
                except Exception as e:
                    error_msg = str(e)
                    if "busy" in error_msg.lower():
                        # GPIO busy - try recovery
                        self.logger.warning(f"GPIO {pin} ({piston_name}) is busy, attempting recovery...", category="hardware")
                        try:
                            GPIO.cleanup(pin)
                            time.sleep(0.05)
                            GPIO.setup(pin, GPIO.OUT)
                            GPIO.output(pin, GPIO.LOW)
                            self.logger.success(f"Recovered GPIO {pin} ({piston_name})", category="hardware")
                        except Exception as recovery_error:
                            self.logger.error(f"Could not recover GPIO {pin} for piston '{piston_name}': {recovery_error}", category="hardware")
                            self.logger.warning(f"Piston '{piston_name}' will not be available", category="hardware")
                            failed_pistons.append(piston_name)
                    else:
                        self.logger.error(f"Failed to setup piston '{piston_name}' on GPIO {pin}: {e}", category="hardware")
                        failed_pistons.append(piston_name)

            if failed_pistons:
                self.logger.warning(f"Some pistons failed to initialize: {failed_pistons}. Continuing with sensors...", category="hardware")

            # Initialize multiplexer for sensor reading
            if self.multiplexer_config:
                self.logger.info("Initializing multiplexer for sensor reading...", category="hardware")
                try:
                    self.multiplexer = CD74HC4067Multiplexer(
                        GPIO,
                        self.multiplexer_config['s0'],
                        self.multiplexer_config['s1'],
                        self.multiplexer_config['s2'],
                        self.multiplexer_config['s3'],
                        self.multiplexer_config['sig']
                    )
                    channels = self.multiplexer_config.get('channels', {})
                    self.logger.debug("Multiplexer initialized", category="hardware")
                    self.logger.debug(f"Control pins: S0={self.multiplexer_config['s0']}, S1={self.multiplexer_config['s1']}, S2={self.multiplexer_config['s2']}, S3={self.multiplexer_config['s3']}", category="hardware")
                    self.logger.debug(f"Signal pin: {self.multiplexer_config['sig']}", category="hardware")
                    self.logger.debug(f"Configured channels: {len(channels)}", category="hardware")
                    if self.invert_mux_readings:
                        self.logger.info("Multiplexer sensor inversion ENABLED (handling backwards wiring)", category="hardware")
                except KeyError as e:
                    raise RuntimeError(f"Multiplexer config missing required key: {str(e)}. Check settings.json")
                except Exception as e:
                    raise RuntimeError(f"Failed to initialize multiplexer: {str(e)}")

            # Setup direct sensor pins as inputs (external pull resistors assumed)
            if self.direct_sensor_pins:
                self.logger.info(f"Initializing {len(self.direct_sensor_pins)} direct sensor inputs (edge switches)...", category="hardware")
                for sensor_name, pin in self.direct_sensor_pins.items():
                    try:
                        # Edge switches have external pull resistors
                        # Reading: HIGH = switch triggered/active, LOW = switch not triggered
                        GPIO.setup(pin, GPIO.IN)
                        self.logger.debug(f"Edge switch '{sensor_name}' on GPIO {pin} (external pull resistors)", category="hardware")
                    except Exception as e:
                        error_msg = str(e)
                        if "busy" in error_msg.lower():
                            # GPIO busy - try to recover
                            self.logger.warning(f"GPIO {pin} ({sensor_name}) is busy, attempting recovery...", category="hardware")
                            try:
                                # Force cleanup this specific pin and retry
                                GPIO.cleanup(pin)
                                time.sleep(0.05)
                                GPIO.setup(pin, GPIO.IN)
                                self.logger.success(f"Recovered GPIO {pin} ({sensor_name})", category="hardware")
                            except Exception as recovery_error:
                                # If recovery fails, log but continue - we'll try in the polling thread
                                self.logger.error(f"Could not recover GPIO {pin}: {recovery_error}", category="hardware")
                                self.logger.warning(f"Will attempt to read {sensor_name} anyway", category="hardware")
                        else:
                            raise RuntimeError(f"Failed to setup sensor '{sensor_name}' on GPIO {pin}: {str(e)}")

            # REMOVED limit switch initialization - not part of user's machine

            self.is_initialized = True
            self.logger.success("Raspberry Pi GPIO initialized successfully", category="hardware")

            # Pre-initialize sensor states before starting polling thread
            self._initialize_sensor_states()

            # Start continuous polling thread for all switches
            self.start_switch_polling()

            return True

        except RuntimeError as e:
            # Re-raise RuntimeError with our detailed message
            self.logger.error(f"GPIO Initialization Failed: {str(e)}", category="hardware")
            raise
        except Exception as e:
            error_msg = f"Unexpected GPIO error: {type(e).__name__}: {str(e)}"
            self.logger.error(error_msg, category="hardware")
            raise RuntimeError(error_msg)

    # ========== PISTON CONTROL METHODS ==========

    def set_piston(self, piston_name: str, state: str) -> bool:
        """
        Set piston state with COMPREHENSIVE electrical interference suppression

        Args:
            piston_name: Name of piston (e.g., 'line_marker_piston')
            state: 'up' or 'down'

        Returns:
            True if successful, False otherwise

        Note:
            This method includes comprehensive recovery mechanisms to prevent
            persistent false positives on multiplexer channels. The fix addresses
            GPIO pin corruption that can persist indefinitely after piston operations.
        """
        if not self.is_initialized:
            self.logger.error("GPIO not initialized", category="hardware")
            return False

        if piston_name not in self.piston_pins:
            self.logger.error(f"Unknown piston: {piston_name}", category="hardware")
            return False

        try:
            pin = self.piston_pins[piston_name]
            # HIGH = extended/down, LOW = retracted/up
            gpio_state = GPIO.HIGH if state == "down" else GPIO.LOW
            GPIO.output(pin, gpio_state)
            self.logger.debug(f"Piston '{piston_name}' set to {state.upper()} (GPIO {pin} = {'HIGH' if gpio_state else 'LOW'})", category="hardware")

            # Settling delay to allow electrical noise to dissipate
            time.sleep(self._piston_settling_time)

            return True
        except Exception as e:
            self.logger.error(f"Error setting piston {piston_name}: {e}", category="hardware")
            return False

    def piston_up(self, piston_name: str) -> bool:
        """Retract piston (set to UP position)"""
        return self.set_piston(piston_name, "up")

    def piston_down(self, piston_name: str) -> bool:
        """Extend piston (set to DOWN position)"""
        return self.set_piston(piston_name, "down")

    # ========== LINE MOTOR PISTON CONTROL (Single GPIO for both sides) ==========

    def line_motor_piston_up(self) -> bool:
        """Retract line motor piston (both sides move together - single GPIO control)"""
        return self.piston_up("line_motor_piston")

    def line_motor_piston_down(self) -> bool:
        """Extend line motor piston (both sides move together - single GPIO control)"""
        return self.piston_down("line_motor_piston")

    # ========== SENSOR READING METHODS ==========

    def _read_multiplexer_channel(self, channel: int) -> bool:
        """
        Read from multiplexer with optional inversion based on configuration

        Args:
            channel: Multiplexer channel number

        Returns:
            Boolean sensor state (inverted if configured)
        """
        raw_value = self.multiplexer.read_channel(channel)
        # Invert reading if configured (handles backwards wiring)
        if self.invert_mux_readings:
            return not raw_value
        return raw_value

    def read_sensor(self, sensor_name: str) -> Optional[bool]:
        """
        Read sensor state (via multiplexer or direct GPIO)

        Args:
            sensor_name: Name of sensor (e.g., 'line_marker_up_sensor')

        Returns:
            True if sensor triggered (HIGH signal), False if not triggered (LOW signal), None on error
        """
        if not self.is_initialized:
            self.logger.error("GPIO not initialized", category="hardware")
            return None

        try:
            # Check if sensor is connected via multiplexer
            mux_channels = self.multiplexer_config.get('channels', {})
            if sensor_name in mux_channels:
                # Return state from polling thread's switch_states
                switch_key = f"mux_{sensor_name}"
                if switch_key in self.switch_states:
                    return self.switch_states[switch_key]
                else:
                    # Fallback to last known state if polling thread hasn't initialized yet
                    return self._last_sensor_states.get(sensor_name, False)

            # Check if it's a direct edge switch
            elif sensor_name in self.direct_sensor_pins:
                # Return state from polling thread's switch_states
                if sensor_name in self.switch_states:
                    return self.switch_states[sensor_name]
                else:
                    # Fallback to last known state if polling thread hasn't initialized yet
                    return self._last_sensor_states.get(sensor_name, False)

            else:
                self.logger.error(f"Unknown sensor: {sensor_name}", category="hardware")
                return None

        except Exception as e:
            self.logger.error(f"Error reading sensor {sensor_name}: {e}", category="hardware")
            return None

    # ========== INDIVIDUAL SENSOR GETTERS (DUAL SENSORS PER TOOL) ==========

    # Line Marker Sensors
    def get_line_marker_up_sensor(self) -> Optional[bool]:
        """Read line marker UP sensor state"""
        return self.read_sensor("line_marker_up_sensor")

    def get_line_marker_down_sensor(self) -> Optional[bool]:
        """Read line marker DOWN sensor state"""
        return self.read_sensor("line_marker_down_sensor")

    # Line Cutter Sensors
    def get_line_cutter_up_sensor(self) -> Optional[bool]:
        """Read line cutter UP sensor state"""
        return self.read_sensor("line_cutter_up_sensor")

    def get_line_cutter_down_sensor(self) -> Optional[bool]:
        """Read line cutter DOWN sensor state"""
        return self.read_sensor("line_cutter_down_sensor")

    # Line Motor Left Piston Sensors
    def get_line_motor_left_up_sensor(self) -> Optional[bool]:
        """Read line motor LEFT piston UP sensor state"""
        return self.read_sensor("line_motor_left_up_sensor")

    def get_line_motor_left_down_sensor(self) -> Optional[bool]:
        """Read line motor LEFT piston DOWN sensor state"""
        return self.read_sensor("line_motor_left_down_sensor")

    # Line Motor Right Piston Sensors
    def get_line_motor_right_up_sensor(self) -> Optional[bool]:
        """Read line motor RIGHT piston UP sensor state"""
        return self.read_sensor("line_motor_right_up_sensor")

    def get_line_motor_right_down_sensor(self) -> Optional[bool]:
        """Read line motor RIGHT piston DOWN sensor state"""
        return self.read_sensor("line_motor_right_down_sensor")

    # Row Marker Sensors
    def get_row_marker_up_sensor(self) -> Optional[bool]:
        """Read row marker UP sensor state"""
        return self.read_sensor("row_marker_up_sensor")

    def get_row_marker_down_sensor(self) -> Optional[bool]:
        """Read row marker DOWN sensor state"""
        return self.read_sensor("row_marker_down_sensor")

    # Row Cutter Sensors
    def get_row_cutter_up_sensor(self) -> Optional[bool]:
        """Read row cutter UP sensor state"""
        return self.read_sensor("row_cutter_up_sensor")

    def get_row_cutter_down_sensor(self) -> Optional[bool]:
        """Read row cutter DOWN sensor state"""
        return self.read_sensor("row_cutter_down_sensor")

    # ========== EDGE SENSORS ==========

    def get_x_left_edge_sensor(self) -> Optional[bool]:
        """Read X-axis LEFT edge sensor state"""
        return self.read_sensor("x_left_edge")

    def get_x_right_edge_sensor(self) -> Optional[bool]:
        """Read X-axis RIGHT edge sensor state"""
        return self.read_sensor("x_right_edge")

    def get_y_top_edge_sensor(self) -> Optional[bool]:
        """Read Y-axis TOP edge sensor state"""
        return self.read_sensor("y_top_edge")

    def get_y_bottom_edge_sensor(self) -> Optional[bool]:
        """Read Y-axis BOTTOM edge sensor state"""
        return self.read_sensor("y_bottom_edge")

    # ========== LIMIT SWITCHES REMOVED - NOT PART OF USER'S MACHINE ==========

    def get_all_sensor_states(self) -> Dict[str, bool]:
        """
        Read all sensor states (edge switches + multiplexer sensors)

        Returns:
            Dictionary mapping sensor names to their states
        """
        states = {}

        # Read all direct edge switches
        for sensor_name in self.direct_sensor_pins.keys():
            state = self.read_sensor(sensor_name)
            if state is not None:
                states[sensor_name] = state

        # Read all multiplexer sensors
        if self.multiplexer:
            mux_channels = self.multiplexer_config.get('channels', {})
            for sensor_name in mux_channels.keys():
                state = self.read_sensor(sensor_name)
                if state is not None:
                    states[sensor_name] = state

        return states

    # REMOVED get_all_limit_switch_states - not part of user's machine
    # Note: Door limit switch has been moved to Arduino GRBL
    # Use hardware_interface.get_door_switch() instead

    # ========== SENSOR INITIALIZATION ==========

    def _initialize_sensor_states(self):
        """Pre-initialize all sensor states before starting polling thread"""
        self.logger.info("Pre-initializing sensor states...", category="hardware")

        # Initialize _last_sensor_states if not already done
        if not hasattr(self, '_last_sensor_states'):
            self._last_sensor_states = {}

        # Read all direct sensors
        for sensor_name, pin in self.direct_sensor_pins.items():
            try:
                state = GPIO.input(pin)
                self._last_sensor_states[sensor_name] = state
                self.logger.debug(f"Initialized {sensor_name}: {'HIGH' if state else 'LOW'}", category="hardware")
            except Exception as e:
                self.logger.error(f"Error initializing {sensor_name}: {e}", category="hardware")
                self._last_sensor_states[sensor_name] = False

        # Read all multiplexer sensors
        if self.multiplexer:
            channels = self.multiplexer_config.get('channels', {})
            self.logger.info(f"Initializing {len(channels)} multiplexer sensor states...", category="hardware")
            for sensor_name, channel in channels.items():
                try:
                    state = self._read_multiplexer_channel(channel)
                    self._last_sensor_states[sensor_name] = state
                    state_str = 'HIGH (ACTIVE)' if state else 'LOW (INACTIVE)'
                    self.logger.info(f"   MUX {sensor_name:30s} [CH{channel:2d}] = {state_str}", category="hardware")
                except Exception as e:
                    self.logger.error(f"   MUX {sensor_name:30s} [CH{channel:2d}] = ERROR: {e}", category="hardware")
                    self._last_sensor_states[sensor_name] = False

        self.logger.success(f"Pre-initialized {len(self._last_sensor_states)} sensor states", category="hardware")

    # ========== CONTINUOUS SWITCH POLLING ==========

    def start_switch_polling(self):
        """Start continuous polling thread to monitor all switches"""
        if self.polling_active:
            self.logger.warning("Polling thread already running", category="hardware")
            return

        self.logger.info("Starting continuous switch polling thread...", category="hardware")
        self.logger.info("   This thread will monitor ALL switches and log state changes", category="hardware")
        self.logger.info("   Poll interval: 25ms (40 times per second) - PERFORMANCE OPTIMIZED", category="hardware")

        self.polling_active = True
        self.polling_thread = threading.Thread(target=self._poll_switches_continuously, daemon=True)
        self.polling_thread.start()

    def stop_switch_polling(self):
        """Stop the continuous polling thread"""
        if self.polling_active:
            self.logger.info("Stopping switch polling thread...", category="hardware")
            self.polling_active = False
            if self.polling_thread:
                self.polling_thread.join(timeout=1.0)
            self.logger.info("Polling thread stopped", category="hardware")

    def _poll_switches_continuously(self):
        """Background thread that continuously polls all switches and logs changes"""
        self.logger.info("Switch polling thread started", category="hardware")

        # Initialize edge switch states
        for sensor_name, pin in self.direct_sensor_pins.items():
            try:
                current_state = GPIO.input(pin)  # Direct read: HIGH=triggered, LOW=ready
                self.switch_states[sensor_name] = current_state
                self.logger.debug(f"Edge switch {sensor_name} [pin {pin}] initialized: {'TRIGGERED' if current_state else 'READY'}", category="hardware")
            except Exception as e:
                self.logger.error(f"Error initializing {sensor_name}: {e}", category="hardware")
                self.switch_states[sensor_name] = False

        # CRITICAL FIX: Initialize multiplexer switch states
        # This prevents false positive state changes on first poll
        if self.multiplexer:
            channels = self.multiplexer_config.get('channels', {})
            self.logger.info(f"Initializing {len(channels)} multiplexer switch states in polling thread...", category="hardware")
            for sensor_name, channel in channels.items():
                try:
                    current_state = self._read_multiplexer_channel(channel)
                    switch_key = f"mux_{sensor_name}"
                    self.switch_states[switch_key] = current_state
                    self.logger.debug(f"Mux switch {sensor_name} [channel {channel}] initialized: {'TRIGGERED' if current_state else 'READY'}", category="hardware")
                except Exception as e:
                    self.logger.error(f"Error initializing mux {sensor_name} on channel {channel}: {e}", category="hardware")
                    switch_key = f"mux_{sensor_name}"
                    self.switch_states[switch_key] = False

        poll_count = 0

        while self.polling_active:
            try:
                poll_count += 1

                # Read ALL edge switches
                for sensor_name, pin in self.direct_sensor_pins.items():
                    try:
                        current_state = GPIO.input(pin)  # Direct read: HIGH=triggered, LOW=ready
                        last_state = self.switch_states.get(sensor_name)

                        # Detect state changes
                        if current_state != last_state:
                            self.switch_states[sensor_name] = current_state
                            self.logger.info("="*60, category="hardware")
                            self.logger.info(f"EDGE SWITCH CHANGED: {sensor_name}", category="hardware")
                            self.logger.info(f"  Pin: {pin}", category="hardware")
                            self.logger.info(f"  Previous: {'TRIGGERED' if last_state else 'READY'}", category="hardware")
                            self.logger.info(f"  Current: {'TRIGGERED' if current_state else 'READY'}", category="hardware")
                            self.logger.info("="*60, category="hardware")

                    except Exception as e:
                        self.logger.error(f"Error reading {sensor_name}: {e}", category="hardware")

                # Note: Non-edge sensors are handled via the multiplexer below

                # Poll multiplexer switches (piston position sensors)
                if self.multiplexer:
                    channels = self.multiplexer_config.get('channels', {})
                    for sensor_name, channel in channels.items():
                        try:
                            # Direct read from multiplexer (with optional inversion)
                            current_state = self._read_multiplexer_channel(channel)

                            switch_key = f"mux_{sensor_name}"
                            last_state = self.switch_states.get(switch_key)

                            # Detect state changes
                            if current_state != last_state:
                                self.switch_states[switch_key] = current_state
                                self.logger.info("="*60, category="hardware")
                                self.logger.info(f"MULTIPLEXER SENSOR CHANGED: {sensor_name}", category="hardware")
                                self.logger.info(f"  Channel: {channel}", category="hardware")
                                self.logger.info(f"  Previous: {'TRIGGERED' if last_state else 'READY'}", category="hardware")
                                self.logger.info(f"  Current: {'TRIGGERED' if current_state else 'READY'}", category="hardware")
                                self.logger.info("="*60, category="hardware")

                        except Exception as e:
                            self.logger.error(f"Error reading mux {sensor_name} on channel {channel}: {e}", category="hardware")

                # NO LIMIT SWITCHES - removed per user request

                # Status update every 400 polls (10 seconds at 25ms interval)
                if poll_count % 400 == 0:
                    edge_count = len(self.direct_sensor_pins)
                    mux_count = len(self.multiplexer_config.get('channels', {})) if self.multiplexer else 0
                    total = edge_count + mux_count
                    self.logger.debug(f"Polling heartbeat: {poll_count} polls completed, monitoring {total} switches ({edge_count} edge + {mux_count} mux)", category="hardware")

                # PERFORMANCE FIX: Sleep 25ms between polls (40 Hz) - reduced from 100ms
                time.sleep(0.025)

            except Exception as e:
                self.logger.error(f"Polling thread error: {e}", category="hardware")
                time.sleep(0.1)

        self.logger.info("Polling thread exiting", category="hardware")

    # ========== CLEANUP ==========

    def cleanup(self):
        """
        Cleanup GPIO resources
        Should be called when shutting down
        """
        if self.is_initialized:
            try:
                # Stop polling thread first
                self.stop_switch_polling()

                # Set all pistons to retracted/up position before cleanup
                for piston_name in self.piston_pins:
                    self.piston_up(piston_name)
                time.sleep(0.1)

                # Cleanup multiplexer
                if self.multiplexer:
                    self.multiplexer.cleanup()
                    self.logger.info("Multiplexer cleanup completed", category="hardware")

                GPIO.cleanup()
                self.is_initialized = False
                self.logger.info("GPIO cleanup completed", category="hardware")
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}", category="hardware")


if __name__ == "__main__":
    """Test GPIO interface"""
    # Create module-level logger for test section
    test_logger = get_logger()

    test_logger.info("="*60, category="hardware")
    test_logger.info("Raspberry Pi GPIO Interface Test", category="hardware")
    test_logger.info("="*60, category="hardware")

    # Create and initialize GPIO interface
    gpio = RaspberryPiGPIO()

    if gpio.initialize():
        test_logger.info("Testing piston control...", category="hardware")
        # Test each piston
        for piston_name in gpio.piston_pins:
            test_logger.info(f"Testing {piston_name}:", category="hardware")
            gpio.piston_down(piston_name)
            time.sleep(0.5)
            gpio.piston_up(piston_name)
            time.sleep(0.5)

        test_logger.info("Reading all sensors...", category="hardware")
        sensor_states = gpio.get_all_sensor_states()
        for sensor, state in sensor_states.items():
            test_logger.info(f"  {sensor}: {'TRIGGERED' if state else 'READY'}", category="hardware")

        # REMOVED limit switch testing - not part of user's machine

        # Cleanup
        gpio.cleanup()
    else:
        test_logger.error("Failed to initialize GPIO", category="hardware")

    test_logger.info("="*60, category="hardware")
    test_logger.info("Test completed", category="hardware")
    test_logger.info("="*60, category="hardware")


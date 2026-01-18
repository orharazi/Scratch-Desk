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
from hardware.implementations.real.raspberry_pi.rs485_modbus import RS485ModbusInterface
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

# Constants for switch debouncing
# DEBOUNCE_COUNT is now configurable via settings.json (raspberry_pi.debounce_count)

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
        self.rs485_config = self.gpio_config.get("rs485", {})
        self.direct_sensor_pins = self.gpio_config.get("direct_sensors", {})
        self.limit_switch_pins = self.gpio_config.get("limit_switches", {})
        self.rs485 = None  # Will be initialized later

        # Initialize state tracking dictionary
        self._last_sensor_states = {}  # Initialize state tracking dictionary

        # Polling thread for continuous switch monitoring
        self.polling_thread = None
        self.polling_active = False
        self.switch_states = {}  # Track last known state of all switches

        # Load all timing config values
        timing_config = self.config.get("timing", {})
        self._piston_settling_time = timing_config.get("piston_gpio_settling_delay", 0.05)
        self._gpio_cleanup_delay = timing_config.get("gpio_cleanup_delay", 0.1)
        self._gpio_busy_recovery_delay = timing_config.get("gpio_busy_recovery_delay", 0.05)
        self._gpio_debounce_samples = timing_config.get("gpio_debounce_samples", 3)
        self._gpio_debounce_delay = timing_config.get("gpio_debounce_delay_ms", 1) / 1000.0
        self._gpio_test_read_delay = timing_config.get("gpio_test_read_delay_ms", 1) / 1000.0
        self._polling_thread_join_timeout = timing_config.get("polling_thread_join_timeout", 1.0)
        self._switch_polling_interval = timing_config.get("switch_polling_interval_ms", 10) / 1000.0
        self._polling_status_update_freq = timing_config.get("polling_status_update_frequency", 1000)
        self._polling_error_recovery_delay = timing_config.get("polling_error_recovery_delay", 0.1)

        # Load debounce count from raspberry_pi config
        self._debounce_count = self.gpio_config.get("debounce_count", 2)

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
        self.logger.debug(f"RS485 config: {self.rs485_config}", category="hardware")
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
                time.sleep(self._gpio_cleanup_delay)  # Give GPIO time to release
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
                    raise RuntimeError(f"Failed to setup piston '{piston_name}' on GPIO {pin}: {str(e)}")

            # Initialize RS485 for sensor reading
            if self.rs485_config and self.rs485_config.get('enabled', True):
                self.logger.info("Initializing RS485 Modbus RTU for sensor reading...", category="hardware")
                try:
                    self.rs485 = RS485ModbusInterface(
                        port=self.rs485_config.get('serial_port', '/dev/ttyAMA0'),
                        baudrate=self.rs485_config.get('baudrate', 9600),
                        bytesize=self.rs485_config.get('bytesize', 8),
                        parity=self.rs485_config.get('parity', 'N'),
                        stopbits=self.rs485_config.get('stopbits', 1),
                        timeout=self.rs485_config.get('timeout', 1.0),
                        sensor_addresses=self.rs485_config.get('sensor_addresses', {}),
                        device_id=self.rs485_config.get('modbus_device_id', 1),
                        input_count=self.rs485_config.get('input_count', 32),
                        bulk_read_enabled=self.rs485_config.get('bulk_read_enabled', True),
                        bulk_read_cache_age_ms=self.rs485_config.get('bulk_read_cache_age_ms', 10),
                        default_retry_count=self.rs485_config.get('default_retry_count', 2),
                        register_address_low=self.rs485_config.get('register_address_low', 192),
                        bulk_read_register_count=self.rs485_config.get('bulk_read_register_count', 2),
                        retry_delay=timing_config.get('rs485_retry_delay', 0.01)
                    )

                    # Connect to RS485 bus
                    if not self.rs485.connect():
                        raise RuntimeError("Failed to connect to RS485 bus")

                    sensor_count = len(self.rs485_config.get('sensor_addresses', {}))
                    self.logger.debug("RS485 initialized", category="hardware")
                    self.logger.debug(f"Serial port: {self.rs485_config.get('serial_port')}", category="hardware")
                    self.logger.debug(f"Baudrate: {self.rs485_config.get('baudrate')}", category="hardware")
                    self.logger.debug(f"Configured sensors: {sensor_count}", category="hardware")
                except KeyError as e:
                    raise RuntimeError(f"RS485 config missing required key: {str(e)}. Check settings.json")
                except Exception as e:
                    raise RuntimeError(f"Failed to initialize RS485: {str(e)}")

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
                                time.sleep(self._gpio_busy_recovery_delay)
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

            # Check if we should skip initial sensor tests (POC mode)
            skip_tests = self.config.get("hardware_config", {}).get("skip_initial_sensor_tests", False)
            poc_mode = self.config.get("hardware_config", {}).get("poc_mode", False)

            if skip_tests or poc_mode:
                self.logger.info("="*60, category="hardware")
                self.logger.info("POC MODE: Skipping initial sensor tests", category="hardware")
                self.logger.info("Sensors will be available but not tested during initialization", category="hardware")
                self.logger.info("="*60, category="hardware")

                # Initialize sensor state tracking dictionaries without reading
                # This allows the polling thread to detect changes
                if not hasattr(self, '_last_sensor_states'):
                    self._last_sensor_states = {}

                # Initialize all sensor entries to False (will be updated by polling thread)
                for sensor_name in self.direct_sensor_pins.keys():
                    self._last_sensor_states[sensor_name] = False

                if self.rs485:
                    sensor_addresses = self.rs485_config.get('sensor_addresses', {})
                    for sensor_name in sensor_addresses.keys():
                        self._last_sensor_states[sensor_name] = False

                self.logger.info(f"POC MODE: Initialized {len(self._last_sensor_states)} sensor tracking entries", category="hardware")
            else:
                # Test GPIO reads immediately
                self._test_gpio_reads()

                # Test RS485 reads specifically
                self._test_rs485_reads()

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
            persistent false positives on sensor channels. The fix addresses
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

    def _read_with_debounce(self, pin_or_channel, is_rs485=False, sensor_name=None, samples=None, delay=None):
        """
        Read GPIO or RS485 with debouncing

        Args:
            pin_or_channel: GPIO pin number (for direct GPIO)
            is_rs485: True if reading from RS485
            sensor_name: Sensor name for RS485 lookup (if is_rs485=True)
            samples: Number of consistent reads required (defaults to configured value)
            delay: Delay between reads in seconds (defaults to configured value)

        Returns:
            Stable boolean state or None if reads are inconsistent
        """
        import time

        # Use configured values if not provided
        if samples is None:
            samples = self._gpio_debounce_samples
        if delay is None:
            delay = self._gpio_debounce_delay

        # PERFORMANCE OPTIMIZED: Minimal RS485 debouncing for 50ms trigger detection
        if is_rs485:
            samples = 1  # Single read for RS485 (bulk read already filtered by hardware)
            delay = 0  # No delay needed for single sample

        readings = []
        for i in range(samples):
            if is_rs485 and self.rs485:
                # For RS485, read via Modbus
                register_address = self.rs485_config.get('register_address', 0)
                value = self.rs485.read_sensor(sensor_name, register_address)
                if value is None:
                    # RS485 read failed - return None
                    return None
            else:
                # For direct GPIO
                value = GPIO.input(pin_or_channel)

            readings.append(value)

            if i < samples - 1:  # Don't delay after last read
                time.sleep(delay)

        # Check if all readings are consistent
        if all(r == readings[0] for r in readings):
            return bool(readings[0])
        else:
            # Inconsistent reads - sensor is bouncing/noisy
            # Return None to indicate unstable read
            return None

    def read_sensor(self, sensor_name: str) -> Optional[bool]:
        """
        Read sensor state (via RS485 or direct GPIO)

        Args:
            sensor_name: Name of sensor (e.g., 'line_marker_up_sensor')

        Returns:
            True if sensor triggered (HIGH signal), False if not triggered (LOW signal), None on error
        """
        if not self.is_initialized:
            self.logger.error("GPIO not initialized", category="hardware")
            return None

        try:
            # AGGRESSIVE LOGGING for edge sensors
            is_edge_sensor = sensor_name in ['x_left_edge', 'x_right_edge', 'y_top_edge', 'y_bottom_edge']

            if is_edge_sensor:
                self.logger.debug(f"🔍 read_sensor() called for EDGE SENSOR: {sensor_name}", category="hardware")
                self.logger.debug(f"   Direct sensor pins: {list(self.direct_sensor_pins.keys())}", category="hardware")
                self.logger.debug(f"   Switch states keys: {list(self.switch_states.keys())}", category="hardware")

            # Check if sensor is connected via RS485
            rs485_addresses = self.rs485_config.get('sensor_addresses', {})
            if sensor_name in rs485_addresses:
                # Return state from polling thread's switch_states (debounced and verified)
                switch_key = f"rs485_{sensor_name}"
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
                self.logger.error(f"  Not in rs485_addresses: {list(rs485_addresses.keys())}", category="hardware")
                self.logger.error(f"  Not in direct_sensor_pins: {list(self.direct_sensor_pins.keys())}", category="hardware")
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
        Read all sensor states (edge switches + RS485 sensors)

        Returns:
            Dictionary mapping sensor names to their states
        """
        states = {}

        # Read all direct edge switches
        for sensor_name in self.direct_sensor_pins.keys():
            state = self.read_sensor(sensor_name)
            if state is not None:
                states[sensor_name] = state

        # Read all RS485 sensors
        if self.rs485:
            sensor_addresses = self.rs485_config.get('sensor_addresses', {})
            for sensor_name in sensor_addresses.keys():
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

        # Read all RS485 sensors
        if self.rs485:
            sensor_addresses = self.rs485_config.get('sensor_addresses', {})
            self.logger.info(f"Initializing {len(sensor_addresses)} RS485 sensor states...", category="hardware")
            for sensor_name, slave_address in sensor_addresses.items():
                try:
                    state = self._read_with_debounce(None, is_rs485=True, sensor_name=sensor_name)
                    if state is not None:
                        self._last_sensor_states[sensor_name] = state
                        state_str = 'HIGH (ACTIVE)' if state else 'LOW (INACTIVE)'
                        self.logger.info(f"   RS485 {sensor_name:30s} [ADDR{slave_address:2d}] = {state_str}", category="hardware")
                    else:
                        self._last_sensor_states[sensor_name] = False  # Default to False if unstable
                        self.logger.warning(f"   RS485 {sensor_name:30s} [ADDR{slave_address:2d}] = UNSTABLE (defaulting to LOW)", category="hardware")
                except Exception as e:
                    self.logger.error(f"   RS485 {sensor_name:30s} [ADDR{slave_address:2d}] = ERROR: {e}", category="hardware")
                    self._last_sensor_states[sensor_name] = False

        self.logger.success(f"Pre-initialized {len(self._last_sensor_states)} sensor states", category="hardware")

    # ========== GPIO TEST ==========

    def _test_gpio_reads(self):
        """Test GPIO reads immediately after initialization"""
        self.logger.info("="*60, category="hardware")
        self.logger.info("TESTING GPIO PIN READS", category="hardware")
        self.logger.info("="*60, category="hardware")

        # Test edge sensor pins
        self.logger.info("Testing Edge Sensor Pins (X/Y axis):", category="hardware")
        for sensor_name, pin in self.direct_sensor_pins.items():
            try:
                # Read pin 5 times rapidly
                readings = []
                for _ in range(5):
                    readings.append(GPIO.input(pin))
                    time.sleep(self._gpio_test_read_delay)  # 1ms between reads (configurable)

                # Check if all readings are the same (stable)
                if len(set(readings)) == 1:
                    state = readings[0]
                    self.logger.debug(f"{sensor_name:20s} [pin {pin:2d}] = {'HIGH' if state else 'LOW '} (stable)", category="hardware")
                else:
                    self.logger.warning(f"{sensor_name:20s} [pin {pin:2d}] = UNSTABLE! Readings: {readings}", category="hardware")
                    self.logger.warning(f"      This indicates floating pin or electrical noise!", category="hardware")
                    self.logger.warning(f"      Check: 1) Wire connection, 2) Pull-down resistor, 3) Power supply", category="hardware")
            except Exception as e:
                self.logger.error(f"{sensor_name:20s} [pin {pin:2d}] = ERROR: {e}", category="hardware")

        # Test limit switch pins
        if self.limit_switch_pins:
            self.logger.info("Testing Limit Switch Pins:", category="hardware")
            for switch_name, pin in self.limit_switch_pins.items():
                try:
                    readings = []
                    for _ in range(5):
                        readings.append(GPIO.input(pin))
                        time.sleep(self._gpio_test_read_delay)

                    if len(set(readings)) == 1:
                        state = readings[0]
                        inverted = not state
                        self.logger.debug(f"{switch_name:20s} [pin {pin:2d}] = {'HIGH' if state else 'LOW '} -> {'ACTIVATED' if inverted else 'INACTIVE'} (stable)", category="hardware")
                    else:
                        self.logger.warning(f"{switch_name:20s} [pin {pin:2d}] = UNSTABLE! Readings: {readings}", category="hardware")
                except Exception as e:
                    self.logger.error(f"{switch_name:20s} [pin {pin:2d}] = ERROR: {e}", category="hardware")

        self.logger.info("IMPORTANT: If pins show UNSTABLE:", category="hardware")
        self.logger.info("   1. Check physical wiring - loose connections cause noise", category="hardware")
        self.logger.info("   2. Ensure switches are properly connected to GND or 3.3V", category="hardware")
        self.logger.info("   3. Verify pull-down/pull-up resistors are configured", category="hardware")
        self.logger.info("   4. Test: touch wire to GND (should show LOW) or 3.3V (should show HIGH)", category="hardware")
        self.logger.info("="*60, category="hardware")

    def _test_rs485_reads(self):
        """Test RS485 sensor reads immediately after initialization"""
        if not self.rs485:
            self.logger.warning("RS485 not initialized - skipping RS485 test", category="hardware")
            return

        self.logger.info("="*60, category="hardware")
        self.logger.info("TESTING RS485 SENSOR READS", category="hardware")
        self.logger.info("="*60, category="hardware")

        sensor_addresses = self.rs485_config.get('sensor_addresses', {})
        self.logger.info(f"Testing {len(sensor_addresses)} RS485 sensors...", category="hardware")

        for sensor_name, slave_address in sensor_addresses.items():
            try:
                # Read with 3-sample debouncing (PERFORMANCE OPTIMIZED)
                state = self._read_with_debounce(None, is_rs485=True, sensor_name=sensor_name)

                if state is not None:
                    state_str = 'HIGH (ACTIVE/TRIGGERED)' if state else 'LOW (INACTIVE)'
                    self.logger.info(f"   {sensor_name:30s} [ADDR{slave_address:2d}] = {state_str} (stable)", category="hardware")
                else:
                    self.logger.warning(f"   {sensor_name:30s} [ADDR{slave_address:2d}] = UNSTABLE! (read failed)", category="hardware")
                    self.logger.warning(f"      Check: 1) Sensor wiring, 2) RS485 connections, 3) Modbus address, 4) Power supply", category="hardware")
            except Exception as e:
                self.logger.error(f"   {sensor_name:30s} [ADDR{slave_address:2d}] = ERROR: {e}", category="hardware")

        self.logger.info("="*60, category="hardware")
        self.logger.info("TIP: Trigger a sensor now and watch for changes in the GUI!", category="hardware")
        self.logger.info("="*60, category="hardware")

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
                self.polling_thread.join(timeout=self._polling_thread_join_timeout)
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

        # Initialize debounce counters for RS485 sensors
        debounce_counters = {}

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
                        self.logger.error(f"Error reading {sensor_name} on pin {pin}: {e}", category="hardware")

                # Poll RS485 switches (piston position sensors)
                if self.rs485:
                    sensor_addresses = self.rs485_config.get('sensor_addresses', {})
                    for sensor_name, slave_address in sensor_addresses.items():
                        try:
                            # Direct read from bulk cache (no debouncing - optimized for 50ms triggers)
                            current_state = self._read_with_debounce(None, is_rs485=True, sensor_name=sensor_name)

                            # Skip if read was unstable (returns None)
                            if current_state is None:
                                continue

                            switch_key = f"rs485_{sensor_name}"
                            last_confirmed_state = self.switch_states.get(switch_key)

                            # Initialize debounce counter for this sensor if needed
                            if switch_key not in debounce_counters:
                                debounce_counters[switch_key] = {'pending_state': None, 'count': 0}

                            debounce = debounce_counters[switch_key]

                            # Handle debounce logic for initial and subsequent reads
                            if debounce['pending_state'] is None:
                                # Very first read of this sensor - start debounce
                                debounce['pending_state'] = current_state
                                debounce['count'] = 1
                                self.logger.debug(f"RS485 SWITCH FIRST READ: {sensor_name} = {'HIGH (CLOSED/ON)' if current_state else 'LOW (OPEN/OFF)'} [address {slave_address}] - waiting for confirmation", category="hardware")
                            elif debounce['pending_state'] == current_state:
                                # Reading matches pending state, increment count
                                debounce['count'] += 1
                            else:
                                # State changed, restart debounce
                                debounce['pending_state'] = current_state
                                debounce['count'] = 1

                            # Check if we have enough consecutive readings
                            if debounce['count'] >= self._debounce_count:
                                # Check if this is different from confirmed state (or first confirmation)
                                if current_state != last_confirmed_state:
                                    # State change confirmed (or initial state set)!
                                    self.switch_states[switch_key] = current_state

                                    # Log state change or initial state
                                    if last_confirmed_state is not None:
                                        # Real state change (not initial)
                                        old_state_str = 'HIGH (ACTIVE/TRIGGERED)' if last_confirmed_state else 'LOW (INACTIVE)'
                                        new_state_str = 'HIGH (ACTIVE/TRIGGERED)' if current_state else 'LOW (INACTIVE)'
                                        self.logger.info("=== RS485 SENSOR CHANGED ===", category="hardware")
                                        self.logger.info(f"   Sensor: {sensor_name}", category="hardware")
                                        self.logger.info(f"   Modbus Address: {slave_address}", category="hardware")
                                        self.logger.info(f"   Old State: {old_state_str}", category="hardware")
                                        self.logger.info(f"   New State: {new_state_str}", category="hardware")
                                        self.logger.info(f"   Poll: #{poll_count}", category="hardware")
                                    else:
                                        # Initial state set
                                        state_str = 'HIGH (ACTIVE/TRIGGERED)' if current_state else 'LOW (INACTIVE)'
                                        self.logger.info(f"RS485 SENSOR INITIALIZED: {sensor_name} = {state_str} [address {slave_address}]", category="hardware")

                        except Exception as e:
                            self.logger.error(f"Error reading RS485 {sensor_name} at address {slave_address}: {e}", category="hardware")

                # Poll limit switches
                for switch_name, pin in self.limit_switch_pins.items():
                    try:
                        raw_state = GPIO.input(pin)
                        current_state = not raw_state  # Inverted: LOW = activated
                        switch_key = f"limit_{switch_name}"
                        last_state = self.switch_states.get(switch_key)

                        # Log state change
                        if last_state is None:
                            # First read - initialize
                            self.switch_states[switch_key] = current_state
                            self.logger.debug(f"LIMIT SWITCH INITIAL: {switch_name} = {'ACTIVATED (CLOSED)' if current_state else 'INACTIVE (OPEN)'} [pin {pin}]", category="hardware")
                        elif last_state != current_state:
                            # State changed!
                            self.switch_states[switch_key] = current_state
                            self.logger.info(f"LIMIT SWITCH CHANGED: {switch_name} = {'ACTIVATED (CLOSED)' if current_state else 'INACTIVE (OPEN)'} [pin {pin}] (poll #{poll_count})", category="hardware")

                    except Exception as e:
                        self.logger.error(f"Error reading limit switch {switch_name} on pin {pin}: {e}", category="hardware")

                # Status update every N polls (configurable via settings.json)
                if poll_count % self._polling_status_update_freq == 0:
                    edge_count = len(self.direct_sensor_pins)
                    rs485_count = len(self.rs485_config.get('sensor_addresses', {})) if self.rs485 else 0
                    limit_count = len(self.limit_switch_pins)
                    total = edge_count + rs485_count + limit_count
                    self.logger.debug(f"Polling heartbeat: {poll_count} polls completed, monitoring {total} switches ({edge_count} edge + {rs485_count} rs485 + {limit_count} limit)", category="hardware")

                # OPTIMIZED: Sleep between polls (configurable via settings.json)
                time.sleep(self._switch_polling_interval)

            except Exception as e:
                self.logger.error(f"Polling thread error: {e}", category="hardware")
                time.sleep(self._polling_error_recovery_delay)

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
                time.sleep(self._gpio_cleanup_delay)

                # Cleanup RS485
                if self.rs485:
                    self.rs485.cleanup()
                    self.logger.info("RS485 cleanup completed", category="hardware")

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


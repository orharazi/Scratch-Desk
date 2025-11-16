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
        self.limit_switch_pins = self.gpio_config.get("limit_switches", {})
        self.multiplexer = None  # Will be initialized later

        # Initialize state tracking dictionary
        self._last_sensor_states = {}  # Initialize state tracking dictionary

        # Polling thread for continuous switch monitoring
        self.polling_thread = None
        self.polling_active = False
        self.switch_states = {}  # Track last known state of all switches

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
        self.logger.debug(f"Limit switch pins: {self.limit_switch_pins}", category="hardware")
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
            import RPi.GPIO as GPIO_TEST
        except (ImportError, RuntimeError) as e:
            error_msg = "NOT RUNNING ON RASPBERRY PI - RPi.GPIO module not available or not on Pi hardware"
            self.logger.error(error_msg, category="hardware")
            self.logger.error("This application requires Raspberry Pi hardware to run in Real Hardware mode.", category="hardware")
            self.logger.error("Switch to Simulation mode in Hardware Settings to test without Pi hardware.", category="hardware")
            raise RuntimeError(error_msg)

        try:
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
            for piston_name, pin in self.piston_pins.items():
                try:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)
                    self.logger.debug(f"Piston '{piston_name}' on GPIO {pin}", category="hardware")
                except Exception as e:
                    raise RuntimeError(f"Failed to setup piston '{piston_name}' on GPIO {pin}: {str(e)}")

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
                except KeyError as e:
                    raise RuntimeError(f"Multiplexer config missing required key: {str(e)}. Check settings.json")
                except Exception as e:
                    raise RuntimeError(f"Failed to initialize multiplexer: {str(e)}")

            # Setup direct sensor pins as inputs with pull-down resistors
            if self.direct_sensor_pins:
                self.logger.info(f"Initializing {len(self.direct_sensor_pins)} direct sensor inputs...", category="hardware")
                for sensor_name, pin in self.direct_sensor_pins.items():
                    try:
                        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                        self.logger.debug(f"Sensor '{sensor_name}' on GPIO {pin}", category="hardware")
                    except Exception as e:
                        raise RuntimeError(f"Failed to setup sensor '{sensor_name}' on GPIO {pin}: {str(e)}")

            # Setup limit switch pins as inputs with pull-up resistors
            if self.limit_switch_pins:
                self.logger.info(f"Initializing {len(self.limit_switch_pins)} limit switches...", category="hardware")
                for switch_name, pin in self.limit_switch_pins.items():
                    try:
                        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                        self.logger.debug(f"Limit switch '{switch_name}' on GPIO {pin}", category="hardware")
                    except Exception as e:
                        raise RuntimeError(f"Failed to setup limit switch '{switch_name}' on GPIO {pin}: {str(e)}")

            self.is_initialized = True
            self.logger.success("Raspberry Pi GPIO initialized successfully", category="hardware")

            # Test GPIO reads immediately
            self._test_gpio_reads()

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
        Set piston state

        Args:
            piston_name: Name of piston (e.g., 'line_marker_piston')
            state: 'up' or 'down'

        Returns:
            True if successful, False otherwise
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

    def _read_with_debounce(self, pin_or_channel, is_multiplexer=False, channel=None, samples=3, delay=0.001):
        """
        Read GPIO or multiplexer with debouncing

        Args:
            pin_or_channel: GPIO pin number or multiplexer channel
            is_multiplexer: True if reading from multiplexer
            channel: Multiplexer channel number (if is_multiplexer=True)
            samples: Number of consistent reads required (default 3)
            delay: Delay between reads in seconds (default 1ms)

        Returns:
            Stable boolean state or None if reads are inconsistent
        """
        import time

        # Multiplexer needs MORE samples and LONGER delays due to channel switching noise
        if is_multiplexer:
            samples = 7  # Require 7 consistent reads for MUX (instead of 3)
            delay = 0.003  # 3ms between samples for MUX (instead of 1ms)

        readings = []
        for i in range(samples):
            if is_multiplexer and self.multiplexer:
                # For multiplexer, select channel and read
                value = self.multiplexer.read_channel(channel)
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
                if not self.multiplexer:
                    self.logger.error("Multiplexer not initialized", category="hardware")
                    return None
                channel = mux_channels[sensor_name]

                # Read from multiplexer channel WITH DEBOUNCING
                state = self._read_with_debounce(channel, is_multiplexer=True, channel=channel, samples=3)

                # If read is unstable (None), skip this update
                if state is None:
                    return self._last_sensor_states.get(sensor_name, False)  # Return last known good state

                # Track state changes for multiplexer sensors
                if not hasattr(self, '_last_sensor_states'):
                    self._last_sensor_states = {}

                # Only log when state actually changes AND read is stable
                if self._last_sensor_states.get(sensor_name) != state:
                    self.logger.info(f"Sensor {sensor_name} changed: {'TRIGGERED' if state else 'READY'} (MUX CH{channel})", category="hardware")
                    self._last_sensor_states[sensor_name] = state

                return state

            # Check if it's a direct sensor
            elif sensor_name in self.direct_sensor_pins:
                pin = self.direct_sensor_pins[sensor_name]

                # Read the GPIO pin WITH DEBOUNCING
                state = self._read_with_debounce(pin, is_multiplexer=False, samples=3)

                # If read is unstable (None), skip this update
                if state is None:
                    return self._last_sensor_states.get(sensor_name, False)  # Return last known good state

                # Track state changes
                if not hasattr(self, '_last_sensor_states'):
                    self._last_sensor_states = {}

                # Only log when state actually changes AND read is stable
                if self._last_sensor_states.get(sensor_name) != state:
                    self.logger.info(f"Sensor {sensor_name} changed: {'TRIGGERED' if state else 'READY'} (pin {pin})", category="hardware")
                    self._last_sensor_states[sensor_name] = state

                return state

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
        state = self.read_sensor("x_left_edge")
        self._debug_edge_sensors()
        return state

    def get_x_right_edge_sensor(self) -> Optional[bool]:
        """Read X-axis RIGHT edge sensor state"""
        return self.read_sensor("x_right_edge")

    def get_y_top_edge_sensor(self) -> Optional[bool]:
        """Read Y-axis TOP edge sensor state"""
        return self.read_sensor("y_top_edge")

    def get_y_bottom_edge_sensor(self) -> Optional[bool]:
        """Read Y-axis BOTTOM edge sensor state"""
        return self.read_sensor("y_bottom_edge")

    def _debug_edge_sensors(self):
        """Periodically print all edge sensor states for debugging"""
        import time
        if not hasattr(self, '_last_debug_time'):
            self._last_debug_time = 0
            self._debug_counter = 0

        current_time = time.time()
        self._debug_counter += 1

        # Print every 2 seconds with read counter
        if current_time - self._last_debug_time > 2.0:
            self._last_debug_time = current_time
            x_left = self.read_sensor("x_left_edge")
            x_right = self.read_sensor("x_right_edge")
            y_top = self.read_sensor("y_top_edge")
            y_bottom = self.read_sensor("y_bottom_edge")

            # Also read all piston sensors
            line_marker_up = self.read_sensor("line_marker_up_sensor")
            line_marker_down = self.read_sensor("line_marker_down_sensor")

            self.logger.debug(f"SENSOR POLLING STATUS (reads: {self._debug_counter}):", category="hardware")
            self.logger.debug(f"   Edge Sensors:", category="hardware")
            self.logger.debug(f"      X-Left: {'TRIG' if x_left else 'READY'} | X-Right: {'TRIG' if x_right else 'READY'}", category="hardware")
            self.logger.debug(f"      Y-Top: {'TRIG' if y_top else 'READY'} | Y-Bottom: {'TRIG' if y_bottom else 'READY'}", category="hardware")
            self.logger.debug(f"   Piston Sensors (sample):", category="hardware")
            self.logger.debug(f"      Line Marker Up: {'TRIG' if line_marker_up else 'READY'} | Down: {'TRIG' if line_marker_down else 'READY'}", category="hardware")
            self.logger.debug(f"   Change a sensor wire now to see it update!", category="hardware")

    # ========== LIMIT SWITCHES ==========

    def read_limit_switch(self, switch_name: str) -> Optional[bool]:
        """
        Read limit switch state

        Args:
            switch_name: Name of limit switch (e.g., 'rows_door')

        Returns:
            True if switch activated (LOW signal), False if not activated (HIGH signal), None on error
        """
        if not self.is_initialized:
            self.logger.error("GPIO not initialized", category="hardware")
            return None

        if switch_name not in self.limit_switch_pins:
            self.logger.error(f"Unknown limit switch: {switch_name}", category="hardware")
            return None

        try:
            pin = self.limit_switch_pins[switch_name]
            # Switch activated = LOW signal (pressed/closed)
            # Switch not activated = HIGH signal (open)
            state = GPIO.input(pin)
            activated = not state  # Invert: LOW = activated (True), HIGH = not activated (False)
            return activated
        except Exception as e:
            self.logger.error(f"Error reading limit switch {switch_name}: {e}", category="hardware")
            return None

    def get_all_sensor_states(self) -> Dict[str, bool]:
        """
        Read all sensor states

        Returns:
            Dictionary mapping sensor names to their states
        """
        states = {}
        for sensor_name in self.sensor_pins:
            state = self.read_sensor(sensor_name)
            if state is not None:
                states[sensor_name] = state
        return states

    def get_all_limit_switch_states(self) -> Dict[str, bool]:
        """
        Read all limit switch states

        Returns:
            Dictionary mapping limit switch names to their states
        """
        states = {}
        for switch_name in self.limit_switch_pins:
            state = self.read_limit_switch(switch_name)
            if state is not None:
                states[switch_name] = state
        return states

    # Note: Door limit switch has been moved to Arduino GRBL
    # Use hardware_interface.get_door_switch() instead

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
                    time.sleep(0.001)  # 1ms between reads

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
                        time.sleep(0.001)

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

    # ========== CONTINUOUS SWITCH POLLING ==========

    def start_switch_polling(self):
        """Start continuous polling thread to monitor all switches"""
        if self.polling_active:
            self.logger.warning("Polling thread already running", category="hardware")
            return

        self.logger.info("Starting continuous switch polling thread...", category="hardware")
        self.logger.info("   This thread will monitor ALL switches and log state changes", category="hardware")
        self.logger.info("   Poll interval: 100ms (10 times per second)", category="hardware")

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
        self.logger.info("Switch polling thread started!", category="hardware")

        poll_count = 0
        debounce_counters = {}  # Track consecutive readings for debouncing
        DEBOUNCE_COUNT = 3  # Require 3 consecutive same readings to confirm change

        while self.polling_active:
            try:
                poll_count += 1

                # Poll all direct sensor switches (edge sensors)
                for sensor_name, pin in self.direct_sensor_pins.items():
                    try:
                        # Read pin multiple times for stability
                        current_state = GPIO.input(pin)

                        # Debounce: require multiple consecutive same readings
                        last_confirmed_state = self.switch_states.get(sensor_name)

                        if sensor_name not in debounce_counters:
                            debounce_counters[sensor_name] = {'pending_state': None, 'count': 0}

                        debounce = debounce_counters[sensor_name]

                        # First read - initialize immediately
                        if last_confirmed_state is None:
                            self.switch_states[sensor_name] = current_state
                            self.logger.debug(f"SWITCH INITIAL STATE: {sensor_name} = {'HIGH (CLOSED/ON)' if current_state else 'LOW (OPEN/OFF)'} [pin {pin}]", category="hardware")
                            self.logger.debug(f"   To change this switch, physically connect/disconnect pin {pin} to GND or 3.3V", category="hardware")
                            debounce['pending_state'] = current_state
                            debounce['count'] = DEBOUNCE_COUNT
                        else:
                            # Check if this reading matches pending state
                            if debounce['pending_state'] == current_state:
                                debounce['count'] += 1
                            else:
                                # State is different, start new debounce sequence
                                debounce['pending_state'] = current_state
                                debounce['count'] = 1

                            # If we have enough consecutive readings and it's different from confirmed state
                            if debounce['count'] >= DEBOUNCE_COUNT and current_state != last_confirmed_state:
                                # State change confirmed!
                                self.switch_states[sensor_name] = current_state
                                old_state_str = 'HIGH (CLOSED/ON)' if last_confirmed_state else 'LOW (OPEN/OFF)'
                                new_state_str = 'HIGH (CLOSED/ON)' if current_state else 'LOW (OPEN/OFF)'
                                self.logger.info("=== SWITCH CHANGED ===", category="hardware")
                                self.logger.info(f"   Switch: {sensor_name}", category="hardware")
                                self.logger.info(f"   Pin: {pin}", category="hardware")
                                self.logger.info(f"   Old: {old_state_str}", category="hardware")
                                self.logger.info(f"   New: {new_state_str}", category="hardware")
                                self.logger.info(f"   Poll: #{poll_count}", category="hardware")
                                self.logger.info("=======================", category="hardware")

                    except Exception as e:
                        self.logger.error(f"Error reading {sensor_name} on pin {pin}: {e}", category="hardware")

                # Poll multiplexer switches (piston position sensors)
                if self.multiplexer:
                    channels = self.multiplexer_config.get('channels', {})
                    for sensor_name, channel in channels.items():
                        try:
                            current_state = self.multiplexer.read_channel(channel)
                            switch_key = f"mux_{sensor_name}"
                            last_state = self.switch_states.get(switch_key)

                            # Log state change
                            if last_state is None:
                                # First read - initialize
                                self.switch_states[switch_key] = current_state
                                self.logger.debug(f"MUX SWITCH INITIAL: {sensor_name} = {'HIGH (CLOSED/ON)' if current_state else 'LOW (OPEN/OFF)'} [channel {channel}]", category="hardware")
                            elif last_state != current_state:
                                # State changed!
                                self.switch_states[switch_key] = current_state
                                self.logger.info(f"MUX SWITCH CHANGED: {sensor_name} = {'HIGH (CLOSED/ON)' if current_state else 'LOW (OPEN/OFF)'} [channel {channel}] (poll #{poll_count})", category="hardware")

                        except Exception as e:
                            self.logger.error(f"Error reading mux {sensor_name} on channel {channel}: {e}", category="hardware")

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

                # Status update every 100 polls (10 seconds at 100ms interval)
                if poll_count % 100 == 0:
                    edge_count = len(self.direct_sensor_pins)
                    mux_count = len(self.multiplexer_config.get('channels', {})) if self.multiplexer else 0
                    limit_count = len(self.limit_switch_pins)
                    total = edge_count + mux_count + limit_count
                    self.logger.debug(f"Polling heartbeat: {poll_count} polls completed, monitoring {total} switches ({edge_count} edge + {mux_count} mux + {limit_count} limit)", category="hardware")

                # Sleep 100ms between polls (10 Hz)
                time.sleep(0.1)

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

        test_logger.info("Reading all limit switches...", category="hardware")
        switch_states = gpio.get_all_limit_switch_states()
        for switch, state in switch_states.items():
            test_logger.info(f"  {switch}: {'ACTIVATED' if state else 'INACTIVE'}", category="hardware")

        # Cleanup
        gpio.cleanup()
    else:
        test_logger.error("Failed to initialize GPIO", category="hardware")

    test_logger.info("="*60, category="hardware")
    test_logger.info("Test completed", category="hardware")
    test_logger.info("="*60, category="hardware")

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
from hardware.multiplexer import CD74HC4067Multiplexer

# Try to import RPi.GPIO, fall back to mock if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    print("✓ RPi.GPIO library loaded successfully")
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    print("⚠ RPi.GPIO not available - running in mock mode")
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
            print(f"MOCK GPIO: setmode({mode})")

        def setwarnings(self, enabled):
            print(f"MOCK GPIO: setwarnings({enabled})")

        def setup(self, pin, mode, pull_up_down=None):
            self._pin_modes[pin] = mode
            if mode == "OUT":
                self._pin_states[pin] = False
            print(f"MOCK GPIO: setup(pin={pin}, mode={mode}, pull_up_down={pull_up_down})")

        def output(self, pin, state):
            self._pin_states[pin] = state
            print(f"MOCK GPIO: output(pin={pin}, state={'HIGH' if state else 'LOW'})")

        def input(self, pin):
            # Return HIGH for sensor pins (simulating not triggered)
            state = self._pin_states.get(pin, True)
            return state

        def cleanup(self):
            print("MOCK GPIO: cleanup()")
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
        self.config = self._load_config(config_path)
        self.gpio_config = self.config.get("hardware_config", {}).get("raspberry_pi", {})
        self.is_initialized = False

        # Pin mappings from settings
        self.piston_pins = self.gpio_config.get("pistons", {})
        self.multiplexer_config = self.gpio_config.get("multiplexer", {})
        self.direct_sensor_pins = self.gpio_config.get("direct_sensors", {})
        self.limit_switch_pins = self.gpio_config.get("limit_switches", {})
        self.multiplexer = None  # Will be initialized later

        # Polling thread for continuous switch monitoring
        self.polling_thread = None
        self.polling_active = False
        self.switch_states = {}  # Track last known state of all switches

        print(f"\n{'='*60}")
        print("Raspberry Pi GPIO Configuration")
        print(f"{'='*60}")
        print(f"GPIO Library: {'REAL RPi.GPIO' if GPIO_AVAILABLE else '⚠️  MOCK GPIO (NOT READING REAL PINS!)'}")
        print(f"GPIO Type: {type(GPIO).__name__}")
        print(f"GPIO Module: {GPIO.__class__.__module__ if hasattr(GPIO, '__class__') else 'N/A'}")

        if not GPIO_AVAILABLE:
            print(f"\n⚠️⚠️⚠️  WARNING  ⚠️⚠️⚠️")
            print(f"MOCK GPIO IS BEING USED!")
            print(f"Real hardware sensors WILL NOT BE READ!")
            print(f"Make sure RPi.GPIO is installed: pip3 install RPi.GPIO")
            print(f"⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️\n")

        print(f"Piston pins: {self.piston_pins}")
        print(f"Multiplexer config: {self.multiplexer_config}")
        print(f"Direct sensor pins: {self.direct_sensor_pins}")
        print(f"Limit switch pins: {self.limit_switch_pins}")
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
        Initialize GPIO pins for pistons, sensors, and limit switches

        Returns:
            True if initialization successful, False otherwise
        """
        if self.is_initialized:
            print("GPIO already initialized")
            return True

        # Check if running on Raspberry Pi
        try:
            import RPi.GPIO as GPIO_TEST
        except (ImportError, RuntimeError) as e:
            error_msg = "❌ NOT RUNNING ON RASPBERRY PI - RPi.GPIO module not available or not on Pi hardware"
            print(f"\n{error_msg}")
            print("   This application requires Raspberry Pi hardware to run in Real Hardware mode.")
            print("   Switch to Simulation mode in Hardware Settings to test without Pi hardware.\n")
            raise RuntimeError(error_msg)

        try:
            # Set GPIO mode (BCM or BOARD)
            gpio_mode = self.gpio_config.get("gpio_mode", "BCM")
            print(f"Setting GPIO mode: {gpio_mode}")

            try:
                if gpio_mode == "BCM":
                    GPIO.setmode(GPIO.BCM)
                else:
                    GPIO.setmode(GPIO.BOARD)
                GPIO.setwarnings(False)
                print(f"✓ GPIO mode set to {gpio_mode}")
            except Exception as e:
                raise RuntimeError(f"Failed to set GPIO mode: {str(e)}. Check GPIO permissions (run with sudo?)")

            # Setup piston pins as outputs (default LOW = retracted/up)
            print(f"\nInitializing {len(self.piston_pins)} piston outputs...")
            for piston_name, pin in self.piston_pins.items():
                try:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)
                    print(f"  ✓ Piston '{piston_name}' on GPIO {pin}")
                except Exception as e:
                    raise RuntimeError(f"Failed to setup piston '{piston_name}' on GPIO {pin}: {str(e)}")

            # Initialize multiplexer for sensor reading
            if self.multiplexer_config:
                print(f"\nInitializing multiplexer for sensor reading...")
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
                    print(f"  ✓ Multiplexer initialized")
                    print(f"  ✓ Control pins: S0={self.multiplexer_config['s0']}, S1={self.multiplexer_config['s1']}, S2={self.multiplexer_config['s2']}, S3={self.multiplexer_config['s3']}")
                    print(f"  ✓ Signal pin: {self.multiplexer_config['sig']}")
                    print(f"  ✓ Configured channels: {len(channels)}")
                except KeyError as e:
                    raise RuntimeError(f"Multiplexer config missing required key: {str(e)}. Check settings.json")
                except Exception as e:
                    raise RuntimeError(f"Failed to initialize multiplexer: {str(e)}")

            # Setup direct sensor pins as inputs with pull-down resistors
            if self.direct_sensor_pins:
                print(f"\nInitializing {len(self.direct_sensor_pins)} direct sensor inputs...")
                for sensor_name, pin in self.direct_sensor_pins.items():
                    try:
                        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                        print(f"  ✓ Sensor '{sensor_name}' on GPIO {pin}")
                    except Exception as e:
                        raise RuntimeError(f"Failed to setup sensor '{sensor_name}' on GPIO {pin}: {str(e)}")

            # Setup limit switch pins as inputs with pull-up resistors
            if self.limit_switch_pins:
                print(f"\nInitializing {len(self.limit_switch_pins)} limit switches...")
                for switch_name, pin in self.limit_switch_pins.items():
                    try:
                        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                        print(f"  ✓ Limit switch '{switch_name}' on GPIO {pin}")
                    except Exception as e:
                        raise RuntimeError(f"Failed to setup limit switch '{switch_name}' on GPIO {pin}: {str(e)}")

            self.is_initialized = True
            print("\n✓ Raspberry Pi GPIO initialized successfully")

            # Start continuous polling thread for all switches
            self.start_switch_polling()

            return True

        except RuntimeError as e:
            # Re-raise RuntimeError with our detailed message
            print(f"\n✗ GPIO Initialization Failed: {str(e)}\n")
            raise
        except Exception as e:
            error_msg = f"Unexpected GPIO error: {type(e).__name__}: {str(e)}"
            print(f"\n✗ {error_msg}\n")
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
            print("GPIO not initialized")
            return False

        if piston_name not in self.piston_pins:
            print(f"Unknown piston: {piston_name}")
            return False

        try:
            pin = self.piston_pins[piston_name]
            # HIGH = extended/down, LOW = retracted/up
            gpio_state = GPIO.HIGH if state == "down" else GPIO.LOW
            GPIO.output(pin, gpio_state)
            print(f"Piston '{piston_name}' set to {state.upper()} (GPIO {pin} = {'HIGH' if gpio_state else 'LOW'})")
            return True
        except Exception as e:
            print(f"Error setting piston {piston_name}: {e}")
            return False

    def piston_up(self, piston_name: str) -> bool:
        """Retract piston (set to UP position)"""
        return self.set_piston(piston_name, "up")

    def piston_down(self, piston_name: str) -> bool:
        """Extend piston (set to DOWN position)"""
        return self.set_piston(piston_name, "down")

    # ========== DUAL LINE MOTOR PISTON CONTROL ==========

    def line_motor_piston_left_up(self) -> bool:
        """Retract line motor LEFT piston"""
        return self.piston_up("line_motor_piston_left")

    def line_motor_piston_left_down(self) -> bool:
        """Extend line motor LEFT piston"""
        return self.piston_down("line_motor_piston_left")

    def line_motor_piston_right_up(self) -> bool:
        """Retract line motor RIGHT piston"""
        return self.piston_up("line_motor_piston_right")

    def line_motor_piston_right_down(self) -> bool:
        """Extend line motor RIGHT piston"""
        return self.piston_down("line_motor_piston_right")

    def line_motor_piston_up(self) -> bool:
        """Retract BOTH line motor pistons (left and right)"""
        left_ok = self.line_motor_piston_left_up()
        right_ok = self.line_motor_piston_right_up()
        return left_ok and right_ok

    def line_motor_piston_down(self) -> bool:
        """Extend BOTH line motor pistons (left and right)"""
        left_ok = self.line_motor_piston_left_down()
        right_ok = self.line_motor_piston_right_down()
        return left_ok and right_ok

    # ========== SENSOR READING METHODS ==========

    def read_sensor(self, sensor_name: str) -> Optional[bool]:
        """
        Read sensor state (via multiplexer or direct GPIO)

        Args:
            sensor_name: Name of sensor (e.g., 'line_marker_up_sensor')

        Returns:
            True if sensor triggered (HIGH signal), False if not triggered (LOW signal), None on error
        """
        if not self.is_initialized:
            print("GPIO not initialized")
            return None

        try:
            # Check if sensor is connected via multiplexer
            mux_channels = self.multiplexer_config.get('channels', {})
            if sensor_name in mux_channels:
                if not self.multiplexer:
                    print(f"Multiplexer not initialized")
                    return None
                channel = mux_channels[sensor_name]
                # Read from multiplexer channel
                state = self.multiplexer.read_channel(channel)
                return state  # HIGH = triggered (True), LOW = not triggered (False)

            # Check if it's a direct sensor
            elif sensor_name in self.direct_sensor_pins:
                pin = self.direct_sensor_pins[sensor_name]

                # Read the GPIO pin - THIS IS THE CRITICAL READ
                state = GPIO.input(pin)

                # Debug: Log ALL reads for edge sensors (not just changes)
                if sensor_name in ['x_left_edge', 'x_right_edge', 'y_top_edge', 'y_bottom_edge']:
                    if not hasattr(self, '_last_edge_states'):
                        self._last_edge_states = {}
                        self._edge_read_count = {}

                    # Count reads
                    self._edge_read_count[sensor_name] = self._edge_read_count.get(sensor_name, 0) + 1

                    # Log changes with read count
                    if self._last_edge_states.get(sensor_name) != state:
                        print(f"🔍 EDGE SENSOR CHANGED: {sensor_name} = {'HIGH (TRIGGERED)' if state else 'LOW (READY)'} (pin {pin}, read #{self._edge_read_count[sensor_name]})")
                        self._last_edge_states[sensor_name] = state

                    # Every 50 reads, show we're still polling (even if no change)
                    if self._edge_read_count[sensor_name] % 50 == 0:
                        print(f"   ✓ Still polling {sensor_name}: {'TRIG' if state else 'READY'} (read #{self._edge_read_count[sensor_name]})")

                return state  # HIGH = triggered (True), LOW = not triggered (False)

            else:
                print(f"Unknown sensor: {sensor_name}")
                return None

        except Exception as e:
            print(f"Error reading sensor {sensor_name}: {e}")
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

            print(f"\n📊 SENSOR POLLING STATUS (reads: {self._debug_counter}):")
            print(f"   Edge Sensors:")
            print(f"      X-Left: {'TRIG' if x_left else 'READY'} | X-Right: {'TRIG' if x_right else 'READY'}")
            print(f"      Y-Top: {'TRIG' if y_top else 'READY'} | Y-Bottom: {'TRIG' if y_bottom else 'READY'}")
            print(f"   Piston Sensors (sample):")
            print(f"      Line Marker Up: {'TRIG' if line_marker_up else 'READY'} | Down: {'TRIG' if line_marker_down else 'READY'}")
            print(f"   💡 Change a sensor wire now to see it update!\n")

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
            print("GPIO not initialized")
            return None

        if switch_name not in self.limit_switch_pins:
            print(f"Unknown limit switch: {switch_name}")
            return None

        try:
            pin = self.limit_switch_pins[switch_name]
            # Switch activated = LOW signal (pressed/closed)
            # Switch not activated = HIGH signal (open)
            state = GPIO.input(pin)
            activated = not state  # Invert: LOW = activated (True), HIGH = not activated (False)
            return activated
        except Exception as e:
            print(f"Error reading limit switch {switch_name}: {e}")
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

    # ========== CONTINUOUS SWITCH POLLING ==========

    def start_switch_polling(self):
        """Start continuous polling thread to monitor all switches"""
        if self.polling_active:
            print("⚠️ Polling thread already running")
            return

        print("\n🔄 Starting continuous switch polling thread...")
        print("   This thread will monitor ALL switches and log state changes")
        print("   Poll interval: 100ms (10 times per second)\n")

        self.polling_active = True
        self.polling_thread = threading.Thread(target=self._poll_switches_continuously, daemon=True)
        self.polling_thread.start()

    def stop_switch_polling(self):
        """Stop the continuous polling thread"""
        if self.polling_active:
            print("🛑 Stopping switch polling thread...")
            self.polling_active = False
            if self.polling_thread:
                self.polling_thread.join(timeout=1.0)
            print("✓ Polling thread stopped")

    def _poll_switches_continuously(self):
        """Background thread that continuously polls all switches and logs changes"""
        print("✅ Switch polling thread started!\n")

        poll_count = 0

        while self.polling_active:
            try:
                poll_count += 1

                # Poll all direct sensor switches (edge sensors)
                for sensor_name, pin in self.direct_sensor_pins.items():
                    try:
                        current_state = GPIO.input(pin)
                        last_state = self.switch_states.get(sensor_name)

                        # Log state change
                        if last_state is None:
                            # First read - initialize
                            self.switch_states[sensor_name] = current_state
                            print(f"🔌 SWITCH INITIAL STATE: {sensor_name} = {'HIGH (CLOSED/ON)' if current_state else 'LOW (OPEN/OFF)'} [pin {pin}]")
                        elif last_state != current_state:
                            # State changed!
                            self.switch_states[sensor_name] = current_state
                            print(f"🔔 SWITCH CHANGED: {sensor_name} = {'HIGH (CLOSED/ON)' if current_state else 'LOW (OPEN/OFF)'} [pin {pin}] (poll #{poll_count})")

                    except Exception as e:
                        print(f"❌ Error reading {sensor_name} on pin {pin}: {e}")

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
                                print(f"🔌 MUX SWITCH INITIAL: {sensor_name} = {'HIGH (CLOSED/ON)' if current_state else 'LOW (OPEN/OFF)'} [channel {channel}]")
                            elif last_state != current_state:
                                # State changed!
                                self.switch_states[switch_key] = current_state
                                print(f"🔔 MUX SWITCH CHANGED: {sensor_name} = {'HIGH (CLOSED/ON)' if current_state else 'LOW (OPEN/OFF)'} [channel {channel}] (poll #{poll_count})")

                        except Exception as e:
                            print(f"❌ Error reading mux {sensor_name} on channel {channel}: {e}")

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
                            print(f"🔌 LIMIT SWITCH INITIAL: {switch_name} = {'ACTIVATED (CLOSED)' if current_state else 'INACTIVE (OPEN)'} [pin {pin}]")
                        elif last_state != current_state:
                            # State changed!
                            self.switch_states[switch_key] = current_state
                            print(f"🔔 LIMIT SWITCH CHANGED: {switch_name} = {'ACTIVATED (CLOSED)' if current_state else 'INACTIVE (OPEN)'} [pin {pin}] (poll #{poll_count})")

                    except Exception as e:
                        print(f"❌ Error reading limit switch {switch_name} on pin {pin}: {e}")

                # Status update every 100 polls (10 seconds at 100ms interval)
                if poll_count % 100 == 0:
                    edge_count = len(self.direct_sensor_pins)
                    mux_count = len(self.multiplexer_config.get('channels', {})) if self.multiplexer else 0
                    limit_count = len(self.limit_switch_pins)
                    total = edge_count + mux_count + limit_count
                    print(f"💓 Polling heartbeat: {poll_count} polls completed, monitoring {total} switches ({edge_count} edge + {mux_count} mux + {limit_count} limit)")

                # Sleep 100ms between polls (10 Hz)
                time.sleep(0.1)

            except Exception as e:
                print(f"❌ Polling thread error: {e}")
                time.sleep(0.1)

        print("🛑 Polling thread exiting")

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
                    print("✓ Multiplexer cleanup completed")

                GPIO.cleanup()
                self.is_initialized = False
                print("✓ GPIO cleanup completed")
            except Exception as e:
                print(f"Error during GPIO cleanup: {e}")


if __name__ == "__main__":
    """Test GPIO interface"""
    print("\n" + "="*60)
    print("Raspberry Pi GPIO Interface Test")
    print("="*60 + "\n")

    # Create and initialize GPIO interface
    gpio = RaspberryPiGPIO()

    if gpio.initialize():
        print("\nTesting piston control...")
        # Test each piston
        for piston_name in gpio.piston_pins:
            print(f"\nTesting {piston_name}:")
            gpio.piston_down(piston_name)
            time.sleep(0.5)
            gpio.piston_up(piston_name)
            time.sleep(0.5)

        print("\nReading all sensors...")
        sensor_states = gpio.get_all_sensor_states()
        for sensor, state in sensor_states.items():
            print(f"  {sensor}: {'TRIGGERED' if state else 'READY'}")

        print("\nReading all limit switches...")
        switch_states = gpio.get_all_limit_switch_states()
        for switch, state in switch_states.items():
            print(f"  {switch}: {'ACTIVATED' if state else 'INACTIVE'}")

        # Cleanup
        gpio.cleanup()
    else:
        print("✗ Failed to initialize GPIO")

    print("\n" + "="*60)
    print("Test completed")
    print("="*60 + "\n")

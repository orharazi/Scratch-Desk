#!/usr/bin/env python3
"""
MODIFIED raspberry_pi_gpio.py with INVERTED EDGE SENSOR LOGIC
==============================================================
This version treats edge sensors as ACTIVE-LOW with PULL-UP resistors
"""

import json
import time
import threading
from typing import Dict, Optional
from hardware.implementations.real.raspberry_pi.multiplexer import CD74HC4067Multiplexer
from core.logger import get_logger

# Module-level logger
module_logger = get_logger()

# Import RPi.GPIO
import RPi.GPIO as GPIO

class RaspberryPiGPIO:
    """Modified version with inverted edge sensor logic"""

    def __init__(self, config_path: str = "config/settings.json"):
        self.logger = get_logger()
        self.config = self._load_config(config_path)
        self.gpio_config = self.config.get("hardware_config", {}).get("raspberry_pi", {})
        self.is_initialized = False

        # Pin mappings from settings
        self.piston_pins = self.gpio_config.get("pistons", {})
        self.multiplexer_config = self.gpio_config.get("multiplexer", {})
        self.direct_sensor_pins = self.gpio_config.get("direct_sensors", {})
        self.limit_switch_pins = self.gpio_config.get("limit_switches", {})
        self.multiplexer = None

        # State tracking
        self._last_sensor_states = {}
        self.polling_thread = None
        self.polling_active = False
        self.switch_states = {}

        self.logger.warning("="*60, category="hardware")
        self.logger.warning("INVERTED EDGE SENSOR LOGIC TEST", category="hardware")
        self.logger.warning("Edge sensors use PULL-UP, ACTIVE-LOW", category="hardware")
        self.logger.warning("="*60, category="hardware")

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            module_logger.error(f"Error loading config: {e}", category="hardware")
            return {}

    def initialize(self) -> bool:
        if self.is_initialized:
            return True

        try:
            GPIO.cleanup()
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Setup piston pins
            for piston_name, pin in self.piston_pins.items():
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
                self.logger.debug(f"Piston '{piston_name}' on GPIO {pin}", category="hardware")

            # Initialize multiplexer
            if self.multiplexer_config:
                self.multiplexer = CD74HC4067Multiplexer(
                    GPIO,
                    self.multiplexer_config['s0'],
                    self.multiplexer_config['s1'],
                    self.multiplexer_config['s2'],
                    self.multiplexer_config['s3'],
                    self.multiplexer_config['sig']
                )

            # CRITICAL CHANGE: Setup edge sensors with PULL-UP instead of PULL-DOWN
            if self.direct_sensor_pins:
                self.logger.warning("Setting up edge sensors with PULL-UP resistors (INVERTED LOGIC)", category="hardware")
                for sensor_name, pin in self.direct_sensor_pins.items():
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Changed to PULL-UP!
                    initial = GPIO.input(pin)
                    # Inverted: LOW = triggered, HIGH = not triggered
                    triggered = not initial
                    self.logger.info(f"Edge sensor '{sensor_name}' on GPIO {pin}: {'LOW (TRIGGERED)' if not initial else 'HIGH (READY)'}", category="hardware")

            # Setup limit switches (keep as-is)
            for switch_name, pin in self.limit_switch_pins.items():
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            self.is_initialized = True
            self.logger.success("GPIO initialized with INVERTED edge sensor logic", category="hardware")

            # Start polling
            self.start_switch_polling()
            return True

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}", category="hardware")
            raise

    def read_sensor(self, sensor_name: str) -> Optional[bool]:
        """Read sensor with inverted logic for edge sensors"""
        if not self.is_initialized:
            return None

        try:
            # Check if it's an edge sensor
            is_edge_sensor = sensor_name in self.direct_sensor_pins

            if is_edge_sensor:
                pin = self.direct_sensor_pins[sensor_name]
                raw_state = GPIO.input(pin)
                # INVERTED LOGIC: LOW = triggered (True), HIGH = not triggered (False)
                inverted_state = not raw_state

                self.logger.debug(f"Edge sensor {sensor_name}: Raw={'HIGH' if raw_state else 'LOW'}, Inverted={'TRIGGERED' if inverted_state else 'READY'}", category="hardware")

                # Store in switch_states with inverted logic
                if sensor_name not in self.switch_states:
                    self.switch_states[sensor_name] = inverted_state

                return inverted_state

            # Multiplexer sensors (no change)
            elif sensor_name in self.multiplexer_config.get('channels', {}):
                switch_key = f"mux_{sensor_name}"
                return self.switch_states.get(switch_key, False)

            else:
                self.logger.error(f"Unknown sensor: {sensor_name}", category="hardware")
                return None

        except Exception as e:
            self.logger.error(f"Error reading sensor {sensor_name}: {e}", category="hardware")
            return None

    def start_switch_polling(self):
        """Start polling thread with inverted edge sensor logic"""
        if self.polling_active:
            return

        self.polling_active = True
        self.polling_thread = threading.Thread(target=self._poll_switches_inverted, daemon=True)
        self.polling_thread.start()
        self.logger.info("Started polling thread with INVERTED edge sensor logic", category="hardware")

    def _poll_switches_inverted(self):
        """Polling thread with inverted logic for edge sensors"""
        self.logger.info("Polling thread started (INVERTED EDGE LOGIC)", category="hardware")

        # Initialize edge sensor states with inverted logic
        for sensor_name, pin in self.direct_sensor_pins.items():
            raw_state = GPIO.input(pin)
            inverted_state = not raw_state  # INVERTED!
            self.switch_states[sensor_name] = inverted_state
            self.logger.info(f"Initial: {sensor_name} = {'TRIGGERED' if inverted_state else 'READY'} (raw={'LOW' if not raw_state else 'HIGH'})", category="hardware")

        poll_count = 0
        last_log_time = time.time()

        while self.polling_active:
            try:
                poll_count += 1

                # Poll edge sensors with inverted logic
                for sensor_name, pin in self.direct_sensor_pins.items():
                    raw_current = GPIO.input(pin)
                    inverted_current = not raw_current  # INVERTED LOGIC!

                    last_state = self.switch_states.get(sensor_name)

                    if inverted_current != last_state:
                        # State changed!
                        self.switch_states[sensor_name] = inverted_current

                        self.logger.warning("🚨🚨🚨 EDGE SENSOR CHANGE (INVERTED) 🚨🚨🚨", category="hardware")
                        self.logger.warning(f"   Sensor: {sensor_name.upper()}", category="hardware")
                        self.logger.warning(f"   GPIO Pin: {pin}", category="hardware")
                        self.logger.warning(f"   Raw GPIO: {'HIGH' if raw_current else 'LOW'}", category="hardware")
                        self.logger.warning(f"   Inverted State: {'TRIGGERED' if inverted_current else 'READY'}", category="hardware")
                        self.logger.warning(f"   Previous: {'TRIGGERED' if last_state else 'READY'}", category="hardware")
                        self.logger.warning("🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨", category="hardware")

                # Log status every 2 seconds
                if time.time() - last_log_time > 2.0:
                    last_log_time = time.time()
                    self.logger.debug(f"[Poll {poll_count}] Edge sensors (INVERTED):", category="hardware")
                    for sensor_name in self.direct_sensor_pins:
                        state = self.switch_states.get(sensor_name, False)
                        self.logger.debug(f"   {sensor_name}: {'TRIGGERED' if state else 'READY'}", category="hardware")

                # Poll multiplexer sensors (unchanged)
                if self.multiplexer:
                    channels = self.multiplexer_config.get('channels', {})
                    for sensor_name, channel in channels.items():
                        try:
                            # Read multiplexer (no inversion)
                            state = self.multiplexer.read_channel(channel)
                            switch_key = f"mux_{sensor_name}"
                            last = self.switch_states.get(switch_key)

                            if state != last:
                                self.switch_states[switch_key] = state
                                self.logger.info(f"MUX CHANGE: {sensor_name} = {'HIGH' if state else 'LOW'}", category="hardware")

                        except Exception as e:
                            pass

                time.sleep(0.025)  # 25ms poll interval

            except Exception as e:
                self.logger.error(f"Polling error: {e}", category="hardware")
                time.sleep(0.1)

    # Edge sensor getters with inverted logic
    def get_x_left_edge_sensor(self) -> Optional[bool]:
        return self.read_sensor("x_left_edge")

    def get_x_right_edge_sensor(self) -> Optional[bool]:
        return self.read_sensor("x_right_edge")

    def get_y_top_edge_sensor(self) -> Optional[bool]:
        return self.read_sensor("y_top_edge")

    def get_y_bottom_edge_sensor(self) -> Optional[bool]:
        return self.read_sensor("y_bottom_edge")

    # Piston controls (unchanged)
    def set_piston(self, piston_name: str, state: str) -> bool:
        if not self.is_initialized:
            return False

        if piston_name not in self.piston_pins:
            return False

        try:
            pin = self.piston_pins[piston_name]
            gpio_state = GPIO.HIGH if state == "down" else GPIO.LOW
            GPIO.output(pin, gpio_state)
            return True
        except Exception as e:
            self.logger.error(f"Error setting piston: {e}", category="hardware")
            return False

    def cleanup(self):
        if self.is_initialized:
            self.polling_active = False
            if self.polling_thread:
                self.polling_thread.join(timeout=1.0)
            GPIO.cleanup()
            self.is_initialized = False

if __name__ == "__main__":
    print("Testing inverted edge sensor logic...")
    gpio = RaspberryPiGPIO()

    if gpio.initialize():
        print("\nMonitoring edge sensors with INVERTED logic...")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                time.sleep(0.5)
                # Read and display edge sensor states
                x_left = gpio.get_x_left_edge_sensor()
                x_right = gpio.get_x_right_edge_sensor()
                y_top = gpio.get_y_top_edge_sensor()
                y_bottom = gpio.get_y_bottom_edge_sensor()

                print(f"\rX-L: {'TRIG' if x_left else 'RDY '} | X-R: {'TRIG' if x_right else 'RDY '} | Y-T: {'TRIG' if y_top else 'RDY '} | Y-B: {'TRIG' if y_bottom else 'RDY '}", end="", flush=True)

        except KeyboardInterrupt:
            print("\n\nStopping...")

        gpio.cleanup()
    else:
        print("Failed to initialize")
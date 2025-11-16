#!/usr/bin/env python3
"""
CD74HC4067 16-Channel Multiplexer Control Module
=================================================

This module handles communication with the CD74HC4067 analog/digital multiplexer
to read multiple sensors through a single GPIO pin on the Raspberry Pi.

Hardware Connection:
- S0, S1, S2, S3: Channel select pins (4-bit binary address)
- SIG: Signal pin for reading sensor values
- Channels 0-15: Up to 16 sensors can be connected

The multiplexer allows reading 12 piston position sensors through one GPIO pin,
saving GPIO pins on the Raspberry Pi.
"""

import time
from core.logger import get_logger


class CD74HC4067Multiplexer:
    """Control CD74HC4067 16-channel multiplexer for sensor reading"""

    def __init__(self, gpio_lib, s0_pin, s1_pin, s2_pin, s3_pin, sig_pin):
        """
        Initialize multiplexer with GPIO pins

        Args:
            gpio_lib: GPIO library (RPi.GPIO or mock)
            s0_pin: GPIO pin for S0 (bit 0)
            s1_pin: GPIO pin for S1 (bit 1)
            s2_pin: GPIO pin for S2 (bit 2)
            s3_pin: GPIO pin for S3 (bit 3)
            sig_pin: GPIO pin for SIG (signal/output)
        """
        self.logger = get_logger()
        self.GPIO = gpio_lib
        self.s0 = s0_pin
        self.s1 = s1_pin
        self.s2 = s2_pin
        self.s3 = s3_pin
        self.sig = sig_pin

        # Setup GPIO pins
        self._setup_pins()

        self.logger.info(
            f"CD74HC4067 Multiplexer initialized: S0={s0_pin}, S1={s1_pin}, S2={s2_pin}, S3={s3_pin}, SIG={sig_pin}",
            category="hardware"
        )

    def _setup_pins(self):
        """Setup GPIO pins for multiplexer control"""
        # Channel select pins as outputs
        self.GPIO.setup(self.s0, self.GPIO.OUT)
        self.GPIO.setup(self.s1, self.GPIO.OUT)
        self.GPIO.setup(self.s2, self.GPIO.OUT)
        self.GPIO.setup(self.s3, self.GPIO.OUT)

        # Signal pin as input with pull-down resistor
        self.GPIO.setup(self.sig, self.GPIO.IN, pull_up_down=self.GPIO.PUD_DOWN)

        # Initialize all select pins to LOW (channel 0)
        self.GPIO.output(self.s0, self.GPIO.LOW)
        self.GPIO.output(self.s1, self.GPIO.LOW)
        self.GPIO.output(self.s2, self.GPIO.LOW)
        self.GPIO.output(self.s3, self.GPIO.LOW)

    def select_channel(self, channel):
        """
        Select multiplexer channel (0-15)

        Args:
            channel: Channel number (0-15)
        """
        if not 0 <= channel <= 15:
            raise ValueError(f"Channel must be 0-15, got {channel}")

        # Convert channel to 4-bit binary and set pins
        # Bit 0 -> S0, Bit 1 -> S1, Bit 2 -> S2, Bit 3 -> S3
        self.GPIO.output(self.s0, self.GPIO.HIGH if (channel & 0b0001) else self.GPIO.LOW)
        self.GPIO.output(self.s1, self.GPIO.HIGH if (channel & 0b0010) else self.GPIO.LOW)
        self.GPIO.output(self.s2, self.GPIO.HIGH if (channel & 0b0100) else self.GPIO.LOW)
        self.GPIO.output(self.s3, self.GPIO.HIGH if (channel & 0b1000) else self.GPIO.LOW)

        # Small delay to allow multiplexer to settle
        time.sleep(0.0001)  # 100 microseconds

    def read_channel(self, channel):
        """
        Read digital value from specific channel

        Args:
            channel: Channel number (0-15)

        Returns:
            bool: True if sensor is triggered (HIGH), False otherwise
        """
        self.select_channel(channel)

        # Small delay to allow signal to stabilize
        time.sleep(0.0001)  # 100 microseconds

        # Read digital value from SIG pin
        value = self.GPIO.input(self.sig)

        # Debug logging for channel reads (reduced frequency)
        if not hasattr(self, '_debug_reads'):
            self._debug_reads = 0
            self._last_channel_states = {}

        self._debug_reads += 1

        # Log when a channel state changes
        if self._last_channel_states.get(channel) != value:
            self.logger.debug(
                f"MUX CHANNEL {channel} CHANGED: {'HIGH (TRIG)' if value else 'LOW (READY)'}",
                category="hardware"
            )
            self._last_channel_states[channel] = value

        return bool(value)

    def cleanup(self):
        """Cleanup GPIO pins"""
        # Set all select pins to LOW
        self.GPIO.output(self.s0, self.GPIO.LOW)
        self.GPIO.output(self.s1, self.GPIO.LOW)
        self.GPIO.output(self.s2, self.GPIO.LOW)
        self.GPIO.output(self.s3, self.GPIO.LOW)

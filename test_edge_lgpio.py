#!/usr/bin/env python3
"""
Test edge switches using lgpio directly
"""

import time
import lgpio
from core.logger import get_logger

logger = get_logger()

def main():
    logger.warning("="*80, category="test")
    logger.warning("EDGE SWITCH TEST - USING LGPIO DIRECTLY", category="test")
    logger.warning("="*80, category="test")

    # Edge switch pins from settings.json
    edge_pins = {
        'x_left_edge': 4,
        'x_right_edge': 17,
        'y_top_edge': 7,
        'y_bottom_edge': 8
    }

    h = None
    try:
        # Open the GPIO chip
        h = lgpio.gpiochip_open(0)
        logger.warning(f"Opened GPIO chip, handle: {h}", category="test")

        # Setup pins as inputs with pull-up resistors
        logger.warning("Setting up edge switch pins:", category="test")
        for name, pin in edge_pins.items():
            try:
                # Claim the GPIO for input with pull-up
                lgpio.gpio_claim_input(h, pin, lgpio.SET_PULL_UP)
                logger.warning(f"✓ {name:20s} on GPIO pin {pin}", category="test")
            except Exception as e:
                logger.error(f"✗ {name:20s} on GPIO pin {pin}: {e}", category="test")

        logger.warning("="*80, category="test")
        logger.warning("MONITORING EDGE SWITCHES FOR 30 SECONDS", category="test")
        logger.warning("PRESS ANY EDGE SWITCH TO SEE STATE CHANGES", category="test")
        logger.warning("="*80, category="test")

        # Store last known states
        last_states = {}
        for name, pin in edge_pins.items():
            try:
                raw = lgpio.gpio_read(h, pin)
                inverted = not raw  # Invert: HIGH = open, LOW = pressed
                last_states[name] = inverted
                logger.warning(f"Initial: {name:20s} = {'TRIGGERED' if inverted else 'READY'} (raw={'HIGH' if raw else 'LOW'})", category="test")
            except Exception as e:
                logger.error(f"Error reading initial state of {name}: {e}", category="test")
                last_states[name] = False

        poll_count = 0
        start_time = time.time()
        last_status_time = start_time

        while time.time() - start_time < 30:
            poll_count += 1

            # Read all edge switches
            for name, pin in edge_pins.items():
                try:
                    raw = lgpio.gpio_read(h, pin)
                    current_state = not raw  # Invert for edge switches

                    # Check for state change
                    if current_state != last_states[name]:
                        logger.warning("="*80, category="test")
                        logger.warning("🚨 STATE CHANGE DETECTED! 🚨", category="test")
                        logger.warning(f"SWITCH: {name}", category="test")
                        logger.warning(f"PIN: {pin}", category="test")
                        logger.warning(f"RAW GPIO: {'HIGH' if raw else 'LOW'}", category="test")
                        logger.warning(f"PREVIOUS: {'TRIGGERED' if last_states[name] else 'READY'}", category="test")
                        logger.warning(f"CURRENT: {'TRIGGERED' if current_state else 'READY'}", category="test")
                        logger.warning(f"POLL #: {poll_count}", category="test")
                        logger.warning("="*80, category="test")

                        last_states[name] = current_state

                except Exception as e:
                    logger.error(f"Error reading {name}: {e}", category="test")

            # Status every 2 seconds
            if time.time() - last_status_time > 2:
                last_status_time = time.time()
                remaining = 30 - (time.time() - start_time)
                states_str = []
                for name in edge_pins:
                    states_str.append(f"{name}:{'T' if last_states.get(name, False) else 'R'}")
                logger.warning(f"STATUS: {remaining:.0f}s left | {' | '.join(states_str)} | Poll #{poll_count}", category="test")

            time.sleep(0.025)  # 40 Hz polling

        logger.warning("="*80, category="test")
        logger.warning("TEST COMPLETE", category="test")
        logger.warning(f"Total polls: {poll_count}", category="test")
        logger.warning("="*80, category="test")

    finally:
        if h is not None:
            # Free all GPIOs
            for name, pin in edge_pins.items():
                try:
                    lgpio.gpio_free(h, pin)
                except:
                    pass
            lgpio.gpiochip_close(h)
            logger.warning("GPIO chip closed", category="test")

if __name__ == "__main__":
    main()
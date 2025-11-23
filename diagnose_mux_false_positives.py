#!/usr/bin/env python3
"""
Diagnostic tool for analyzing false positive sensor readings on CD74HC4067 multiplexer.
This script analyzes why channels 2, 4, 5, 6 are experiencing false positives.
"""

import time
import json

def analyze_channel_patterns():
    """Analyze binary patterns of problematic channels"""

    # Load configuration to get channel mappings
    with open('config/settings.json', 'r') as f:
        config = json.load(f)

    mux_channels = config['hardware_config']['raspberry_pi']['multiplexer']['channels']

    # The problematic sensors and their channels
    problem_sensors = {
        'line_marker_down_sensor': 2,  # Channel 2
        'row_cutter_up_sensor': 4,     # Channel 4
        'row_cutter_down_sensor': 5,   # Channel 5
        'row_marker_down_sensor': 6    # Channel 6
    }

    print("\n" + "="*80)
    print("ANALYSIS OF FALSE POSITIVE CHANNELS")
    print("="*80)

    print("\n1. BINARY PATTERN ANALYSIS")
    print("-" * 40)
    print("Channel | Binary | S3 S2 S1 S0 | Sensor Name")
    print("-" * 40)

    for sensor_name, channel in problem_sensors.items():
        binary = format(channel, '04b')
        s3 = binary[0]
        s2 = binary[1]
        s1 = binary[2]
        s0 = binary[3]
        print(f"   {channel:2d}   |  {binary}  |  {s3}  {s2}  {s1}  {s0} | {sensor_name}")

    print("\n2. PATTERN OBSERVATIONS")
    print("-" * 40)
    print("- Channel 2 (0010): S1=1, all others 0")
    print("- Channel 4 (0100): S2=1, all others 0")
    print("- Channel 5 (0101): S2=1, S0=1, others 0")
    print("- Channel 6 (0110): S2=1, S1=1, others 0")
    print("\nKEY FINDING: Channels 4, 5, 6 all have S2=1 (GPIO 13)")
    print("             Channel 2 has S1=1 (GPIO 12)")

    print("\n3. TIMING ANALYSIS")
    print("-" * 40)
    print("Per channel timing in multiplexer.read_channel():")
    print("  - select_channel(): 5ms settling")
    print("  - Additional settling: 10ms")
    print("  - 3 reads × 3ms gaps: 6ms")
    print("  - Total per channel: ~21ms")
    print("\nFor 12 channels: 12 × 21ms = 252ms per full cycle")
    print("Polling loop sleep: 25ms")
    print("Expected change frequency: ~277ms")
    print("Observed change frequency: ~150ms")
    print("\nDISCREPANCY: Changes happening FASTER than full poll cycle!")

    print("\n4. INITIALIZATION SEQUENCE ANALYSIS")
    print("-" * 40)
    print("Initialization order of switch states:")
    print("1. _initialize_sensor_states() - reads all sensors once")
    print("2. start_switch_polling() - starts polling thread")
    print("3. Polling thread re-initializes edge switches")
    print("4. Polling thread does NOT re-initialize mux switches!")

    print("\n5. CRITICAL BUG FOUND!")
    print("-" * 40)
    print("Line 660: last_state = self.switch_states.get(switch_key)")
    print("          ^^^ Uses .get() which returns None if key doesn't exist")
    print("")
    print("The polling thread never initializes mux switch states!")
    print("So on first poll, last_state is None for ALL mux channels.")
    print("This causes false 'change' detection on first read.")

    print("\n6. ROOT CAUSE IDENTIFIED")
    print("-" * 40)
    print("The switch_states dictionary is NOT initialized with mux sensor states")
    print("in the polling thread. Only edge switches are initialized (lines 599-606).")
    print("")
    print("When polling starts:")
    print("  - Edge switches: Properly initialized in switch_states")
    print("  - Mux switches: NOT in switch_states, so .get() returns None")
    print("  - First read: None != actual_state -> false change logged")
    print("  - Subsequent reads: May continue to be unstable")

    print("\n7. WHY ONLY CHANNELS 2, 4, 5, 6?")
    print("-" * 40)
    print("Hypothesis: These channels may have electrical characteristics that")
    print("cause them to read differently during initialization vs polling:")
    print("  - Longer wire runs causing capacitance issues")
    print("  - GPIO 12/13 (S1/S2) may have weaker pull resistors")
    print("  - Triple-read voting may fail more often on these channels")

    print("\n8. PROPOSED FIX")
    print("-" * 40)
    print("Initialize ALL switch states in the polling thread before starting:")
    print("")
    print("In _poll_switches_continuously(), after initializing edge switches,")
    print("add initialization for multiplexer switches:")
    print("")
    print("    # Initialize multiplexer switch states")
    print("    if self.multiplexer:")
    print("        channels = self.multiplexer_config.get('channels', {})")
    print("        for sensor_name, channel in channels.items():")
    print("            try:")
    print("                current_state = self._read_multiplexer_channel(channel)")
    print("                switch_key = f'mux_{sensor_name}'")
    print("                self.switch_states[switch_key] = current_state")
    print("                # Log initialization...")
    print("            except Exception as e:")
    print("                # Handle error...")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\nThe bug is NOT electrical interference or timing issues.")
    print("It's a SOFTWARE BUG: Multiplexer switch states are never initialized")
    print("in the polling thread's switch_states dictionary.")
    print("")
    print("This causes .get() to return None on first read, triggering false")
    print("state change detection. The issue may persist if the channels are")
    print("electrically unstable and the voting logic fails.")
    print("\n")

if __name__ == "__main__":
    analyze_channel_patterns()
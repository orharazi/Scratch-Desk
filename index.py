#!/usr/bin/env python3

import tkinter as tk
import sys
import os
import atexit
import signal

# Add the current directory to the Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_app import ScratchDeskGUI

# Global reference for cleanup handlers
_hardware = None
_cleaned_up = False


def _shutdown_air_pressure():
    """Turn off air pressure - called by atexit and signal handlers"""
    global _cleaned_up
    if _cleaned_up:
        return
    _cleaned_up = True
    try:
        if _hardware is not None:
            _hardware.air_pressure_valve_up()
    except:
        pass


def _signal_handler(signum, frame):
    """Handle SIGTERM/SIGINT to ensure air pressure is turned off"""
    _shutdown_air_pressure()
    sys.exit(0)


def main():
    """Main entry point for the Scratch Desk Control System"""
    global _hardware

    root = tk.Tk()
    app = ScratchDeskGUI(root)
    _hardware = app.hardware

    # Register cleanup for any exit path
    atexit.register(_shutdown_air_pressure)
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    def on_closing():
        """Handle window close (X button) - ensure air pressure is turned off"""
        _shutdown_air_pressure()
        try:
            root.destroy()
        except:
            pass

    root.protocol("WM_DELETE_WINDOW", on_closing)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _shutdown_air_pressure()
        try:
            root.destroy()
        except:
            pass


if __name__ == "__main__":
    main()

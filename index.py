#!/usr/bin/env python3

import argparse
import tkinter as tk
import sys
import os
import atexit
import signal

# Add the current directory to the Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.wayland_focus import patch_wayland_focus
patch_wayland_focus()

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

    parser = argparse.ArgumentParser(description="Scratch Desk CNC Control System")
    parser.add_argument("--grbl-debug", action="store_true",
                        help="Show only GRBL commands in terminal output")
    args = parser.parse_args()

    if args.grbl_debug:
        from core.logger import get_logger
        get_logger().set_grbl_only_mode()

    # className sets the XWayland WM_CLASS, which becomes the wlroots app_id.
    # The focus code (gui/wayland_focus.py) targets app_id 'scratch-desk' to
    # refocus the main window; without this, the root window's app_id is the
    # default 'tk' and every app_id-based wlrctl focus call matches nothing.
    root = tk.Tk(className='scratch-desk')
    app = ScratchDeskGUI(root)
    _hardware = app.hardware

    # Turn on air pressure when application starts
    _hardware.air_pressure_valve_down()

    # Register cleanup for any exit path
    atexit.register(_shutdown_air_pressure)
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    def on_closing():
        """Handle window close (X button) - safe shutdown sequence"""
        # 1. Stop execution engine if running
        try:
            if app.execution_engine.is_running:
                app.execution_engine.stop_execution()
        except Exception:
            pass

        # 2. Raise all pistons to safe position
        try:
            _hardware.line_marker_up()
            _hardware.line_cutter_up()
            _hardware.row_marker_up()
            _hardware.row_cutter_up()
        except Exception:
            pass

        # 3. Shut off air pressure
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

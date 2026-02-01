#!/usr/bin/env python3
"""
Admin Tool - Scratch Desk CNC Control System
=============================================

Administrative interface for:
- Hardware testing and motor control
- Piston and sensor management
- GRBL settings configuration
- Safety rules management (CRUD)
- System configuration editing

Usage:
    python3 admin_tool.py
"""

import tkinter as tk
import sys
import os

from admin.admin_app import AdminToolGUI


def main():
    """Main entry point for the Admin Tool"""
    root = tk.Tk()
    app = AdminToolGUI(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            root.destroy()
        except:
            pass


if __name__ == "__main__":
    main()

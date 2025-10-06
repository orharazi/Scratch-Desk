#!/usr/bin/env python3

import tkinter as tk
import sys
import os

# Add the current directory to the Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_app import ScratchDeskGUI


def main():
    """Main entry point for the Scratch Desk Control System"""
    root = tk.Tk()
    app = ScratchDeskGUI(root)
    
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
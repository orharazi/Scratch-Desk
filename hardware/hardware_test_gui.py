#!/usr/bin/env python3

"""
Hardware Test GUI
=================

Interactive GUI for testing hardware connections:
- Motor movement controls (X and Y)
- Piston control buttons
- Live sensor state monitoring
- Real-time position display
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.hardware_interface import HardwareInterface


class HardwareTestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Hardware Connection Test Interface")
        self.root.geometry("1200x800")

        # Initialize hardware
        self.hardware = HardwareInterface()
        self.is_connected = False
        self.monitor_running = False

        # Create UI
        self.create_ui()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_ui(self):
        """Create the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Connection status at top
        self.create_connection_section(main_frame, 0)

        # Left side - Motor controls
        self.create_motor_section(main_frame, 1, 0)

        # Right side - Piston and sensor monitoring
        self.create_monitoring_section(main_frame, 1, 1)

    def create_connection_section(self, parent, row):
        """Create connection status and control section"""
        frame = ttk.LabelFrame(parent, text="Connection", padding="10")
        frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Status label
        self.status_label = ttk.Label(frame, text="Not Connected",
                                     font=("Arial", 12, "bold"),
                                     foreground="red")
        self.status_label.grid(row=0, column=0, padx=5)

        # Connect button
        self.connect_btn = ttk.Button(frame, text="Connect Hardware",
                                      command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=1, padx=5)

        # Mode label
        mode = "REAL HARDWARE" if self.hardware.use_real_hardware else "MOCK MODE"
        mode_label = ttk.Label(frame, text=f"Mode: {mode}",
                              font=("Arial", 10))
        mode_label.grid(row=0, column=2, padx=5)

    def create_motor_section(self, parent, row, col):
        """Create motor control section"""
        frame = ttk.LabelFrame(parent, text="Motor Control", padding="10")
        frame.grid(row=row, column=col, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # Position display
        position_frame = ttk.LabelFrame(frame, text="Current Position", padding="10")
        position_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.x_pos_label = ttk.Label(position_frame, text="X: 0.00 cm",
                                     font=("Arial", 14, "bold"))
        self.x_pos_label.grid(row=0, column=0, padx=10)

        self.y_pos_label = ttk.Label(position_frame, text="Y: 0.00 cm",
                                     font=("Arial", 14, "bold"))
        self.y_pos_label.grid(row=0, column=1, padx=10)

        # X Motor controls
        x_frame = ttk.LabelFrame(frame, text="X Motor (Rows)", padding="10")
        x_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        ttk.Label(x_frame, text="Position (cm):").grid(row=0, column=0, sticky=tk.W)
        self.x_entry = ttk.Entry(x_frame, width=10)
        self.x_entry.insert(0, "0")
        self.x_entry.grid(row=0, column=1, padx=5)

        ttk.Button(x_frame, text="Move X",
                  command=self.move_x).grid(row=0, column=2, padx=5)

        # X Quick positions
        quick_x_frame = ttk.Frame(x_frame)
        quick_x_frame.grid(row=1, column=0, columnspan=3, pady=(10, 0))

        ttk.Button(quick_x_frame, text="X=0", width=8,
                  command=lambda: self.quick_move_x(0)).grid(row=0, column=0, padx=2)
        ttk.Button(quick_x_frame, text="X=30", width=8,
                  command=lambda: self.quick_move_x(30)).grid(row=0, column=1, padx=2)
        ttk.Button(quick_x_frame, text="X=60", width=8,
                  command=lambda: self.quick_move_x(60)).grid(row=0, column=2, padx=2)
        ttk.Button(quick_x_frame, text="X=100", width=8,
                  command=lambda: self.quick_move_x(100)).grid(row=0, column=3, padx=2)

        # Y Motor controls
        y_frame = ttk.LabelFrame(frame, text="Y Motor (Lines)", padding="10")
        y_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        ttk.Label(y_frame, text="Position (cm):").grid(row=0, column=0, sticky=tk.W)
        self.y_entry = ttk.Entry(y_frame, width=10)
        self.y_entry.insert(0, "0")
        self.y_entry.grid(row=0, column=1, padx=5)

        ttk.Button(y_frame, text="Move Y",
                  command=self.move_y).grid(row=0, column=2, padx=5)

        # Y Quick positions
        quick_y_frame = ttk.Frame(y_frame)
        quick_y_frame.grid(row=1, column=0, columnspan=3, pady=(10, 0))

        ttk.Button(quick_y_frame, text="Y=0", width=8,
                  command=lambda: self.quick_move_y(0)).grid(row=0, column=0, padx=2)
        ttk.Button(quick_y_frame, text="Y=20", width=8,
                  command=lambda: self.quick_move_y(20)).grid(row=0, column=1, padx=2)
        ttk.Button(quick_y_frame, text="Y=40", width=8,
                  command=lambda: self.quick_move_y(40)).grid(row=0, column=2, padx=2)
        ttk.Button(quick_y_frame, text="Y=70", width=8,
                  command=lambda: self.quick_move_y(70)).grid(row=0, column=3, padx=2)

        # Home button
        ttk.Button(frame, text="🏠 Home All Motors",
                  command=self.home_motors,
                  width=20).grid(row=3, column=0, pady=10)

        # Emergency stop button
        stop_btn = tk.Button(frame, text="⚠ EMERGENCY STOP",
                           command=self.emergency_stop,
                           bg="red", fg="white",
                           font=("Arial", 12, "bold"),
                           width=20, height=2)
        stop_btn.grid(row=4, column=0, pady=10)

    def create_monitoring_section(self, parent, row, col):
        """Create piston and sensor monitoring section"""
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Pistons section
        piston_frame = ttk.LabelFrame(frame, text="Piston Control", padding="10")
        piston_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.piston_widgets = {}
        pistons = [
            ("Line Marker", "line_marker_piston"),
            ("Line Cutter", "line_cutter_piston"),
            ("Line Motor", "line_motor_piston"),
            ("Row Marker", "row_marker_piston"),
            ("Row Cutter", "row_cutter_piston")
        ]

        for i, (name, piston_id) in enumerate(pistons):
            # Piston name
            ttk.Label(piston_frame, text=name, width=15).grid(row=i, column=0, sticky=tk.W, pady=2)

            # State label
            state_label = ttk.Label(piston_frame, text="UP",
                                   width=8, anchor=tk.CENTER,
                                   relief=tk.SUNKEN, background="#95A5A6")
            state_label.grid(row=i, column=1, padx=5, pady=2)

            # UP button
            up_btn = ttk.Button(piston_frame, text="↑ UP", width=8,
                              command=lambda pid=piston_id: self.piston_up(pid))
            up_btn.grid(row=i, column=2, padx=2, pady=2)

            # DOWN button
            down_btn = ttk.Button(piston_frame, text="↓ DOWN", width=8,
                                command=lambda pid=piston_id: self.piston_down(pid))
            down_btn.grid(row=i, column=3, padx=2, pady=2)

            self.piston_widgets[piston_id] = state_label

        # Tool Sensors section
        sensor_frame = ttk.LabelFrame(frame, text="Tool Sensors (Live)", padding="10")
        sensor_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.sensor_widgets = {}
        sensors = [
            ("Line Marker Sensor", "line_marker_state"),
            ("Line Cutter Sensor", "line_cutter_state"),
            ("Line Motor Sensor", "line_motor_piston_sensor"),
            ("Row Marker Sensor", "row_marker_state"),
            ("Row Cutter Sensor", "row_cutter_state")
        ]

        for i, (name, sensor_id) in enumerate(sensors):
            # Sensor name
            ttk.Label(sensor_frame, text=name, width=20).grid(row=i, column=0, sticky=tk.W, pady=2)

            # State indicator
            state_label = ttk.Label(sensor_frame, text="READY",
                                   width=12, anchor=tk.CENTER,
                                   relief=tk.SUNKEN, background="#27AE60",
                                   foreground="white", font=("Arial", 9, "bold"))
            state_label.grid(row=i, column=1, padx=5, pady=2)

            self.sensor_widgets[sensor_id] = state_label

        # Edge Detection Sensors section
        edge_frame = ttk.LabelFrame(frame, text="Edge Detection Sensors (Live)", padding="10")
        edge_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        edge_sensors = [
            ("X Left Edge", "x_left_edge"),
            ("X Right Edge", "x_right_edge"),
            ("Y Top Edge", "y_top_edge"),
            ("Y Bottom Edge", "y_bottom_edge")
        ]

        for i, (name, sensor_id) in enumerate(edge_sensors):
            # Sensor name
            ttk.Label(edge_frame, text=name, width=20).grid(row=i, column=0, sticky=tk.W, pady=2)

            # State indicator
            state_label = ttk.Label(edge_frame, text="READY",
                                   width=12, anchor=tk.CENTER,
                                   relief=tk.SUNKEN, background="#27AE60",
                                   foreground="white", font=("Arial", 9, "bold"))
            state_label.grid(row=i, column=1, padx=5, pady=2)

            self.sensor_widgets[sensor_id] = state_label

        # Limit Switches section
        limit_frame = ttk.LabelFrame(frame, text="Limit Switches (Live)", padding="10")
        limit_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))

        self.limit_switch_widgets = {}
        limit_switches = [
            ("Y Top Limit", "y_top"),
            ("Y Bottom Limit", "y_bottom"),
            ("X Right Limit", "x_right"),
            ("X Left Limit", "x_left"),
            ("Door Safety (Rows)", "rows")
        ]

        for i, (name, switch_id) in enumerate(limit_switches):
            # Switch name
            ttk.Label(limit_frame, text=name, width=20).grid(row=i, column=0, sticky=tk.W, pady=2)

            # State indicator
            state_label = ttk.Label(limit_frame, text="INACTIVE",
                                   width=12, anchor=tk.CENTER,
                                   relief=tk.SUNKEN, background="#95A5A6",
                                   foreground="white", font=("Arial", 9, "bold"))
            state_label.grid(row=i, column=1, padx=5, pady=2)

            self.limit_switch_widgets[switch_id] = state_label

    def toggle_connection(self):
        """Connect or disconnect hardware"""
        if not self.is_connected:
            # Connect
            if self.hardware.initialize():
                self.is_connected = True
                self.status_label.config(text="Connected", foreground="green")
                self.connect_btn.config(text="Disconnect")

                # Start monitoring thread
                self.monitor_running = True
                self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
                self.monitor_thread.start()

                messagebox.showinfo("Success", "Hardware connected successfully!")
            else:
                messagebox.showerror("Error", "Failed to connect to hardware")
        else:
            # Disconnect
            self.monitor_running = False
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.join(timeout=2)

            self.hardware.shutdown()
            self.is_connected = False
            self.status_label.config(text="Not Connected", foreground="red")
            self.connect_btn.config(text="Connect Hardware")

    def monitor_loop(self):
        """Monitor sensors and update display"""
        while self.monitor_running:
            try:
                # Update sensor states
                if self.hardware.use_real_hardware and self.hardware.gpio:
                    # Read all sensors
                    sensor_states = self.hardware.gpio.get_all_sensor_states()

                    for sensor_id, widget in self.sensor_widgets.items():
                        state = sensor_states.get(sensor_id, False)

                        if state:
                            widget.config(text="TRIGGERED", background="#E74C3C")
                        else:
                            widget.config(text="READY", background="#27AE60")

                    # Read all limit switches
                    limit_switch_states = self.hardware.gpio.get_all_limit_switch_states()

                    for switch_id, widget in self.limit_switch_widgets.items():
                        # For rows switch, check the limit_switch_states dict
                        if switch_id == "rows":
                            state = self.hardware.gpio.get_limit_switch_state(switch_id)
                        else:
                            # For motor limit switches (y_top, y_bottom, x_left, x_right)
                            state = self.hardware.gpio.get_limit_switch_state(switch_id)

                        if state:
                            widget.config(text="ACTIVATED", background="#E74C3C")
                        else:
                            widget.config(text="INACTIVE", background="#95A5A6")

                time.sleep(0.2)  # Update 5 times per second
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(1)

    def move_x(self):
        """Move X motor to specified position"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        try:
            position = float(self.x_entry.get())
            if self.hardware.move_x(position):
                self.x_pos_label.config(text=f"X: {position:.2f} cm")
            else:
                messagebox.showerror("Error", "Failed to move X motor")
        except ValueError:
            messagebox.showerror("Error", "Invalid position value")

    def move_y(self):
        """Move Y motor to specified position"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        try:
            position = float(self.y_entry.get())
            if self.hardware.move_y(position):
                self.y_pos_label.config(text=f"Y: {position:.2f} cm")
            else:
                messagebox.showerror("Error", "Failed to move Y motor")
        except ValueError:
            messagebox.showerror("Error", "Invalid position value")

    def quick_move_x(self, position):
        """Quick move X to preset position"""
        self.x_entry.delete(0, tk.END)
        self.x_entry.insert(0, str(position))
        self.move_x()

    def quick_move_y(self, position):
        """Quick move Y to preset position"""
        self.y_entry.delete(0, tk.END)
        self.y_entry.insert(0, str(position))
        self.move_y()

    def home_motors(self):
        """Home all motors"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        if messagebox.askyesno("Home Motors", "Move all motors to home position (0, 0)?"):
            if self.hardware.home_motors():
                self.x_pos_label.config(text="X: 0.00 cm")
                self.y_pos_label.config(text="Y: 0.00 cm")
                self.x_entry.delete(0, tk.END)
                self.x_entry.insert(0, "0")
                self.y_entry.delete(0, tk.END)
                self.y_entry.insert(0, "0")
                messagebox.showinfo("Success", "Motors homed successfully")
            else:
                messagebox.showerror("Error", "Failed to home motors")

    def emergency_stop(self):
        """Emergency stop all motors"""
        if not self.is_connected:
            return

        if self.hardware.emergency_stop():
            messagebox.showwarning("Emergency Stop", "All motors stopped!\nClick OK to resume.")
            self.hardware.resume_operation()

    def piston_up(self, piston_id):
        """Raise piston"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        method_name = f"{piston_id}_up"
        if hasattr(self.hardware, method_name):
            method = getattr(self.hardware, method_name)
            if method():
                self.piston_widgets[piston_id].config(text="UP", background="#95A5A6")
            else:
                messagebox.showerror("Error", f"Failed to raise {piston_id}")

    def piston_down(self, piston_id):
        """Lower piston"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        method_name = f"{piston_id}_down"
        if hasattr(self.hardware, method_name):
            method = getattr(self.hardware, method_name)
            if method():
                self.piston_widgets[piston_id].config(text="DOWN", background="#27AE60")
            else:
                messagebox.showerror("Error", f"Failed to lower {piston_id}")

    def on_closing(self):
        """Handle window closing"""
        if self.is_connected:
            if messagebox.askokcancel("Quit", "Disconnect hardware and quit?"):
                self.monitor_running = False
                if hasattr(self, 'monitor_thread'):
                    self.monitor_thread.join(timeout=2)
                self.hardware.shutdown()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """Main function"""
    root = tk.Tk()
    app = HardwareTestGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

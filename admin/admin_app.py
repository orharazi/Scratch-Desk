#!/usr/bin/env python3
"""
Admin Tool GUI
==============

Comprehensive administrative interface for Scratch Desk CNC Control System:
- Motor movement controls with jogging and presets
- Piston control with sensor feedback
- GRBL settings management
- Real-time status monitoring
- Command console with logging
- Safety rules management (NEW)
- System configuration editor (NEW)
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import queue
from datetime import datetime
import re

from hardware.interfaces.hardware_factory import get_hardware_interface
from core.logger import get_logger
from core.translations import t

# Import new tabs
from admin.tabs.safety_tab import SafetyTab
from admin.tabs.config_tab import ConfigTab
from admin.tabs.analytics_tab import AnalyticsTab


class AdminToolGUI:
    """Admin Tool GUI - Main Application Class"""

    def __init__(self, root, hardware=None, launched_from_app=False):
        self.root = root
        self.root.title(t("Admin Tool - Scratch Desk CNC"))
        self.root.geometry("1400x900")

        # Track if launched from main app (to avoid disconnecting shared hardware)
        self.launched_from_app = launched_from_app

        # Make window resizable
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Initialize variables
        self.hardware = hardware
        self.is_connected = hardware is not None
        self.monitor_running = False
        self._closing = False
        self.grbl_connected = False
        self.command_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Serial port variables
        self.selected_rs485_port = tk.StringVar()

        # Initialize centralized logger
        self.logger = get_logger()

        # Port selection
        self.available_ports = []
        self.selected_port = tk.StringVar(value=t("Auto-detect"))

        # Hardware mode toggle
        self.use_real_hardware = tk.BooleanVar(value=False)

        # Position tracking
        self.current_x = 0.0
        self.current_y = 0.0
        self.jog_step = tk.StringVar(value="1.0")

        # GRBL settings cache
        self.grbl_settings = {}

        # Load port mappings from config
        self.port_mappings = self.load_port_mappings()

        # Load initial hardware mode from config
        self.load_hardware_mode()

        # Initialize widget dictionaries
        self.sensor_widgets = {}
        self.sensor_connection_widgets = {}
        self.piston_widgets = {}
        self.piston_connection_widgets = {}

        # Create UI
        self.create_ui()

        # Start log processor thread
        self.log_processor_running = True
        self.log_processor_thread = threading.Thread(target=self.process_logs, daemon=True)
        self.log_processor_thread.start()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        if self.launched_from_app and self.hardware is not None:
            # Launched from main app - use existing hardware, skip auto-init
            self.root.after(100, self._setup_from_app)
        else:
            # Standalone mode - auto-initialize hardware on startup
            self.root.after(100, self.auto_initialize)

    def _setup_from_app(self):
        """Set up admin tool when launched from main app with existing hardware"""
        # Update UI to reflect connected state
        mode = t("REAL HARDWARE") if hasattr(self.hardware, 'gpio') else t("MOCK/SIMULATION")
        self.mode_label.config(text=t("Mode: {mode}", mode=mode))
        self.hw_status_label.config(text=t("Connected"), foreground="green")
        self.connect_btn.config(text=t("Disconnect"), state="disabled")
        self.hardware_mode_check.config(state="disabled")

        # Check GRBL connection
        if hasattr(self.hardware, 'grbl') and self.hardware.grbl and self.hardware.grbl.is_connected:
            self.grbl_connected = True
            self.grbl_status_label.config(text=t("Connected"), foreground="green")
            self.root.after(100, self.read_grbl_settings)
        else:
            self.grbl_status_label.config(text=t("Not Available"), foreground="orange")

        # Start monitor loop for live sensor/position updates
        self.monitor_running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

        self.enable_controls(True)
        self.log("INFO", t("Admin Tool opened from main app (shared hardware connection)"))

    def load_port_mappings(self):
        """Load GPIO port mappings from config"""
        try:
            import json
            with open('config/settings.json', 'r') as f:
                config = json.load(f)

            rpi_config = config.get('hardware_config', {}).get('raspberry_pi', {})

            mappings = {}

            # Pistons
            pistons = rpi_config.get('pistons', {})
            for name, pin in pistons.items():
                mappings[name] = {'type': 'GPIO', 'port': f'GPIO{pin}', 'pin': pin}

            # RS485 sensors
            rs485_sensors = rpi_config.get('rs485', {}).get('sensor_addresses', {})
            for name, address in rs485_sensors.items():
                mappings[name] = {'type': 'RS485', 'port': f'RS485-ADDR{address}', 'pin': address}

            # Limit switches
            limit_switches = rpi_config.get('limit_switches', {})
            for name, pin in limit_switches.items():
                mappings[name] = {'type': 'GPIO', 'port': f'GPIO{pin}', 'pin': pin}

            return mappings
        except Exception as e:
            print(f"Error loading port mappings: {e}")
            return {}

    def load_hardware_mode(self):
        """Load hardware mode from config"""
        try:
            import json
            with open('config/settings.json', 'r') as f:
                config = json.load(f)
            use_real = config.get('hardware_config', {}).get('use_real_hardware', False)
            self.use_real_hardware.set(use_real)
        except Exception as e:
            print(f"Error loading hardware mode: {e}")
            self.use_real_hardware.set(False)

    def create_ui(self):
        """Create the main user interface with tabs"""
        # Top frame for connection status
        self.create_top_bar()

        # Main notebook with tabs
        self.notebook = ttk.Notebook(self.root, padding="5")
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Set minimum size
        self.root.minsize(1200, 700)

        # Create tab frames
        self.motors_tab = ttk.Frame(self.notebook)
        self.pistons_tab = ttk.Frame(self.notebook)
        self.grbl_tab = ttk.Frame(self.notebook)
        self.safety_tab_frame = ttk.Frame(self.notebook)
        self.config_tab_frame = ttk.Frame(self.notebook)
        self.analytics_tab_frame = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.motors_tab, text=t("Motors & Position"))
        self.notebook.add(self.pistons_tab, text=t("Pistons & Sensors"))
        self.notebook.add(self.grbl_tab, text=t("GRBL"))
        self.notebook.add(self.safety_tab_frame, text=t("Safety Rules"))
        self.notebook.add(self.config_tab_frame, text=t("System Config"))
        self.notebook.add(self.analytics_tab_frame, text=t("Analytics"))

        # Create tab contents
        self.create_motors_tab()
        self.create_pistons_tab()
        self.create_grbl_tab()

        # Create new admin tabs
        self.safety_tab = SafetyTab(self.safety_tab_frame, self)
        self.config_tab = ConfigTab(self.config_tab_frame, self)
        self.analytics_tab = AnalyticsTab(self.analytics_tab_frame, self)

    def create_top_bar(self):
        """Create top status bar with connection controls"""
        top_frame = ttk.Frame(self.root, relief=tk.RIDGE, borderwidth=2)
        top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        top_frame.columnconfigure(1, weight=1)
        top_frame.rowconfigure(0, minsize=80)

        # Connection status section
        conn_frame = ttk.Frame(top_frame)
        conn_frame.grid(row=0, column=2, padx=10, pady=15, sticky="ne")

        ttk.Label(conn_frame, text=t("Hardware:"), font=("Arial", 10, "bold")).grid(row=0, column=0, padx=(0, 5))
        self.hw_status_label = ttk.Label(conn_frame, text=t("Not Connected"), foreground="red", font=("Arial", 10))
        self.hw_status_label.grid(row=0, column=1, padx=5)

        ttk.Label(conn_frame, text=t("GRBL:"), font=("Arial", 10, "bold")).grid(row=0, column=2, padx=(20, 5))
        self.grbl_status_label = ttk.Label(conn_frame, text=t("Not Connected"), foreground="red", font=("Arial", 10))
        self.grbl_status_label.grid(row=0, column=3, padx=5)

        # Port selection
        ttk.Label(conn_frame, text=t("GRBL Port:"), font=("Arial", 10, "bold")).grid(row=0, column=4, padx=(20, 5))
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.selected_port, state="readonly", width=20)
        self.port_combo.grid(row=0, column=5, padx=5)

        ttk.Label(conn_frame, text=t("RS485 Port:"), font=("Arial", 10, "bold")).grid(row=1, column=4, padx=(20, 5), pady=(8, 0))
        self.rs485_port_combo = ttk.Combobox(conn_frame, textvariable=self.selected_rs485_port, state="readonly", width=20)
        self.rs485_port_combo.grid(row=1, column=5, padx=5, pady=(8, 0))

        ttk.Button(conn_frame, text="🔄", width=3, command=self.scan_ports).grid(row=0, column=6, rowspan=2, padx=2)

        # Hardware mode toggle
        ttk.Label(conn_frame, text=t("Mode:"), font=("Arial", 10, "bold")).grid(row=0, column=7, rowspan=2, padx=(20, 5))
        self.hardware_mode_check = ttk.Checkbutton(
            conn_frame,
            text=t("Use Real Hardware"),
            variable=self.use_real_hardware,
            command=self.on_hardware_mode_changed
        )
        self.hardware_mode_check.grid(row=0, column=8, rowspan=2, padx=5)

        # Connect button
        self.connect_btn = ttk.Button(conn_frame, text=t("Connect Hardware"), command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=9, rowspan=2, padx=20)

        self.scan_ports()

        # Mode indicator and admin actions
        mode_frame = ttk.Frame(top_frame)
        mode_frame.grid(row=0, column=1, padx=10, pady=15, sticky="ne")
        self.mode_label = ttk.Label(mode_frame, text=t("Mode: Unknown"), font=("Arial", 10))
        self.mode_label.pack(anchor="e")

        ttk.Button(mode_frame, text=t("Change Admin Password"), command=self.change_admin_password).pack(anchor="e", pady=(5, 0))

        # Emergency stop
        self.emergency_btn = tk.Button(top_frame, text=t("EMERGENCY STOP"),
                                       command=self.emergency_stop,
                                       bg="red", fg="white",
                                       font=("Arial", 12, "bold"),
                                       width=15, height=2)
        self.emergency_btn.grid(row=0, column=0, padx=10, pady=15, sticky="n")

    def create_motors_tab(self):
        """Create motors control tab"""
        self.motors_tab.columnconfigure(0, weight=1, minsize=400)
        self.motors_tab.columnconfigure(1, weight=1, minsize=400)
        self.motors_tab.rowconfigure(0, weight=0)
        self.motors_tab.rowconfigure(1, weight=1)

        # Position display
        status_frame = ttk.LabelFrame(self.motors_tab, text=t("GRBL Status & Position"), padding="10")
        status_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        pos_display_frame = ttk.Frame(status_frame)
        pos_display_frame.grid(row=0, column=0, sticky="e", padx=10)

        self.x_pos_var = tk.StringVar(value=t("X: {x:.2f} cm", x=0.00))
        self.y_pos_var = tk.StringVar(value=t("Y: {y:.2f} cm", y=0.00))

        ttk.Label(pos_display_frame, textvariable=self.x_pos_var, font=("Arial", 20, "bold")).grid(row=0, column=0, padx=20)
        ttk.Label(pos_display_frame, textvariable=self.y_pos_var, font=("Arial", 20, "bold")).grid(row=0, column=1, padx=20)

        status_display_frame = ttk.Frame(status_frame)
        status_display_frame.grid(row=0, column=1, sticky="e", padx=40)

        # RTL: labels on right (col=1), values on left (col=0)
        ttk.Label(status_display_frame, text=t("State:"), font=("Arial", 10)).grid(row=0, column=1, padx=(5, 0), sticky="e")
        self.motor_status_label = ttk.Label(status_display_frame, text=t("Idle"), font=("Arial", 10, "bold"), foreground="green")
        self.motor_status_label.grid(row=0, column=0, padx=5, sticky="e")

        ttk.Label(status_display_frame, text=t("Work Pos:"), font=("Arial", 10)).grid(row=1, column=1, padx=(5, 0), sticky="e")
        self.grbl_work_pos_label = ttk.Label(status_display_frame, text=t("X: 0.00 Y: 0.00"), font=("Arial", 10))
        self.grbl_work_pos_label.grid(row=1, column=0, padx=5, sticky="e")

        homing_frame = ttk.Frame(status_frame)
        homing_frame.grid(row=0, column=2, sticky="w", padx=10)
        ttk.Button(homing_frame, text=t("Start Homing Sequence"),
                  command=self.start_homing_sequence).pack(pady=5)

        # Left - Jog controls
        left_frame = ttk.Frame(self.motors_tab)
        left_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        jog_frame = ttk.LabelFrame(left_frame, text=t("Jog Control"), padding="10")
        jog_frame.pack(fill="both", expand=True, pady=(0, 5))

        ttk.Label(jog_frame, text=t("Step Size:")).grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="e")
        step_frame = ttk.Frame(jog_frame)
        step_frame.grid(row=1, column=0, columnspan=3, pady=(0, 10))

        ttk.Radiobutton(step_frame, text=t("0.1mm"), variable=self.jog_step, value="0.01").pack(side=tk.RIGHT, padx=5)
        ttk.Radiobutton(step_frame, text=t("1mm"), variable=self.jog_step, value="0.1").pack(side=tk.RIGHT, padx=5)
        ttk.Radiobutton(step_frame, text=t("10mm"), variable=self.jog_step, value="1.0").pack(side=tk.RIGHT, padx=5)
        ttk.Radiobutton(step_frame, text=t("100mm"), variable=self.jog_step, value="10.0").pack(side=tk.RIGHT, padx=5)

        jog_btn_frame = ttk.Frame(jog_frame)
        jog_btn_frame.grid(row=2, column=0, columnspan=3, pady=10)

        ttk.Button(jog_btn_frame, text="Y+\n↑", width=8, command=lambda: self.jog('Y', 1)).grid(row=0, column=1, padx=2, pady=2)
        ttk.Button(jog_btn_frame, text="←\nX-", width=8, command=lambda: self.jog('X', -1)).grid(row=1, column=0, padx=2, pady=2)
        ttk.Button(jog_btn_frame, text=t("HOME"), width=8, command=self.home_motors).grid(row=1, column=1, padx=2, pady=2)
        ttk.Button(jog_btn_frame, text="X+\n→", width=8, command=lambda: self.jog('X', 1)).grid(row=1, column=2, padx=2, pady=2)
        ttk.Button(jog_btn_frame, text="↓\nY-", width=8, command=lambda: self.jog('Y', -1)).grid(row=2, column=1, padx=2, pady=2)

        # Manual position
        manual_frame = ttk.LabelFrame(left_frame, text=t("Go to Position"), padding="10")
        manual_frame.pack(fill="x", pady=5)

        # RTL: labels on right, entries on left
        ttk.Label(manual_frame, text=t("X (cm):")).grid(row=0, column=2, sticky="e", pady=2)
        self.x_entry = ttk.Entry(manual_frame, width=10)
        self.x_entry.insert(0, "0")
        self.x_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(manual_frame, text=t("Y (cm):")).grid(row=1, column=2, sticky="e", pady=2)
        self.y_entry = ttk.Entry(manual_frame, width=10)
        self.y_entry.insert(0, "0")
        self.y_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Button(manual_frame, text=t("Move"), command=self.move_to_position, width=15).grid(row=0, column=0, rowspan=2, padx=10)

        # Right - Presets
        right_frame = ttk.Frame(self.motors_tab)
        right_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        preset_frame = ttk.LabelFrame(right_frame, text=t("Preset Positions"), padding="10")
        preset_frame.pack(fill="both", expand=True, pady=(0, 5))

        presets = [
            (t("Origin (0, 0)"), 0, 0),
            (t("Center (50, 35)"), 50, 35),
            (t("Top Right (100, 0)"), 100, 0),
            (t("Top Left (0, 0)"), 0, 0),
            (t("Bottom Right (100, 70)"), 100, 70),
            (t("Bottom Left (0, 70)"), 0, 70),
            (t("Test Position 1 (25, 25)"), 25, 25),
            (t("Test Position 2 (75, 45)"), 75, 45),
        ]

        for i, (name, x, y) in enumerate(presets):
            btn = ttk.Button(preset_frame, text=name,
                           command=lambda x=x, y=y: self.move_to_preset(x, y))
            btn.grid(row=i//2, column=i%2, padx=5, pady=3, sticky="ew")

        # Speed control
        speed_frame = ttk.LabelFrame(right_frame, text=t("Movement Speed"), padding="10")
        speed_frame.pack(fill="x", pady=5)

        self.speed_var = tk.StringVar(value="normal")
        ttk.Radiobutton(speed_frame, text=t("Slow"), variable=self.speed_var, value="slow").pack(side=tk.RIGHT, padx=5)
        ttk.Radiobutton(speed_frame, text=t("Normal"), variable=self.speed_var, value="normal").pack(side=tk.RIGHT, padx=5)
        ttk.Radiobutton(speed_frame, text=t("Fast"), variable=self.speed_var, value="fast").pack(side=tk.RIGHT, padx=5)

        # Limit switches
        limit_frame = ttk.LabelFrame(right_frame, text=t("Limit Switches (Live)"), padding="10")
        limit_frame.pack(fill="x", pady=5)

        limit_switches = [
            (t("Top Limit"), "top_limit_switch"),
            (t("Bottom Limit"), "bottom_limit_switch"),
            (t("Left Limit"), "left_limit_switch"),
            (t("Right Limit"), "right_limit_switch"),
            (t("Door Sensor"), "door_sensor")
        ]

        for i, (name, switch_id) in enumerate(limit_switches):
            # RTL: name on right, port, connection, state on left
            ttk.Label(limit_frame, text=name, width=13).grid(row=i, column=3, sticky="e", pady=2)

            port_info = self.port_mappings.get(switch_id, {})
            port_text = port_info.get('port', 'N/A') if port_info else 'N/A'
            ttk.Label(limit_frame, text=f"[{port_text}]", font=("Courier", 9, "bold"), foreground="#555555").grid(row=i, column=2, sticky="e", pady=2)

            conn_indicator = tk.Label(limit_frame, text="●", font=("Arial", 10), fg="#95A5A6")
            conn_indicator.grid(row=i, column=1, padx=2, pady=2)
            self.sensor_connection_widgets[switch_id] = conn_indicator

            state_label = ttk.Label(limit_frame, text=t("OPEN"), width=10,
                                   relief=tk.SUNKEN, anchor=tk.CENTER,
                                   background="#95A5A6", foreground="white",
                                   font=("Arial", 8, "bold"))
            state_label.grid(row=i, column=0, padx=5, pady=2)
            self.sensor_widgets[switch_id] = state_label

    def create_pistons_tab(self):
        """Create pistons and sensors tab"""
        self.pistons_tab.columnconfigure(0, weight=1, minsize=400)
        self.pistons_tab.columnconfigure(1, weight=1, minsize=400)
        self.pistons_tab.rowconfigure(0, weight=1)

        # Left - Piston controls
        left_frame = ttk.Frame(self.pistons_tab)
        left_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        piston_frame = ttk.LabelFrame(left_frame, text=t("Piston Control"), padding="10")
        piston_frame.pack(fill="both", expand=True)

        self.piston_methods = {
            "line_marker": (t("Line Marker"), "line_marker_piston"),
            "line_cutter": (t("Line Cutter"), "line_cutter_piston"),
            "line_motor": (t("Line Motor (Both)"), "line_motor_piston"),
            "row_marker": (t("Row Marker"), "row_marker_piston"),
            "row_cutter": (t("Row Cutter"), "row_cutter_piston"),
            "air_pressure": (t("Air Pressure"), "air_pressure_valve")
        }

        for i, (key, (name, method_base)) in enumerate(self.piston_methods.items()):
            # RTL: name on right (col=3), port/conn in middle, state/buttons on left
            name_frame = ttk.Frame(piston_frame)
            name_frame.grid(row=i, column=3, sticky="e", pady=5)

            port_info = self.port_mappings.get(method_base, {})
            if port_info:
                port_text = f"[{port_info.get('port', 'N/A')}] "
                ttk.Label(name_frame, text=port_text, font=("Courier", 10, "bold"), foreground="#555555").pack(side=tk.RIGHT, padx=5)

            ttk.Label(name_frame, text=name, font=("Arial", 10, "bold")).pack(side=tk.RIGHT)

            conn_indicator = tk.Label(piston_frame, text="●", font=("Arial", 12), fg="#95A5A6")
            conn_indicator.grid(row=i, column=2, padx=5, pady=5)
            self.piston_connection_widgets[key] = conn_indicator

            state_frame = ttk.Frame(piston_frame)
            state_frame.grid(row=i, column=1, padx=10, pady=5)

            state_label = ttk.Label(state_frame, text=t("UNKNOWN"), width=10,
                                   relief=tk.SUNKEN, anchor=tk.CENTER,
                                   background="#95A5A6", foreground="white",
                                   font=("Arial", 10, "bold"))
            state_label.pack()

            btn_frame = ttk.Frame(piston_frame)
            btn_frame.grid(row=i, column=0, pady=5)

            up_btn = ttk.Button(btn_frame, text=t("UP"), width=10,
                              command=lambda k=key: self.piston_up(k))
            up_btn.pack(side=tk.RIGHT, padx=2)

            down_btn = ttk.Button(btn_frame, text=t("DOWN"), width=10,
                                command=lambda k=key: self.piston_down(k))
            down_btn.pack(side=tk.RIGHT, padx=2)

            self.piston_widgets[key] = state_label

        # Right - Sensor monitoring
        right_frame = ttk.Frame(self.pistons_tab)
        right_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        sensor_frame = ttk.LabelFrame(right_frame, text=t("Tool Position Sensors (Live)"), padding="10")
        sensor_frame.pack(fill="both", expand=True, pady=(0, 5))

        sensor_groups = [
            (t("Line Marker"), [
                (t("UP Sensor"), "line_marker_up_sensor"),
                (t("DOWN Sensor"), "line_marker_down_sensor")
            ]),
            (t("Line Cutter"), [
                (t("UP Sensor"), "line_cutter_up_sensor"),
                (t("DOWN Sensor"), "line_cutter_down_sensor")
            ]),
            (t("Line Motor"), [
                (t("Left UP"), "line_motor_left_up_sensor"),
                (t("Left DOWN"), "line_motor_left_down_sensor"),
                (t("Right UP"), "line_motor_right_up_sensor"),
                (t("Right DOWN"), "line_motor_right_down_sensor")
            ]),
            (t("Row Marker"), [
                (t("UP Sensor"), "row_marker_up_sensor"),
                (t("DOWN Sensor"), "row_marker_down_sensor")
            ]),
            (t("Row Cutter"), [
                (t("UP Sensor"), "row_cutter_up_sensor"),
                (t("DOWN Sensor"), "row_cutter_down_sensor")
            ])
        ]

        row = 0
        for group_name, sensors in sensor_groups:
            ttk.Label(sensor_frame, text=group_name, font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=4, sticky="e", pady=(5, 0))
            row += 1

            for sensor_name, sensor_id in sensors:
                # RTL: name on right (col=3), port (col=2), connection (col=1), state on left (col=0)
                ttk.Label(sensor_frame, text=f"  {sensor_name}:", width=15).grid(row=row, column=3, sticky="e", pady=2)

                port_info = self.port_mappings.get(sensor_id, {})
                port_text = port_info.get('port', 'N/A') if port_info else 'N/A'
                ttk.Label(sensor_frame, text=f"[{port_text}]", font=("Courier", 9, "bold"), foreground="#555555").grid(row=row, column=2, sticky="e", pady=2)

                conn_indicator = tk.Label(sensor_frame, text="●", font=("Arial", 10), fg="#95A5A6")
                conn_indicator.grid(row=row, column=1, padx=2, pady=2)
                self.sensor_connection_widgets[sensor_id] = conn_indicator

                state_label = ttk.Label(sensor_frame, text=t("INACTIVE"), width=10,
                                       relief=tk.SUNKEN, anchor=tk.CENTER,
                                       background="#95A5A6", foreground="white",
                                       font=("Arial", 8, "bold"))
                state_label.grid(row=row, column=0, padx=5, pady=2)
                self.sensor_widgets[sensor_id] = state_label
                row += 1

        # Edge switches
        edge_frame = ttk.LabelFrame(right_frame, text=t("Edge Switches"), padding="10")
        edge_frame.pack(fill="x", pady=5)

        edge_sensors = [
            (t("X Left Edge"), "x_left_edge_sensor"),
            (t("X Right Edge"), "x_right_edge_sensor"),
            (t("Y Top Edge"), "y_top_edge_sensor"),
            (t("Y Bottom Edge"), "y_bottom_edge_sensor")
        ]

        for i, (name, sensor_id) in enumerate(edge_sensors):
            # RTL: name on right (col=3), port (col=2), connection (col=1), state on left (col=0)
            ttk.Label(edge_frame, text=name, width=13).grid(row=i, column=3, sticky="e", pady=2)

            port_info = self.port_mappings.get(sensor_id, {})
            port_text = port_info.get('port', 'N/A') if port_info else 'N/A'
            ttk.Label(edge_frame, text=f"[{port_text}]", font=("Courier", 9, "bold"), foreground="#555555").grid(row=i, column=2, sticky="e", pady=2)

            conn_indicator = tk.Label(edge_frame, text="●", font=("Arial", 10), fg="#95A5A6")
            conn_indicator.grid(row=i, column=1, padx=2, pady=2)
            self.sensor_connection_widgets[sensor_id] = conn_indicator

            state_label = ttk.Label(edge_frame, text=t("INACTIVE"), width=10,
                                   relief=tk.SUNKEN, anchor=tk.CENTER,
                                   background="#95A5A6", foreground="white",
                                   font=("Arial", 8, "bold"))
            state_label.grid(row=i, column=0, padx=5, pady=2)
            self.sensor_widgets[sensor_id] = state_label

    def _load_grbl_config_from_settings(self):
        """Load GRBL configuration values from settings.json"""
        try:
            import json
            with open('config/settings.json', 'r') as f:
                config = json.load(f)
            return config.get('hardware_config', {}).get('arduino_grbl', {}).get('grbl_configuration', {})
        except Exception:
            return {}

    def create_grbl_tab(self):
        """Create merged GRBL tab with settings, G-code console, and logs"""
        self.grbl_tab.columnconfigure(0, weight=1)
        self.grbl_tab.columnconfigure(1, weight=1)
        self.grbl_tab.rowconfigure(1, weight=3)
        self.grbl_tab.rowconfigure(2, weight=2)

        # --- Row 0: Control buttons ---
        control_frame = ttk.Frame(self.grbl_tab)
        control_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        ttk.Button(control_frame, text=t("Read Settings ($$)"), command=self.read_grbl_settings).pack(side=tk.RIGHT, padx=5)
        self.save_grbl_btn = ttk.Button(control_frame, text=t("Save to Settings"), command=self.save_grbl_to_settings)
        self.save_grbl_btn.pack(side=tk.RIGHT, padx=5)
        self.apply_grbl_btn = ttk.Button(control_frame, text=t("Apply (Session)"), command=self.write_grbl_settings)
        self.apply_grbl_btn.pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text=t("Reset to Defaults"), command=self.reset_grbl_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text=t("Unlock ($X)"), command=self.unlock_grbl).pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text=t("Home ($H)"), command=self.home_grbl).pack(side=tk.RIGHT, padx=5)

        # --- Row 1 Right: GRBL Configuration ---
        settings_frame = ttk.LabelFrame(self.grbl_tab, text=t("GRBL Configuration"), padding="10")
        settings_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        canvas = tk.Canvas(settings_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # RTL: scrollbar on left, canvas on right
        scrollbar.pack(side="left", fill="y")
        canvas.pack(side="right", fill="both", expand=True)

        # Load defaults from settings.json grbl_configuration
        grbl_config = self._load_grbl_config_from_settings()

        self.grbl_entries = {}
        key_settings = [
            ("$0", t("Step pulse"), t("Step pulse time (microseconds)")),
            ("$1", t("Step idle delay"), t("Step idle delay (milliseconds)")),
            ("$2", t("Step port invert"), t("Step port invert mask")),
            ("$3", t("Direction port invert"), t("Direction port invert mask")),
            ("$4", t("Step enable invert"), t("Step enable invert (boolean)")),
            ("$5", t("Limit pins invert"), t("Limit pins invert (boolean)")),
            ("$6", t("Probe pin invert"), t("Probe pin invert (boolean)")),
            ("$10", t("Status report"), t("Status report mask")),
            ("$11", t("Junction deviation"), t("Junction deviation (mm)")),
            ("$12", t("Arc tolerance"), t("Arc tolerance (mm)")),
            ("$13", t("Report inches"), t("Report in inches (boolean)")),
            ("$20", t("Soft limits"), t("Soft limits enable (boolean)")),
            ("$21", t("Hard limits"), t("Hard limits enable (boolean)")),
            ("$22", t("Homing cycle"), t("Homing cycle enable (boolean)")),
            ("$23", t("Homing dir invert"), t("Homing direction invert mask")),
            ("$24", t("Homing feed"), t("Homing feed rate (mm/min)")),
            ("$25", t("Homing seek"), t("Homing seek rate (mm/min)")),
            ("$26", t("Homing debounce"), t("Homing debounce (milliseconds)")),
            ("$27", t("Homing pull-off"), t("Homing pull-off distance (mm)")),
            ("$30", t("Max spindle speed"), t("Maximum spindle speed (RPM)")),
            ("$31", t("Min spindle speed"), t("Minimum spindle speed (RPM)")),
            ("$32", t("Laser mode"), t("Laser mode enable (boolean)")),
            ("$100", t("X steps/mm"), t("Steps per mm for X axis")),
            ("$101", t("Y steps/mm"), t("Steps per mm for Y axis")),
            ("$102", t("Z steps/mm"), t("Steps per mm for Z axis")),
            ("$110", t("X Max rate"), t("Maximum rate for X axis (mm/min)")),
            ("$111", t("Y Max rate"), t("Maximum rate for Y axis (mm/min)")),
            ("$112", t("Z Max rate"), t("Maximum rate for Z axis (mm/min)")),
            ("$120", t("X Acceleration"), t("X axis acceleration (mm/sec^2)")),
            ("$121", t("Y Acceleration"), t("Y axis acceleration (mm/sec^2)")),
            ("$122", t("Z Acceleration"), t("Z axis acceleration (mm/sec^2)")),
            ("$130", t("X Max travel"), t("Maximum travel for X axis (mm)")),
            ("$131", t("Y Max travel"), t("Maximum travel for Y axis (mm)")),
            ("$132", t("Z Max travel"), t("Maximum travel for Z axis (mm)"))
        ]

        for i, (param, name, tooltip) in enumerate(key_settings):
            row_frame = ttk.Frame(scrollable_frame)
            row_frame.grid(row=i, column=0, sticky="ew", pady=2)

            # RTL: param and name on right, entry on left
            ttk.Label(row_frame, text=f"{param}", font=("Courier", 10, "bold"), width=6).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Label(row_frame, text=name, width=20, anchor="e").pack(side=tk.RIGHT, padx=5)

            entry = ttk.Entry(row_frame, width=15)
            default_val = str(grbl_config.get(param, "0"))
            entry.insert(0, default_val)
            entry.pack(side=tk.RIGHT, padx=5)

            self.create_tooltip(entry, tooltip)
            self.grbl_entries[param] = entry

        # --- Row 1 Left: G-code Console ---
        gcode_frame = ttk.LabelFrame(self.grbl_tab, text=t("G-code Commands & Console"), padding="10")
        gcode_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        input_frame = ttk.Frame(gcode_frame)
        input_frame.pack(fill="x", pady=(10, 5))

        # RTL: label on right, entry in middle, send button on left
        ttk.Label(input_frame, text=t("Command:")).pack(side=tk.RIGHT, padx=(0, 5))
        self.grbl_command_entry = ttk.Entry(input_frame)
        self.grbl_command_entry.pack(side=tk.RIGHT, fill="x", expand=True, padx=5)
        self.grbl_command_entry.bind("<Return>", lambda e: self.send_grbl_command())

        ttk.Button(input_frame, text=t("Send"), command=self.send_grbl_command).pack(side=tk.LEFT)

        ttk.Label(gcode_frame, text=t("Response:")).pack(anchor="e", pady=(5, 0))
        self.grbl_response_text = scrolledtext.ScrolledText(gcode_frame, height=12, width=40, font=("Courier", 9))
        self.grbl_response_text.pack(fill="both", expand=True)

        # --- Row 2: Status & Logs (spanning both columns) ---
        log_frame = ttk.LabelFrame(self.grbl_tab, text=t("Status & Logs"), padding="5")
        log_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)

        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # RTL: log level on right, auto-scroll middle, buttons on left
        ttk.Label(log_control_frame, text=t("Log Level:")).pack(side=tk.RIGHT, padx=(0, 5))
        self.log_level_var = tk.StringVar(value="INFO")
        log_level_combo = ttk.Combobox(log_control_frame, textvariable=self.log_level_var,
                                       values=["DEBUG", "INFO", "WARNING", "ERROR"],
                                       state="readonly", width=10)
        log_level_combo.pack(side=tk.RIGHT, padx=(0, 5))

        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_control_frame, text=t("Auto-scroll"), variable=self.auto_scroll_var).pack(side=tk.RIGHT, padx=20)

        ttk.Button(log_control_frame, text=t("Save Log"), command=self.save_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_control_frame, text=t("Clear Log"), command=self.clear_log).pack(side=tk.LEFT, padx=5)

        self.console_text = scrolledtext.ScrolledText(log_frame, height=10, width=100,
                                                      font=("Courier", 9), bg="black", fg="white")
        self.console_text.grid(row=1, column=0, sticky="nsew")

        self.console_text.tag_config("DEBUG", foreground="gray")
        self.console_text.tag_config("INFO", foreground="white")
        self.console_text.tag_config("WARNING", foreground="yellow")
        self.console_text.tag_config("ERROR", foreground="red")
        self.console_text.tag_config("SUCCESS", foreground="lime")
        self.console_text.tag_config("GRBL", foreground="cyan")

        self.log("INFO", t("Admin Tool initialized"))
        self.log("INFO", t("Click 'Connect Hardware' to begin"))

    def create_tooltip(self, widget, text):
        """Create tooltip for widget"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, background="yellow",
                           relief="solid", borderwidth=1, font=("Arial", 9))
            label.pack()
            widget.tooltip = tooltip

        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def log(self, level, message):
        """Add message to log queue"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_queue.put((timestamp, level, message))

    def process_logs(self):
        """Process log messages from queue"""
        while self.log_processor_running:
            try:
                if not self.log_queue.empty():
                    timestamp, level, message = self.log_queue.get_nowait()

                    levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
                    current_level_index = levels.index(self.log_level_var.get())
                    message_level_index = levels.index(level) if level in levels else 1

                    if message_level_index >= current_level_index:
                        formatted_msg = f"[{timestamp}] [{level:7}] {message}\n"
                        self.console_text.insert(tk.END, formatted_msg, level)

                        if self.auto_scroll_var.get():
                            self.console_text.see(tk.END)

                time.sleep(0.01)
            except Exception as e:
                print(f"Log processor error: {e}")
                time.sleep(0.1)

    # Hardware connection methods
    def on_hardware_mode_changed(self):
        """Handle hardware mode toggle"""
        use_real = self.use_real_hardware.get()
        try:
            import json
            with open('config/settings.json', 'r') as f:
                config = json.load(f)

            if 'hardware_config' not in config:
                config['hardware_config'] = {}
            config['hardware_config']['use_real_hardware'] = use_real

            with open('config/settings.json', 'w') as f:
                json.dump(config, f, indent=2)

            self.log("INFO", t("Hardware mode changed to: {mode}", mode='REAL' if use_real else 'MOCK'))

            if self.is_connected:
                self.log("WARNING", t("Please disconnect and reconnect to apply hardware mode change"))
                messagebox.showinfo(t("Hardware Mode Changed"),
                                   t("Please disconnect and reconnect to apply the new hardware mode."))
        except Exception as e:
            self.log("ERROR", t("Failed to update hardware mode: {error}", error=str(e)))

    def scan_ports(self):
        """Scan for serial ports"""
        try:
            import serial.tools.list_ports

            ports = serial.tools.list_ports.comports()
            self.available_ports = [t("Auto-detect")]

            for port in ports:
                port_name = f"{port.device} - {port.description}"
                self.available_ports.append(port_name)

            self.port_combo['values'] = self.available_ports
            self.rs485_port_combo['values'] = self.available_ports

            if len(self.available_ports) > 1:
                self.log("INFO", t("Found {count} serial port(s)", count=len(self.available_ports)-1))
        except Exception as e:
            self.log("ERROR", t("Error scanning ports: {error}", error=str(e)))
            self.available_ports = [t("Auto-detect")]

    def auto_initialize(self):
        """Auto-initialize on startup"""
        self.log("INFO", t("Auto-initializing hardware..."))
        self.toggle_connection()

    def toggle_connection(self):
        """Toggle hardware connection"""
        if not self.is_connected:
            self.connect_hardware()
        else:
            self.disconnect_hardware()

    def connect_hardware(self):
        """Connect to hardware"""
        try:
            self.log("INFO", t("Connecting to hardware..."))

            import json
            try:
                with open('config/settings.json', 'r') as f:
                    config = json.load(f)
            except:
                config = {}

            selected = self.selected_port.get()
            if selected and selected != t("Auto-detect"):
                port_device = selected.split(" - ")[0]
                self.log("INFO", t("Using selected GRBL port: {port}", port=port_device))

                if 'hardware_config' not in config:
                    config['hardware_config'] = {}
                if 'arduino_grbl' not in config['hardware_config']:
                    config['hardware_config']['arduino_grbl'] = {}
                config['hardware_config']['arduino_grbl']['serial_port'] = port_device

            selected_rs485 = self.selected_rs485_port.get()
            if selected_rs485 and selected_rs485 != t("Auto-detect"):
                rs485_port_device = selected_rs485.split(" - ")[0]
                self.log("INFO", t("Using selected RS485 port: {port}", port=rs485_port_device))

                if 'hardware_config' not in config:
                    config['hardware_config'] = {}
                if 'raspberry_pi' not in config['hardware_config']:
                    config['hardware_config']['raspberry_pi'] = {}
                if 'rs485' not in config['hardware_config']['raspberry_pi']:
                    config['hardware_config']['raspberry_pi']['rs485'] = {}
                config['hardware_config']['raspberry_pi']['rs485']['serial_port'] = rs485_port_device

            try:
                with open('config/settings.json', 'w') as f:
                    json.dump(config, f, indent=2)
            except:
                pass

            self.hardware = get_hardware_interface()

            mode = t("REAL HARDWARE") if hasattr(self.hardware, 'gpio') else t("MOCK/SIMULATION")
            self.mode_label.config(text=t("Mode: {mode}", mode=mode))
            self.log("INFO", t("Hardware mode: {mode}", mode=mode))

            if self.hardware.initialize():
                self.is_connected = True
                self.hw_status_label.config(text=t("Connected"), foreground="green")
                self.connect_btn.config(text=t("Disconnect"))
                self.log("SUCCESS", t("Hardware connected successfully"))

                if hasattr(self.hardware, 'grbl') and self.hardware.grbl and self.hardware.grbl.is_connected:
                    self.grbl_connected = True
                    self.grbl_status_label.config(text=t("Connected"), foreground="green")
                    self.log("SUCCESS", t("GRBL connected successfully"))
                    self.root.after(100, self.read_grbl_settings)
                else:
                    self.grbl_status_label.config(text=t("Not Available"), foreground="orange")

                self.monitor_running = True
                self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
                self.monitor_thread.start()

                self.enable_controls(True)
            else:
                self.log("ERROR", t("Failed to initialize hardware"))

        except Exception as e:
            self.log("ERROR", t("Connection error: {error}", error=str(e)))

    def disconnect_hardware(self):
        """Disconnect from hardware"""
        self.log("INFO", t("Disconnecting from hardware..."))

        self.monitor_running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=2)

        if self.hardware:
            self.hardware.shutdown()

        self.is_connected = False
        self.grbl_connected = False
        self.hw_status_label.config(text=t("Not Connected"), foreground="red")
        self.grbl_status_label.config(text=t("Not Connected"), foreground="red")
        self.connect_btn.config(text=t("Connect Hardware"))

        self.enable_controls(False)
        self.log("INFO", t("Hardware disconnected"))

    def enable_controls(self, enabled):
        """Enable/disable controls"""
        state = "normal" if enabled else "disabled"
        for tab in [self.motors_tab, self.pistons_tab, self.grbl_tab]:
            for widget in tab.winfo_children():
                if isinstance(widget, (ttk.Button, ttk.Entry)):
                    widget.config(state=state)
                elif isinstance(widget, (ttk.Frame, ttk.LabelFrame)):
                    for child in widget.winfo_children():
                        if isinstance(child, (ttk.Button, ttk.Entry)):
                            child.config(state=state)

    def _safe_config(self, widget, **kwargs):
        """Schedule a widget config update, safely ignoring destroyed widgets."""
        def _do_config():
            if self._closing:
                return
            try:
                widget.config(**kwargs)
            except tk.TclError:
                pass
        self.root.after_idle(_do_config)

    def monitor_loop(self):
        """Background monitor loop"""
        self.log("INFO", t("Monitor loop started"))
        last_position_update = 0
        position_update_interval = 0.2

        while self.monitor_running:
            try:
                current_time = time.time()

                if current_time - last_position_update >= position_update_interval:
                    if self.grbl_connected and hasattr(self.hardware, 'grbl') and self.hardware.grbl:
                        status = self.hardware.grbl.get_status()
                        if status:
                            new_x = status.get('x', 0)
                            new_y = status.get('y', 0)
                            if abs(new_x - self.current_x) > 0.01 or abs(new_y - self.current_y) > 0.01:
                                self.current_x = new_x
                                self.current_y = new_y
                                self.root.after_idle(lambda: self.x_pos_var.set(t("X: {x:.2f} cm", x=self.current_x)) if not self._closing else None)
                                self.root.after_idle(lambda: self.y_pos_var.set(t("Y: {y:.2f} cm", y=self.current_y)) if not self._closing else None)

                            state = status.get('state', 'Unknown')
                            color = "green" if state == "Idle" else "orange" if state == "Run" else "red"
                            self._safe_config(self.motor_status_label, text=state, foreground=color)

                    elif self.is_connected and hasattr(self.hardware, 'get_current_x'):
                        try:
                            new_x = self.hardware.get_current_x()
                            new_y = self.hardware.get_current_y()
                            if abs(new_x - self.current_x) > 0.01 or abs(new_y - self.current_y) > 0.01:
                                self.current_x = new_x
                                self.current_y = new_y
                                self.root.after_idle(lambda: self.x_pos_var.set(t("X: {x:.2f} cm", x=self.current_x)) if not self._closing else None)
                                self.root.after_idle(lambda: self.y_pos_var.set(t("Y: {y:.2f} cm", y=self.current_y)) if not self._closing else None)
                        except:
                            pass

                    last_position_update = current_time

                if self.is_connected:
                    for sensor_id, widget in self.sensor_widgets.items():
                        getter_method = f"get_{sensor_id}"
                        if hasattr(self.hardware, getter_method):
                            try:
                                state = getattr(self.hardware, getter_method)()

                                if sensor_id in self.sensor_connection_widgets:
                                    self._safe_config(self.sensor_connection_widgets[sensor_id], fg="#27AE60")

                                if "limit_switch" in sensor_id or sensor_id == "door_sensor":
                                    if state:
                                        self._safe_config(widget, text=t("CLOSED"), background="#27AE60")
                                    else:
                                        self._safe_config(widget, text=t("OPEN"), background="#E74C3C")
                                else:
                                    if state:
                                        self._safe_config(widget, text=t("ACTIVE"), background="#27AE60")
                                    else:
                                        self._safe_config(widget, text=t("INACTIVE"), background="#95A5A6")
                            except:
                                if sensor_id in self.sensor_connection_widgets:
                                    self._safe_config(self.sensor_connection_widgets[sensor_id], fg="#E74C3C")

                    for piston_key, (name, method_base) in self.piston_methods.items():
                        if piston_key == "line_motor":
                            state_method = "get_line_motor_piston_state"
                        else:
                            state_method = f"get_{method_base}_state"

                        if hasattr(self.hardware, state_method):
                            try:
                                state = getattr(self.hardware, state_method)()

                                self._safe_config(self.piston_connection_widgets[piston_key], fg="#27AE60")

                                widget = self.piston_widgets[piston_key]
                                if state == "up":
                                    self._safe_config(widget, text=t("UP"), background="#3498DB")
                                elif state == "down":
                                    self._safe_config(widget, text=t("DOWN"), background="#27AE60")
                                else:
                                    self._safe_config(widget, text=t("UNKNOWN"), background="#95A5A6")
                            except:
                                self._safe_config(self.piston_connection_widgets[piston_key], fg="#E74C3C")

                time.sleep(0.1)

            except Exception as e:
                self.log("ERROR", t("Monitor error: {error}", error=str(e)))
                time.sleep(1)

    # Motor control methods
    def jog(self, axis, direction):
        """Jog motor"""
        if not self.is_connected:
            messagebox.showwarning(t("Not Connected"), t("Please connect hardware first"))
            return

        try:
            step = float(self.jog_step.get())

            if axis == 'X':
                new_pos = self.current_x + (step * direction)
                self.log("INFO", t("Jogging X to {pos:.2f}cm", pos=new_pos))
                self.hardware.move_x(new_pos)
            else:
                new_pos = self.current_y + (step * direction)
                self.log("INFO", t("Jogging Y to {pos:.2f}cm", pos=new_pos))
                self.hardware.move_y(new_pos)

            time.sleep(0.5)
            self.update_position_display()
        except Exception as e:
            self.log("ERROR", t("Jog error: {error}", error=str(e)))

    def move_to_position(self):
        """Move to position"""
        if not self.is_connected:
            return

        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())

            self.log("INFO", t("Moving to X={x:.2f}, Y={y:.2f}", x=x, y=y))
            if self.hardware.move_to(x, y):
                self.log("SUCCESS", t("Move complete"))
                time.sleep(0.5)
                self.update_position_display()
        except ValueError:
            self.log("ERROR", t("Invalid position values"))

    def move_to_preset(self, x, y):
        """Move to preset position"""
        if not self.is_connected:
            return

        self.log("INFO", t("Moving to preset X={x:.2f}, Y={y:.2f}", x=x, y=y))
        if self.hardware.move_to(x, y):
            self.log("SUCCESS", t("Move complete"))
            time.sleep(0.5)
            self.update_position_display()

    def home_motors(self):
        """Home motors"""
        if not self.is_connected:
            return

        if messagebox.askyesno(t("Home Motors"), t("Move all motors to home (0, 0)?")):
            self.log("INFO", t("Homing all motors..."))
            if self.hardware.home_motors():
                self.log("SUCCESS", t("Motors homed"))
                self.current_x = 0
                self.current_y = 0

    def emergency_stop(self):
        """Emergency stop"""
        self.log("WARNING", t("EMERGENCY STOP!"))
        if self.is_connected and self.hardware.emergency_stop():
            messagebox.showwarning(t("Emergency Stop"), t("All motors stopped!"))
            self.hardware.resume_operation()
            self.log("INFO", t("Emergency stop cleared"))

    def start_homing_sequence(self):
        """Start homing sequence"""
        if not self.is_connected:
            return

        if not self.grbl_connected:
            messagebox.showwarning(t("GRBL Not Connected"), t("GRBL is not connected."))
            return

        if not messagebox.askyesno(t("Start Homing"), t("Start complete homing sequence?")):
            return

        self.log("INFO", t("Starting homing sequence..."))

        def homing_thread():
            try:
                success, error_msg = self.hardware.perform_complete_homing_sequence()
                if success:
                    self.log("SUCCESS", t("Homing complete"))
                    self.root.after(0, lambda: messagebox.showinfo(t("Done"), t("Homing complete")))
                else:
                    self.log("ERROR", t("Homing failed: {error}", error=error_msg))
            except Exception as e:
                self.log("ERROR", t("Homing error: {error}", error=str(e)))

        threading.Thread(target=homing_thread, daemon=True).start()

    def update_position_display(self):
        """Update position display"""
        if not self.grbl_connected:
            return

        try:
            status = self.hardware.grbl.get_status(log_changes_only=False)
            if status:
                self.current_x = status.get('x', 0)
                self.current_y = status.get('y', 0)
                self.x_pos_var.set(t("X: {x:.2f} cm", x=self.current_x))
                self.y_pos_var.set(t("Y: {y:.2f} cm", y=self.current_y))
        except:
            pass

    # Piston control methods
    def piston_up(self, piston_key):
        """Raise piston"""
        if not self.is_connected:
            return

        name, _ = self.piston_methods[piston_key]
        self.log("INFO", t("Raising {name}", name=name))

        success = False
        if piston_key == "line_marker":
            success = self.hardware.line_marker_piston_up()
        elif piston_key == "line_cutter":
            success = self.hardware.line_cutter_piston_up()
        elif piston_key == "line_motor":
            success = self.hardware.line_motor_piston_up()
        elif piston_key == "row_marker":
            success = self.hardware.row_marker_piston_up()
        elif piston_key == "row_cutter":
            success = self.hardware.row_cutter_piston_up()
        elif piston_key == "air_pressure":
            success = self.hardware.air_pressure_valve_up()

        if success:
            self.piston_widgets[piston_key].config(text=t("UP"), background="#3498DB")
            self.log("SUCCESS", t("{name} raised", name=name))

    def piston_down(self, piston_key):
        """Lower piston"""
        if not self.is_connected:
            return

        name, _ = self.piston_methods[piston_key]
        self.log("INFO", t("Lowering {name}", name=name))

        success = False
        if piston_key == "line_marker":
            success = self.hardware.line_marker_piston_down()
        elif piston_key == "line_cutter":
            success = self.hardware.line_cutter_piston_down()
        elif piston_key == "line_motor":
            success = self.hardware.line_motor_piston_down()
        elif piston_key == "row_marker":
            success = self.hardware.row_marker_piston_down()
        elif piston_key == "row_cutter":
            success = self.hardware.row_cutter_piston_down()
        elif piston_key == "air_pressure":
            success = self.hardware.air_pressure_valve_down()

        if success:
            self.piston_widgets[piston_key].config(text=t("DOWN"), background="#27AE60")
            self.log("SUCCESS", t("{name} lowered", name=name))

    # GRBL methods
    def read_grbl_settings(self):
        """Read GRBL settings"""
        if not self.grbl_connected:
            return

        self.log("INFO", t("Reading GRBL settings..."))

        try:
            if hasattr(self.hardware, 'grbl') and hasattr(self.hardware.grbl, '_send_command'):
                response = self.hardware.grbl._send_command("$$")

                if response:
                    self.grbl_response_text.delete(1.0, tk.END)
                    self.grbl_response_text.insert(tk.END, response)

                    for line in response.split('\n'):
                        match = re.match(r'(\$\d+)=(.+)', line)
                        if match:
                            param, value = match.group(1), match.group(2)
                            if param in self.grbl_entries:
                                self.grbl_entries[param].delete(0, tk.END)
                                self.grbl_entries[param].insert(0, value)
                            self.grbl_settings[param] = value

                    self.log("SUCCESS", t("GRBL settings loaded"))
        except Exception as e:
            self.log("ERROR", t("Error reading settings: {error}", error=str(e)))

    def write_grbl_settings(self):
        """Write GRBL settings"""
        if not self.grbl_connected:
            return

        if not messagebox.askyesno(t("Apply Settings"), t("Apply changes to GRBL?")):
            return

        self.log("INFO", t("Applying GRBL settings..."))

        try:
            for param, entry in self.grbl_entries.items():
                new_value = entry.get().strip()
                if new_value and param in self.grbl_settings:
                    if new_value != self.grbl_settings[param]:
                        command = f"{param}={new_value}"
                        if hasattr(self.hardware.grbl, '_send_command'):
                            response = self.hardware.grbl._send_command(command)
                            if response and "ok" in response.lower():
                                self.grbl_settings[param] = new_value

            self.log("SUCCESS", t("Settings applied (session only)"))
            self.root.after(500, self.read_grbl_settings)
        except Exception as e:
            self.log("ERROR", t("Error applying settings: {error}", error=str(e)))

    def save_grbl_to_settings(self):
        """Save GRBL settings to settings.json, apply to GRBL hardware, and update System Config tab"""
        if not messagebox.askyesno(t("Save GRBL Settings"),
                                   t("Save GRBL configuration to settings.json and apply to hardware?")):
            return

        self.log("INFO", t("Saving GRBL settings to settings.json..."))

        try:
            import json

            # Collect current values from UI entries
            grbl_config = {}
            for param, entry in self.grbl_entries.items():
                value_str = entry.get().strip()
                if value_str:
                    try:
                        if '.' in value_str:
                            grbl_config[param] = float(value_str)
                        else:
                            grbl_config[param] = int(value_str)
                    except ValueError:
                        grbl_config[param] = value_str

            # Read current settings.json
            with open('config/settings.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Update grbl_configuration section
            if 'hardware_config' not in config:
                config['hardware_config'] = {}
            if 'arduino_grbl' not in config['hardware_config']:
                config['hardware_config']['arduino_grbl'] = {}
            config['hardware_config']['arduino_grbl']['grbl_configuration'] = grbl_config

            # Write back to settings.json
            with open('config/settings.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.log("SUCCESS", t("GRBL settings saved to settings.json"))

            # Apply to GRBL hardware if connected
            if self.grbl_connected:
                self.log("INFO", t("Applying settings to GRBL hardware..."))
                for param, entry in self.grbl_entries.items():
                    new_value = entry.get().strip()
                    if new_value and param in self.grbl_settings:
                        if new_value != self.grbl_settings[param]:
                            command = f"{param}={new_value}"
                            if hasattr(self.hardware, 'grbl') and hasattr(self.hardware.grbl, '_send_command'):
                                response = self.hardware.grbl._send_command(command)
                                if response and "ok" in response.lower():
                                    self.grbl_settings[param] = new_value
                self.log("SUCCESS", t("Settings applied to GRBL hardware"))
                self.root.after(500, self.read_grbl_settings)

            # Refresh the System Config tab to reflect updated settings
            if hasattr(self, 'config_tab') and self.config_tab:
                self.config_tab.load_settings()
                self.config_tab.refresh_ui()
                self.log("INFO", t("System Config tab refreshed"))

        except Exception as e:
            self.log("ERROR", t("Error saving GRBL settings: {error}", error=str(e)))

    def reset_grbl_settings(self):
        """Reset GRBL to defaults"""
        if not self.grbl_connected:
            return

        if not messagebox.askyesno(t("Reset Settings"), t("Reset GRBL to factory defaults?")):
            return

        try:
            if hasattr(self.hardware.grbl, '_send_command'):
                self.hardware.grbl._send_command("$RST=$")
                self.log("SUCCESS", t("GRBL reset to defaults"))
                self.root.after(500, self.read_grbl_settings)
        except Exception as e:
            self.log("ERROR", t("Error resetting: {error}", error=str(e)))

    def unlock_grbl(self):
        """Unlock GRBL"""
        if not self.grbl_connected:
            return

        try:
            if hasattr(self.hardware.grbl, '_send_command'):
                response = self.hardware.grbl._send_command("$X")
                if response and "ok" in response.lower():
                    self.log("SUCCESS", t("GRBL unlocked"))
        except Exception as e:
            self.log("ERROR", t("Error unlocking: {error}", error=str(e)))

    def home_grbl(self):
        """Home GRBL"""
        if not self.grbl_connected:
            return

        try:
            if hasattr(self.hardware.grbl, '_send_command'):
                response = self.hardware.grbl._send_command("$H", timeout=30)
                if response and "ok" in response.lower():
                    self.log("SUCCESS", t("GRBL homing completed"))
        except Exception as e:
            self.log("ERROR", t("Error homing: {error}", error=str(e)))

    def send_grbl_command(self):
        """Send GRBL command"""
        if not self.grbl_connected:
            return

        command = self.grbl_command_entry.get().strip()
        if not command:
            return

        self.log("GRBL", t("Sending: {command}", command=command))

        try:
            if hasattr(self.hardware.grbl, '_send_command'):
                response = self.hardware.grbl._send_command(command)
                if response:
                    self.grbl_response_text.insert(tk.END, f"\n> {command}\n{response}\n")
                    self.grbl_response_text.see(tk.END)
                    self.log("GRBL", t("Response: {response}", response=response.replace('\n', ' ')))

            self.grbl_command_entry.delete(0, tk.END)
        except Exception as e:
            self.log("ERROR", t("Error sending: {error}", error=str(e)))

    # Console methods
    def clear_log(self):
        """Clear log"""
        self.console_text.delete(1.0, tk.END)
        self.log("INFO", t("Log cleared"))

    def save_log(self):
        """Save log to file"""
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"admin_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.console_text.get(1.0, tk.END))
                self.log("SUCCESS", t("Log saved to {filename}", filename=filename))
            except Exception as e:
                self.log("ERROR", t("Failed to save: {error}", error=str(e)))

    def change_admin_password(self):
        """Open dialog to change the admin password"""
        dialog = tk.Toplevel(self.root)
        dialog.title(t("Change Admin Password"))
        dialog.geometry("350x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 175
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 100
        dialog.geometry(f"350x200+{x}+{y}")

        ttk.Label(dialog, text=t("New Password:"), font=("Arial", 10)).pack(pady=(20, 5))
        new_pass_entry = ttk.Entry(dialog, show="*", width=25, font=("Arial", 12))
        new_pass_entry.pack(pady=2)
        new_pass_entry.focus_set()

        ttk.Label(dialog, text=t("Confirm Password:"), font=("Arial", 10)).pack(pady=(10, 5))
        confirm_entry = ttk.Entry(dialog, show="*", width=25, font=("Arial", 12))
        confirm_entry.pack(pady=2)

        error_label = ttk.Label(dialog, text="", foreground="red", font=("Arial", 9))
        error_label.pack()

        def save_password():
            new_pass = new_pass_entry.get()
            confirm = confirm_entry.get()

            if not new_pass:
                error_label.config(text=t("Password cannot be empty"))
                return
            if new_pass != confirm:
                error_label.config(text=t("Passwords do not match"))
                return

            try:
                import json
                with open('config/settings.json', 'r') as f:
                    config = json.load(f)

                if 'admin' not in config:
                    config['admin'] = {}
                config['admin']['password'] = new_pass

                with open('config/settings.json', 'w') as f:
                    json.dump(config, f, indent=2)

                self.log("SUCCESS", t("Admin password changed"))
                dialog.destroy()
                messagebox.showinfo(t("Success"), t("Admin password changed successfully."))
            except Exception as e:
                self.log("ERROR", t("Failed to change password: {error}", error=str(e)))
                error_label.config(text=str(e))

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=t("Save"), command=save_password).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=t("Cancel"), command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def on_closing(self):
        """Handle window close"""
        self._closing = True
        if self.launched_from_app:
            # Launched from main app - just close the window, don't touch hardware
            self.monitor_running = False
            self.log_processor_running = False
            self.root.destroy()
        elif self.is_connected:
            if messagebox.askokcancel(t("Quit"), t("Disconnect and quit?")):
                self.log_processor_running = False
                self.disconnect_hardware()
                self.root.destroy()
            else:
                self._closing = False
        else:
            self.log_processor_running = False
            self.root.destroy()


def main():
    """Main function"""
    root = tk.Tk()
    app = AdminToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

"""
Ultimate Hardware Test GUI
==========================

Comprehensive testing interface for Scratch Desk hardware:
- Motor movement controls with jogging and presets
- Piston control with sensor feedback
- GRBL settings management
- Real-time status monitoring
- Command console with logging
- Emergency controls
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

# Add parent directory to path (go up two levels from tools/ to project root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hardware.interfaces.hardware_factory import get_hardware_interface


class UltimateHardwareTestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ultimate Hardware Test Interface - Scratch Desk")
        self.root.geometry("1400x900")

        # Make window resizable
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Initialize variables
        self.hardware = None
        self.is_connected = False
        self.monitor_running = False
        self.grbl_connected = False
        self.command_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Port selection
        self.available_ports = []
        self.selected_port = tk.StringVar(value="Auto-detect")

        # Position tracking
        self.current_x = 0.0
        self.current_y = 0.0
        self.jog_step = tk.StringVar(value="1.0")

        # GRBL settings cache
        self.grbl_settings = {}

        # Load port mappings from config
        self.port_mappings = self.load_port_mappings()

        # Create UI
        self.create_ui()

        # Start log processor thread
        self.log_processor_running = True
        self.log_processor_thread = threading.Thread(target=self.process_logs, daemon=True)
        self.log_processor_thread.start()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Auto-initialize hardware on startup
        self.root.after(100, self.auto_initialize)

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

            # Multiplexer sensors
            mux_channels = rpi_config.get('multiplexer', {}).get('channels', {})
            for name, channel in mux_channels.items():
                mappings[name] = {'type': 'MUX', 'port': f'MUX-CH{channel}', 'pin': channel}

            # Direct sensors
            direct_sensors = rpi_config.get('direct_sensors', {})
            for name, pin in direct_sensors.items():
                # Map to the sensor name format used in UI
                sensor_name = f"{name}_sensor"
                mappings[sensor_name] = {'type': 'GPIO', 'port': f'GPIO{pin}', 'pin': pin}

            # Limit switches (placeholder - may not be in config yet)
            limit_switches = rpi_config.get('limit_switches', {})
            for name, pin in limit_switches.items():
                mappings[name] = {'type': 'GPIO', 'port': f'GPIO{pin}', 'pin': pin}

            return mappings
        except Exception as e:
            print(f"Error loading port mappings: {e}")
            return {}

    def create_ui(self):
        """Create the main user interface with tabs"""
        # Top frame for connection status
        self.create_top_bar()

        # Main notebook with tabs
        self.notebook = ttk.Notebook(self.root, padding="5")
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Create tabs
        self.motors_tab = ttk.Frame(self.notebook)
        self.pistons_tab = ttk.Frame(self.notebook)
        self.grbl_tab = ttk.Frame(self.notebook)
        self.console_tab = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.motors_tab, text="Motors & Position")
        self.notebook.add(self.pistons_tab, text="Pistons & Sensors")
        self.notebook.add(self.grbl_tab, text="GRBL Settings")
        self.notebook.add(self.console_tab, text="Status & Logs")

        # Create tab contents
        self.create_motors_tab()
        self.create_pistons_tab()
        self.create_grbl_tab()
        self.create_console_tab()

    def create_top_bar(self):
        """Create top status bar with connection controls"""
        top_frame = ttk.Frame(self.root, relief=tk.RIDGE, borderwidth=2)
        top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        top_frame.columnconfigure(1, weight=1)

        # Connection status section
        conn_frame = ttk.Frame(top_frame)
        conn_frame.grid(row=0, column=0, padx=10, pady=5)

        ttk.Label(conn_frame, text="Hardware:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=(0, 5))
        self.hw_status_label = ttk.Label(conn_frame, text="Not Connected", foreground="red", font=("Arial", 10))
        self.hw_status_label.grid(row=0, column=1, padx=5)

        ttk.Label(conn_frame, text="GRBL:", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=(20, 5))
        self.grbl_status_label = ttk.Label(conn_frame, text="Not Connected", foreground="red", font=("Arial", 10))
        self.grbl_status_label.grid(row=0, column=3, padx=5)

        # Port selection dropdown
        ttk.Label(conn_frame, text="Port:", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=(20, 5))
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.selected_port, state="readonly", width=20)
        self.port_combo.grid(row=0, column=5, padx=5)

        # Refresh ports button
        ttk.Button(conn_frame, text="🔄", width=3, command=self.scan_ports).grid(row=0, column=6, padx=2)

        # Connect/Disconnect button
        self.connect_btn = ttk.Button(conn_frame, text="Connect Hardware", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=7, padx=20)

        # Scan ports on startup
        self.scan_ports()

        # Mode indicator
        mode_frame = ttk.Frame(top_frame)
        mode_frame.grid(row=0, column=1, padx=10, pady=5)

        self.mode_label = ttk.Label(mode_frame, text="Mode: Unknown", font=("Arial", 10))
        self.mode_label.pack()

        # Emergency stop (always visible)
        self.emergency_btn = tk.Button(top_frame, text="⚠ EMERGENCY STOP",
                                       command=self.emergency_stop,
                                       bg="red", fg="white",
                                       font=("Arial", 12, "bold"),
                                       width=15, height=1)
        self.emergency_btn.grid(row=0, column=2, padx=10, pady=5)

    def create_motors_tab(self):
        """Create motors control tab with jogging and presets"""
        # Configure grid weights
        self.motors_tab.columnconfigure(0, weight=1)
        self.motors_tab.columnconfigure(1, weight=1)
        self.motors_tab.rowconfigure(1, weight=1)

        # Position display at top
        pos_frame = ttk.LabelFrame(self.motors_tab, text="Current Position", padding="10")
        pos_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Large position display
        self.x_pos_var = tk.StringVar(value="X: 0.00 cm")
        self.y_pos_var = tk.StringVar(value="Y: 0.00 cm")

        ttk.Label(pos_frame, textvariable=self.x_pos_var, font=("Arial", 20, "bold")).grid(row=0, column=0, padx=20)
        ttk.Label(pos_frame, textvariable=self.y_pos_var, font=("Arial", 20, "bold")).grid(row=0, column=1, padx=20)

        # Status indicators
        ttk.Label(pos_frame, text="Status:", font=("Arial", 10)).grid(row=0, column=2, padx=(40, 5))
        self.motor_status_label = ttk.Label(pos_frame, text="Idle", font=("Arial", 10, "bold"), foreground="green")
        self.motor_status_label.grid(row=0, column=3, padx=5)

        # Left side - Manual control and jogging
        left_frame = ttk.Frame(self.motors_tab)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Jog control
        jog_frame = ttk.LabelFrame(left_frame, text="Jog Control", padding="10")
        jog_frame.pack(fill="both", expand=True, pady=(0, 5))

        # Step size selector
        ttk.Label(jog_frame, text="Step Size:").grid(row=0, column=0, columnspan=2, pady=(0, 5))
        step_frame = ttk.Frame(jog_frame)
        step_frame.grid(row=1, column=0, columnspan=3, pady=(0, 10))

        ttk.Radiobutton(step_frame, text="0.1mm", variable=self.jog_step, value="0.01").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(step_frame, text="1mm", variable=self.jog_step, value="0.1").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(step_frame, text="10mm", variable=self.jog_step, value="1.0").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(step_frame, text="100mm", variable=self.jog_step, value="10.0").pack(side=tk.LEFT, padx=5)

        # Jog buttons (arrow layout)
        jog_btn_frame = ttk.Frame(jog_frame)
        jog_btn_frame.grid(row=2, column=0, columnspan=3, pady=10)

        # Y+ button (up)
        ttk.Button(jog_btn_frame, text="Y+\n↑", width=8, command=lambda: self.jog('Y', 1)).grid(row=0, column=1, padx=2, pady=2)

        # X- button (left)
        ttk.Button(jog_btn_frame, text="←\nX-", width=8, command=lambda: self.jog('X', -1)).grid(row=1, column=0, padx=2, pady=2)

        # Home button (center)
        ttk.Button(jog_btn_frame, text="HOME", width=8, command=self.home_motors).grid(row=1, column=1, padx=2, pady=2)

        # X+ button (right)
        ttk.Button(jog_btn_frame, text="X+\n→", width=8, command=lambda: self.jog('X', 1)).grid(row=1, column=2, padx=2, pady=2)

        # Y- button (down)
        ttk.Button(jog_btn_frame, text="↓\nY-", width=8, command=lambda: self.jog('Y', -1)).grid(row=2, column=1, padx=2, pady=2)

        # Manual position entry
        manual_frame = ttk.LabelFrame(left_frame, text="Go to Position", padding="10")
        manual_frame.pack(fill="x", pady=5)

        ttk.Label(manual_frame, text="X (cm):").grid(row=0, column=0, sticky="w", pady=2)
        self.x_entry = ttk.Entry(manual_frame, width=10)
        self.x_entry.insert(0, "0")
        self.x_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(manual_frame, text="Y (cm):").grid(row=1, column=0, sticky="w", pady=2)
        self.y_entry = ttk.Entry(manual_frame, width=10)
        self.y_entry.insert(0, "0")
        self.y_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Button(manual_frame, text="Move", command=self.move_to_position, width=15).grid(row=0, column=2, rowspan=2, padx=10)

        # Right side - Presets and quick positions
        right_frame = ttk.Frame(self.motors_tab)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        # Preset positions
        preset_frame = ttk.LabelFrame(right_frame, text="Preset Positions", padding="10")
        preset_frame.pack(fill="both", expand=True, pady=(0, 5))

        presets = [
            ("Origin (0, 0)", 0, 0),
            ("Center (50, 35)", 50, 35),
            ("Top Right (100, 0)", 100, 0),
            ("Top Left (0, 0)", 0, 0),
            ("Bottom Right (100, 70)", 100, 70),
            ("Bottom Left (0, 70)", 0, 70),
            ("Test Position 1 (25, 25)", 25, 25),
            ("Test Position 2 (75, 45)", 75, 45),
        ]

        for i, (name, x, y) in enumerate(presets):
            btn = ttk.Button(preset_frame, text=name,
                           command=lambda x=x, y=y: self.move_to_preset(x, y))
            btn.grid(row=i//2, column=i%2, padx=5, pady=3, sticky="ew")

        # Speed control
        speed_frame = ttk.LabelFrame(right_frame, text="Movement Speed", padding="10")
        speed_frame.pack(fill="x", pady=5)

        self.speed_var = tk.StringVar(value="normal")
        ttk.Radiobutton(speed_frame, text="Slow", variable=self.speed_var, value="slow").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(speed_frame, text="Normal", variable=self.speed_var, value="normal").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(speed_frame, text="Fast", variable=self.speed_var, value="fast").pack(side=tk.LEFT, padx=5)

    def create_pistons_tab(self):
        """Create pistons and sensors control tab"""
        # Configure grid
        self.pistons_tab.columnconfigure(0, weight=1)
        self.pistons_tab.columnconfigure(1, weight=1)

        # Left side - Piston controls
        left_frame = ttk.Frame(self.pistons_tab)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        piston_frame = ttk.LabelFrame(left_frame, text="Piston Control", padding="10")
        piston_frame.pack(fill="both", expand=True)

        self.piston_widgets = {}
        self.piston_connection_widgets = {}
        self.piston_methods = {
            "line_marker": ("Line Marker", "line_marker_piston"),
            "line_cutter": ("Line Cutter", "line_cutter_piston"),
            "line_motor": ("Line Motor (Both)", "line_motor_piston"),  # Special handling
            "row_marker": ("Row Marker", "row_marker_piston"),
            "row_cutter": ("Row Cutter", "row_cutter_piston")
        }

        for i, (key, (name, method_base)) in enumerate(self.piston_methods.items()):
            # Piston name with port info
            name_frame = ttk.Frame(piston_frame)
            name_frame.grid(row=i, column=0, sticky="w", pady=5)

            ttk.Label(name_frame, text=name, font=("Arial", 10, "bold")).pack(side=tk.LEFT)

            # Port information
            port_info = self.port_mappings.get(method_base, {})
            if port_info:
                port_text = f" [{port_info.get('port', 'N/A')}]"
                ttk.Label(name_frame, text=port_text, font=("Courier", 8), foreground="gray").pack(side=tk.LEFT, padx=5)

            # Connection indicator
            conn_indicator = tk.Label(piston_frame, text="●", font=("Arial", 12),
                                     fg="#95A5A6")  # Gray by default
            conn_indicator.grid(row=i, column=1, padx=5, pady=5)
            self.piston_connection_widgets[key] = conn_indicator

            # State indicator
            state_frame = ttk.Frame(piston_frame)
            state_frame.grid(row=i, column=2, padx=10, pady=5)

            state_label = ttk.Label(state_frame, text="UNKNOWN", width=10,
                                   relief=tk.SUNKEN, anchor=tk.CENTER,
                                   background="#95A5A6", foreground="white",
                                   font=("Arial", 10, "bold"))
            state_label.pack()

            # Control buttons
            btn_frame = ttk.Frame(piston_frame)
            btn_frame.grid(row=i, column=3, pady=5)

            up_btn = ttk.Button(btn_frame, text="↑ UP", width=10,
                              command=lambda k=key: self.piston_up(k))
            up_btn.pack(side=tk.LEFT, padx=2)

            down_btn = ttk.Button(btn_frame, text="↓ DOWN", width=10,
                                command=lambda k=key: self.piston_down(k))
            down_btn.pack(side=tk.LEFT, padx=2)

            self.piston_widgets[key] = state_label

        # Right side - Sensor monitoring
        right_frame = ttk.Frame(self.pistons_tab)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Tool sensors
        sensor_frame = ttk.LabelFrame(right_frame, text="Tool Position Sensors (Live)", padding="10")
        sensor_frame.pack(fill="both", expand=True, pady=(0, 5))

        self.sensor_widgets = {}
        self.sensor_connection_widgets = {}

        # Create sensor display with grouping
        sensor_groups = [
            ("Line Marker", [
                ("UP Sensor", "line_marker_up_sensor"),
                ("DOWN Sensor", "line_marker_down_sensor")
            ]),
            ("Line Cutter", [
                ("UP Sensor", "line_cutter_up_sensor"),
                ("DOWN Sensor", "line_cutter_down_sensor")
            ]),
            ("Line Motor", [
                ("Left UP", "line_motor_left_up_sensor"),
                ("Left DOWN", "line_motor_left_down_sensor"),
                ("Right UP", "line_motor_right_up_sensor"),
                ("Right DOWN", "line_motor_right_down_sensor")
            ]),
            ("Row Marker", [
                ("UP Sensor", "row_marker_up_sensor"),
                ("DOWN Sensor", "row_marker_down_sensor")
            ]),
            ("Row Cutter", [
                ("UP Sensor", "row_cutter_up_sensor"),
                ("DOWN Sensor", "row_cutter_down_sensor")
            ])
        ]

        row = 0
        for group_name, sensors in sensor_groups:
            # Group header
            ttk.Label(sensor_frame, text=group_name, font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=4, sticky="w", pady=(5, 0))
            row += 1

            for sensor_name, sensor_id in sensors:
                # Sensor name
                ttk.Label(sensor_frame, text=f"  {sensor_name}:", width=15).grid(row=row, column=0, sticky="w", pady=2)

                # Port info
                port_info = self.port_mappings.get(sensor_id, {})
                port_text = port_info.get('port', 'N/A') if port_info else 'N/A'
                ttk.Label(sensor_frame, text=f"[{port_text}]", font=("Courier", 7), foreground="gray").grid(row=row, column=1, sticky="w", pady=2)

                # Connection indicator
                conn_indicator = tk.Label(sensor_frame, text="●", font=("Arial", 10), fg="#95A5A6")
                conn_indicator.grid(row=row, column=2, padx=2, pady=2)
                self.sensor_connection_widgets[sensor_id] = conn_indicator

                # State label
                state_label = ttk.Label(sensor_frame, text="INACTIVE", width=10,
                                       relief=tk.SUNKEN, anchor=tk.CENTER,
                                       background="#95A5A6", foreground="white",
                                       font=("Arial", 8, "bold"))
                state_label.grid(row=row, column=3, padx=5, pady=2)

                self.sensor_widgets[sensor_id] = state_label
                row += 1

        # Edge sensors
        edge_frame = ttk.LabelFrame(right_frame, text="Edge Detection Sensors", padding="10")
        edge_frame.pack(fill="x", pady=5)

        edge_sensors = [
            ("X Left Edge", "x_left_edge_sensor"),
            ("X Right Edge", "x_right_edge_sensor"),
            ("Y Top Edge", "y_top_edge_sensor"),
            ("Y Bottom Edge", "y_bottom_edge_sensor")
        ]

        for i, (name, sensor_id) in enumerate(edge_sensors):
            # Sensor name
            ttk.Label(edge_frame, text=name, width=13).grid(row=i, column=0, sticky="w", pady=2)

            # Port info
            port_info = self.port_mappings.get(sensor_id, {})
            port_text = port_info.get('port', 'N/A') if port_info else 'N/A'
            ttk.Label(edge_frame, text=f"[{port_text}]", font=("Courier", 7), foreground="gray").grid(row=i, column=1, sticky="w", pady=2)

            # Connection indicator
            conn_indicator = tk.Label(edge_frame, text="●", font=("Arial", 10), fg="#95A5A6")
            conn_indicator.grid(row=i, column=2, padx=2, pady=2)
            self.sensor_connection_widgets[sensor_id] = conn_indicator

            # State label
            state_label = ttk.Label(edge_frame, text="INACTIVE", width=10,
                                   relief=tk.SUNKEN, anchor=tk.CENTER,
                                   background="#95A5A6", foreground="white",
                                   font=("Arial", 8, "bold"))
            state_label.grid(row=i, column=3, padx=5, pady=2)

            self.sensor_widgets[sensor_id] = state_label

        # Limit switches
        limit_frame = ttk.LabelFrame(right_frame, text="Limit Switches (Live)", padding="10")
        limit_frame.pack(fill="x", pady=5)

        limit_switches = [
            ("Top Limit", "top_limit_switch"),
            ("Bottom Limit", "bottom_limit_switch"),
            ("Left Limit", "left_limit_switch"),
            ("Right Limit", "right_limit_switch"),
            ("Rows Limit", "rows_limit_switch")
        ]

        for i, (name, switch_id) in enumerate(limit_switches):
            # Switch name
            ttk.Label(limit_frame, text=name, width=13).grid(row=i, column=0, sticky="w", pady=2)

            # Port info
            port_info = self.port_mappings.get(switch_id, {})
            port_text = port_info.get('port', 'N/A') if port_info else 'N/A'
            ttk.Label(limit_frame, text=f"[{port_text}]", font=("Courier", 7), foreground="gray").grid(row=i, column=1, sticky="w", pady=2)

            # Connection indicator
            conn_indicator = tk.Label(limit_frame, text="●", font=("Arial", 10), fg="#95A5A6")
            conn_indicator.grid(row=i, column=2, padx=2, pady=2)
            self.sensor_connection_widgets[switch_id] = conn_indicator

            # State label
            state_label = ttk.Label(limit_frame, text="OPEN", width=10,
                                   relief=tk.SUNKEN, anchor=tk.CENTER,
                                   background="#95A5A6", foreground="white",
                                   font=("Arial", 8, "bold"))
            state_label.grid(row=i, column=3, padx=5, pady=2)

            self.sensor_widgets[switch_id] = state_label

    def create_grbl_tab(self):
        """Create GRBL settings management tab"""
        # Configure grid
        self.grbl_tab.columnconfigure(0, weight=1)
        self.grbl_tab.columnconfigure(1, weight=1)
        self.grbl_tab.rowconfigure(1, weight=1)

        # Control buttons at top
        control_frame = ttk.Frame(self.grbl_tab)
        control_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        ttk.Button(control_frame, text="Read Settings ($$)", command=self.read_grbl_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Apply Changes", command=self.write_grbl_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Reset to Defaults", command=self.reset_grbl_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Unlock ($X)", command=self.unlock_grbl).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Home ($H)", command=self.home_grbl).pack(side=tk.LEFT, padx=5)

        # Settings display
        settings_frame = ttk.LabelFrame(self.grbl_tab, text="GRBL Configuration", padding="10")
        settings_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Create scrollable frame for settings
        canvas = tk.Canvas(settings_frame, bg="white")
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Key settings to edit - in ascending order with default values
        self.grbl_entries = {}
        key_settings = [
            ("$0", "Step pulse", "Step pulse time (microseconds)", "10"),
            ("$1", "Step idle delay", "Step idle delay (milliseconds)", "25"),
            ("$2", "Step port invert", "Step port invert mask", "0"),
            ("$3", "Direction port invert", "Direction port invert mask", "0"),
            ("$4", "Step enable invert", "Step enable invert (boolean)", "0"),
            ("$5", "Limit pins invert", "Limit pins invert (boolean)", "0"),
            ("$6", "Probe pin invert", "Probe pin invert (boolean)", "0"),
            ("$10", "Status report", "Status report mask", "1"),
            ("$11", "Junction deviation", "Junction deviation (mm)", "0.010"),
            ("$12", "Arc tolerance", "Arc tolerance (mm)", "0.002"),
            ("$13", "Report inches", "Report in inches (boolean)", "0"),
            ("$20", "Soft limits", "Soft limits enable (boolean)", "0"),
            ("$21", "Hard limits", "Hard limits enable (boolean)", "0"),
            ("$22", "Homing cycle", "Homing cycle enable (boolean)", "0"),
            ("$23", "Homing dir invert", "Homing direction invert mask", "0"),
            ("$24", "Homing feed", "Homing feed rate (mm/min)", "25.0"),
            ("$25", "Homing seek", "Homing seek rate (mm/min)", "500.0"),
            ("$26", "Homing debounce", "Homing debounce (milliseconds)", "250"),
            ("$27", "Homing pull-off", "Homing pull-off distance (mm)", "1.0"),
            ("$30", "Max spindle speed", "Maximum spindle speed (RPM)", "1000"),
            ("$31", "Min spindle speed", "Minimum spindle speed (RPM)", "0"),
            ("$32", "Laser mode", "Laser mode enable (boolean)", "0"),
            ("$100", "X steps/mm", "Steps per mm for X axis", "250.0"),
            ("$101", "Y steps/mm", "Steps per mm for Y axis", "250.0"),
            ("$102", "Z steps/mm", "Steps per mm for Z axis", "250.0"),
            ("$110", "X Max rate", "Maximum rate for X axis (mm/min)", "500.0"),
            ("$111", "Y Max rate", "Maximum rate for Y axis (mm/min)", "500.0"),
            ("$112", "Z Max rate", "Maximum rate for Z axis (mm/min)", "500.0"),
            ("$120", "X Acceleration", "X axis acceleration (mm/sec²)", "10.0"),
            ("$121", "Y Acceleration", "Y axis acceleration (mm/sec²)", "10.0"),
            ("$122", "Z Acceleration", "Z axis acceleration (mm/sec²)", "10.0"),
            ("$130", "X Max travel", "Maximum travel for X axis (mm)", "200.0"),
            ("$131", "Y Max travel", "Maximum travel for Y axis (mm)", "200.0"),
            ("$132", "Z Max travel", "Maximum travel for Z axis (mm)", "200.0")
        ]

        for i, (param, name, tooltip, default) in enumerate(key_settings):
            row_frame = ttk.Frame(scrollable_frame)
            row_frame.grid(row=i, column=0, sticky="ew", pady=2)

            ttk.Label(row_frame, text=f"{param}", font=("Courier", 10, "bold"), width=6).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Label(row_frame, text=name, width=20).pack(side=tk.LEFT, padx=5)

            entry = ttk.Entry(row_frame, width=15)
            entry.insert(0, default)  # Set default value
            entry.pack(side=tk.LEFT, padx=5)

            # Add tooltip
            self.create_tooltip(entry, tooltip)

            self.grbl_entries[param] = entry

        # Command console on right
        console_frame = ttk.LabelFrame(self.grbl_tab, text="Direct GRBL Commands", padding="10")
        console_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        # Command input
        input_frame = ttk.Frame(console_frame)
        input_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(input_frame, text="Command:").pack(side=tk.LEFT, padx=(0, 5))
        self.grbl_command_entry = ttk.Entry(input_frame)
        self.grbl_command_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        self.grbl_command_entry.bind("<Return>", lambda e: self.send_grbl_command())

        ttk.Button(input_frame, text="Send", command=self.send_grbl_command).pack(side=tk.LEFT)

        # Response display
        ttk.Label(console_frame, text="Response:").pack(anchor="w", pady=(5, 0))
        self.grbl_response_text = scrolledtext.ScrolledText(console_frame, height=20, width=40,
                                                           font=("Courier", 9))
        self.grbl_response_text.pack(fill="both", expand=True)

    def create_console_tab(self):
        """Create status and logging console tab"""
        # Configure grid
        self.console_tab.rowconfigure(0, weight=1)
        self.console_tab.columnconfigure(0, weight=1)

        # Main console frame
        console_frame = ttk.Frame(self.console_tab)
        console_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        console_frame.rowconfigure(1, weight=1)
        console_frame.columnconfigure(0, weight=1)

        # Control buttons
        control_frame = ttk.Frame(console_frame)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        ttk.Button(control_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Save Log", command=self.save_log).pack(side=tk.LEFT, padx=5)

        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Auto-scroll", variable=self.auto_scroll_var).pack(side=tk.LEFT, padx=20)

        # Log level selector
        ttk.Label(control_frame, text="Log Level:").pack(side=tk.LEFT, padx=(20, 5))
        self.log_level_var = tk.StringVar(value="INFO")
        log_level_combo = ttk.Combobox(control_frame, textvariable=self.log_level_var,
                                       values=["DEBUG", "INFO", "WARNING", "ERROR"],
                                       state="readonly", width=10)
        log_level_combo.pack(side=tk.LEFT)

        # Console text widget
        self.console_text = scrolledtext.ScrolledText(console_frame, height=30, width=100,
                                                      font=("Courier", 9), bg="black", fg="white")
        self.console_text.grid(row=1, column=0, sticky="nsew")

        # Configure text tags for different log levels
        self.console_text.tag_config("DEBUG", foreground="gray")
        self.console_text.tag_config("INFO", foreground="white")
        self.console_text.tag_config("WARNING", foreground="yellow")
        self.console_text.tag_config("ERROR", foreground="red")
        self.console_text.tag_config("SUCCESS", foreground="lime")
        self.console_text.tag_config("GRBL", foreground="cyan")

        # Welcome message
        self.log("INFO", "Ultimate Hardware Test GUI initialized")
        self.log("INFO", "Click 'Connect Hardware' to begin testing")

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
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

                    # Check log level filter
                    levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
                    current_level_index = levels.index(self.log_level_var.get())
                    message_level_index = levels.index(level) if level in levels else 1

                    if message_level_index >= current_level_index:
                        # Format and insert message
                        formatted_msg = f"[{timestamp}] [{level:7}] {message}\n"

                        self.console_text.insert(tk.END, formatted_msg, level)

                        # Auto-scroll if enabled
                        if self.auto_scroll_var.get():
                            self.console_text.see(tk.END)

                time.sleep(0.01)
            except Exception as e:
                print(f"Log processor error: {e}")
                time.sleep(0.1)

    def scan_ports(self):
        """Scan for available serial ports"""
        try:
            import serial.tools.list_ports

            ports = serial.tools.list_ports.comports()
            self.available_ports = ["Auto-detect"]

            for port in ports:
                port_name = f"{port.device} - {port.description}"
                self.available_ports.append(port_name)

            # Update combobox
            self.port_combo['values'] = self.available_ports

            if len(self.available_ports) > 1:
                self.log("INFO", f"Found {len(self.available_ports)-1} serial port(s)")
            else:
                self.log("WARNING", "No serial ports found")

        except Exception as e:
            self.log("ERROR", f"Error scanning ports: {str(e)}")
            self.available_ports = ["Auto-detect"]
            self.port_combo['values'] = self.available_ports

    def auto_initialize(self):
        """Auto-initialize hardware on startup"""
        self.log("INFO", "Auto-initializing hardware...")
        self.toggle_connection()

    def toggle_connection(self):
        """Connect or disconnect hardware"""
        if not self.is_connected:
            self.connect_hardware()
        else:
            self.disconnect_hardware()

    def connect_hardware(self):
        """Connect to hardware"""
        try:
            self.log("INFO", "Connecting to hardware...")

            # Get selected port
            selected = self.selected_port.get()
            if selected and selected != "Auto-detect":
                # Extract just the port device (e.g., "/dev/ttyACM0" from "/dev/ttyACM0 - Arduino...")
                port_device = selected.split(" - ")[0]
                self.log("INFO", f"Using selected port: {port_device}")

                # Load config and temporarily override port if specified
                import json
                try:
                    with open('config/settings.json', 'r') as f:
                        config = json.load(f)
                    # Override the serial port in config
                    if 'grbl' in config:
                        config['grbl']['serial_port'] = port_device
                        # Save temporarily
                        with open('config/settings.json', 'w') as f:
                            json.dump(config, f, indent=4)
                        self.log("INFO", f"Configured GRBL port: {port_device}")
                except Exception as e:
                    self.log("WARNING", f"Could not update port in config: {e}")
            else:
                self.log("INFO", "Using auto-detect mode")

            # Get hardware interface
            self.hardware = get_hardware_interface()

            # Check mode
            mode = "REAL HARDWARE" if hasattr(self.hardware, 'gpio') else "MOCK/SIMULATION"
            self.mode_label.config(text=f"Mode: {mode}")
            self.log("INFO", f"Hardware mode: {mode}")

            # Initialize hardware
            if self.hardware.initialize():
                self.is_connected = True
                self.hw_status_label.config(text="Connected", foreground="green")
                self.connect_btn.config(text="Disconnect")
                self.log("SUCCESS", "Hardware connected successfully")

                # Check GRBL connection
                if hasattr(self.hardware, 'grbl') and self.hardware.grbl and self.hardware.grbl.is_connected:
                    self.grbl_connected = True
                    self.grbl_status_label.config(text="Connected", foreground="green")
                    self.log("SUCCESS", "GRBL connected successfully")

                    # Read initial settings
                    self.root.after(100, self.read_grbl_settings)
                else:
                    self.grbl_status_label.config(text="Not Available", foreground="orange")
                    self.log("WARNING", "GRBL not available")

                # Start monitoring thread
                self.monitor_running = True
                self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
                self.monitor_thread.start()

                # Enable all controls
                self.enable_controls(True)

            else:
                self.log("ERROR", "Failed to initialize hardware")
                messagebox.showerror("Connection Error", "Failed to initialize hardware")

        except Exception as e:
            self.log("ERROR", f"Connection error: {str(e)}")
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")

    def disconnect_hardware(self):
        """Disconnect from hardware"""
        self.log("INFO", "Disconnecting from hardware...")

        # Stop monitoring
        self.monitor_running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=2)

        # Shutdown hardware
        if self.hardware:
            self.hardware.shutdown()

        self.is_connected = False
        self.grbl_connected = False
        self.hw_status_label.config(text="Not Connected", foreground="red")
        self.grbl_status_label.config(text="Not Connected", foreground="red")
        self.connect_btn.config(text="Connect Hardware")

        # Disable controls
        self.enable_controls(False)

        self.log("INFO", "Hardware disconnected")

    def enable_controls(self, enabled):
        """Enable or disable all control widgets"""
        state = "normal" if enabled else "disabled"

        # Enable/disable all buttons in tabs (except emergency stop)
        for tab in [self.motors_tab, self.pistons_tab, self.grbl_tab]:
            for widget in tab.winfo_children():
                if isinstance(widget, (ttk.Button, ttk.Entry)):
                    widget.config(state=state)
                elif isinstance(widget, (ttk.Frame, ttk.LabelFrame)):
                    for child in widget.winfo_children():
                        if isinstance(child, (ttk.Button, ttk.Entry)):
                            child.config(state=state)

    def monitor_loop(self):
        """Monitor sensors and positions in background"""
        while self.monitor_running:
            try:
                # Update position from GRBL
                if self.grbl_connected and hasattr(self.hardware, 'grbl'):
                    status = self.hardware.grbl.get_status()
                    if status:
                        self.current_x = status.get('x', 0)
                        self.current_y = status.get('y', 0)
                        self.x_pos_var.set(f"X: {self.current_x:.2f} cm")
                        self.y_pos_var.set(f"Y: {self.current_y:.2f} cm")

                        state = status.get('state', 'Unknown')
                        color = "green" if state == "Idle" else "orange" if state == "Run" else "red"
                        self.motor_status_label.config(text=state, foreground=color)

                # Update sensors and connection indicators
                if self.is_connected:
                    # Update tool sensors and limit switches
                    for sensor_id, widget in self.sensor_widgets.items():
                        getter_method = f"get_{sensor_id}"
                        if hasattr(self.hardware, getter_method):
                            try:
                                state = getattr(self.hardware, getter_method)()

                                # Update connection indicator (green if method works)
                                if sensor_id in self.sensor_connection_widgets:
                                    self.sensor_connection_widgets[sensor_id].config(fg="#27AE60")  # Green

                                # Different display for limit switches
                                if "limit_switch" in sensor_id:
                                    if state:
                                        widget.config(text="CLOSED", background="#E74C3C", foreground="white")  # Red when triggered
                                    else:
                                        widget.config(text="OPEN", background="#95A5A6", foreground="white")  # Gray when open
                                else:
                                    # Regular sensors
                                    if state:
                                        widget.config(text="ACTIVE", background="#27AE60", foreground="white")  # Green
                                    else:
                                        widget.config(text="INACTIVE", background="#95A5A6", foreground="white")  # Gray
                            except:
                                # Connection failed
                                if sensor_id in self.sensor_connection_widgets:
                                    self.sensor_connection_widgets[sensor_id].config(fg="#E74C3C")  # Red for error
                        else:
                            # Method not found - no connection
                            if sensor_id in self.sensor_connection_widgets:
                                self.sensor_connection_widgets[sensor_id].config(fg="#95A5A6")  # Gray

                    # Update piston connection indicators
                    for piston_key, (name, method_base) in self.piston_methods.items():
                        # Check if piston control methods exist
                        if piston_key == "line_motor":
                            up_method = "line_motor_piston_up"
                            down_method = "line_motor_piston_down"
                        else:
                            up_method = f"{method_base}_up"
                            down_method = f"{method_base}_down"

                        if hasattr(self.hardware, up_method) and hasattr(self.hardware, down_method):
                            self.piston_connection_widgets[piston_key].config(fg="#27AE60")  # Green - connected
                        else:
                            self.piston_connection_widgets[piston_key].config(fg="#95A5A6")  # Gray - not found

                time.sleep(0.1)  # Update 10 times per second

            except Exception as e:
                self.log("ERROR", f"Monitor error: {str(e)}")
                time.sleep(1)

    # Motor control methods
    def jog(self, axis, direction):
        """Jog motor in specified direction"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        try:
            step = float(self.jog_step.get())

            if axis == 'X':
                new_pos = self.current_x + (step * direction)
                self.log("INFO", f"Jogging X by {step * direction:.2f}cm to {new_pos:.2f}cm")
                self.hardware.move_x(new_pos)
            else:  # Y
                new_pos = self.current_y + (step * direction)
                self.log("INFO", f"Jogging Y by {step * direction:.2f}cm to {new_pos:.2f}cm")
                self.hardware.move_y(new_pos)

        except Exception as e:
            self.log("ERROR", f"Jog error: {str(e)}")

    def move_to_position(self):
        """Move to manually entered position"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())

            self.log("INFO", f"Moving to position X={x:.2f}cm, Y={y:.2f}cm")
            if self.hardware.move_to(x, y):
                self.log("SUCCESS", f"Moved to X={x:.2f}cm, Y={y:.2f}cm")
            else:
                self.log("ERROR", "Move command failed")

        except ValueError:
            self.log("ERROR", "Invalid position values")
            messagebox.showerror("Error", "Invalid position values")

    def move_to_preset(self, x, y):
        """Move to preset position"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        self.log("INFO", f"Moving to preset position X={x:.2f}cm, Y={y:.2f}cm")
        if self.hardware.move_to(x, y):
            self.log("SUCCESS", f"Moved to preset X={x:.2f}cm, Y={y:.2f}cm")
        else:
            self.log("ERROR", "Move to preset failed")

    def home_motors(self):
        """Home all motors"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        if messagebox.askyesno("Home Motors", "Move all motors to home position (0, 0)?"):
            self.log("INFO", "Homing all motors...")
            if self.hardware.home_motors():
                self.log("SUCCESS", "Motors homed successfully")
                self.current_x = 0
                self.current_y = 0
                self.x_entry.delete(0, tk.END)
                self.x_entry.insert(0, "0")
                self.y_entry.delete(0, tk.END)
                self.y_entry.insert(0, "0")
            else:
                self.log("ERROR", "Homing failed")

    def emergency_stop(self):
        """Emergency stop all motors"""
        self.log("WARNING", "EMERGENCY STOP activated!")

        if self.is_connected and self.hardware.emergency_stop():
            messagebox.showwarning("Emergency Stop",
                                 "All motors stopped!\nClick OK to resume.")
            self.hardware.resume_operation()
            self.log("INFO", "Emergency stop cleared, operation resumed")

    # Piston control methods
    def piston_up(self, piston_key):
        """Raise piston"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        name, method_base = self.piston_methods[piston_key]

        # Special handling for line motor (uses different method names)
        if piston_key == "line_motor":
            method_name = "line_motor_piston_up"
        else:
            method_name = f"{method_base}_up"

        self.log("INFO", f"Raising {name}")

        if hasattr(self.hardware, method_name):
            if getattr(self.hardware, method_name)():
                self.piston_widgets[piston_key].config(text="UP", background="#3498DB")
                self.log("SUCCESS", f"{name} raised")
            else:
                self.log("ERROR", f"Failed to raise {name}")
        else:
            self.log("ERROR", f"Method {method_name} not found")

    def piston_down(self, piston_key):
        """Lower piston"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect hardware first")
            return

        name, method_base = self.piston_methods[piston_key]

        # Special handling for line motor (uses different method names)
        if piston_key == "line_motor":
            method_name = "line_motor_piston_down"
        else:
            method_name = f"{method_base}_down"

        self.log("INFO", f"Lowering {name}")

        if hasattr(self.hardware, method_name):
            if getattr(self.hardware, method_name)():
                self.piston_widgets[piston_key].config(text="DOWN", background="#27AE60")
                self.log("SUCCESS", f"{name} lowered")
            else:
                self.log("ERROR", f"Failed to lower {name}")
        else:
            self.log("ERROR", f"Method {method_name} not found")

    # GRBL methods
    def read_grbl_settings(self):
        """Read GRBL settings"""
        if not self.grbl_connected:
            self.log("WARNING", "GRBL not connected")
            return

        self.log("INFO", "Reading GRBL settings...")

        try:
            # Send $$ command to get all settings
            if hasattr(self.hardware, 'grbl') and hasattr(self.hardware.grbl, '_send_command'):
                response = self.hardware.grbl._send_command("$$")

                if response:
                    self.grbl_response_text.delete(1.0, tk.END)
                    self.grbl_response_text.insert(tk.END, response)

                    # Parse settings
                    lines = response.split('\n')
                    for line in lines:
                        # Match pattern like "$100=250.000"
                        match = re.match(r'(\$\d+)=(.+)', line)
                        if match:
                            param = match.group(1)
                            value = match.group(2)

                            if param in self.grbl_entries:
                                self.grbl_entries[param].delete(0, tk.END)
                                self.grbl_entries[param].insert(0, value)

                            self.grbl_settings[param] = value

                    self.log("SUCCESS", "GRBL settings loaded")
                else:
                    self.log("ERROR", "Failed to read GRBL settings")
            else:
                self.log("ERROR", "GRBL command interface not available")

        except Exception as e:
            self.log("ERROR", f"Error reading settings: {str(e)}")

    def write_grbl_settings(self):
        """Write modified GRBL settings"""
        if not self.grbl_connected:
            self.log("WARNING", "GRBL not connected")
            return

        if not messagebox.askyesno("Apply Settings",
                                  "Apply changes to GRBL configuration?\n\n" +
                                  "WARNING: Incorrect settings can damage hardware!"):
            return

        self.log("INFO", "Applying GRBL settings...")

        try:
            changes_made = False

            for param, entry in self.grbl_entries.items():
                new_value = entry.get().strip()
                if new_value and param in self.grbl_settings:
                    if new_value != self.grbl_settings[param]:
                        # Send setting command
                        command = f"{param}={new_value}"
                        self.log("INFO", f"Setting {command}")

                        if hasattr(self.hardware.grbl, '_send_command'):
                            response = self.hardware.grbl._send_command(command)

                            if response and "ok" in response.lower():
                                self.log("SUCCESS", f"Set {param} = {new_value}")
                                self.grbl_settings[param] = new_value
                                changes_made = True
                            else:
                                self.log("ERROR", f"Failed to set {param}")

            if changes_made:
                self.log("SUCCESS", "Settings applied successfully")
                # Re-read settings to confirm
                self.root.after(500, self.read_grbl_settings)
            else:
                self.log("INFO", "No changes to apply")

        except Exception as e:
            self.log("ERROR", f"Error applying settings: {str(e)}")

    def reset_grbl_settings(self):
        """Reset GRBL to default settings"""
        if not self.grbl_connected:
            self.log("WARNING", "GRBL not connected")
            return

        if not messagebox.askyesno("Reset Settings",
                                  "Reset GRBL to factory defaults?\n\n" +
                                  "This will reset ALL settings!"):
            return

        self.log("WARNING", "Resetting GRBL to defaults...")

        try:
            if hasattr(self.hardware.grbl, '_send_command'):
                response = self.hardware.grbl._send_command("$RST=$")

                if response:
                    self.log("SUCCESS", "GRBL reset to defaults")
                    # Re-read settings
                    self.root.after(500, self.read_grbl_settings)
                else:
                    self.log("ERROR", "Failed to reset GRBL")

        except Exception as e:
            self.log("ERROR", f"Error resetting GRBL: {str(e)}")

    def unlock_grbl(self):
        """Unlock GRBL"""
        if not self.grbl_connected:
            self.log("WARNING", "GRBL not connected")
            return

        self.log("INFO", "Unlocking GRBL...")

        try:
            if hasattr(self.hardware.grbl, '_send_command'):
                response = self.hardware.grbl._send_command("$X")

                if response and "ok" in response.lower():
                    self.log("SUCCESS", "GRBL unlocked")
                else:
                    self.log("ERROR", "Failed to unlock GRBL")

        except Exception as e:
            self.log("ERROR", f"Error unlocking GRBL: {str(e)}")

    def home_grbl(self):
        """Home GRBL"""
        if not self.grbl_connected:
            self.log("WARNING", "GRBL not connected")
            return

        self.log("INFO", "Homing GRBL...")

        try:
            if hasattr(self.hardware.grbl, '_send_command'):
                response = self.hardware.grbl._send_command("$H", timeout=30)

                if response and "ok" in response.lower():
                    self.log("SUCCESS", "GRBL homing completed")
                else:
                    self.log("ERROR", "GRBL homing failed")

        except Exception as e:
            self.log("ERROR", f"Error homing GRBL: {str(e)}")

    def send_grbl_command(self):
        """Send direct GRBL command"""
        if not self.grbl_connected:
            self.log("WARNING", "GRBL not connected")
            return

        command = self.grbl_command_entry.get().strip()
        if not command:
            return

        self.log("GRBL", f"Sending: {command}")

        try:
            if hasattr(self.hardware.grbl, '_send_command'):
                response = self.hardware.grbl._send_command(command)

                if response:
                    self.grbl_response_text.insert(tk.END, f"\n> {command}\n{response}\n")
                    self.grbl_response_text.see(tk.END)
                    self.log("GRBL", f"Response: {response.replace(chr(10), ' ')}")
                else:
                    self.grbl_response_text.insert(tk.END, f"\n> {command}\n[No response]\n")
                    self.grbl_response_text.see(tk.END)
                    self.log("WARNING", "No response from GRBL")

            # Clear command entry
            self.grbl_command_entry.delete(0, tk.END)

        except Exception as e:
            self.log("ERROR", f"Error sending command: {str(e)}")

    # Console methods
    def clear_log(self):
        """Clear the console log"""
        self.console_text.delete(1.0, tk.END)
        self.log("INFO", "Log cleared")

    def save_log(self):
        """Save log to file"""
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"hardware_test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.console_text.get(1.0, tk.END))
                self.log("SUCCESS", f"Log saved to {filename}")
            except Exception as e:
                self.log("ERROR", f"Failed to save log: {str(e)}")

    def on_closing(self):
        """Handle window closing"""
        if self.is_connected:
            if messagebox.askokcancel("Quit", "Disconnect hardware and quit?"):
                self.log_processor_running = False
                self.disconnect_hardware()
                self.root.destroy()
        else:
            self.log_processor_running = False
            self.root.destroy()


def main():
    """Main function"""
    root = tk.Tk()
    app = UltimateHardwareTestGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
import tkinter as tk
import json
from mock_hardware import (
    get_current_x, get_current_y, get_hardware_status,
    get_line_marker_piston_state, get_row_marker_limit_switch,
    get_row_marker_state, get_line_cutter_state, get_row_cutter_state,
    get_line_tools_height, get_sensor_trigger_states
)


class HardwareStatusPanel:
    """Comprehensive hardware status monitoring panel"""

    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        self.status_labels = {}

        # Load settings
        self.settings = main_app.settings
        self.hw_settings = self.settings.get("hardware_monitor", {})
        self.colors = self.hw_settings.get("status_colors", {})
        self.ui_fonts = self.settings.get("ui_fonts", {})

        # Get colors with fallbacks
        self.bg_color = self.hw_settings.get("background_color", "#2C3E50")
        self.section_bg = self.hw_settings.get("section_bg_color", "#34495E")
        self.text_color = self.hw_settings.get("text_color", "#ECF0F1")
        self.label_color = self.hw_settings.get("label_color", "#BDC3C7")
        self.separator_color = self.hw_settings.get("separator_color", "#7F8C8D")
        self.update_interval = self.hw_settings.get("update_interval_ms", 200)

        # Create the hardware status panel
        self.create_hardware_status_panel()

        # Schedule regular updates
        self.schedule_update()

    def create_hardware_status_panel(self):
        """Create comprehensive hardware status display"""
        # Get font settings
        title_font = tuple(self.ui_fonts.get("title", ["Arial", 12, "bold"]))

        # Main container with border
        main_container = tk.Frame(self.parent_frame, relief=tk.RIDGE, bd=3, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Title
        title_frame = tk.Frame(main_container, bg=self.section_bg)
        title_frame.pack(fill=tk.X, padx=2, pady=2)
        tk.Label(title_frame, text="⚙️ HARDWARE STATUS MONITOR",
                font=title_font, bg=self.section_bg, fg=self.text_color).pack(pady=5)

        # Content frame
        content_frame = tk.Frame(main_container, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create 5 columns: Motors | Line Tools | Row Tools | Sensors | System
        columns_frame = tk.Frame(content_frame, bg=self.bg_color)
        columns_frame.pack(fill=tk.BOTH, expand=True)

        # Column 1: MOTORS & POSITION
        motors_frame = self._create_section_frame(columns_frame, "🎯 MOTORS & POSITION")
        motors_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(motors_frame, "X Motor Position", "x_position",
                                self.colors.get("motor_x", "#E74C3C"))
        self._create_status_item(motors_frame, "Y Motor Position", "y_position",
                                self.colors.get("motor_y", "#3498DB"))

        # Column 2: LINE TOOLS (Y-Axis)
        line_tools_frame = self._create_section_frame(columns_frame, "✏️ LINE TOOLS (Y-Axis)")
        line_tools_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(line_tools_frame, "Line Marker Piston", "line_marker_piston",
                                self.colors.get("line_tools", "#3498DB"))
        self._create_status_item(line_tools_frame, "Line Cutter", "line_cutter",
                                self.colors.get("line_tools", "#9B59B6"))
        self._create_status_item(line_tools_frame, "Line Tools Height", "line_tools_height",
                                self.colors.get("line_tools", "#1ABC9C"))

        # Column 3: ROW TOOLS (X-Axis)
        row_tools_frame = self._create_section_frame(columns_frame, "✂️ ROW TOOLS (X-Axis)")
        row_tools_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(row_tools_frame, "Row Marker State", "row_marker_state",
                                self.colors.get("row_tools", "#E74C3C"))
        self._create_status_item(row_tools_frame, "Row Marker Limit", "row_marker_limit",
                                self.colors.get("row_tools", "#E67E22"))
        self._create_status_item(row_tools_frame, "Row Cutter", "row_cutter",
                                self.colors.get("row_tools", "#C0392B"))

        # Column 4: SENSORS
        sensors_frame = self._create_section_frame(columns_frame, "📡 SENSORS")
        sensors_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(sensors_frame, "X Left Sensor", "x_left_sensor",
                                self.colors.get("sensors_x", "#F39C12"))
        self._create_status_item(sensors_frame, "X Right Sensor", "x_right_sensor",
                                self.colors.get("sensors_x", "#F39C12"))
        self._create_status_item(sensors_frame, "Y Top Sensor", "y_top_sensor",
                                self.colors.get("sensors_y", "#27AE60"))
        self._create_status_item(sensors_frame, "Y Bottom Sensor", "y_bottom_sensor",
                                self.colors.get("sensors_y", "#27AE60"))

        # Column 5: SYSTEM STATUS & PROGRESS
        system_frame = self._create_section_frame(columns_frame, "⚡ SYSTEM & PROGRESS")
        system_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(system_frame, "Operation Mode", "operation_mode",
                                self.colors.get("system", "#8E44AD"))
        self._create_status_item(system_frame, "Safety Status", "safety_status",
                                self.colors.get("active", "#27AE60"))

        # Add progress bar section
        self._create_progress_section(system_frame)

    def _create_section_frame(self, parent, title):
        """Create a section frame with title"""
        heading_font = tuple(self.ui_fonts.get("heading", ["Arial", 9, "bold"]))
        frame = tk.Frame(parent, relief=tk.SOLID, bd=1, bg=self.section_bg)

        # Section title
        title_label = tk.Label(frame, text=title, font=heading_font,
                              bg=self.section_bg, fg=self.text_color)
        title_label.pack(pady=3)

        # Separator
        tk.Frame(frame, height=1, bg=self.separator_color).pack(fill=tk.X, padx=2)

        return frame

    def _create_status_item(self, parent, label_text, status_key, color):
        """Create a status item with label and value"""
        label_font = tuple(self.ui_fonts.get("label", ["Arial", 8, "bold"]))
        normal_font = tuple(self.ui_fonts.get("normal", ["Arial", 9]))

        item_frame = tk.Frame(parent, bg=self.section_bg)
        item_frame.pack(fill=tk.X, padx=5, pady=3)

        # Label
        label = tk.Label(item_frame, text=label_text + ":",
                        font=label_font, bg=self.section_bg, fg=self.label_color,
                        anchor='w')
        label.pack(fill=tk.X)

        # Status value with colored background
        status_frame = tk.Frame(item_frame, bg=color, relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, pady=2)

        status_label = tk.Label(status_frame, text="---",
                               font=normal_font, bg=color, fg='white',
                               anchor='center')
        status_label.pack(fill=tk.X, padx=2, pady=2)

        # Store reference
        self.status_labels[status_key] = (status_label, status_frame, color)

    def _create_progress_section(self, parent):
        """Create progress bar section"""
        from tkinter import ttk

        label_font = tuple(self.ui_fonts.get("label", ["Arial", 8, "bold"]))
        normal_font = tuple(self.ui_fonts.get("normal", ["Arial", 8]))

        progress_container = tk.Frame(parent, bg=self.section_bg)
        progress_container.pack(fill=tk.X, padx=5, pady=5)

        # Label
        tk.Label(progress_container, text="Execution Progress:",
                font=label_font, bg=self.section_bg, fg=self.label_color,
                anchor='w').pack(fill=tk.X)

        # Progress bar
        progress_bar = ttk.Progressbar(progress_container, mode='determinate')
        progress_bar.pack(fill=tk.X, pady=2)

        # Progress text
        progress_text = tk.Label(progress_container, text="0% Complete",
                                font=normal_font, bg=self.section_bg, fg=self.text_color,
                                anchor='center')
        progress_text.pack(fill=tk.X)

        # Store references in main app
        self.main_app.progress = progress_bar
        self.main_app.progress_text = progress_text

    def update_hardware_status(self):
        """Update all hardware status displays"""
        try:
            # Get all hardware states
            hw_status = get_hardware_status()

            # Get colors from settings
            active_color = self.colors.get("active", "#27AE60")
            inactive_color = self.colors.get("inactive", "#95A5A6")
            critical_color = self.colors.get("critical", "#E74C3C")
            motor_x_color = self.colors.get("motor_x", "#E74C3C")
            motor_y_color = self.colors.get("motor_y", "#3498DB")
            sensor_x_color = self.colors.get("sensors_x", "#F39C12")
            sensor_y_color = self.colors.get("sensors_y", "#27AE60")
            sensor_trig_x = self.colors.get("sensor_triggered_x", "#FF3300")
            sensor_trig_y = self.colors.get("sensor_triggered_y", "#00FF00")

            # Update motor positions
            self._update_status_display('x_position', f"{hw_status['x_position']:.1f} cm", motor_x_color)
            self._update_status_display('y_position', f"{hw_status['y_position']:.1f} cm", motor_y_color)

            # Update line tools
            line_piston = get_line_marker_piston_state().upper()
            self._update_status_display('line_marker_piston', line_piston,
                                       active_color if line_piston == 'DOWN' else inactive_color)

            line_cutter = hw_status['line_cutter'].upper()
            self._update_status_display('line_cutter', line_cutter,
                                       critical_color if line_cutter == 'OPEN' else inactive_color)

            line_height = hw_status['line_tools_height'].upper()
            self._update_status_display('line_tools_height', line_height,
                                       active_color if line_height == 'DOWN' else inactive_color)

            # Update row tools
            row_marker = hw_status['row_marker'].upper()
            self._update_status_display('row_marker_state', row_marker,
                                       active_color if row_marker == 'OPEN' else inactive_color)

            row_limit = get_row_marker_limit_switch().upper()
            self._update_status_display('row_marker_limit', row_limit,
                                       active_color if row_limit == 'DOWN' else inactive_color)

            row_cutter = hw_status['row_cutter'].upper()
            self._update_status_display('row_cutter', row_cutter,
                                       critical_color if row_cutter == 'OPEN' else inactive_color)

            # Update sensors with live trigger detection
            sensor_triggers = get_sensor_trigger_states()

            # X sensors - show TRIGGERED in bright color when active
            self._update_status_display('x_left_sensor',
                                       'TRIGGERED!' if sensor_triggers['x_left'] else 'READY',
                                       sensor_trig_x if sensor_triggers['x_left'] else sensor_x_color)
            self._update_status_display('x_right_sensor',
                                       'TRIGGERED!' if sensor_triggers['x_right'] else 'READY',
                                       sensor_trig_x if sensor_triggers['x_right'] else sensor_x_color)

            # Y sensors - show TRIGGERED in bright color when active
            self._update_status_display('y_top_sensor',
                                       'TRIGGERED!' if sensor_triggers['y_top'] else 'READY',
                                       sensor_trig_y if sensor_triggers['y_top'] else sensor_y_color)
            self._update_status_display('y_bottom_sensor',
                                       'TRIGGERED!' if sensor_triggers['y_bottom'] else 'READY',
                                       sensor_trig_y if sensor_triggers['y_bottom'] else sensor_y_color)

            # Update system status
            if hasattr(self.main_app, 'canvas_manager'):
                mode = self.main_app.canvas_manager.motor_operation_mode.upper()
                mode_color = '#E74C3C' if mode == 'IDLE' else '#F39C12' if mode == 'LINES' else '#3498DB'
                self._update_status_display('operation_mode', mode, mode_color)
            else:
                self._update_status_display('operation_mode', 'IDLE', '#95A5A6')

            self._update_status_display('safety_status', 'OK', '#27AE60')

        except Exception as e:
            print(f"Error updating hardware status: {e}")

    def _update_status_display(self, status_key, text, color):
        """Update a single status display with text and color"""
        if status_key in self.status_labels:
            label, frame, _ = self.status_labels[status_key]
            label.config(text=text, bg=color)
            frame.config(bg=color)

    def schedule_update(self):
        """Schedule periodic hardware status updates"""
        self.update_hardware_status()
        # Update at configured interval for real-time monitoring
        self.main_app.root.after(self.update_interval, self.schedule_update)

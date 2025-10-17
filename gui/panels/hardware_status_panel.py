import tkinter as tk
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

        # Create the hardware status panel
        self.create_hardware_status_panel()

        # Schedule regular updates
        self.schedule_update()

    def create_hardware_status_panel(self):
        """Create comprehensive hardware status display"""
        # Main container with border
        main_container = tk.Frame(self.parent_frame, relief=tk.RIDGE, bd=3, bg='#2C3E50')
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Title
        title_frame = tk.Frame(main_container, bg='#34495E')
        title_frame.pack(fill=tk.X, padx=2, pady=2)
        tk.Label(title_frame, text="⚙️ HARDWARE STATUS MONITOR",
                font=('Arial', 12, 'bold'), bg='#34495E', fg='#ECF0F1').pack(pady=5)

        # Content frame
        content_frame = tk.Frame(main_container, bg='#2C3E50')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create 5 columns: Motors | Line Tools | Row Tools | Sensors | System
        columns_frame = tk.Frame(content_frame, bg='#2C3E50')
        columns_frame.pack(fill=tk.BOTH, expand=True)

        # Column 1: MOTORS & POSITION
        motors_frame = self._create_section_frame(columns_frame, "🎯 MOTORS & POSITION")
        motors_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(motors_frame, "X Motor Position", "x_position", "#E74C3C")
        self._create_status_item(motors_frame, "Y Motor Position", "y_position", "#3498DB")

        # Column 2: LINE TOOLS (Y-Axis)
        line_tools_frame = self._create_section_frame(columns_frame, "✏️ LINE TOOLS (Y-Axis)")
        line_tools_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(line_tools_frame, "Line Marker Piston", "line_marker_piston", "#3498DB")
        self._create_status_item(line_tools_frame, "Line Cutter", "line_cutter", "#9B59B6")
        self._create_status_item(line_tools_frame, "Line Tools Height", "line_tools_height", "#1ABC9C")

        # Column 3: ROW TOOLS (X-Axis)
        row_tools_frame = self._create_section_frame(columns_frame, "✂️ ROW TOOLS (X-Axis)")
        row_tools_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(row_tools_frame, "Row Marker State", "row_marker_state", "#E74C3C")
        self._create_status_item(row_tools_frame, "Row Marker Limit", "row_marker_limit", "#E67E22")
        self._create_status_item(row_tools_frame, "Row Cutter", "row_cutter", "#C0392B")

        # Column 4: SENSORS
        sensors_frame = self._create_section_frame(columns_frame, "📡 SENSORS")
        sensors_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(sensors_frame, "X Left Sensor", "x_left_sensor", "#F39C12")
        self._create_status_item(sensors_frame, "X Right Sensor", "x_right_sensor", "#F39C12")
        self._create_status_item(sensors_frame, "Y Top Sensor", "y_top_sensor", "#27AE60")
        self._create_status_item(sensors_frame, "Y Bottom Sensor", "y_bottom_sensor", "#27AE60")

        # Column 5: SYSTEM STATUS
        system_frame = self._create_section_frame(columns_frame, "⚡ SYSTEM")
        system_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        self._create_status_item(system_frame, "Operation Mode", "operation_mode", "#8E44AD")
        self._create_status_item(system_frame, "Safety Status", "safety_status", "#27AE60")

    def _create_section_frame(self, parent, title):
        """Create a section frame with title"""
        frame = tk.Frame(parent, relief=tk.SOLID, bd=1, bg='#34495E')

        # Section title
        title_label = tk.Label(frame, text=title, font=('Arial', 9, 'bold'),
                              bg='#34495E', fg='#ECF0F1')
        title_label.pack(pady=3)

        # Separator
        tk.Frame(frame, height=1, bg='#7F8C8D').pack(fill=tk.X, padx=2)

        return frame

    def _create_status_item(self, parent, label_text, status_key, color):
        """Create a status item with label and value"""
        item_frame = tk.Frame(parent, bg='#34495E')
        item_frame.pack(fill=tk.X, padx=5, pady=3)

        # Label
        label = tk.Label(item_frame, text=label_text + ":",
                        font=('Arial', 8, 'bold'), bg='#34495E', fg='#BDC3C7',
                        anchor='w')
        label.pack(fill=tk.X)

        # Status value with colored background
        status_frame = tk.Frame(item_frame, bg=color, relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, pady=2)

        status_label = tk.Label(status_frame, text="---",
                               font=('Arial', 9, 'bold'), bg=color, fg='white',
                               anchor='center')
        status_label.pack(fill=tk.X, padx=2, pady=2)

        # Store reference
        self.status_labels[status_key] = (status_label, status_frame, color)

    def update_hardware_status(self):
        """Update all hardware status displays"""
        try:
            # Get all hardware states
            hw_status = get_hardware_status()

            # Update motor positions
            self._update_status_display('x_position', f"{hw_status['x_position']:.1f} cm", '#E74C3C')
            self._update_status_display('y_position', f"{hw_status['y_position']:.1f} cm", '#3498DB')

            # Update line tools
            line_piston = get_line_marker_piston_state().upper()
            self._update_status_display('line_marker_piston', line_piston,
                                       '#27AE60' if line_piston == 'DOWN' else '#95A5A6')

            line_cutter = hw_status['line_cutter'].upper()
            self._update_status_display('line_cutter', line_cutter,
                                       '#E74C3C' if line_cutter == 'OPEN' else '#95A5A6')

            line_height = hw_status['line_tools_height'].upper()
            self._update_status_display('line_tools_height', line_height,
                                       '#27AE60' if line_height == 'DOWN' else '#95A5A6')

            # Update row tools
            row_marker = hw_status['row_marker'].upper()
            self._update_status_display('row_marker_state', row_marker,
                                       '#27AE60' if row_marker == 'OPEN' else '#95A5A6')

            row_limit = get_row_marker_limit_switch().upper()
            self._update_status_display('row_marker_limit', row_limit,
                                       '#27AE60' if row_limit == 'DOWN' else '#95A5A6')

            row_cutter = hw_status['row_cutter'].upper()
            self._update_status_display('row_cutter', row_cutter,
                                       '#E74C3C' if row_cutter == 'OPEN' else '#95A5A6')

            # Update sensors with live trigger detection
            sensor_triggers = get_sensor_trigger_states()

            # X sensors - show TRIGGERED in bright color when active
            self._update_status_display('x_left_sensor',
                                       'TRIGGERED!' if sensor_triggers['x_left'] else 'READY',
                                       '#FF3300' if sensor_triggers['x_left'] else '#F39C12')
            self._update_status_display('x_right_sensor',
                                       'TRIGGERED!' if sensor_triggers['x_right'] else 'READY',
                                       '#FF3300' if sensor_triggers['x_right'] else '#F39C12')

            # Y sensors - show TRIGGERED in bright color when active
            self._update_status_display('y_top_sensor',
                                       'TRIGGERED!' if sensor_triggers['y_top'] else 'READY',
                                       '#00FF00' if sensor_triggers['y_top'] else '#27AE60')
            self._update_status_display('y_bottom_sensor',
                                       'TRIGGERED!' if sensor_triggers['y_bottom'] else 'READY',
                                       '#00FF00' if sensor_triggers['y_bottom'] else '#27AE60')

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
        # Update every 200ms for real-time monitoring
        self.main_app.root.after(200, self.schedule_update)

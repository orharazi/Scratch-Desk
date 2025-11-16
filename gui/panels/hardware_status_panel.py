import tkinter as tk
import json
from core.logger import get_logger


class HardwareStatusPanel:
    """Compact grid-based hardware status monitoring panel"""

    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        self.logger = get_logger()
        # Access hardware through main_app
        self.hardware = main_app.hardware
        self.status_widgets = {}  # {key: {'label': tk.Label, 'frame': tk.Frame}}

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

        # State colors from settings
        self.piston_up_color = self.colors.get("piston_up", "#95A5A6")  # Gray
        self.piston_down_color = self.colors.get("piston_down", "#27AE60")  # Green
        self.sensor_ready_color = self.colors.get("sensor_ready", "#3498DB")  # Blue
        self.sensor_triggered_color = self.colors.get("sensor_triggered", "#E74C3C")  # Red
        self.switch_off_color = self.colors.get("switch_off", "#7F8C8D")  # Dark gray
        self.switch_on_color = self.colors.get("switch_on", "#F39C12")  # Orange

        # Create the hardware status panel
        self.create_hardware_status_panel()

        # Schedule regular updates
        self.schedule_update()

    def create_hardware_status_panel(self):
        """Create compact grid-based hardware status display"""
        # Fonts
        title_font = tuple(self.ui_fonts.get("title", ["Arial", 11, "bold"]))
        heading_font = tuple(self.ui_fonts.get("heading", ["Arial", 8, "bold"]))
        label_font = tuple(self.ui_fonts.get("label", ["Arial", 7]))
        tiny_font = tuple(self.ui_fonts.get("tiny", ["Arial", 6]))

        # Main container
        main_container = tk.Frame(self.parent_frame, relief=tk.RIDGE, bd=2, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Title
        tk.Label(main_container, text="⚙️ HARDWARE STATUS",
                font=title_font, bg=self.section_bg, fg=self.text_color).pack(fill=tk.X, pady=(2, 0))

        # Content grid
        grid_frame = tk.Frame(main_container, bg=self.bg_color)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # Configure grid columns with equal weight (3 columns now)
        for i in range(3):
            grid_frame.columnconfigure(i, weight=1, uniform="cols")

        row = 0

        # MOTORS & SYSTEM Section (combined to save space)
        self._create_section_header(grid_frame, 0, row, "🎯 MOTORS & SYSTEM", heading_font)
        row_offset = row + 1
        self._create_grid_item(grid_frame, 0, row_offset, "X Position", "x_position", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 1, "Y Position", "y_position", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 2, "Top Limit Switch", "top_limit_switch", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 3, "Bottom Limit Switch", "bottom_limit_switch", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 4, "Right Limit Switch", "right_limit_switch", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 5, "Left Limit Switch", "left_limit_switch", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 6, "Rows Limit Switch", "rows_limit_switch", label_font, tiny_font)
        # System items (merged into same column)
        row_offset += 7
        self._create_operation_mode_item(grid_frame, 0, row_offset, heading_font, label_font, tiny_font)
        row_offset += 3
        self._create_progress_section(grid_frame, 0, row_offset, label_font, tiny_font)

        # LINES Section
        self._create_section_header(grid_frame, 1, row, "✏️ LINES", heading_font)
        row_offset = row + 1
        # Tool Sensors subsection (UP/DOWN sensors for each tool)
        self._create_subsection_header(grid_frame, 1, row_offset, "Tool Sensors", tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 1, row_offset, "Marker ↑", "line_marker_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 1, "Marker ↓", "line_marker_down_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 2, "Cutter ↑", "line_cutter_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 3, "Cutter ↓", "line_cutter_down_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 4, "Motor L↑", "line_motor_left_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 5, "Motor L↓", "line_motor_left_down_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 6, "Motor R↑", "line_motor_right_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 7, "Motor R↓", "line_motor_right_down_sensor", label_font, tiny_font)
        # Edge Sensors subsection
        row_offset += 8
        self._create_subsection_header(grid_frame, 1, row_offset, "Edge Sensors", tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 1, row_offset, "X Left", "x_left_edge_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 1, "X Right", "x_right_edge_sensor", label_font, tiny_font)
        # Pistons subsection
        row_offset += 2
        self._create_subsection_header(grid_frame, 1, row_offset, "Pistons", tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 1, row_offset, "Marker", "lines_piston_marker", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 1, "Cutter", "lines_piston_cutter", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 2, "Motor L", "lines_piston_motor_left", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 3, "Motor R", "lines_piston_motor_right", label_font, tiny_font)

        # ROWS Section
        self._create_section_header(grid_frame, 2, row, "✂️ ROWS", heading_font)
        row_offset = row + 1
        # Tool Sensors subsection (UP/DOWN sensors for each tool)
        self._create_subsection_header(grid_frame, 2, row_offset, "Tool Sensors", tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 2, row_offset, "Marker ↑", "row_marker_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 1, "Marker ↓", "row_marker_down_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 2, "Cutter ↑", "row_cutter_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 3, "Cutter ↓", "row_cutter_down_sensor", label_font, tiny_font)
        # Edge Sensors subsection
        row_offset += 4
        self._create_subsection_header(grid_frame, 2, row_offset, "Edge Sensors", tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 2, row_offset, "Y Top", "y_top_edge_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 1, "Y Bottom", "y_bottom_edge_sensor", label_font, tiny_font)
        # Pistons subsection
        row_offset += 2
        self._create_subsection_header(grid_frame, 2, row_offset, "Pistons", tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 2, row_offset, "Marker", "rows_piston_marker", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 1, "Cutter", "rows_piston_cutter", label_font, tiny_font)

    def _create_section_header(self, parent, col, row, text, font):
        """Create section header"""
        label = tk.Label(parent, text=text, font=font,
                        bg=self.section_bg, fg=self.text_color,
                        relief=tk.RAISED, bd=1)
        label.grid(row=row, column=col, sticky="ew", padx=1, pady=(0, 1))

    def _create_subsection_header(self, parent, col, row, text, font):
        """Create subsection header"""
        label = tk.Label(parent, text=text, font=font,
                        bg=self.section_bg, fg=self.label_color,
                        anchor='w')
        label.grid(row=row, column=col, sticky="ew", padx=2, pady=(2, 0))

    def _create_grid_item(self, parent, col, row, label_text, status_key, label_font, value_font):
        """Create compact grid item with label and colored status (70/30 split)"""
        # Container frame
        container = tk.Frame(parent, bg=self.section_bg)
        container.grid(row=row, column=col, sticky="ew", padx=1, pady=1)

        # Configure 70/30 width split with minimum size for label
        container.columnconfigure(0, weight=7, minsize=100)  # Label gets 70% with min width
        container.columnconfigure(1, weight=3, minsize=50)   # Status gets 30% with min width

        # Label (left side - 70%) with fixed width for alignment
        label = tk.Label(container, text=label_text + ":", font=label_font,
                        bg=self.section_bg, fg=self.label_color,
                        anchor='w', width=18)  # Fixed width ensures vertical alignment
        label.grid(row=0, column=0, sticky="w", padx=(2, 1))

        # Status frame with color indicator (right side - 30%)
        status_frame = tk.Frame(container, bg=self.switch_off_color, relief=tk.SUNKEN, bd=1)
        status_frame.grid(row=0, column=1, sticky="ew", padx=(0, 2))

        # Status text with fixed width to prevent resizing
        status_label = tk.Label(status_frame, text="---", font=value_font,
                               bg=self.switch_off_color, fg='white',
                               anchor='center', width=10)  # Fixed width prevents resize
        status_label.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Debug: Print widget creation
        self.logger.debug(f"Created widget: {status_key}", category="gui")

        # Store references
        self.status_widgets[status_key] = {
            'label': status_label,
            'frame': status_frame
        }

    def _create_operation_mode_item(self, parent, col, row, heading_font, label_font, value_font):
        """Create operation mode display"""
        # Mode label
        tk.Label(parent, text="Mode:", font=label_font,
                bg=self.section_bg, fg=self.label_color,
                anchor='w').grid(row=row, column=col, sticky="ew", padx=2)

        # Status frame
        status_frame = tk.Frame(parent, bg='#95A5A6', relief=tk.RAISED, bd=1)
        status_frame.grid(row=row + 1, column=col, sticky="ew", padx=1, pady=1)

        status_label = tk.Label(status_frame, text="IDLE", font=heading_font,
                               bg='#95A5A6', fg='white', anchor='center')
        status_label.pack(fill=tk.BOTH, expand=True, pady=2)

        # Explanation
        explanation_label = tk.Label(parent, text="System ready", font=value_font,
                                    bg=self.section_bg, fg=self.label_color,
                                    anchor='w', wraplength=120)
        explanation_label.grid(row=row + 2, column=col, sticky="ew", padx=2)

        # Store references
        self.status_widgets['operation_mode'] = {
            'label': status_label,
            'frame': status_frame
        }
        self.status_widgets['operation_explanation'] = {
            'label': explanation_label,
            'frame': None
        }

    def _create_blocker_status_item(self, parent, col, row, label_font, value_font):
        """Create blocker/warning status display"""
        # Blocker label
        tk.Label(parent, text="Safety:", font=label_font,
                bg=self.section_bg, fg=self.label_color,
                anchor='w').grid(row=row, column=col, sticky="ew", padx=2)

        # Status frame
        status_frame = tk.Frame(parent, bg='#27AE60', relief=tk.SUNKEN, bd=1)
        status_frame.grid(row=row + 1, column=col, sticky="ew", padx=1, pady=1)

        status_label = tk.Label(status_frame, text="OK", font=value_font,
                               bg='#27AE60', fg='white', anchor='center',
                               wraplength=120)
        status_label.pack(fill=tk.BOTH, expand=True, pady=2, padx=2)

        # Store references
        self.status_widgets['blocker_status'] = {
            'label': status_label,
            'frame': status_frame
        }

    def _create_progress_section(self, parent, col, row, label_font, value_font):
        """Create compact progress section"""
        from tkinter import ttk

        # Progress label
        tk.Label(parent, text="Progress:", font=label_font,
                bg=self.section_bg, fg=self.label_color,
                anchor='w').grid(row=row, column=col, sticky="ew", padx=2, pady=(5, 0))

        # Progress bar
        progress_bar = ttk.Progressbar(parent, mode='determinate', length=100)
        progress_bar.grid(row=row + 1, column=col, sticky="ew", padx=2, pady=1)

        # Progress text
        progress_text = tk.Label(parent, text="0%", font=value_font,
                                bg=self.section_bg, fg=self.text_color,
                                anchor='center')
        progress_text.grid(row=row + 2, column=col, sticky="ew", padx=2)

        # Store references in main app
        self.main_app.progress = progress_bar
        self.main_app.progress_text = progress_text

    def update_hardware_status(self):
        """Update all hardware status displays"""
        try:
            # Trigger auto-reset for edge sensors (resets sensors triggered > 1 second ago)
            self.hardware.get_sensor_trigger_states()

            # Get all hardware states
            hw_status = self.hardware.get_hardware_status()

            # Check for hardware initialization errors
            if 'error' in hw_status and not hw_status.get('is_initialized', True):
                self.logger.error(f" HARDWARE ERROR: {hw_status['error']}", category="gui")
                # Show error in position displays
                self._update_widget('x_position', "ERROR", "#FF0000")
                self._update_widget('y_position', hw_status['error'][:20], "#FF0000")
                return

            # Debug: Print that we're updating
            self.logger.debug(f" Hardware status update: X={hw_status.get('x_position', '?')}, Y={hw_status.get('y_position', '?')}", category="gui")

            # Motor positions
            self._update_widget('x_position', f"{hw_status['x_position']:.1f}", self.colors.get("motor_x", "#E74C3C"))
            self._update_widget('y_position', f"{hw_status['y_position']:.1f}", self.colors.get("motor_y", "#3498DB"))

            # Limit switches - color coded: OFF=gray, ON=orange
            # Y-axis (Lines) - Top/Bottom
            y_top_ls = self.hardware.get_limit_switch_state('y_top')
            self._update_widget('top_limit_switch',
                               'ON' if y_top_ls else 'OFF',
                               self.switch_on_color if y_top_ls else self.switch_off_color)
            y_bottom_ls = self.hardware.get_limit_switch_state('y_bottom')
            self._update_widget('bottom_limit_switch',
                               'ON' if y_bottom_ls else 'OFF',
                               self.switch_on_color if y_bottom_ls else self.switch_off_color)

            # X-axis (Rows) - Right/Left
            x_right_ls = self.hardware.get_limit_switch_state('x_right')
            self._update_widget('right_limit_switch',
                               'ON' if x_right_ls else 'OFF',
                               self.switch_on_color if x_right_ls else self.switch_off_color)
            x_left_ls = self.hardware.get_limit_switch_state('x_left')
            self._update_widget('left_limit_switch',
                               'ON' if x_left_ls else 'OFF',
                               self.switch_on_color if x_left_ls else self.switch_off_color)

            # Rows limit switch
            rows_ls = self.hardware.get_limit_switch_state('rows')
            self._update_widget('rows_limit_switch',
                               'ON' if rows_ls else 'OFF',
                               self.switch_on_color if rows_ls else self.switch_off_color)

            # LINES SECTION - Tool Sensors (UP/DOWN sensors for each tool)
            # Color coded: READY (False)=blue, TRIGGERED (True)=red
            # Line Marker Sensors
            line_marker_up = self.hardware.get_line_marker_up_sensor()
            self._update_widget('line_marker_up_sensor',
                               'TRIG' if line_marker_up else 'READY',
                               self.sensor_triggered_color if line_marker_up else self.sensor_ready_color)
            line_marker_down = self.hardware.get_line_marker_down_sensor()
            self._update_widget('line_marker_down_sensor',
                               'TRIG' if line_marker_down else 'READY',
                               self.sensor_triggered_color if line_marker_down else self.sensor_ready_color)

            # Line Cutter Sensors
            line_cutter_up = self.hardware.get_line_cutter_up_sensor()
            self._update_widget('line_cutter_up_sensor',
                               'TRIG' if line_cutter_up else 'READY',
                               self.sensor_triggered_color if line_cutter_up else self.sensor_ready_color)
            line_cutter_down = self.hardware.get_line_cutter_down_sensor()
            self._update_widget('line_cutter_down_sensor',
                               'TRIG' if line_cutter_down else 'READY',
                               self.sensor_triggered_color if line_cutter_down else self.sensor_ready_color)

            # Line Motor Left Piston Sensors
            line_motor_left_up = self.hardware.get_line_motor_left_up_sensor()
            self._update_widget('line_motor_left_up_sensor',
                               'TRIG' if line_motor_left_up else 'READY',
                               self.sensor_triggered_color if line_motor_left_up else self.sensor_ready_color)
            line_motor_left_down = self.hardware.get_line_motor_left_down_sensor()
            self._update_widget('line_motor_left_down_sensor',
                               'TRIG' if line_motor_left_down else 'READY',
                               self.sensor_triggered_color if line_motor_left_down else self.sensor_ready_color)

            # Line Motor Right Piston Sensors
            line_motor_right_up = self.hardware.get_line_motor_right_up_sensor()
            self._update_widget('line_motor_right_up_sensor',
                               'TRIG' if line_motor_right_up else 'READY',
                               self.sensor_triggered_color if line_motor_right_up else self.sensor_ready_color)
            line_motor_right_down = self.hardware.get_line_motor_right_down_sensor()
            self._update_widget('line_motor_right_down_sensor',
                               'TRIG' if line_motor_right_down else 'READY',
                               self.sensor_triggered_color if line_motor_right_down else self.sensor_ready_color)

            # Edge Sensors (X-axis for Lines)
            x_left_edge = self.hardware.get_x_left_edge()
            self._update_widget('x_left_edge_sensor',
                               'TRIG' if x_left_edge else 'READY',
                               self.sensor_triggered_color if x_left_edge else self.sensor_ready_color)
            x_right_edge = self.hardware.get_x_right_edge()
            self._update_widget('x_right_edge_sensor',
                               'TRIG' if x_right_edge else 'READY',
                               self.sensor_triggered_color if x_right_edge else self.sensor_ready_color)

            # Pistons - color coded: UP=gray, DOWN=green
            line_marker_piston_state = self.hardware.get_line_marker_piston_state().upper()
            self._update_widget('lines_piston_marker', line_marker_piston_state,
                               self.piston_down_color if line_marker_piston_state == 'DOWN' else self.piston_up_color)

            line_cutter_piston_state = self.hardware.get_line_cutter_piston_state().upper()
            self._update_widget('lines_piston_cutter', line_cutter_piston_state,
                               self.piston_down_color if line_cutter_piston_state == 'DOWN' else self.piston_up_color)

            # Line motor sensors (left and right have separate sensors, shared piston control)
            line_motor_left_state = self.hardware.get_line_motor_piston_state().upper()
            self._update_widget('lines_piston_motor_left', line_motor_left_state,
                               self.piston_down_color if line_motor_left_state == 'DOWN' else self.piston_up_color)

            line_motor_right_state = self.hardware.get_line_motor_piston_state().upper()
            self._update_widget('lines_piston_motor_right', line_motor_right_state,
                               self.piston_down_color if line_motor_right_state == 'DOWN' else self.piston_up_color)

            # ROWS SECTION - Tool Sensors (UP/DOWN sensors for each tool)
            # Color coded: READY (False)=blue, TRIGGERED (True)=red
            # Row Marker Sensors
            row_marker_up = self.hardware.get_row_marker_up_sensor()
            self._update_widget('row_marker_up_sensor',
                               'TRIG' if row_marker_up else 'READY',
                               self.sensor_triggered_color if row_marker_up else self.sensor_ready_color)
            row_marker_down = self.hardware.get_row_marker_down_sensor()
            self._update_widget('row_marker_down_sensor',
                               'TRIG' if row_marker_down else 'READY',
                               self.sensor_triggered_color if row_marker_down else self.sensor_ready_color)

            # Row Cutter Sensors
            row_cutter_up = self.hardware.get_row_cutter_up_sensor()
            self._update_widget('row_cutter_up_sensor',
                               'TRIG' if row_cutter_up else 'READY',
                               self.sensor_triggered_color if row_cutter_up else self.sensor_ready_color)
            row_cutter_down = self.hardware.get_row_cutter_down_sensor()
            self._update_widget('row_cutter_down_sensor',
                               'TRIG' if row_cutter_down else 'READY',
                               self.sensor_triggered_color if row_cutter_down else self.sensor_ready_color)

            # Edge Sensors (Y-axis for Rows)
            y_top_edge = self.hardware.get_y_top_edge()
            self._update_widget('y_top_edge_sensor',
                               'TRIG' if y_top_edge else 'READY',
                               self.sensor_triggered_color if y_top_edge else self.sensor_ready_color)
            y_bottom_edge = self.hardware.get_y_bottom_edge()
            self._update_widget('y_bottom_edge_sensor',
                               'TRIG' if y_bottom_edge else 'READY',
                               self.sensor_triggered_color if y_bottom_edge else self.sensor_ready_color)

            # Pistons - color coded: UP=gray, DOWN=green
            row_marker_piston_state = self.hardware.get_row_marker_piston_state().upper()
            self._update_widget('rows_piston_marker', row_marker_piston_state,
                               self.piston_down_color if row_marker_piston_state == 'DOWN' else self.piston_up_color)

            row_cutter_piston_state = self.hardware.get_row_cutter_piston_state().upper()
            self._update_widget('rows_piston_cutter', row_cutter_piston_state,
                               self.piston_down_color if row_cutter_piston_state == 'DOWN' else self.piston_up_color)

            # Update operation mode
            self._update_operation_mode()

        except Exception as e:
            self.logger.error(f" ERROR in update_hardware_status: {e}", category="gui")
            import traceback
            traceback.print_exc()

    def _update_operation_mode(self):
        """Update operation mode with status and explanation"""
        if hasattr(self.main_app, 'execution_engine'):
            engine = self.main_app.execution_engine

            if engine.is_running:
                if hasattr(engine, 'is_blocked') and engine.is_blocked:
                    status = "BLOCKED"
                    explanation = getattr(engine, 'block_reason', 'Waiting')
                    color = '#E67E22'  # Orange
                elif hasattr(self.main_app, 'canvas_manager'):
                    mode = self.main_app.canvas_manager.motor_operation_mode.upper()
                    if mode == 'LINES':
                        status = "LINES"
                        explanation = "Marking lines"
                        color = '#3498DB'  # Blue
                    elif mode == 'ROWS':
                        status = "ROWS"
                        explanation = "Cutting rows"
                        color = '#E74C3C'  # Red
                    else:
                        status = "IDLE"
                        explanation = "System ready"
                        color = '#95A5A6'
                else:
                    status = "IDLE"
                    explanation = "System ready"
                    color = '#95A5A6'
            elif hasattr(engine, 'execution_completed') and engine.execution_completed:
                status = "SUCCESS"
                explanation = "All done!"
                color = '#27AE60'  # Green
            elif hasattr(engine, 'execution_failed') and engine.execution_failed:
                status = "FAIL"
                explanation = "Not completed"
                color = '#C0392B'  # Dark red
            else:
                status = "IDLE"
                explanation = "System ready"
                color = '#95A5A6'
        else:
            status = "IDLE"
            explanation = "System ready"
            color = '#95A5A6'

        self._update_widget('operation_mode', status, color)
        if 'operation_explanation' in self.status_widgets:
            self.status_widgets['operation_explanation']['label'].config(text=explanation)

    def _update_blocker_status(self):
        """Update blocker/safety status display"""
        blocker_message = "OK"
        blocker_color = '#27AE60'  # Green

        # Check if execution engine is running
        if hasattr(self.main_app, 'execution_engine') and self.main_app.execution_engine.is_running:
            # Get current operation mode
            if hasattr(self.main_app, 'canvas_manager'):
                mode = self.main_app.canvas_manager.motor_operation_mode.upper()

                # Get row marker state (piston position)
                row_marker_state = self.hardware.get_row_marker_piston_state().upper()

                # Safety check: row marker position must match operation type
                if mode == 'LINES':
                    # During LINES operation, row marker MUST be DOWN
                    if row_marker_state != 'DOWN':
                        blocker_message = "⚠️ Row marker must be DOWN for Lines operation"
                        blocker_color = '#E67E22'  # Orange warning
                elif mode == 'ROWS':
                    # During ROWS operation, row marker MUST be UP
                    if row_marker_state != 'UP':
                        blocker_message = "⚠️ Row marker must be UP for Rows operation"
                        blocker_color = '#E67E22'  # Orange warning

        self._update_widget('blocker_status', blocker_message, blocker_color)

    def _update_widget(self, key, text, color):
        """Update widget text and color"""
        if key in self.status_widgets:
            widget = self.status_widgets[key]
            widget['label'].config(text=text, bg=color)
            if widget['frame']:
                widget['frame'].config(bg=color)

    def schedule_update(self):
        """Schedule periodic hardware status updates"""
        self.update_hardware_status()
        self.main_app.root.after(self.update_interval, self.schedule_update)

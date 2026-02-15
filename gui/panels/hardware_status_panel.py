import tkinter as tk
import json
from core.logger import get_logger
from core.translations import t
from core.machine_state import MachineState, get_state_manager


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
        tk.Label(main_container, text=t("⚙️ HARDWARE STATUS"),
                font=title_font, bg=self.section_bg, fg=self.text_color).pack(fill=tk.X, pady=(2, 0))

        # Content grid
        grid_frame = tk.Frame(main_container, bg=self.bg_color)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # Configure grid columns with equal weight (3 columns)
        for i in range(3):
            grid_frame.columnconfigure(i, weight=1, uniform="cols")

        row = 0

        # MOTORS & SYSTEM Section (combined to save space)
        self._create_section_header(grid_frame, 0, row, t("🎯 MOTORS & SYSTEM"), heading_font)
        row_offset = row + 1
        self._create_grid_item(grid_frame, 0, row_offset, t("X Position"), "x_position", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 1, t("Y Position"), "y_position", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 2, t("Top Limit Switch"), "top_limit_switch", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 3, t("Bottom Limit Switch"), "bottom_limit_switch", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 4, t("Right Limit Switch"), "right_limit_switch", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 5, t("Left Limit Switch"), "left_limit_switch", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 6, t("Door Sensor"), "door_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 0, row_offset + 7, t("Air Pressure"), "air_pressure_valve", label_font, tiny_font)
        # System items (merged into same column)
        row_offset += 8
        self._create_operation_mode_item(grid_frame, 0, row_offset, heading_font, label_font, tiny_font)
        row_offset += 3
        self._create_progress_section(grid_frame, 0, row_offset, label_font, tiny_font)

        # LINES Section
        self._create_section_header(grid_frame, 1, row, t("✏️ LINES"), heading_font)
        row_offset = row + 1
        # Tool Sensors subsection (UP/DOWN sensors for each tool)
        self._create_subsection_header(grid_frame, 1, row_offset, t("Tool Sensors"), tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 1, row_offset, t("Marker Up Sensor"), "line_marker_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 1, t("Marker Down Sensor"), "line_marker_down_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 2, t("Cutter Up Sensor"), "line_cutter_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 3, t("Cutter Down Sensor"), "line_cutter_down_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 4, t("Motor Left Up"), "line_motor_left_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 5, t("Motor Left Down"), "line_motor_left_down_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 6, t("Motor Right Up"), "line_motor_right_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 7, t("Motor Right Down"), "line_motor_right_down_sensor", label_font, tiny_font)
        # Edge Sensors subsection
        row_offset += 8
        self._create_subsection_header(grid_frame, 1, row_offset, t("Edge Sensors"), tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 1, row_offset, t("X Left Edge"), "x_left_edge_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 1, t("X Right Edge"), "x_right_edge_sensor", label_font, tiny_font)
        # Pistons subsection
        row_offset += 2
        self._create_subsection_header(grid_frame, 1, row_offset, t("Pistons"), tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 1, row_offset, t("Line Marker"), "lines_piston_marker", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 1, t("Line Cutter"), "lines_piston_cutter", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 2, t("Motor Left"), "lines_piston_motor_left", label_font, tiny_font)
        self._create_grid_item(grid_frame, 1, row_offset + 3, t("Motor Right"), "lines_piston_motor_right", label_font, tiny_font)

        # ROWS Section
        self._create_section_header(grid_frame, 2, row, t("✂️ ROWS"), heading_font)
        row_offset = row + 1
        # Tool Sensors subsection (UP/DOWN sensors for each tool)
        self._create_subsection_header(grid_frame, 2, row_offset, t("Tool Sensors"), tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 2, row_offset, t("Marker Up Sensor"), "row_marker_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 1, t("Marker Down Sensor"), "row_marker_down_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 2, t("Cutter Up Sensor"), "row_cutter_up_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 3, t("Cutter Down Sensor"), "row_cutter_down_sensor", label_font, tiny_font)
        # Edge Sensors subsection
        row_offset += 4
        self._create_subsection_header(grid_frame, 2, row_offset, t("Edge Sensors"), tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 2, row_offset, t("Y Top Edge"), "y_top_edge_sensor", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 1, t("Y Bottom Edge"), "y_bottom_edge_sensor", label_font, tiny_font)
        # Pistons subsection
        row_offset += 2
        self._create_subsection_header(grid_frame, 2, row_offset, t("Pistons"), tiny_font)
        row_offset += 1
        self._create_grid_item(grid_frame, 2, row_offset, t("Row Marker"), "rows_piston_marker", label_font, tiny_font)
        self._create_grid_item(grid_frame, 2, row_offset + 1, t("Row Cutter"), "rows_piston_cutter", label_font, tiny_font)

    def _create_section_header(self, parent, col, row, text, font):
        """Create section header"""
        label = tk.Label(parent, text=text, font=font,
                        bg=self.section_bg, fg=self.text_color,
                        relief=tk.RAISED, bd=1)
        label.grid(row=row, column=col, sticky="ew", padx=1, pady=0)

    def _create_subsection_header(self, parent, col, row, text, font):
        """Create subsection header"""
        label = tk.Label(parent, text=text, font=font,
                        bg=self.section_bg, fg=self.label_color,
                        anchor='e')
        label.grid(row=row, column=col, sticky="ew", padx=2, pady=0)

    def _create_grid_item(self, parent, col, row, label_text, status_key, label_font, value_font):
        """Create compact grid item with label and colored status (RTL)"""
        # Container frame - use pack layout for consistent RTL: [status] [label]
        container = tk.Frame(parent, bg=self.section_bg)
        container.grid(row=row, column=col, sticky="ew", padx=1, pady=0)

        # Label on right (RTL) - shrinks to fit text
        label = tk.Label(container, text=":" + label_text, font=label_font,
                        bg=self.section_bg, fg=self.label_color,
                        anchor='e')
        label.pack(side=tk.RIGHT, padx=(0, 2))

        # Status indicator on left - fixed character width for consistency
        status_frame = tk.Frame(container, bg=self.switch_off_color, relief=tk.SUNKEN, bd=1)
        status_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(2, 0))

        status_label = tk.Label(status_frame, text="---", font=value_font,
                               bg=self.switch_off_color, fg='white',
                               anchor='center', width=21)
        status_label.pack(fill=tk.BOTH, expand=True, padx=1)

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
        tk.Label(parent, text=t("Mode:"), font=label_font,
                bg=self.section_bg, fg=self.label_color,
                anchor='e').grid(row=row, column=col, sticky="ew", padx=2)

        # Status frame
        status_frame = tk.Frame(parent, bg='#95A5A6', relief=tk.RAISED, bd=1)
        status_frame.grid(row=row + 1, column=col, sticky="ew", padx=1, pady=1)

        status_label = tk.Label(status_frame, text=t("IDLE"), font=heading_font,
                               bg='#95A5A6', fg='white', anchor='center')
        status_label.pack(fill=tk.BOTH, expand=True, pady=2)

        # Explanation
        explanation_label = tk.Label(parent, text=t("System ready"), font=value_font,
                                    bg=self.section_bg, fg=self.label_color,
                                    anchor='e', wraplength=120)
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
        tk.Label(parent, text=t("Safety:"), font=label_font,
                bg=self.section_bg, fg=self.label_color,
                anchor='e').grid(row=row, column=col, sticky="ew", padx=2)

        # Status frame
        status_frame = tk.Frame(parent, bg='#27AE60', relief=tk.SUNKEN, bd=1)
        status_frame.grid(row=row + 1, column=col, sticky="ew", padx=1, pady=1)

        status_label = tk.Label(status_frame, text=t("OK"), font=value_font,
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
        tk.Label(parent, text=t("Progress:"), font=label_font,
                bg=self.section_bg, fg=self.label_color,
                anchor='e').grid(row=row, column=col, sticky="ew", padx=2, pady=(5, 0))

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
                self._update_widget('x_position', t("ERROR"), "#FF0000")
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
                               t('ON') if y_top_ls else t('OFF'),
                               self.switch_on_color if y_top_ls else self.switch_off_color)
            y_bottom_ls = self.hardware.get_limit_switch_state('y_bottom')
            self._update_widget('bottom_limit_switch',
                               t('ON') if y_bottom_ls else t('OFF'),
                               self.switch_on_color if y_bottom_ls else self.switch_off_color)

            # X-axis (Rows) - Right/Left
            x_right_ls = self.hardware.get_limit_switch_state('x_right')
            self._update_widget('right_limit_switch',
                               t('ON') if x_right_ls else t('OFF'),
                               self.switch_on_color if x_right_ls else self.switch_off_color)
            x_left_ls = self.hardware.get_limit_switch_state('x_left')
            self._update_widget('left_limit_switch',
                               t('ON') if x_left_ls else t('OFF'),
                               self.switch_on_color if x_left_ls else self.switch_off_color)

            # Door sensor
            door_state = self.hardware.get_door_sensor()
            self._update_widget('door_sensor',
                               t('ON') if door_state else t('OFF'),
                               self.switch_on_color if door_state else self.switch_off_color)

            # Air pressure valve - DOWN=open (green), UP=closed (gray)
            air_pressure_state = self.hardware.get_air_pressure_valve_state()
            is_air_on = air_pressure_state == "down"
            self._update_widget('air_pressure_valve',
                               t('ON') if is_air_on else t('OFF'),
                               self.piston_down_color if is_air_on else self.piston_up_color)

            # LINES SECTION - Tool Sensors (UP/DOWN sensors for each tool)
            # Color coded: READY (False)=blue, TRIGGERED (True)=red
            # Line Marker Sensors
            line_marker_up = self.hardware.get_line_marker_up_sensor()
            self._update_widget('line_marker_up_sensor',
                               t('TRIG') if line_marker_up else t('READY'),
                               self.sensor_triggered_color if line_marker_up else self.sensor_ready_color)
            line_marker_down = self.hardware.get_line_marker_down_sensor()
            self._update_widget('line_marker_down_sensor',
                               t('TRIG') if line_marker_down else t('READY'),
                               self.sensor_triggered_color if line_marker_down else self.sensor_ready_color)

            # Line Cutter Sensors
            line_cutter_up = self.hardware.get_line_cutter_up_sensor()
            self._update_widget('line_cutter_up_sensor',
                               t('TRIG') if line_cutter_up else t('READY'),
                               self.sensor_triggered_color if line_cutter_up else self.sensor_ready_color)
            line_cutter_down = self.hardware.get_line_cutter_down_sensor()
            self._update_widget('line_cutter_down_sensor',
                               t('TRIG') if line_cutter_down else t('READY'),
                               self.sensor_triggered_color if line_cutter_down else self.sensor_ready_color)

            # Line Motor Left Piston Sensors
            line_motor_left_up = self.hardware.get_line_motor_left_up_sensor()
            self._update_widget('line_motor_left_up_sensor',
                               t('TRIG') if line_motor_left_up else t('READY'),
                               self.sensor_triggered_color if line_motor_left_up else self.sensor_ready_color)
            line_motor_left_down = self.hardware.get_line_motor_left_down_sensor()
            self._update_widget('line_motor_left_down_sensor',
                               t('TRIG') if line_motor_left_down else t('READY'),
                               self.sensor_triggered_color if line_motor_left_down else self.sensor_ready_color)

            # Line Motor Right Piston Sensors
            line_motor_right_up = self.hardware.get_line_motor_right_up_sensor()
            self._update_widget('line_motor_right_up_sensor',
                               t('TRIG') if line_motor_right_up else t('READY'),
                               self.sensor_triggered_color if line_motor_right_up else self.sensor_ready_color)
            line_motor_right_down = self.hardware.get_line_motor_right_down_sensor()
            self._update_widget('line_motor_right_down_sensor',
                               t('TRIG') if line_motor_right_down else t('READY'),
                               self.sensor_triggered_color if line_motor_right_down else self.sensor_ready_color)

            # Edge Sensors (X-axis for Lines)
            x_left_edge = self.hardware.get_x_left_edge()
            self._update_widget('x_left_edge_sensor',
                               t('TRIG') if x_left_edge else t('READY'),
                               self.sensor_triggered_color if x_left_edge else self.sensor_ready_color)
            x_right_edge = self.hardware.get_x_right_edge()
            self._update_widget('x_right_edge_sensor',
                               t('TRIG') if x_right_edge else t('READY'),
                               self.sensor_triggered_color if x_right_edge else self.sensor_ready_color)

            # Pistons - color coded: UP=gray, DOWN=green
            line_marker_piston_state = self.hardware.get_line_marker_piston_state().upper()
            self._update_widget('lines_piston_marker', t(line_marker_piston_state),
                               self.piston_down_color if line_marker_piston_state == 'DOWN' else self.piston_up_color)

            line_cutter_piston_state = self.hardware.get_line_cutter_piston_state().upper()
            self._update_widget('lines_piston_cutter', t(line_cutter_piston_state),
                               self.piston_down_color if line_cutter_piston_state == 'DOWN' else self.piston_up_color)

            # Line motor sensors (left and right have separate sensors, shared piston control)
            line_motor_left_state = self.hardware.get_line_motor_piston_state().upper()
            self._update_widget('lines_piston_motor_left', t(line_motor_left_state),
                               self.piston_down_color if line_motor_left_state == 'DOWN' else self.piston_up_color)

            line_motor_right_state = self.hardware.get_line_motor_piston_state().upper()
            self._update_widget('lines_piston_motor_right', t(line_motor_right_state),
                               self.piston_down_color if line_motor_right_state == 'DOWN' else self.piston_up_color)

            # ROWS SECTION - Tool Sensors (UP/DOWN sensors for each tool)
            # Color coded: READY (False)=blue, TRIGGERED (True)=red
            # Row Marker Sensors
            row_marker_up = self.hardware.get_row_marker_up_sensor()
            self._update_widget('row_marker_up_sensor',
                               t('TRIG') if row_marker_up else t('READY'),
                               self.sensor_triggered_color if row_marker_up else self.sensor_ready_color)
            row_marker_down = self.hardware.get_row_marker_down_sensor()
            self._update_widget('row_marker_down_sensor',
                               t('TRIG') if row_marker_down else t('READY'),
                               self.sensor_triggered_color if row_marker_down else self.sensor_ready_color)

            # Row Cutter Sensors
            row_cutter_up = self.hardware.get_row_cutter_up_sensor()
            self._update_widget('row_cutter_up_sensor',
                               t('TRIG') if row_cutter_up else t('READY'),
                               self.sensor_triggered_color if row_cutter_up else self.sensor_ready_color)
            row_cutter_down = self.hardware.get_row_cutter_down_sensor()
            self._update_widget('row_cutter_down_sensor',
                               t('TRIG') if row_cutter_down else t('READY'),
                               self.sensor_triggered_color if row_cutter_down else self.sensor_ready_color)

            # Edge Sensors (Y-axis for Rows)
            y_top_edge = self.hardware.get_y_top_edge()
            self._update_widget('y_top_edge_sensor',
                               t('TRIG') if y_top_edge else t('READY'),
                               self.sensor_triggered_color if y_top_edge else self.sensor_ready_color)
            y_bottom_edge = self.hardware.get_y_bottom_edge()
            self._update_widget('y_bottom_edge_sensor',
                               t('TRIG') if y_bottom_edge else t('READY'),
                               self.sensor_triggered_color if y_bottom_edge else self.sensor_ready_color)

            # Pistons - color coded: UP=gray, DOWN=green
            row_marker_piston_state = self.hardware.get_row_marker_piston_state().upper()
            self._update_widget('rows_piston_marker', t(row_marker_piston_state),
                               self.piston_down_color if row_marker_piston_state == 'DOWN' else self.piston_up_color)

            row_cutter_piston_state = self.hardware.get_row_cutter_piston_state().upper()
            self._update_widget('rows_piston_cutter', t(row_cutter_piston_state),
                               self.piston_down_color if row_cutter_piston_state == 'DOWN' else self.piston_up_color)

            # Update operation mode
            self._update_operation_mode()

        except Exception as e:
            self.logger.error(f" ERROR in update_hardware_status: {e}", category="gui")
            import traceback
            traceback.print_exc()

    def _update_operation_mode(self):
        """Update operation mode with status and explanation"""
        # Check machine state manager first (takes priority)
        state_manager = get_state_manager()
        current_state = state_manager.state

        # Handle special machine states first
        if current_state == MachineState.HOMING:
            status = t("HOMING")
            explanation = t("Running homing sequence...")
            color = '#E67E22'  # Orange
            self._update_widget('operation_mode', status, color)
            if 'operation_explanation' in self.status_widgets:
                self.status_widgets['operation_explanation']['label'].config(text=explanation)
            return

        if current_state == MachineState.SWITCHING_MODE:
            status = t("SWITCHING")
            explanation = t("Changing hardware mode...")
            color = '#9B59B6'  # Purple
            self._update_widget('operation_mode', status, color)
            if 'operation_explanation' in self.status_widgets:
                self.status_widgets['operation_explanation']['label'].config(text=explanation)
            return

        if current_state == MachineState.ERROR:
            status = t("ERROR")
            explanation = state_manager.error_message or t("Check hardware connection")
            color = '#C0392B'  # Dark red
            self._update_widget('operation_mode', status, color)
            if 'operation_explanation' in self.status_widgets:
                self.status_widgets['operation_explanation']['label'].config(text=explanation)
            return

        # Normal execution engine status
        if hasattr(self.main_app, 'execution_engine'):
            engine = self.main_app.execution_engine

            if engine.is_running:
                if hasattr(engine, 'is_blocked') and engine.is_blocked:
                    status = t("BLOCKED")
                    explanation = getattr(engine, 'block_reason', t('Waiting'))
                    color = '#E67E22'  # Orange
                elif hasattr(self.main_app, 'canvas_manager'):
                    mode = self.main_app.canvas_manager.motor_operation_mode.upper()

                    # Get current step Hebrew operation title if available
                    current_step = None
                    if hasattr(self.main_app, 'steps') and hasattr(engine, 'current_step_index'):
                        if 0 <= engine.current_step_index < len(self.main_app.steps):
                            current_step = self.main_app.steps[engine.current_step_index]

                    if mode == 'LINES':
                        status = t("LINES")
                        # Use Hebrew operation title if available, otherwise fallback
                        if current_step and 'hebOperationTitle' in current_step:
                            explanation = current_step['hebOperationTitle']
                        else:
                            explanation = t("Marking lines")
                        color = '#3498DB'  # Blue
                    elif mode == 'ROWS':
                        status = t("ROWS")
                        # Use Hebrew operation title if available, otherwise fallback
                        if current_step and 'hebOperationTitle' in current_step:
                            explanation = current_step['hebOperationTitle']
                        else:
                            explanation = t("Cutting rows")
                        color = '#E74C3C'  # Red
                    else:
                        status = t("IDLE")
                        # Use Hebrew operation title if available during idle operations
                        if current_step and 'hebOperationTitle' in current_step:
                            explanation = current_step['hebOperationTitle']
                        else:
                            explanation = t("System ready")
                        color = '#95A5A6'
                else:
                    status = t("IDLE")
                    explanation = t("System ready")
                    color = '#95A5A6'
            elif hasattr(engine, 'execution_completed') and engine.execution_completed:
                status = t("SUCCESS")
                explanation = t("All done!")
                color = '#27AE60'  # Green
            elif hasattr(engine, 'execution_failed') and engine.execution_failed:
                status = t("FAIL")
                explanation = t("Not completed")
                color = '#C0392B'  # Dark red
            else:
                status = t("IDLE")
                explanation = t("System ready")
                color = '#95A5A6'
        else:
            status = t("IDLE")
            explanation = t("System ready")
            color = '#95A5A6'

        self._update_widget('operation_mode', status, color)
        if 'operation_explanation' in self.status_widgets:
            self.status_widgets['operation_explanation']['label'].config(text=explanation)

    def _update_blocker_status(self):
        """Update blocker/safety status display using centralized safety rules"""
        blocker_message = t("OK")
        blocker_color = '#27AE60'  # Green

        # Check if execution engine is running
        if hasattr(self.main_app, 'execution_engine') and self.main_app.execution_engine.is_running:
            operation_type = self.main_app.execution_engine.current_operation_type
            if operation_type:
                try:
                    from core.safety_system import safety_system
                    violated_rules = safety_system.rules_manager.evaluate_monitor_rules(operation_type)
                    if violated_rules:
                        # Show first (highest priority) violation
                        rule = violated_rules[0]
                        # Prefer Hebrew message
                        msg = rule.get("message_he", rule.get("message", rule.get("id", "")))
                        # Truncate for display
                        first_line = msg.split('\n')[0] if msg else rule.get("id", "")
                        blocker_message = first_line
                        blocker_color = '#E67E22'  # Orange warning
                except Exception:
                    pass

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

import tkinter as tk
from mock_hardware import (
    get_current_x, get_current_y, move_x, move_y, get_hardware_status,
    get_line_marker_piston_state, get_row_marker_limit_switch
)


class CanvasSetup:
    """Handles canvas setup, grid drawing, and basic visual elements"""
    
    def __init__(self, main_app, canvas_manager):
        self.main_app = main_app
        self.canvas_manager = canvas_manager
        self.canvas_objects = main_app.canvas_objects
    
    def setup_canvas(self):
        """Setup canvas elements for desk simulation using settings"""
        # Get settings or use defaults
        sim_settings = self.main_app.settings.get("simulation", {})
        gui_settings = self.main_app.settings.get("gui_settings", {})
        hardware_limits = self.main_app.settings.get("hardware_limits", {})
        
        # Canvas dimensions from settings (use actual dimensions for calculations)
        self.main_app.canvas_width = getattr(self.main_app, 'actual_canvas_width', gui_settings.get("canvas_width", 600))
        self.main_app.canvas_height = getattr(self.main_app, 'actual_canvas_height', gui_settings.get("canvas_height", 400))
        
        # Coordinate conversion from settings
        self.main_app.scale_x = sim_settings.get("scale_x", 5.0)  # pixels per cm
        self.main_app.scale_y = sim_settings.get("scale_y", 3.5)  # pixels per cm
        self.main_app.offset_x = sim_settings.get("offset_x", 50)  # Left margin
        self.main_app.offset_y = sim_settings.get("offset_y", 50)  # Top margin
        self.main_app.grid_spacing = sim_settings.get("grid_spacing", 20)
        
        # Clear canvas first and reset canvas objects references
        self.main_app.canvas.delete("all")
        self.canvas_objects.clear()  # Clear canvas object references since they were deleted
        
        # Draw workspace boundary
        workspace_rect = self.main_app.canvas.create_rectangle(
            self.main_app.offset_x, self.main_app.offset_y,
            self.main_app.canvas_width - self.main_app.offset_x, self.main_app.canvas_height - self.main_app.offset_y,
            outline='black', width=2, fill='lightgray', stipple='gray12'
        )
        
        # Draw coordinate grid if enabled
        if sim_settings.get("show_grid", True):
            self.draw_coordinate_grid(sim_settings)
        
        # Draw axis labels
        self.draw_axis_labels()
        
        # Draw default paper area
        self.draw_default_paper_area(sim_settings, hardware_limits)
        
        # Draw motor position lines
        self.draw_motor_position_lines(sim_settings)
        
        # Draw tool status indicators
        self.draw_tool_status_indicators()
    
    def draw_coordinate_grid(self, sim_settings):
        """Draw the coordinate grid"""
        max_x_cm = sim_settings.get("max_display_x", 120)  # Maximum X in cm from settings
        max_y_cm = sim_settings.get("max_display_y", 80)  # Maximum Y in cm from settings
        
        # Vertical grid lines (X axis)
        for i in range(0, max_x_cm + 1, self.main_app.grid_spacing):
            x_pixel = self.main_app.offset_x + i * self.main_app.scale_x
            if x_pixel <= self.main_app.canvas_width - self.main_app.offset_x:
                self.main_app.canvas.create_line(
                    x_pixel, self.main_app.offset_y, 
                    x_pixel, self.main_app.canvas_height - self.main_app.offset_y,
                    fill='lightgray', width=1, dash=(3,3)
                )
                # X axis labels (show every other to avoid clutter)
                if i % (self.main_app.grid_spacing * 2) == 0:
                    self.main_app.canvas.create_text(
                        x_pixel, self.main_app.offset_y - 15, 
                        text=f'{i}cm', font=('Arial', 7), fill='darkblue'
                    )
        
        # Horizontal grid lines (Y axis) - note Y is inverted for display
        for i in range(0, max_y_cm + 1, self.main_app.grid_spacing):
            y_pixel = self.main_app.offset_y + (max_y_cm - i) * self.main_app.scale_y  # Invert Y
            if y_pixel >= self.main_app.offset_y and y_pixel <= self.main_app.canvas_height - self.main_app.offset_y:
                self.main_app.canvas.create_line(
                    self.main_app.offset_x, y_pixel, 
                    self.main_app.canvas_width - self.main_app.offset_x, y_pixel,
                    fill='lightgray', width=1, dash=(3,3)
                )
                # Y axis labels (show every other to avoid clutter)
                if i % (self.main_app.grid_spacing * 2) == 0:
                    self.main_app.canvas.create_text(
                        self.main_app.offset_x - 25, y_pixel, 
                        text=f'{i}cm', font=('Arial', 7), fill='darkblue'
                    )
    
    def draw_axis_labels(self):
        """Draw axis labels"""
        self.main_app.canvas.create_text(
            self.main_app.canvas_width // 2, self.main_app.canvas_height - 10, 
            text="X Axis (cm)", font=('Arial', 10, 'bold'), fill='darkblue'
        )
        self.main_app.canvas.create_text(
            10, self.main_app.canvas_height // 2, 
            text="Y Axis (cm)", font=('Arial', 10, 'bold'), fill='darkblue', angle=90
        )
    
    def draw_default_paper_area(self, sim_settings, hardware_limits):
        """Draw the default paper area"""
        # Paper area placeholder (will be updated when program is selected)
        # Use settings for paper start position and default size
        paper_start_x = hardware_limits.get("paper_start_x", 15.0)
        paper_bottom_left_y = paper_start_x  # Use same value for Y start
        default_paper_width = sim_settings.get("max_display_x", 120) * 0.4  # 40% of max display
        default_paper_height = sim_settings.get("max_display_y", 80) * 0.5   # 50% of max display
        
        # Convert to canvas coordinates - Y axis is inverted
        max_y_cm = sim_settings.get("max_display_y", 80)
        canvas_x1 = self.main_app.offset_x + paper_start_x * self.main_app.scale_x
        canvas_y1 = self.main_app.offset_y + (max_y_cm - paper_bottom_left_y - default_paper_height) * self.main_app.scale_y  # Top of paper
        canvas_x2 = self.main_app.offset_x + (paper_start_x + default_paper_width) * self.main_app.scale_x
        canvas_y2 = self.main_app.offset_y + (max_y_cm - paper_bottom_left_y) * self.main_app.scale_y  # Bottom of paper
        
        self.canvas_objects['paper'] = self.main_app.canvas.create_rectangle(
            canvas_x1, canvas_y1, canvas_x2, canvas_y2,
            outline='blue', width=3, fill='lightblue', stipple='gray50'
        )
        
        # Paper area label - position at top of paper
        self.main_app.canvas.create_text(
            canvas_x1 + (canvas_x2 - canvas_x1) / 2, canvas_y1 - 10,
            text="Paper Area", font=('Arial', 9, 'bold'), fill='blue'
        )
        
        # Add a marker at paper start position to show paper start
        marker_x = self.main_app.offset_x + paper_start_x * self.main_app.scale_x
        marker_y = self.main_app.offset_y + (max_y_cm - paper_start_x) * self.main_app.scale_y
        self.main_app.canvas.create_oval(
            marker_x - 3, marker_y - 3, marker_x + 3, marker_y + 3,
            fill='red', outline='darkred', width=2
        )
        self.main_app.canvas.create_text(
            marker_x + 15, marker_y - 10,
            text=f"({paper_start_x},{paper_start_x})", font=('Arial', 8, 'bold'), fill='red'
        )
    
    def draw_motor_position_lines(self, sim_settings):
        """Draw X and Y motor position lines across the entire board"""
        # Get current motor positions
        current_x = get_current_x()
        current_y = get_current_y()
        
        max_y_cm = sim_settings.get("max_display_y", 80)
        max_x_cm = sim_settings.get("max_display_x", 120)
        
        # Calculate canvas coordinates for motor positions
        motor_x_canvas = self.main_app.offset_x + current_x * self.main_app.scale_x
        motor_y_canvas = self.main_app.offset_y + (max_y_cm - current_y) * self.main_app.scale_y
        
        # Get workspace boundaries
        workspace_left = self.main_app.offset_x
        workspace_right = self.main_app.canvas_width - self.main_app.offset_x
        workspace_top = self.main_app.offset_y
        workspace_bottom = self.main_app.canvas_height - self.main_app.offset_y
        
        # X Motor Line (Vertical line representing X motor position)
        # This line shows where the X motor/carriage is positioned
        self.canvas_objects['x_motor_line'] = self.main_app.canvas.create_line(
            motor_x_canvas, workspace_top,           # Top of workspace
            motor_x_canvas, workspace_bottom,        # Bottom of workspace
            fill='red', width=3, tags="motor_lines"
        )
        
        # Y Motor Line (Horizontal line representing Y motor position)  
        # This line shows where the Y motor/carriage is positioned
        self.canvas_objects['y_motor_line'] = self.main_app.canvas.create_line(
            workspace_left, motor_y_canvas,          # Left of workspace
            workspace_right, motor_y_canvas,         # Right of workspace
            fill='blue', width=3, tags="motor_lines"
        )
        
        # Add intersection point to show current tool position clearly
        self.canvas_objects['motor_intersection'] = self.main_app.canvas.create_oval(
            motor_x_canvas - 4, motor_y_canvas - 4,
            motor_x_canvas + 4, motor_y_canvas + 4,
            fill='purple', outline='purple4', width=2, tags="motor_lines"
        )
        
        # Add labels for the motor lines
        self.canvas_objects['x_motor_label'] = self.main_app.canvas.create_text(
            motor_x_canvas + 15, workspace_top + 15,
            text=f"X={current_x:.1f}cm", fill='red', font=('Arial', 8, 'bold'),
            anchor='nw', tags="motor_lines"
        )
        
        self.canvas_objects['y_motor_label'] = self.main_app.canvas.create_text(
            workspace_left + 15, motor_y_canvas - 15,
            text=f"Y={current_y:.1f}cm", fill='blue', font=('Arial', 8, 'bold'),
            anchor='sw', tags="motor_lines"
        )
        
        # Add sensor position indicators on motor lines
        self.create_sensor_indicators(sim_settings)
    
    def create_sensor_indicators(self, sim_settings):
        """Create sensor position indicators on motor lines"""
        # Get paper dimensions from current program if available
        if hasattr(self.main_app, 'current_program') and self.main_app.current_program:
            program = self.main_app.current_program
            paper_width = program.width
            paper_height = program.high
        else:
            # Default paper dimensions from settings
            max_x = sim_settings.get("max_display_x", 120)
            max_y = sim_settings.get("max_display_y", 80)
            paper_width = max_x * 0.25  # 25% of max display
            paper_height = max_y * 0.5  # 50% of max display
        
        # Paper offset coordinates from settings
        hardware_limits = self.main_app.settings.get("hardware_limits", {})
        PAPER_OFFSET_X = hardware_limits.get("paper_start_x", 15.0)
        PAPER_OFFSET_Y = PAPER_OFFSET_X  # Use same value for Y start
        
        max_y_cm = sim_settings.get("max_display_y", 80)
        
        # Calculate sensor positions on desk
        left_sensor_x = PAPER_OFFSET_X
        right_sensor_x = PAPER_OFFSET_X + paper_width
        bottom_sensor_y = PAPER_OFFSET_Y  
        top_sensor_y = PAPER_OFFSET_Y + paper_height
        
        # Convert to canvas coordinates
        left_x_canvas = self.main_app.offset_x + left_sensor_x * self.main_app.scale_x
        right_x_canvas = self.main_app.offset_x + right_sensor_x * self.main_app.scale_x
        bottom_y_canvas = self.main_app.offset_y + (max_y_cm - bottom_sensor_y) * self.main_app.scale_y
        top_y_canvas = self.main_app.offset_y + (max_y_cm - top_sensor_y) * self.main_app.scale_y
        
        # Get workspace boundaries
        workspace_top = self.main_app.offset_y
        workspace_bottom = self.main_app.canvas_height - self.main_app.offset_y
        workspace_left = self.main_app.offset_x
        workspace_right = self.main_app.canvas_width - self.main_app.offset_x
        
        # X-axis sensors (on vertical motor line, but at sensor X positions)
        # Left sensor indicator - small circle on the left edge position
        self.canvas_objects['x_left_sensor'] = self.main_app.canvas.create_oval(
            left_x_canvas - 3, workspace_top - 8, left_x_canvas + 3, workspace_top - 2,
            fill='orange', outline='darkorange', width=2, tags="sensor_indicators"
        )
        self.canvas_objects['x_left_label'] = self.main_app.canvas.create_text(
            left_x_canvas, workspace_top - 12,
            text="L", fill='darkorange', font=('Arial', 7, 'bold'),
            anchor='s', tags="sensor_indicators"
        )
        
        # Right sensor indicator - small circle on the right edge position  
        self.canvas_objects['x_right_sensor'] = self.main_app.canvas.create_oval(
            right_x_canvas - 3, workspace_top - 8, right_x_canvas + 3, workspace_top - 2,
            fill='orange', outline='darkorange', width=2, tags="sensor_indicators"
        )
        self.canvas_objects['x_right_label'] = self.main_app.canvas.create_text(
            right_x_canvas, workspace_top - 12,
            text="R", fill='darkorange', font=('Arial', 7, 'bold'),
            anchor='s', tags="sensor_indicators"
        )
        
        # Y-axis sensors (on horizontal motor line, but at sensor Y positions)
        # Bottom sensor indicator - small circle on the bottom edge position
        self.canvas_objects['y_bottom_sensor'] = self.main_app.canvas.create_oval(
            workspace_left - 8, bottom_y_canvas - 3, workspace_left - 2, bottom_y_canvas + 3,
            fill='green', outline='darkgreen', width=2, tags="sensor_indicators"
        )
        self.canvas_objects['y_bottom_label'] = self.main_app.canvas.create_text(
            workspace_left - 12, bottom_y_canvas,
            text="B", fill='darkgreen', font=('Arial', 7, 'bold'),
            anchor='e', tags="sensor_indicators"
        )
        
        # Top sensor indicator - small circle on the top edge position
        self.canvas_objects['y_top_sensor'] = self.main_app.canvas.create_oval(
            workspace_left - 8, top_y_canvas - 3, workspace_left - 2, top_y_canvas + 3,
            fill='green', outline='darkgreen', width=2, tags="sensor_indicators"
        )
        self.canvas_objects['y_top_label'] = self.main_app.canvas.create_text(
            workspace_left - 12, top_y_canvas,
            text="T", fill='darkgreen', font=('Arial', 7, 'bold'),
            anchor='e', tags="sensor_indicators"
        )
    
    def draw_tool_status_indicators(self):
        """Draw tool status indicators"""
        # Tool indicators (line marker, cutter tools)
        status_x = self.main_app.canvas_width - 120
        status_y = 20
        
        # Line marker tool status
        self.canvas_objects['line_marker_status'] = self.main_app.canvas.create_rectangle(
            status_x, status_y, status_x + 15, status_y + 15,
            fill='gray', outline='black', width=1, tags="tool_status"
        )
        self.canvas_objects['line_marker_label'] = self.main_app.canvas.create_text(
            status_x + 20, status_y + 7,
            text="Line Marker", fill='black', font=('Arial', 8, 'bold'),
            anchor='w', tags="tool_status"
        )
        
        # Cutter tool status
        cutter_y = status_y + 25
        self.canvas_objects['cutter_status'] = self.main_app.canvas.create_rectangle(
            status_x, cutter_y, status_x + 15, cutter_y + 15,
            fill='gray', outline='black', width=1, tags="tool_status"
        )
        self.canvas_objects['cutter_label'] = self.main_app.canvas.create_text(
            status_x + 20, cutter_y + 7,
            text="Cutter", fill='black', font=('Arial', 8, 'bold'),
            anchor='w', tags="tool_status"
        )
        
        # Create comprehensive work operations status display on canvas
        self.create_canvas_work_status_display()

    def create_canvas_work_status_display(self):
        """Create comprehensive work operations status display on canvas board area"""
        # Get settings
        operation_colors = self.main_app.settings.get("operation_colors", {})
        mark_colors = operation_colors.get("mark", {
            "pending": "#880808",
            "in_progress": "#FF8800",
            "completed": "#00AA00"
        })
        cut_colors = operation_colors.get("cuts", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })

        # Position status display in top-right corner of canvas
        status_x = self.main_app.canvas_width - 280
        status_y = 15

        # Create background frame
        bg_width = 270
        bg_height = 180
        self.canvas_objects['status_bg'] = self.main_app.canvas.create_rectangle(
            status_x, status_y, status_x + bg_width, status_y + bg_height,
            fill='#E8F4F8', outline='#2C5F7F', width=2
        )

        # Title
        title_y = status_y + 10
        self.canvas_objects['status_title'] = self.main_app.canvas.create_text(
            status_x + bg_width/2, title_y,
            text="📋 WORK OPERATIONS STATUS", font=('Arial', 10, 'bold'),
            fill='#2C5F7F'
        )

        # Section 1: MARK Operations (Lines)
        section1_y = title_y + 20
        self.canvas_objects['mark_section_title'] = self.main_app.canvas.create_text(
            status_x + 10, section1_y,
            text="✏️ MARK (Lines)", font=('Arial', 9, 'bold'),
            fill='#1A4D6B', anchor='w'
        )

        # Mark status indicators
        indicator_y = section1_y + 15
        self._create_status_line_indicator(
            status_x + 15, indicator_y,
            "Ready:", mark_colors['pending'], 'mark_ready'
        )
        self._create_status_line_indicator(
            status_x + 95, indicator_y,
            "Working:", mark_colors['in_progress'], 'mark_working'
        )
        self._create_status_line_indicator(
            status_x + 185, indicator_y,
            "Done:", mark_colors['completed'], 'mark_done'
        )

        # Line motor limit switch status
        limit_y = indicator_y + 20
        self.canvas_objects['line_motor_limit'] = self.main_app.canvas.create_text(
            status_x + 15, limit_y,
            text="Line Motor: DOWN", font=('Arial', 8, 'bold'),
            fill='#666666', anchor='w'
        )

        # Section 2: CUT Operations (Rows)
        section2_y = limit_y + 25
        self.canvas_objects['cut_section_title'] = self.main_app.canvas.create_text(
            status_x + 10, section2_y,
            text="✂️ CUT (Rows)", font=('Arial', 9, 'bold'),
            fill='#6B1A4D', anchor='w'
        )

        # Cut status indicators
        cut_indicator_y = section2_y + 15
        self._create_status_line_indicator(
            status_x + 15, cut_indicator_y,
            "Ready:", cut_colors['pending'], 'cut_ready'
        )
        self._create_status_line_indicator(
            status_x + 95, cut_indicator_y,
            "Working:", cut_colors['in_progress'], 'cut_working'
        )
        self._create_status_line_indicator(
            status_x + 185, cut_indicator_y,
            "Done:", cut_colors['completed'], 'cut_done'
        )

        # Row motor limit switch status
        row_limit_y = cut_indicator_y + 20
        self.canvas_objects['row_motor_limit'] = self.main_app.canvas.create_text(
            status_x + 15, row_limit_y,
            text="Row Marker: UP", font=('Arial', 8, 'bold'),
            fill='#666666', anchor='w'
        )

        # Section 3: Real-time Operation States
        section3_y = row_limit_y + 25
        self.canvas_objects['realtime_section_title'] = self.main_app.canvas.create_text(
            status_x + 10, section3_y,
            text="⚡ REAL-TIME STATUS", font=('Arial', 9, 'bold'),
            fill='#4D6B1A', anchor='w'
        )

        # Current operation display
        current_op_y = section3_y + 15
        self.canvas_objects['current_line_op'] = self.main_app.canvas.create_text(
            status_x + 15, current_op_y,
            text="Lines: Ready", font=('Arial', 8),
            fill='#333333', anchor='w'
        )

        row_op_y = current_op_y + 15
        self.canvas_objects['current_row_op'] = self.main_app.canvas.create_text(
            status_x + 15, row_op_y,
            text="Rows: Ready", font=('Arial', 8),
            fill='#333333', anchor='w'
        )

    def _create_status_line_indicator(self, x, y, label, color, obj_key):
        """Helper to create a status line with label and colored indicator"""
        # Label text
        self.canvas_objects[f'{obj_key}_label'] = self.main_app.canvas.create_text(
            x, y,
            text=label, font=('Arial', 7),
            fill='#333333', anchor='w'
        )

        # Colored line indicator (20px long, 3px wide)
        line_x = x + 35
        self.canvas_objects[f'{obj_key}_line'] = self.main_app.canvas.create_line(
            line_x, y, line_x + 20, y,
            fill=color, width=3
        )

    def update_canvas_work_status_display(self):
        """Update the canvas work status display with real-time hardware states"""
        # Update Line Motor Piston State
        line_piston_state = get_line_marker_piston_state()
        if 'line_motor_limit' in self.canvas_objects:
            if line_piston_state == "down":
                self.main_app.canvas.itemconfig(
                    self.canvas_objects['line_motor_limit'],
                    text="Line Motor: DOWN",
                    fill='#00AA00'  # Green when down (ready to mark)
                )
            else:
                self.main_app.canvas.itemconfig(
                    self.canvas_objects['line_motor_limit'],
                    text="Line Motor: UP",
                    fill='#666666'  # Gray when up
                )

        # Update Row Marker Limit Switch State
        row_marker_state = get_row_marker_limit_switch()
        if 'row_motor_limit' in self.canvas_objects:
            if row_marker_state == "down":
                self.main_app.canvas.itemconfig(
                    self.canvas_objects['row_motor_limit'],
                    text="Row Marker: DOWN",
                    fill='#00AA00'  # Green when down (marking)
                )
            else:
                self.main_app.canvas.itemconfig(
                    self.canvas_objects['row_motor_limit'],
                    text="Row Marker: UP",
                    fill='#666666'  # Gray when up
                )

        # Update real-time operation states based on motor operation mode
        motor_mode = self.canvas_manager.motor_operation_mode

        if 'current_line_op' in self.canvas_objects:
            if motor_mode == "lines":
                self.main_app.canvas.itemconfig(
                    self.canvas_objects['current_line_op'],
                    text="Lines: WORKING",
                    fill='#FF8800'  # Orange for in progress
                )
            else:
                self.main_app.canvas.itemconfig(
                    self.canvas_objects['current_line_op'],
                    text="Lines: Ready",
                    fill='#333333'
                )

        if 'current_row_op' in self.canvas_objects:
            if motor_mode == "rows":
                self.main_app.canvas.itemconfig(
                    self.canvas_objects['current_row_op'],
                    text="Rows: WORKING",
                    fill='#FF0088'  # Magenta for in progress
                )
            else:
                self.main_app.canvas.itemconfig(
                    self.canvas_objects['current_row_op'],
                    text="Rows: Ready",
                    fill='#333333'
                )
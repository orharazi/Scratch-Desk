import tkinter as tk
import re
from mock_hardware import get_current_x, get_current_y, move_x, move_y, get_hardware_status


class CanvasManager:
    """Manages the desk simulation canvas and all drawing operations"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        # Use main app's canvas_objects for consistency
        self.canvas_objects = main_app.canvas_objects
        
        # Motor operation state tracking for independent visualization
        self.motor_operation_mode = "idle"  # "idle", "lines", "rows"
        self.lines_motor_position = 0.0  # Y position for lines operations
        self.rows_motor_position = 0.0   # X position for rows operations
        
        # Sensor trigger state tracking
        self.sensor_override_active = False  # True when sensor position should be maintained
        self.sensor_override_timer = None    # Timer to clear sensor override
        self.sensor_position_x = 0.0         # Store sensor triggered X position
        self.sensor_position_y = 0.0         # Store sensor triggered Y position
    
    def set_motor_operation_mode(self, mode):
        """Set the motor operation mode for proper visualization"""
        if mode in ["idle", "lines", "rows"]:
            self.motor_operation_mode = mode
            print(f"Motor visualization mode: {mode}")
        else:
            print(f"Invalid motor mode: {mode}")
    
    def update_lines_motor_position(self, y_position):
        """Update lines motor position (Y-axis) during lines operations"""
        self.lines_motor_position = y_position
    
    def update_rows_motor_position(self, x_position):
        """Update rows motor position (X-axis) during rows operations"""
        self.rows_motor_position = x_position
    
    def detect_operation_mode_from_step(self, step_description):
        """Automatically detect operation mode from step description"""
        if not step_description:
            return
        
        step_desc = step_description.lower()
        
        # Lines operation keywords
        if any(keyword in step_desc for keyword in [
            "lines operation", "line marking", "cut top edge", "cut bottom edge", 
            "mark line", "lines complete", "init: move y motor"
        ]):
            self.set_motor_operation_mode("lines")
        
        # Rows operation keywords  
        elif any(keyword in step_desc for keyword in [
            "rows operation", "row marking", "cut first row", "cut last row",
            "mark row", "rows complete", "init: move x motor", "mark page",
            "move to.*page", "rightmost page", "right to left"
        ]):
            self.set_motor_operation_mode("rows")
        
        # Idle/home operations
        elif any(keyword in step_desc for keyword in [
            "home position", "starting program", "program complete", "system ready"
        ]):
            self.set_motor_operation_mode("idle")
        
    def setup_canvas(self):
        """Setup canvas elements for desk simulation using settings"""
        # Get settings or use defaults
        sim_settings = self.main_app.settings.get("simulation", {})
        gui_settings = self.main_app.settings.get("gui_settings", {})
        
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
        self.draw_default_paper_area(sim_settings)
        
        # Draw motor position lines
        self.draw_motor_position_lines(sim_settings)
        
        # Draw tool status indicators
        self.draw_tool_status_indicators()
    
    def draw_coordinate_grid(self, sim_settings):
        """Draw the coordinate grid"""
        max_x_cm = sim_settings.get("max_display_x", 800)  # Maximum X in cm from settings
        max_y_cm = sim_settings.get("max_display_y", 400)  # Maximum Y in cm from settings
        
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
    
    def draw_default_paper_area(self, sim_settings):
        """Draw the default paper area"""
        # Paper area placeholder (will be updated when program is selected)
        # Default paper area with bottom-left at (15, 15) - size 200x250cm
        paper_bottom_left_x = 15.0
        paper_bottom_left_y = 15.0
        default_paper_width = 200.0
        default_paper_height = 250.0
        
        # Convert to canvas coordinates - Y axis is inverted
        max_y_cm = sim_settings.get("max_display_y", 400)
        canvas_x1 = self.main_app.offset_x + paper_bottom_left_x * self.main_app.scale_x
        canvas_y1 = self.main_app.offset_y + (max_y_cm - paper_bottom_left_y - default_paper_height) * self.main_app.scale_y  # Top of paper
        canvas_x2 = self.main_app.offset_x + (paper_bottom_left_x + default_paper_width) * self.main_app.scale_x
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
        
        # Add a marker at (15, 15) to show paper start position
        marker_x = self.main_app.offset_x + 15 * self.main_app.scale_x
        marker_y = self.main_app.offset_y + (max_y_cm - 15) * self.main_app.scale_y
        self.main_app.canvas.create_oval(
            marker_x - 3, marker_y - 3, marker_x + 3, marker_y + 3,
            fill='red', outline='darkred', width=2
        )
        self.main_app.canvas.create_text(
            marker_x + 15, marker_y - 10,
            text="(15,15)", font=('Arial', 8, 'bold'), fill='red'
        )
    
    def draw_motor_position_lines(self, sim_settings):
        """Draw X and Y motor position lines across the entire board"""
        # Get current motor positions
        from mock_hardware import get_current_x, get_current_y
        current_x = get_current_x()
        current_y = get_current_y()
        
        max_y_cm = sim_settings.get("max_display_y", 80)
        max_x_cm = sim_settings.get("max_display_x", 100)
        
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
            # Default paper dimensions
            paper_width = 30.0
            paper_height = 40.0
        
        # Paper offset coordinates (where paper starts on the desk)
        PAPER_OFFSET_X = 15.0
        PAPER_OFFSET_Y = 15.0
        
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
    
    def trigger_sensor_visualization(self, sensor_type):
        """Highlight sensor trigger and move pointer to sensor position with independent motor display"""
        if not hasattr(self.main_app, 'current_program') or not self.main_app.current_program:
            return
        
        # Clear any existing sensor override first to prevent conflicts
        if self.sensor_override_active:
            print(f"🔄 CLEARING previous sensor override for new sensor: {sensor_type}")
            self.clear_sensor_override()
        
        program = self.main_app.current_program
        
        # Calculate sensor positions
        PAPER_OFFSET_X = 15.0
        PAPER_OFFSET_Y = 15.0
        
        # Store current hardware positions
        from mock_hardware import get_current_x, get_current_y
        current_x = get_current_x()
        current_y = get_current_y()
        
        if sensor_type == 'x_left':
            sensor_x = PAPER_OFFSET_X  # Left edge at paper offset (15.0)
            self.sensor_position_x = sensor_x
            self.sensor_position_y = current_y
            print(f"🔴 X_LEFT SENSOR TRIGGERED: Setting sensor_position_x = {sensor_x:.1f} (left paper edge)")
            # Highlight left sensor
            if 'x_left_sensor' in self.canvas_objects:
                self.main_app.canvas.itemconfig(self.canvas_objects['x_left_sensor'], 
                                               fill='red', outline='darkred', width=3)
            # Move pointer to left edge
            self.animate_pointer_to_sensor('x', sensor_x)
            
        elif sensor_type == 'x_right':
            sensor_x = PAPER_OFFSET_X + program.width  # Right edge at paper offset + width
            self.sensor_position_x = sensor_x
            self.sensor_position_y = current_y
            print(f"🔴 X_RIGHT SENSOR TRIGGERED: Setting sensor_position_x = {sensor_x:.1f} (right paper edge, width={program.width})")
            # Highlight right sensor  
            if 'x_right_sensor' in self.canvas_objects:
                self.main_app.canvas.itemconfig(self.canvas_objects['x_right_sensor'],
                                               fill='red', outline='darkred', width=3)
            # Move pointer to right edge
            self.animate_pointer_to_sensor('x', sensor_x)
            
        elif sensor_type == 'y_top':
            # Y_TOP sensor always triggers at the actual sensor position on paper
            sensor_y = PAPER_OFFSET_Y + program.high  # Top edge of paper
            self.sensor_position_x = current_x
            self.sensor_position_y = sensor_y
            print(f"🔵 Y_TOP SENSOR TRIGGERED: Pointer moves to actual sensor position ({current_x:.1f}, {sensor_y:.1f})")
            
            # Highlight top sensor
            if 'y_top_sensor' in self.canvas_objects:
                self.main_app.canvas.itemconfig(self.canvas_objects['y_top_sensor'],
                                               fill='red', outline='darkred', width=3)
            # Move pointer to actual sensor position
            self.animate_pointer_to_sensor('y', sensor_y)
            
        elif sensor_type == 'y_bottom':
            # Y_BOTTOM sensor always triggers at the actual sensor position on paper
            sensor_y = PAPER_OFFSET_Y  # Bottom edge of paper
            self.sensor_position_x = current_x
            self.sensor_position_y = sensor_y
            print(f"🔵 Y_BOTTOM SENSOR TRIGGERED: Pointer moves to actual sensor position ({current_x:.1f}, {sensor_y:.1f})")
                
            # Highlight bottom sensor
            if 'y_bottom_sensor' in self.canvas_objects:
                self.main_app.canvas.itemconfig(self.canvas_objects['y_bottom_sensor'],
                                               fill='red', outline='darkred', width=3)
            # Move pointer to actual sensor position
            self.animate_pointer_to_sensor('y', sensor_y)
        
        # Set sensor override to prevent position updates from moving pointer
        self.sensor_override_active = True
        print(f"🔒 SENSOR OVERRIDE ACTIVATED: Pointer locked at ({self.sensor_position_x:.1f}, {self.sensor_position_y:.1f})")
        
        # Initialize hardware position tracking for move detection
        from mock_hardware import get_current_x, get_current_y
        self._last_displayed_hardware_x = get_current_x()
        self._last_displayed_hardware_y = get_current_y()
        
        # Clear sensor override timer - extend for rows operations to keep pointer at sensor positions
        # During rows operations, extend timer to prevent pointer from returning to 0 too quickly
        timeout_ms = 3000 if self.motor_operation_mode == "rows" else 1000
        
        if self.sensor_override_timer:
            self.main_app.root.after_cancel(self.sensor_override_timer)
        self.sensor_override_timer = self.main_app.root.after(timeout_ms, self.clear_sensor_override)
        
        # Reset sensor highlight after 500ms (reduce delay)
        self.main_app.root.after(500, lambda: self.reset_sensor_highlights())
    
    def animate_pointer_to_sensor(self, axis, position):
        """Move pointer to sensor position while displaying motor lines according to operation mode"""
        max_y_cm = self.main_app.settings.get("simulation", {}).get("max_display_y", 80)
        
        # Get current hardware position for the other axis
        current_x = get_current_x()
        current_y = get_current_y()
        
        if axis == 'x':
            # X sensor triggered - pointer moves to (sensor_x, current_y)
            pointer_x = position
            pointer_y = current_y
            
        elif axis == 'y':
            # Y sensor triggered - pointer moves to (current_x, sensor_y)
            pointer_x = current_x
            # During rows operations, Y position should be the sensor position (which is 0.0 in rows mode)
            pointer_y = position
        
        # POINTER always shows actual sensor position
        pointer_x_canvas = self.main_app.offset_x + pointer_x * self.main_app.scale_x
        pointer_y_canvas = self.main_app.offset_y + (max_y_cm - pointer_y) * self.main_app.scale_y
        
        # MOTOR LINES display based on operation mode (independent motor behavior)
        if self.motor_operation_mode == "lines":
            # During lines: X motor line at 0, Y motor line at actual position
            motor_line_x = 0.0
            motor_line_y = pointer_y
            x_label_text = "X=0.0cm (HOLD)"
            x_label_color = "gray"
            y_label_text = f"Y={pointer_y:.1f}cm (SENSOR)" if axis == 'y' else f"Y={pointer_y:.1f}cm (ACTIVE)"
            y_label_color = "blue"
            
        elif self.motor_operation_mode == "rows":
            # During rows: Y motor line at 0, X motor line at actual position
            motor_line_x = pointer_x
            motor_line_y = 0.0
            x_label_text = f"X={pointer_x:.1f}cm (SENSOR)" if axis == 'x' else f"X={pointer_x:.1f}cm (ACTIVE)"
            x_label_color = "red"
            y_label_text = "Y=0.0cm (HOLD)"
            y_label_color = "gray"
            
        else:
            # Idle mode: motor lines show actual positions
            motor_line_x = pointer_x
            motor_line_y = pointer_y
            x_label_text = f"X={pointer_x:.1f}cm" + (" (SENSOR)" if axis == 'x' else "")
            x_label_color = "red"
            y_label_text = f"Y={pointer_y:.1f}cm" + (" (SENSOR)" if axis == 'y' else "")
            y_label_color = "blue"
        
        # Convert motor line positions to canvas coordinates
        motor_x_canvas = self.main_app.offset_x + motor_line_x * self.main_app.scale_x
        motor_y_canvas = self.main_app.offset_y + (max_y_cm - motor_line_y) * self.main_app.scale_y
        
        # Get workspace boundaries
        workspace_left = self.main_app.offset_x
        workspace_right = self.main_app.canvas_width - self.main_app.offset_x
        workspace_top = self.main_app.offset_y
        workspace_bottom = self.main_app.canvas_height - self.main_app.offset_y
        
        # Update X motor line
        if 'x_motor_line' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['x_motor_line'],
                                       motor_x_canvas, workspace_top,
                                       motor_x_canvas, workspace_bottom)
        
        # Update Y motor line
        if 'y_motor_line' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['y_motor_line'],
                                       workspace_left, motor_y_canvas,
                                       workspace_right, motor_y_canvas)
        
        # Update intersection point (pointer) - ALWAYS at actual sensor position
        if 'motor_intersection' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['motor_intersection'],
                                       pointer_x_canvas - 4, pointer_y_canvas - 4,
                                       pointer_x_canvas + 4, pointer_y_canvas + 4)
        
        # Update motor labels
        if 'x_motor_label' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['x_motor_label'],
                                       motor_x_canvas + 15, workspace_top + 15)
            self.main_app.canvas.itemconfig(self.canvas_objects['x_motor_label'],
                                           text=x_label_text, fill=x_label_color)
        
        if 'y_motor_label' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['y_motor_label'],
                                       workspace_left + 15, motor_y_canvas - 15)
            self.main_app.canvas.itemconfig(self.canvas_objects['y_motor_label'],
                                           text=y_label_text, fill=y_label_color)
    
    def update_sensor_position_display(self):
        """Update display while maintaining sensor trigger position"""
        max_y_cm = self.main_app.settings.get("simulation", {}).get("max_display_y", 80)
        
        # Use stored sensor position for pointer
        pointer_x = self.sensor_position_x
        pointer_y = self.sensor_position_y
        
        print(f"🎯 POINTER DISPLAY: sensor override active, showing pointer at ({pointer_x:.1f}, {pointer_y:.1f})")
        
        # Motor lines display based on operation mode (independent motor behavior)
        if self.motor_operation_mode == "lines":
            # During lines: X motor line at 0, Y motor line follows sensor Y position
            motor_line_x = 0.0
            motor_line_y = pointer_y
            x_label_text = "X=0.0cm (HOLD)"
            x_label_color = "gray"
            y_label_text = f"Y={pointer_y:.1f}cm (SENSOR)"
            y_label_color = "blue"
            
        elif self.motor_operation_mode == "rows":
            # During rows: Y motor line at 0, X motor line follows sensor X position
            motor_line_x = pointer_x
            motor_line_y = 0.0
            x_label_text = f"X={pointer_x:.1f}cm (SENSOR)"
            x_label_color = "red"
            y_label_text = "Y=0.0cm (HOLD)"
            y_label_color = "gray"
            
        else:
            # Idle mode: motor lines show sensor positions
            motor_line_x = pointer_x
            motor_line_y = pointer_y
            x_label_text = f"X={pointer_x:.1f}cm (SENSOR)"
            x_label_color = "red"
            y_label_text = f"Y={pointer_y:.1f}cm (SENSOR)"
            y_label_color = "blue"
        
        # Convert to canvas coordinates
        pointer_x_canvas = self.main_app.offset_x + pointer_x * self.main_app.scale_x
        pointer_y_canvas = self.main_app.offset_y + (max_y_cm - pointer_y) * self.main_app.scale_y
        motor_x_canvas = self.main_app.offset_x + motor_line_x * self.main_app.scale_x
        motor_y_canvas = self.main_app.offset_y + (max_y_cm - motor_line_y) * self.main_app.scale_y
        
        # Get workspace boundaries
        workspace_left = self.main_app.offset_x
        workspace_right = self.main_app.canvas_width - self.main_app.offset_x
        workspace_top = self.main_app.offset_y
        workspace_bottom = self.main_app.canvas_height - self.main_app.offset_y
        
        # Update X motor line
        if 'x_motor_line' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['x_motor_line'],
                                       motor_x_canvas, workspace_top,
                                       motor_x_canvas, workspace_bottom)
        
        # Update Y motor line
        if 'y_motor_line' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['y_motor_line'],
                                       workspace_left, motor_y_canvas,
                                       workspace_right, motor_y_canvas)
        
        # Update intersection point (pointer) - ALWAYS at sensor position
        if 'motor_intersection' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['motor_intersection'],
                                       pointer_x_canvas - 4, pointer_y_canvas - 4,
                                       pointer_x_canvas + 4, pointer_y_canvas + 4)
        
        # Update motor labels
        if 'x_motor_label' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['x_motor_label'],
                                       motor_x_canvas + 15, workspace_top + 15)
            self.main_app.canvas.itemconfig(self.canvas_objects['x_motor_label'],
                                           text=x_label_text, fill=x_label_color)
        
        if 'y_motor_label' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['y_motor_label'],
                                       workspace_left + 15, motor_y_canvas - 15)
            self.main_app.canvas.itemconfig(self.canvas_objects['y_motor_label'],
                                           text=y_label_text, fill=y_label_color)
    
    def clear_sensor_override(self):
        """Clear sensor override and return to normal position tracking"""
        print("🔓 CLEARING SENSOR OVERRIDE - returning to normal position tracking")
        self.sensor_override_active = False
        if self.sensor_override_timer:
            self.main_app.root.after_cancel(self.sensor_override_timer)
            self.sensor_override_timer = None
    
    def smart_sensor_override_clear(self, step_description):
        """Intelligently clear sensor override only when moving on the relevant axis"""
        if not hasattr(self, 'sensor_override_active') or not self.sensor_override_active:
            return
        
        # Don't clear sensor override for axis moves that don't affect the sensor position
        step_desc = step_description.lower()
        
        # Determine which axis is moving from the step description
        moving_x = ('move x' in step_desc or 'move_x' in step_desc or 'rows motor' in step_desc or 
                   'rightmost page' in step_desc or ('page' in step_desc and 'move to' in step_desc))
        moving_y = ('move y' in step_desc or 'move_y' in step_desc or 'lines motor' in step_desc or 
                   'move to next line' in step_desc or 'move to first line' in step_desc or 
                   ('move to' in step_desc and 'position' in step_desc and 'cm' in step_desc))
        
        print(f"🔍 SMART OVERRIDE CHECK: step='{step_description}', moving_x={moving_x}, moving_y={moving_y}, mode={self.motor_operation_mode}")
        
        # During lines operations, preserve X sensor positions when moving Y
        if self.motor_operation_mode == "lines" and moving_y:
            # Y motor is moving to next line - keep X sensor position, update Y immediately
            print(f"🔒 PRESERVING X sensor position ({self.sensor_position_x:.1f}) during Y move (lines mode)")
            
            # Get hardware positions to update Y
            from mock_hardware import get_current_y, get_current_x
            new_y = get_current_y()
            current_x = get_current_x()
            
            # Update sensor positions: preserve X from sensor, update Y from hardware
            self.sensor_position_y = new_y
            print(f"    ✅ Y motor moved to {new_y:.1f}cm, maintaining X sensor position at {self.sensor_position_x:.1f}cm")
            print(f"    📍 Hardware at ({current_x:.1f}, {new_y:.1f}), displaying pointer at ({self.sensor_position_x:.1f}, {new_y:.1f})")
            
            # Cancel the automatic timer since we're handling this manually
            if self.sensor_override_timer:
                self.main_app.root.after_cancel(self.sensor_override_timer)
                self.sensor_override_timer = None
            
            # Keep sensor override active to maintain X position
            # Force immediate display update to show the new position
            self.update_sensor_position_display()
            print(f"    🎯 Pointer should now be at sensor X position ({self.sensor_position_x:.1f}) and new Y position ({new_y:.1f})")
            return  # Don't clear override, just update Y component
            
        # During rows operations, preserve Y sensor positions when moving X  
        elif self.motor_operation_mode == "rows" and moving_x:
            # X motor is moving to next page/position - keep Y sensor position, update X immediately
            print(f"🔒 PRESERVING Y sensor position ({self.sensor_position_y:.1f}) during X move (rows mode)")
            # Update X position to new hardware position but preserve Y sensor position
            from mock_hardware import get_current_x
            new_x = get_current_x()
            self.sensor_position_x = new_x
            print(f"    ✅ Updated X component to {new_x:.1f}, keeping Y at {self.sensor_position_y:.1f}")
            
            # Cancel the automatic timer since we're handling this manually
            if self.sensor_override_timer:
                self.main_app.root.after_cancel(self.sensor_override_timer)
                self.sensor_override_timer = None
            
            # Keep sensor override active to maintain Y position
            # Force immediate display update to show the new position
            self.update_sensor_position_display()
            return  # Don't clear override, just update X component
        
        # For other cases or when moving the sensor axis, clear the override
        print(f"🔓 CLEARING SENSOR OVERRIDE for move: {step_description}")
        self.clear_sensor_override()
    
    def reset_sensor_highlights(self):
        """Reset sensor indicators to normal colors"""
        # Reset X sensors
        if 'x_left_sensor' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['x_left_sensor'],
                                           fill='orange', outline='darkorange', width=2)
        if 'x_right_sensor' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['x_right_sensor'],
                                           fill='orange', outline='darkorange', width=2)
        
        # Reset Y sensors  
        if 'y_top_sensor' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['y_top_sensor'],
                                           fill='green', outline='darkgreen', width=2)
        if 'y_bottom_sensor' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['y_bottom_sensor'],
                                           fill='green', outline='darkgreen', width=2)
    
    def draw_tool_status_indicators(self):
        """Draw tool status indicators"""
        # Main tool indicators (first row)
        status_y = 15
        self.canvas_objects['line_marker'] = self.main_app.canvas.create_text(
            120, status_y, text="Line Marker: UP", fill='green', font=('Arial', 9, 'bold')
        )
        
        self.canvas_objects['line_cutter'] = self.main_app.canvas.create_text(
            280, status_y, text="Line Cutter: UP", fill='green', font=('Arial', 9, 'bold')
        )
        
        self.canvas_objects['row_marker'] = self.main_app.canvas.create_text(
            440, status_y, text="Row Marker: UP", fill='green', font=('Arial', 9, 'bold')
        )
        
        self.canvas_objects['row_cutter'] = self.main_app.canvas.create_text(
            600, status_y, text="Row Cutter: UP", fill='green', font=('Arial', 9, 'bold')
        )
        
        # State indicators (second row)
        state_y = 35
        self.canvas_objects['line_marker_piston'] = self.main_app.canvas.create_text(
            150, state_y, text="Line Marker State: DOWN", fill='red', font=('Arial', 8, 'bold')
        )
        
        self.canvas_objects['row_marker_limit_switch'] = self.main_app.canvas.create_text(
            400, state_y, text="Row Marker State: UP", fill='darkgreen', font=('Arial', 8, 'bold')
        )
    
    def update_canvas_paper_area(self):
        """Update canvas to show current program's paper area and work lines"""
        if not self.main_app.current_program:
            return
        
        # Clear all tagged objects for clean redraw
        self.main_app.canvas.delete("work_lines")
        
        p = self.main_app.current_program
        
        # Paper coordinates (bottom-left corner at 15, 15)
        PAPER_OFFSET_X = 15.0
        PAPER_OFFSET_Y = 15.0
        paper_bottom_left_x = PAPER_OFFSET_X
        paper_bottom_left_y = PAPER_OFFSET_Y
        
        # ACTUAL paper size (with repeats)
        paper_width = p.width * p.repeat_rows
        paper_height = p.high * p.repeat_lines
        
        print(f"🖼️ CANVAS UPDATE: Showing ACTUAL paper size {paper_width}×{paper_height}cm (repeats: {p.repeat_rows}×{p.repeat_lines})")
        
        # Convert to canvas coordinates
        max_y_cm = self.main_app.settings.get("simulation", {}).get("max_display_y", 80)
        canvas_x1 = self.main_app.offset_x + paper_bottom_left_x * self.main_app.scale_x
        canvas_y1 = self.main_app.offset_y + (max_y_cm - paper_bottom_left_y - paper_height) * self.main_app.scale_y
        canvas_x2 = self.main_app.offset_x + (paper_bottom_left_x + paper_width) * self.main_app.scale_x
        canvas_y2 = self.main_app.offset_y + (max_y_cm - paper_bottom_left_y) * self.main_app.scale_y
        
        # Update or create paper rectangle
        if 'paper' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['paper'], canvas_x1, canvas_y1, canvas_x2, canvas_y2)
        else:
            self.canvas_objects['paper'] = self.main_app.canvas.create_rectangle(
                canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                outline='blue', width=3, fill='lightblue', stipple='gray50'
            )
        
        # Add program label with repeat information
        single_size = f"{p.width}×{p.high}cm"
        repeats_info = f"{p.repeat_rows}×{p.repeat_lines}" if (p.repeat_rows > 1 or p.repeat_lines > 1) else ""
        
        if repeats_info:
            label_text = f"{p.program_name}\nActual: {paper_width}×{paper_height}cm (Pattern: {single_size}, Repeats: {repeats_info})"
        else:
            label_text = f"{p.program_name}\n{paper_width}×{paper_height}cm"
        
        self.main_app.canvas.create_text(
            canvas_x1 + (canvas_x2 - canvas_x1) / 2, canvas_y1 - 25,
            text=label_text, 
            font=('Arial', 9, 'bold'), fill='darkblue', tags="work_lines", justify='center'
        )
        
        # Add line marking and cutting visualizations
        self.draw_work_lines(p, paper_bottom_left_x, paper_bottom_left_y, max_y_cm)
        
        # Legend is now drawn in center panel UI instead of on canvas
    
    def draw_work_lines(self, program, paper_x, paper_y, max_y_cm):
        """Draw visualization of lines that will be marked and cut with REPEAT SUPPORT"""
        
        # Initialize operation states when program changes
        self.initialize_operation_states(program)
        
        # Clear previous work line objects
        self.main_app.work_line_objects = {}
        
        # Calculate ACTUAL paper dimensions with repeats
        actual_paper_width = program.width * program.repeat_rows
        actual_paper_height = program.high * program.repeat_lines
        
        print(f"📏 DRAWING WORK LINES: ACTUAL size {actual_paper_width}×{actual_paper_height}cm")
        
        # CORRECTED REPEAT VISUALIZATION: Process each repeated section individually
        # Each section has its own margins - match step generator logic exactly
        print(f"🖼️ CANVAS REPEAT: {program.repeat_lines} sections of {program.high}cm each")
        
        # Process each repeated section from top to bottom
        overall_line_num = 0
        for section_num in range(program.repeat_lines):
            section_start_y = paper_y + (program.repeat_lines - section_num) * program.high  # Top of this section
            section_end_y = paper_y + (program.repeat_lines - section_num - 1) * program.high  # Bottom of this section
            
            # Calculate line positions within THIS section (with section-specific margins)
            first_line_y_section = section_start_y - program.top_padding
            last_line_y_section = section_end_y + program.bottom_padding
            available_space_section = first_line_y_section - last_line_y_section
            
            if program.number_of_lines > 1:
                line_spacing_section = available_space_section / (program.number_of_lines - 1)
            else:
                line_spacing_section = 0
            
            print(f"   Canvas Section {section_num + 1}: lines from {first_line_y_section:.1f} to {last_line_y_section:.1f}cm")
            
            # Draw all lines in this section
            for line_in_section in range(program.number_of_lines):
                overall_line_num += 1
                line_y_real = first_line_y_section - (line_in_section * line_spacing_section)
                
                # Convert to canvas coordinates - lines span ENTIRE repeated paper width
                line_y_canvas = self.main_app.offset_y + (max_y_cm - line_y_real) * self.main_app.scale_y
                line_x1_canvas = self.main_app.offset_x + paper_x * self.main_app.scale_x
                line_x2_canvas = self.main_app.offset_x + (paper_x + actual_paper_width) * self.main_app.scale_x
                
                # Dynamic color based on state
                state = self.main_app.operation_states['lines'].get(overall_line_num, 'pending')
                if state == 'completed':
                    line_color = '#00AA00'  # Bright green for completed
                    dash_pattern = (10, 2)  # Solid-like for completed
                    width = 3
                elif state == 'in_progress':
                    line_color = '#FF8800'  # Orange for in progress
                    dash_pattern = (8, 4)
                    width = 3
                else:  # pending
                    line_color = '#FF4444'  # Red for pending
                    dash_pattern = (5, 5)
                    width = 2
                
                # Draw line
                line_id = self.main_app.canvas.create_line(
                    line_x1_canvas, line_y_canvas, line_x2_canvas, line_y_canvas,
                    fill=line_color, width=width, dash=dash_pattern, tags="work_lines"
                )
                
                # Store line object for dynamic updates
                self.main_app.work_line_objects[f'line_{overall_line_num}'] = {
                    'id': line_id,
                    'type': 'line',
                    'color_pending': '#FF4444',
                    'color_progress': '#FF8800',
                    'color_completed': '#00AA00'
                }
                
                # Add line number label with matching color
                label_id = self.main_app.canvas.create_text(
                    line_x1_canvas - 25, line_y_canvas,
                    text=f"L{overall_line_num}", font=('Arial', 9, 'bold'), fill=line_color, tags="work_lines"
                )
                self.main_app.work_line_objects[f'line_{overall_line_num}']['label_id'] = label_id
        
        # Draw vertical lines (Row Pattern) WITH REPEAT SUPPORT - Show ALL page marks across repeated sections
        first_page_start = paper_x + program.left_margin
        
        # Calculate TOTAL pages across all repeated sections
        total_pages = program.number_of_pages * program.repeat_rows
        
        print(f"📄 DRAWING PAGES: {total_pages} total pages ({program.number_of_pages} per section × {program.repeat_rows} sections)")
        
        # Draw each page's start and end marks (across entire repeated area)
        page_mark_id = 1  # For tracking state
        
        for page_num in range(total_pages):
            # Calculate page start position across ENTIRE repeated paper
            page_start_x = first_page_start + page_num * (program.page_width + program.buffer_between_pages)
            
            # Calculate page end position  
            page_end_x = page_start_x + program.page_width
            
            # Draw page START mark - spans ACTUAL paper height
            page_start_canvas = self.main_app.offset_x + page_start_x * self.main_app.scale_x
            page_y1_canvas = self.main_app.offset_y + (max_y_cm - (paper_y + actual_paper_height)) * self.main_app.scale_y
            page_y2_canvas = self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y
            
            # Individual row state tracking - each edge is independent
            # Convert LEFT-TO-RIGHT drawing to RIGHT-TO-LEFT numbering
            # Drawing: page_num 0,1,2,3 (left to right)
            # RTL: page_num 3,2,1,0 (right to left) → R1,R2,R3... (right to left)
            rtl_drawing_row_num = (page_num * 2) + 1  # Drawing row number (left to right)
            individual_row_num = program.number_of_pages * 2 - rtl_drawing_row_num + 1  # Convert to RTL numbering
            row_state = self.main_app.operation_states['rows'].get(f'row_{rtl_drawing_row_num}', 'pending')
            
            if row_state == 'completed':
                start_color = '#0088AA'  # Cyan for completed
                start_dash = (8, 2)
                start_width = 3
            elif row_state == 'in_progress':
                start_color = '#8800FF'  # Purple for in progress
                start_dash = (6, 3)
                start_width = 3
            else:  # pending
                start_color = '#4444FF'  # Blue for pending
                start_dash = (4, 4)
                start_width = 2
            
            # Create individual row line (right edge)
            row_start_id = self.main_app.canvas.create_line(
                page_start_canvas, page_y1_canvas,
                page_start_canvas, page_y2_canvas,
                fill=start_color, width=start_width, dash=start_dash, tags="work_lines"
            )
            
            # Row label (R1, R3, R5, etc.)
            self.main_app.canvas.create_text(
                page_start_canvas, page_y2_canvas + 15,
                text=f"R{individual_row_num}", font=('Arial', 8, 'bold'), 
                fill=start_color, tags="work_lines"
            )
            
            # Draw page END mark
            page_end_canvas = self.main_app.offset_x + page_end_x * self.main_app.scale_x
            
            # Individual row state tracking - left edge is independent
            # Convert LEFT-TO-RIGHT drawing to RIGHT-TO-LEFT numbering for left edges
            rtl_drawing_row_num_left = (page_num * 2) + 2  # Drawing row number for left edges
            individual_row_num_left = program.number_of_pages * 2 - rtl_drawing_row_num_left + 1  # Convert to RTL numbering
            end_row_state = self.main_app.operation_states['rows'].get(f'row_{rtl_drawing_row_num_left}', 'pending')
            
            if end_row_state == 'completed':
                end_color = '#0088AA'  # Cyan for completed
                end_dash = (8, 2)
                end_width = 3
            elif end_row_state == 'in_progress':
                end_color = '#8800FF'  # Purple for in progress
                end_dash = (6, 3)
                end_width = 3
            else:  # pending
                end_color = '#4444FF'  # Blue for pending
                end_dash = (4, 4)
                end_width = 2
            
            # Create individual row line (left edge)
            row_end_id = self.main_app.canvas.create_line(
                page_end_canvas, page_y1_canvas,
                page_end_canvas, page_y2_canvas,
                fill=end_color, width=end_width, dash=end_dash, tags="work_lines"
            )
            
            # Row label (R2, R4, R6, etc.)
            self.main_app.canvas.create_text(
                page_end_canvas, page_y2_canvas + 15,
                text=f"R{individual_row_num_left}", font=('Arial', 8, 'bold'), 
                fill=end_color, tags="work_lines"
            )
            
            # Store individual row objects for dynamic updates (using drawing row numbers as keys)
            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num}'] = {
                'id': row_start_id,
                'type': 'row',
                'color_pending': '#4444FF',
                'color_progress': '#8800FF',
                'color_completed': '#0088AA'
            }
            
            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num_left}'] = {
                'id': row_end_id,
                'type': 'row',
                'color_pending': '#4444FF',
                'color_progress': '#8800FF',
                'color_completed': '#0088AA'
            }
        
        # Draw cut edges - horizontal cuts (top and bottom)
        cuts = ['top', 'bottom', 'left', 'right']
        cut_positions = [
            (paper_y + program.high, 'horizontal'),  # top edge of paper
            (paper_y, 'horizontal'),                 # bottom edge of paper  
            (paper_x, 'vertical'),                   # left edge of paper
            (paper_x + program.width, 'vertical')    # right edge of paper
        ]
        cut_labels = ['TOP CUT', 'BOTTOM CUT', 'LEFT CUT', 'RIGHT CUT']
        
        for i, (cut_pos, orientation) in enumerate(cut_positions):
            cut_name = cuts[i]
            state = self.main_app.operation_states['cuts'].get(cut_name, 'pending')
            
            if state == 'completed':
                cut_color = '#AA00AA'  # Magenta for completed
                width = 4
            elif state == 'in_progress':
                cut_color = '#FF0088'  # Pink for in progress
                width = 4
            else:  # pending
                cut_color = '#8800FF'  # Purple for pending
                width = 3
            
            if orientation == 'horizontal':
                cut_y_canvas = self.main_app.offset_y + (max_y_cm - cut_pos) * self.main_app.scale_y
                cut_id = self.main_app.canvas.create_line(
                    self.main_app.offset_x + paper_x * self.main_app.scale_x, cut_y_canvas,
                    self.main_app.offset_x + (paper_x + program.width) * self.main_app.scale_x, cut_y_canvas,
                    fill=cut_color, width=width, tags="work_lines"
                )
                
                # Cut label
                label_id = self.main_app.canvas.create_text(
                    self.main_app.offset_x + (paper_x + program.width) * self.main_app.scale_x + 50, cut_y_canvas,
                    text=cut_labels[i], font=('Arial', 8, 'bold'), fill=cut_color, tags="work_lines"
                )
                
                # Store cut object for dynamic updates
                self.main_app.work_line_objects[f'cut_{cut_name}'] = {
                    'id': cut_id,
                    'type': 'cut',
                    'color_pending': '#8800FF',
                    'color_progress': '#FF0088',
                    'color_completed': '#AA00AA'
                }
                self.main_app.work_line_objects[f'cut_{cut_name}']['label_id'] = label_id
            else:  # vertical
                cut_x_canvas = self.main_app.offset_x + cut_pos * self.main_app.scale_x
                cut_id = self.main_app.canvas.create_line(
                    cut_x_canvas, self.main_app.offset_y + (max_y_cm - (paper_y + program.high)) * self.main_app.scale_y,
                    cut_x_canvas, self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y,
                    fill=cut_color, width=width, tags="work_lines"
                )
                
                # Store cut object for dynamic updates
                self.main_app.work_line_objects[f'cut_{cut_name}'] = {
                    'id': cut_id,
                    'type': 'cut',
                    'color_pending': '#8800FF',
                    'color_progress': '#FF0088',
                    'color_completed': '#AA00AA'
                }
    
    def initialize_operation_states(self, program):
        """Initialize operation states for the current program WITH REPEAT SUPPORT"""
        # Calculate TOTAL elements across all repeated sections
        total_lines = program.number_of_lines * program.repeat_lines
        total_pages = program.number_of_pages * program.repeat_rows
        total_rows = total_pages * 2  # 2 rows per page (right edge + left edge)
        
        print(f"🔄 INITIALIZING STATES: {total_lines} lines, {total_pages} pages, {total_rows} rows (with repeats)")
        
        self.main_app.operation_states = {
            'lines': {},      # Track line marking states: {1: 'pending', 2: 'completed', ...}
            'cuts': {},       # Track cutting states: {'top'/'bottom'/'left'/'right': 'pending'/'completed'}
            'pages': {},      # Track page states: {0: 'pending', 1: 'completed', ...}
            'rows': {}        # Track individual row states: {'row_1': 'pending', 'row_2': 'completed', ...}
        }
        
        # Initialize ALL lines across repeated sections as pending
        for line_num in range(1, total_lines + 1):
            self.main_app.operation_states['lines'][line_num] = 'pending'
        
        # Initialize all cuts as pending
        for cut_name in ['top', 'bottom', 'left', 'right']:
            self.main_app.operation_states['cuts'][cut_name] = 'pending'
        
        # Initialize ALL pages across repeated sections as pending (both start and end for each page)
        for page_num in range(1, total_pages + 1):
            self.main_app.operation_states['pages'][f'{page_num}_start'] = 'pending'
            self.main_app.operation_states['pages'][f'{page_num}_end'] = 'pending'
        
        # Initialize ALL individual rows across repeated sections as pending
        for row_num in range(1, total_rows + 1):
            self.main_app.operation_states['rows'][f'row_{row_num}'] = 'pending'
    
    def draw_enhanced_legend(self):
        """Draw an enhanced color-coded legend showing operation states"""
        # Position legend at bottom of canvas for maximum simulation space
        legend_x = 20  # Start from left side
        legend_y = self.main_app.canvas_height - 180  # Near bottom
        box_width = self.main_app.canvas_width - 40  # Full width minus margins
        box_height = 120  # Reduced height for compactness
        
        # Legend background
        self.main_app.canvas.create_rectangle(
            legend_x, legend_y, legend_x + box_width, legend_y + box_height,
            fill='lightyellow', outline='black', width=2, tags="legend"
        )
        
        # Legend title
        title_y = legend_y + 15
        self.main_app.canvas.create_text(legend_x + 150, title_y, text="📋 WORK OPERATIONS STATUS", 
                                font=('Arial', 11, 'bold'), fill='darkblue', tags="legend")
        
        # Color indicators and descriptions
        # Two columns: Lines/Cuts on left, Pages on right
        col_width = 140
        
        # Lines and Cuts column
        start_x = legend_x + 10
        legend_y += 10
        
        self.draw_operation_column(start_x, legend_y + 10, "✏️ MARK", [
            ('L1, L2, L3...', 'Line markings'),
            ('🔴 Pending', '#FF4444'),
            ('🟠 In Progress', '#FF8800'),  
            ('🟢 Completed', '#00AA00')
        ])
        
        self.draw_operation_column(start_x + col_width, legend_y + 10, "✂️ CUT", [
            ('TOP/BOTTOM/LEFT/RIGHT', 'Edge cuts'),
            ('🟣 Pending', '#8800FF'),
            ('🩷 In Progress', '#FF0088'),
            ('🟣 Completed', '#AA00AA')
        ])
        
        # Progress summary right below the work operations box
        self.draw_progress_summary(legend_x, legend_y + box_height + 5, box_width)
    
    def draw_operation_column(self, x, y, title, states):
        """Draw a column of operation states with colors"""
        # Column title
        self.main_app.canvas.create_text(x + 60, y, text=title, 
                                font=('Arial', 10, 'bold'), fill='black', tags="legend")
        
        y += 20
        for i, (emoji_text, description) in enumerate(states):
            y_pos = y + (i * 15)
            
            # Show colored indicator or description
            if description.startswith('#'):  # It's a color code
                self.main_app.canvas.create_text(x + 12, y_pos, text=emoji_text, 
                                        font=('Arial', 9), fill=description, tags="legend")
            else:  # It's descriptive text
                self.main_app.canvas.create_text(x + 12, y_pos, text=emoji_text, 
                                        font=('Arial', 8), fill='darkgray', tags="legend")
    
    def draw_progress_summary(self, x, y, width):
        """Draw overall progress summary with progress bar"""
        if not self.main_app.current_program:
            return
        
        total_operations = 0
        completed_operations = 0
        
        # Count line states
        for state in self.main_app.operation_states['lines'].values():
            total_operations += 1
            if state == 'completed':
                completed_operations += 1
        
        # Count cut states
        for state in self.main_app.operation_states['cuts'].values():
            total_operations += 1
            if state == 'completed':
                completed_operations += 1
        
        # Calculate progress percentage
        if total_operations > 0:
            progress_percent = (completed_operations / total_operations) * 100
        else:
            progress_percent = 0
        
        # Progress bar background
        bar_width = width - 20
        bar_height = 15
        bar_x = x + 10
        bar_y = y + 25
        
        self.main_app.canvas.create_rectangle(
            bar_x, bar_y, bar_x + bar_width, bar_y + bar_height,
            fill='lightgray', outline='black', width=1, tags="legend"
        )
        
        # Progress bar fill
        if progress_percent > 0:
            fill_width = (bar_width * progress_percent) / 100
            self.main_app.canvas.create_rectangle(
                bar_x, bar_y, bar_x + fill_width, bar_y + bar_height,
                fill='green', outline='', tags="legend"
            )
        
        # Progress text
        summary_text = f"📊 Overall Progress: {completed_operations}/{total_operations} ({progress_percent:.0f}%)"
        self.main_app.canvas.create_text(x + 10, y, text=summary_text, 
                               font=('Arial', 9, 'bold'), fill='darkgreen', tags="legend")
    
    def update_operation_state(self, operation_type, operation_id, new_state):
        """Update the state of a specific operation and refresh visualization"""
        if operation_type in self.main_app.operation_states:
            self.main_app.operation_states[operation_type][operation_id] = new_state
            # Refresh only the work lines without redrawing everything
            if self.main_app.current_program:
                self.refresh_work_lines_colors()
    
    def track_operation_from_step(self, step_description):
        """Track operations from step descriptions for real-time updates"""
        if not self.main_app.current_program:
            return
            
        desc = step_description.lower()
        
        # Track line marking operations - pattern: "Mark line X/Y: Open/Close line marker"
        if 'lines' in desc and 'line marker' in desc:
            line_match = re.search(r'mark line (\d+)/(\d+)', desc)
            if line_match:
                line_num = int(line_match.group(1))
                if 'open line marker' in desc:
                    self.update_operation_state('lines', line_num, 'in_progress')
                    print(f"🟠 Line {line_num} marking started (IN PROGRESS)")
                elif 'close line marker' in desc:
                    self.update_operation_state('lines', line_num, 'completed')
                    print(f"🟢 Line {line_num} marking completed (COMPLETED)")
        
        # Track cutting operations - pattern: "Cut top/bottom edge: Open/Close line cutter"
        elif 'lines' in desc and 'line cutter' in desc:
            if 'cut top edge' in desc:
                if 'open line cutter' in desc:
                    self.update_operation_state('cuts', 'top', 'in_progress')
                    print("🟠 Top cut started (IN PROGRESS)")
                elif 'close line cutter' in desc:
                    self.update_operation_state('cuts', 'top', 'completed')
                    print("🟣 Top cut completed (COMPLETED)")
            elif 'cut bottom edge' in desc:
                if 'open line cutter' in desc:
                    self.update_operation_state('cuts', 'bottom', 'in_progress')
                    print("🟠 Bottom cut started (IN PROGRESS)")
                elif 'close line cutter' in desc:
                    self.update_operation_state('cuts', 'bottom', 'completed')
                    print("🟣 Bottom cut completed (COMPLETED)")
        
        # Track row marking operations - INDIVIDUAL ROW TRACKING (not page-based)
        elif 'row marker' in desc and 'rtl page' in desc:
            page_match = re.search(r'rtl page (\d+)/(\d+)', desc)
            if page_match:
                rtl_page_num = int(page_match.group(1))  # RTL page numbering: 1=rightmost, ascending
                total_pages = int(page_match.group(2))
                
                # Calculate individual row number for RIGHT-TO-LEFT operation
                # RTL Page 1 (rightmost) RIGHT edge = Row 1 (rightmost drawn row)
                # RTL Page 1 (rightmost) LEFT edge = Row 2
                # RTL Page 2 RIGHT edge = Row 3, etc.
                # But we need to map to the drawing system which numbers LEFT-TO-RIGHT
                
                # Calculate RTL row number
                if '(right edge)' in desc:
                    rtl_row_num = (rtl_page_num - 1) * 2 + 1  # 1, 3, 5, 7...
                    edge_type = 'RIGHT'
                elif '(left edge)' in desc:
                    rtl_row_num = (rtl_page_num - 1) * 2 + 2  # 2, 4, 6, 8...
                    edge_type = 'LEFT'
                
                # Convert RTL row number to drawing system row number (flip the mapping)
                # RTL Row 1 (rightmost) → Drawing Row 8 (rightmost in 8-row system)
                # RTL Row 2 → Drawing Row 7, RTL Row 3 → Drawing Row 6, etc.
                total_rows = total_pages * 2
                individual_row_num = total_rows - rtl_row_num + 1
                
                # Use individual row tracking instead of page-based
                row_key = f'row_{individual_row_num}'
                
                if 'open row marker' in desc:
                    self.update_operation_state('rows', row_key, 'in_progress')
                    print(f"🟠 RTL Page {rtl_page_num} {edge_type} edge → RTL Row {rtl_row_num} → Drawing Row {individual_row_num} marking started (IN PROGRESS)")
                elif 'close row marker' in desc:
                    self.update_operation_state('rows', row_key, 'completed')
                    print(f"🔵 RTL Page {rtl_page_num} {edge_type} edge → RTL Row {rtl_row_num} → Drawing Row {individual_row_num} marking completed (COMPLETED)")
        
        # Track row cutting operations - NEW PATTERN: "Cut RIGHT/LEFT paper edge: Open/Close row cutter"
        elif 'row cutter' in desc:
            if 'cut right paper edge' in desc:
                if 'open row cutter' in desc:
                    self.update_operation_state('cuts', 'right', 'in_progress')
                    print("🟠 RIGHT paper edge cut started (IN PROGRESS)")
                elif 'close row cutter' in desc:
                    self.update_operation_state('cuts', 'right', 'completed')
                    print("🟣 RIGHT paper edge cut completed (COMPLETED)")
            elif 'cut left paper edge' in desc:
                if 'open row cutter' in desc:
                    self.update_operation_state('cuts', 'left', 'in_progress')
                    print("🟠 LEFT paper edge cut started (IN PROGRESS)")
                elif 'close row cutter' in desc:
                    self.update_operation_state('cuts', 'left', 'completed')
                    print("🟣 LEFT paper edge cut completed (COMPLETED)")
    
    def refresh_work_lines_colors(self):
        """Refresh work line colors based on current operation states without redrawing"""
        if not hasattr(self.main_app, 'work_line_objects') or not self.main_app.current_program:
            return
            
        # Update line colors
        actual_lines = self.main_app.current_program.number_of_lines  
        for line_num in range(1, actual_lines + 1):
            obj_key = f'line_{line_num}'
            if obj_key in self.main_app.work_line_objects:
                obj = self.main_app.work_line_objects[obj_key]
                state = self.main_app.operation_states['lines'].get(line_num, 'pending')
                
                if state == 'completed':
                    color = obj['color_completed']
                    width = 3
                elif state == 'in_progress':
                    color = obj['color_progress']
                    width = 3
                else:
                    color = obj['color_pending']
                    width = 2
                
                # Update line color
                self.main_app.canvas.itemconfig(obj['id'], fill=color, width=width)
                if 'label_id' in obj:
                    self.main_app.canvas.itemconfig(obj['label_id'], fill=color)
        
        # Update cut colors
        for cut_name in ['top', 'bottom', 'left', 'right']:
            obj_key = f'cut_{cut_name}'
            if obj_key in self.main_app.work_line_objects:
                obj = self.main_app.work_line_objects[obj_key]
                state = self.main_app.operation_states['cuts'].get(cut_name, 'pending')
                
                if state == 'completed':
                    color = obj['color_completed']
                    width = 4
                elif state == 'in_progress':
                    color = obj['color_progress']
                    width = 4
                else:
                    color = obj['color_pending']
                    width = 3
                
                # Update cut color
                self.main_app.canvas.itemconfig(obj['id'], fill=color, width=width)
                if 'label_id' in obj:
                    self.main_app.canvas.itemconfig(obj['label_id'], fill=color)
        
        # Update individual row colors (each row edge is completely independent)
        total_rows = self.main_app.current_program.number_of_pages * 2
        for row_num in range(1, total_rows + 1):
            row_obj_key = f'row_{row_num}'
            row_state = self.main_app.operation_states['rows'].get(f'row_{row_num}', 'pending')
            
            if row_obj_key in self.main_app.work_line_objects:
                obj = self.main_app.work_line_objects[row_obj_key]
                
                if row_state == 'completed':
                    color = obj['color_completed']
                    dash = (8, 2)
                    width = 3
                    print(f"🔵 UPDATING ROW {row_num} COLOR: COMPLETED (Cyan)")
                elif row_state == 'in_progress':
                    color = obj['color_progress']
                    dash = (6, 3)
                    width = 3
                    print(f"🟠 UPDATING ROW {row_num} COLOR: IN PROGRESS (Purple)")
                else:
                    color = obj['color_pending']
                    dash = (4, 4)
                    width = 2
                
                # Update individual row color and style
                self.main_app.canvas.itemconfig(obj['id'], fill=color, width=width, dash=dash)
                print(f"✅ Row {row_num} color updated to {color} (state: {row_state})")
    
    def move_tool_to_first_line(self):
        """Move tool to the first line position when program is selected"""
        if not self.main_app.current_program:
            return
            
        # Calculate first line position based on program (matches step generator)
        PAPER_OFFSET_X = 15.0  # Paper starts at (15, 15)
        PAPER_OFFSET_Y = 15.0
        
        # First line Y position: PAPER_OFFSET_Y + program.high - program.top_padding
        first_line_y = PAPER_OFFSET_Y + self.main_app.current_program.high - self.main_app.current_program.top_padding
        
        # Move to left edge of paper for X position  
        tool_x = PAPER_OFFSET_X
        
        # Move hardware to first line position
        move_x(tool_x)
        move_y(first_line_y)
        
        # Update display
        self.update_position_display()
        
        print(f"Tool moved to first line position: ({tool_x:.1f}, {first_line_y:.1f}) - Paper offset + program coordinates")
    
    
    def update_position_display(self):
        """Update position display with independent motor visualization"""
        try:
            # Check for sensor override but don't block hardware movement updates
            if self.sensor_override_active:
                # Get current hardware position to check if hardware actually moved
                current_hardware_x = get_current_x()
                current_hardware_y = get_current_y()
                
                # Check if hardware moved significantly (indicating a move_y or move_x operation)
                if hasattr(self, '_last_displayed_hardware_x') and hasattr(self, '_last_displayed_hardware_y'):
                    x_change = abs(current_hardware_x - self._last_displayed_hardware_x)
                    y_change = abs(current_hardware_y - self._last_displayed_hardware_y)
                    
                    # If hardware moved significantly, update the appropriate sensor position component
                    if self.motor_operation_mode == "lines" and y_change > 0.1:
                        # Y hardware moved during lines mode - update sensor Y position but PRESERVE X sensor position
                        print(f"🔄 HARDWARE Y MOVED during lines mode:")
                        print(f"    Y: {self.sensor_position_y:.1f} → {current_hardware_y:.1f} (updated)")
                        print(f"    X: {self.sensor_position_x:.1f} (preserved from sensor trigger)")
                        
                        # Update Y to hardware position but keep X from sensor
                        self.sensor_position_y = current_hardware_y
                        # DO NOT UPDATE sensor_position_x - keep it at sensor trigger position
                        
                        self._last_displayed_hardware_x = current_hardware_x
                        self._last_displayed_hardware_y = current_hardware_y
                        # Update display with new positions
                        self.update_sensor_position_display()
                        return
                        
                    elif self.motor_operation_mode == "rows" and x_change > 0.1:
                        # X hardware moved during rows mode - update sensor X position but PRESERVE Y sensor position
                        print(f"🔄 HARDWARE X MOVED during rows mode:")
                        print(f"    X: {self.sensor_position_x:.1f} → {current_hardware_x:.1f} (updated)")
                        print(f"    Y: {self.sensor_position_y:.1f} (preserved from sensor trigger)")
                        
                        # Update X to hardware position but keep Y from sensor
                        self.sensor_position_x = current_hardware_x
                        # DO NOT UPDATE sensor_position_y - keep it at sensor trigger position
                        
                        self._last_displayed_hardware_x = current_hardware_x
                        self._last_displayed_hardware_y = current_hardware_y
                        # Update display with new positions
                        self.update_sensor_position_display()
                        return
                
                # No significant hardware movement - maintain current sensor override
                # print(f"🔒 SENSOR OVERRIDE ACTIVE - maintaining sensor position ({self.sensor_position_x:.1f}, {self.sensor_position_y:.1f})")
                self.update_sensor_position_display()
                return
            
            # Get current position from hardware
            hardware_x = get_current_x()
            hardware_y = get_current_y()
            
            # Store current positions for next comparison (hardware movement is handled above in sensor override section)
            # This section now only handles normal position updates when no sensor override is active
            
            # Store current positions for next comparison
            self._last_hardware_x = hardware_x
            self._last_hardware_y = hardware_y
            
            # Show independent motor behavior in simulation
            # During lines operations: only Y motor moves, X motor stays at 0
            # During rows operations: only X motor moves, Y motor stays at 0
            if self.motor_operation_mode == "lines":
                display_x = 0.0  # X motor stays at home during lines operations
                display_y = hardware_y  # Y motor shows actual position
                self.update_lines_motor_position(hardware_y)
            elif self.motor_operation_mode == "rows":  
                display_x = hardware_x  # X motor shows actual position  
                display_y = 0.0  # Y motor stays at home during rows operations
                self.update_rows_motor_position(hardware_x)
            else:
                # Idle mode: show actual positions (both can move)
                display_x = hardware_x
                display_y = hardware_y
            
            # Update position label with actual hardware positions
            if hasattr(self.main_app, 'position_label'):
                self.main_app.position_label.config(text=f"Position: X={hardware_x:.1f}, Y={hardware_y:.1f}")
            
            # Update motor position lines using display positions
            max_y_cm = self.main_app.settings.get("simulation", {}).get("max_display_y", 80)
            motor_x_canvas = self.main_app.offset_x + display_x * self.main_app.scale_x
            motor_y_canvas = self.main_app.offset_y + (max_y_cm - display_y) * self.main_app.scale_y  # Invert Y for canvas
            
            # Get workspace boundaries
            workspace_left = self.main_app.offset_x
            workspace_right = self.main_app.canvas_width - self.main_app.offset_x
            workspace_top = self.main_app.offset_y
            workspace_bottom = self.main_app.canvas_height - self.main_app.offset_y
            
            # Update X motor line (vertical line)
            if 'x_motor_line' in self.canvas_objects:
                self.main_app.canvas.coords(self.canvas_objects['x_motor_line'],
                                 motor_x_canvas, workspace_top,
                                 motor_x_canvas, workspace_bottom)
            
            # Update Y motor line (horizontal line)
            if 'y_motor_line' in self.canvas_objects:
                self.main_app.canvas.coords(self.canvas_objects['y_motor_line'],
                                 workspace_left, motor_y_canvas,
                                 workspace_right, motor_y_canvas)
                
            # Update intersection point
            if 'motor_intersection' in self.canvas_objects:
                self.main_app.canvas.coords(self.canvas_objects['motor_intersection'],
                                 motor_x_canvas - 4, motor_y_canvas - 4,
                                 motor_x_canvas + 4, motor_y_canvas + 4)
            
            # Update motor position labels with display positions and operation mode info
            if 'x_motor_label' in self.canvas_objects:
                self.main_app.canvas.coords(self.canvas_objects['x_motor_label'],
                                 motor_x_canvas + 15, workspace_top + 15)
                
                # Show different info based on operation mode
                if self.motor_operation_mode == "lines":
                    label_text = f"X=0.0cm (HOLD)"
                    label_color = "gray"
                elif self.motor_operation_mode == "rows":
                    label_text = f"X={hardware_x:.1f}cm (ACTIVE)"
                    label_color = "red"
                else:
                    label_text = f"X={hardware_x:.1f}cm"
                    label_color = "red"
                    
                self.main_app.canvas.itemconfig(self.canvas_objects['x_motor_label'],
                                 text=label_text, fill=label_color)
                
            if 'y_motor_label' in self.canvas_objects:
                self.main_app.canvas.coords(self.canvas_objects['y_motor_label'],
                                 workspace_left + 15, motor_y_canvas - 15)
                
                # Show different info based on operation mode
                if self.motor_operation_mode == "lines":
                    label_text = f"Y={hardware_y:.1f}cm (ACTIVE)"
                    label_color = "blue"
                elif self.motor_operation_mode == "rows":
                    label_text = f"Y=0.0cm (HOLD)"
                    label_color = "gray"
                else:
                    label_text = f"Y={hardware_y:.1f}cm"
                    label_color = "blue"
                    
                self.main_app.canvas.itemconfig(self.canvas_objects['y_motor_label'],
                                 text=label_text, fill=label_color)
            
            # Update position indicators (tool status indicators)
            self._update_position_indicators(motor_x_canvas, motor_y_canvas, hardware_x, hardware_y)
            
        except Exception as e:
            print(f"Error updating position display: {e}")
    
    def _update_position_indicators(self, canvas_x, canvas_y, current_x, current_y):
        """Update position indicators on canvas edges"""
        try:
            
            # Enhanced position indicators with operation context
            # X-axis position indicator (vertical line on bottom edge) - BLUE for X
            if 'x_position_line' in self.canvas_objects:
                self.main_app.canvas.delete(self.canvas_objects['x_position_line'])
            if 'x_position_label' in self.canvas_objects:
                self.main_app.canvas.delete(self.canvas_objects['x_position_label'])
                
            # X position line on bottom edge
            x_line_y = self.main_app.canvas_height - self.main_app.offset_y
            self.canvas_objects['x_position_line'] = self.main_app.canvas.create_line(
                canvas_x, x_line_y - 10, canvas_x, x_line_y + 10,
                fill='blue', width=3, tags="position_indicators"
            )
            self.canvas_objects['x_position_label'] = self.main_app.canvas.create_text(
                canvas_x, x_line_y + 20, text=f"X: {current_x:.1f}cm",
                font=('Arial', 8, 'bold'), fill='blue', tags="position_indicators"
            )
            
            # Y-axis position indicator (horizontal line on left edge) - RED for Y  
            if 'y_position_line' in self.canvas_objects:
                self.main_app.canvas.delete(self.canvas_objects['y_position_line'])
            if 'y_position_label' in self.canvas_objects:
                self.main_app.canvas.delete(self.canvas_objects['y_position_label'])
                
            # Y position line on left edge
            y_line_x = self.main_app.offset_x
            self.canvas_objects['y_position_line'] = self.main_app.canvas.create_line(
                y_line_x - 10, canvas_y, y_line_x + 10, canvas_y,
                fill='red', width=3, tags="position_indicators"
            )
            self.canvas_objects['y_position_label'] = self.main_app.canvas.create_text(
                y_line_x - 30, canvas_y, text=f"Y: {current_y:.1f}cm",
                font=('Arial', 8, 'bold'), fill='red', tags="position_indicators"
            )
            
            # Add operation context indicator
            self.update_operation_context_display(canvas_x, canvas_y, current_x, current_y)
            
            # Update tool status indicators (get from hardware state)
            status = get_hardware_status()
            
            # Update canvas tool status texts
            if 'line_marker' in self.canvas_objects:
                marker_status = "DOWN" if status['line_marker'] == 'down' else "UP"
                marker_color = "red" if status['line_marker'] == 'down' else "green"
                self.main_app.canvas.itemconfig(self.canvas_objects['line_marker'], 
                                     text=f"Line Marker: {marker_status}", fill=marker_color)
            
            if 'line_marker_piston' in self.canvas_objects:
                piston_status = "UP" if status['line_marker_piston'] == 'up' else "DOWN"
                piston_color = "blue" if status['line_marker_piston'] == 'up' else "red"
                self.main_app.canvas.itemconfig(self.canvas_objects['line_marker_piston'], 
                                     text=f"Line Marker State: {piston_status}", fill=piston_color)
            
            if 'line_cutter' in self.canvas_objects:
                cutter_status = "DOWN" if status['line_cutter'] == 'down' else "UP"
                cutter_color = "red" if status['line_cutter'] == 'down' else "green"
                self.main_app.canvas.itemconfig(self.canvas_objects['line_cutter'], 
                                     text=f"Line Cutter: {cutter_status}", fill=cutter_color)
            
            if 'row_marker' in self.canvas_objects:
                marker_status = "DOWN" if status['row_marker'] == 'down' else "UP"
                marker_color = "red" if status['row_marker'] == 'down' else "green"
                self.main_app.canvas.itemconfig(self.canvas_objects['row_marker'], 
                                     text=f"Row Marker: {marker_status}", fill=marker_color)
            
            if 'row_marker_limit_switch' in self.canvas_objects:
                limit_status = "DOWN" if status['row_marker_limit_switch'] == 'down' else "UP"
                limit_color = "darkred" if status['row_marker_limit_switch'] == 'down' else "darkgreen"
                self.main_app.canvas.itemconfig(self.canvas_objects['row_marker_limit_switch'], 
                                     text=f"Row Marker State: {limit_status}", fill=limit_color)
            
            if 'row_cutter' in self.canvas_objects:
                cutter_status = "DOWN" if status['row_cutter'] == 'down' else "UP"
                cutter_color = "red" if status['row_cutter'] == 'down' else "green"
                self.main_app.canvas.itemconfig(self.canvas_objects['row_cutter'], 
                                     text=f"Row Cutter: {cutter_status}", fill=cutter_color)
        
        except Exception as e:
            # Handle any errors silently for Pi optimization
            pass
    
    def update_operation_context_display(self, canvas_x, canvas_y, current_x, current_y):
        """Display operation context and position indicators"""
        if not self.main_app.current_program:
            return
            
        # Clear previous context indicators
        if 'context_indicator' in self.canvas_objects:
            self.main_app.canvas.delete(self.canvas_objects['context_indicator'])
        if 'context_label' in self.canvas_objects:
            self.main_app.canvas.delete(self.canvas_objects['context_label'])
            
        # Determine current operation context based on position
        context = self.determine_operation_context(current_x, current_y)
        
        # Create context indicator - a circle around the main tool position
        indicator_size = 12
        if context['type'] == 'line_marking':
            color = '#FF8800'  # Orange for line marking
            symbol = '📏'
        elif context['type'] == 'cutting':
            color = '#AA00AA'  # Magenta for cutting
            symbol = '✂️'
        else:
            color = '#888888'  # Gray for idle/moving
            symbol = '🔄'
            
        # Outer context circle
        self.canvas_objects['context_indicator'] = self.main_app.canvas.create_oval(
            canvas_x - indicator_size, canvas_y - indicator_size, 
            canvas_x + indicator_size, canvas_y + indicator_size,
            outline=color, width=3, dash=(4, 4), tags="position_indicators"
        )
        
        # Context label with operation info
        self.canvas_objects['context_label'] = self.main_app.canvas.create_text(
            canvas_x, canvas_y - 25, text=f"{symbol} {context['description']}",
            font=('Arial', 8, 'bold'), fill=color, tags="position_indicators"
        )
    
    def determine_operation_context(self, x, y):
        """Determine what operation the tool is positioned for"""
        if not self.main_app.current_program:
            return {'type': 'idle', 'description': 'No program'}
            
        PAPER_OFFSET_Y = 15.0
        
        # Check current step to determine operation phase
        current_step_desc = ""
        if (self.main_app.execution_engine and 
            self.main_app.execution_engine.current_step_index < len(self.main_app.steps)):
            current_step = self.main_app.steps[self.main_app.execution_engine.current_step_index]
            current_step_desc = current_step.get('description', '').lower()
        
        # Check if at cutting positions first, but be position-accurate
        top_cut_pos = PAPER_OFFSET_Y + self.main_app.current_program.high
        bottom_cut_pos = PAPER_OFFSET_Y  # Bottom cut at paper starting position
        
        if abs(y - top_cut_pos) < 0.5:
            return {'type': 'cutting', 'description': 'Top Edge Cut'}
        elif abs(y - bottom_cut_pos) < 0.5:
            # Check if we're currently in a bottom cutting step AND actually at bottom position
            if ('cut bottom edge' in current_step_desc or 'bottom cut' in current_step_desc):
                return {'type': 'cutting', 'description': 'Bottom Edge Cut'}
            # If at bottom position but not in cutting step, treat as line marking
        
        # Check if at line marking positions
        first_line_y = PAPER_OFFSET_Y + self.main_app.current_program.high - self.main_app.current_program.top_padding
        last_line_y = PAPER_OFFSET_Y + self.main_app.current_program.bottom_padding  # Last line above bottom edge
        
        if first_line_y >= y >= last_line_y:
            # Calculate which line this might be based on actual position
            actual_lines = self.main_app.current_program.number_of_lines  
            if actual_lines > 1:
                line_spacing = (first_line_y - last_line_y) / (actual_lines - 1)
                line_index = round((first_line_y - y) / line_spacing) + 1
                if 1 <= line_index <= actual_lines:
                    return {'type': 'line_marking', 'description': f'Line {line_index}/{actual_lines}'}
        
        return {'type': 'moving', 'description': 'Moving/Positioning'}
    
    def update_tool_status_from_step(self, step_description):
        """Update tool status indicators based on step description"""
        if not step_description:
            return
        
        step_desc = step_description.lower()
        
        # Handle move operations - ensure tools are UP during movement
        if 'move' in step_desc and ('motor' in step_desc or 'position' in step_desc):
            # During any motor movement, all tools should be UP for safety
            self.ensure_all_tools_up()
            print(f"🔄 Motor movement detected - ensuring all tools are UP for safety")
        
        # Parse tool action steps and update canvas indicators
        # Pattern: "Tool action: Open/Close [tool_name]"
        
        # Line marker tool actions
        if 'line marker' in step_desc:
            if 'open line marker' in step_desc:
                # Line marker opening (going down)
                if 'line_marker' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['line_marker'], 
                                                   text="Line Marker: DOWN", fill='red')
                print("🔴 Line Marker: DOWN (marking)")
                
            elif 'close line marker' in step_desc:
                # Line marker closing (going up)
                if 'line_marker' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['line_marker'], 
                                                   text="Line Marker: UP", fill='green')
                print("🟢 Line Marker: UP (raised)")
        
        # Line cutter tool actions
        elif 'line cutter' in step_desc:
            if 'open line cutter' in step_desc:
                # Line cutter opening (going down)
                if 'line_cutter' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['line_cutter'], 
                                                   text="Line Cutter: DOWN", fill='red')
                print("🔴 Line Cutter: DOWN (cutting)")
                
            elif 'close line cutter' in step_desc:
                # Line cutter closing (going up)
                if 'line_cutter' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['line_cutter'], 
                                                   text="Line Cutter: UP", fill='green')
                print("🟢 Line Cutter: UP (raised)")
        
        # Row marker tool actions
        elif 'row marker' in step_desc:
            if 'open row marker' in step_desc:
                # Row marker opening (going down)
                if 'row_marker' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['row_marker'], 
                                                   text="Row Marker: DOWN", fill='red')
                print("🔴 Row Marker: DOWN (marking)")
                
            elif 'close row marker' in step_desc:
                # Row marker closing (going up)
                if 'row_marker' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['row_marker'], 
                                                   text="Row Marker: UP", fill='green')
                print("🟢 Row Marker: UP (raised)")
        
        # Row cutter tool actions
        elif 'row cutter' in step_desc:
            if 'open row cutter' in step_desc:
                # Row cutter opening (going down)
                if 'row_cutter' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['row_cutter'], 
                                                   text="Row Cutter: DOWN", fill='red')
                print("🔴 Row Cutter: DOWN (cutting)")
                
            elif 'close row cutter' in step_desc:
                # Row cutter closing (going up)
                if 'row_cutter' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['row_cutter'], 
                                                   text="Row Cutter: UP", fill='green')
                print("🟢 Row Cutter: UP (raised)")
        
        print(f"Tool status updated from step: {step_description}")
    
    def ensure_all_tools_up(self):
        """Ensure all tool indicators show UP state during motor movements"""
        # Set all tool indicators to UP state for safety during movement
        if 'line_marker' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['line_marker'], 
                                           text="Line Marker: UP", fill='green')
        
        if 'line_cutter' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['line_cutter'], 
                                           text="Line Cutter: UP", fill='green')
        
        if 'row_marker' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['row_marker'], 
                                           text="Row Marker: UP", fill='green')
        
        if 'row_cutter' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['row_cutter'], 
                                           text="Row Cutter: UP", fill='green')
    

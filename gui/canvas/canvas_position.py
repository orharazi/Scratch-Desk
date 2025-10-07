import tkinter as tk
from mock_hardware import get_current_x, get_current_y, move_x, move_y


class CanvasPosition:
    """Handles position tracking, motor visualization, and movement operations"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.canvas_objects = main_app.canvas_objects
        
        # Motor operation state tracking for independent visualization
        self.motor_operation_mode = "idle"  # "idle", "lines", "rows"
        self.lines_motor_position = 0.0  # Y position for lines operations
        self.rows_motor_position = 0.0   # X position for rows operations
        
        # Position tracking for sensor override
        self._last_hardware_x = 0.0
        self._last_hardware_y = 0.0
        self._last_displayed_hardware_x = 0.0
        self._last_displayed_hardware_y = 0.0
    
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
            "line marker", "line cutter", "move y"
        ]):
            self.set_motor_operation_mode("lines")
        
        # Rows operation keywords
        elif any(keyword in step_desc for keyword in [
            "rows operation", "row marking", "cut right paper edge", "cut left paper edge",
            "row marker", "row cutter", "move x"
        ]):
            self.set_motor_operation_mode("rows")
        
        # Home/idle keywords
        elif any(keyword in step_desc for keyword in [
            "home position", "program complete", "program start"
        ]):
            self.set_motor_operation_mode("idle")
    
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
            # Check for sensor override from the sensor manager
            sensor_manager = getattr(self.main_app, 'canvas_sensors', None)
            if sensor_manager and sensor_manager.sensor_override_active:
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
                        print(f"    Y: {sensor_manager.sensor_position_y:.1f} → {current_hardware_y:.1f} (updated)")
                        print(f"    X: {sensor_manager.sensor_position_x:.1f} (preserved from sensor trigger)")
                        
                        # Update Y to hardware position but keep X from sensor
                        sensor_manager.sensor_position_y = current_hardware_y
                        # DO NOT UPDATE sensor_position_x - keep it at sensor trigger position
                        
                        self._last_displayed_hardware_x = current_hardware_x
                        self._last_displayed_hardware_y = current_hardware_y
                        # Update display with new positions
                        sensor_manager.update_sensor_position_display()
                        return
                        
                    elif self.motor_operation_mode == "rows" and x_change > 0.1:
                        # X hardware moved during rows mode - update sensor X position but PRESERVE Y sensor position
                        print(f"🔄 HARDWARE X MOVED during rows mode:")
                        print(f"    X: {sensor_manager.sensor_position_x:.1f} → {current_hardware_x:.1f} (updated)")
                        print(f"    Y: {sensor_manager.sensor_position_y:.1f} (preserved from sensor trigger)")
                        
                        # Update X to hardware position but keep Y from sensor
                        sensor_manager.sensor_position_x = current_hardware_x
                        # DO NOT UPDATE sensor_position_y - keep it at sensor trigger position
                        
                        self._last_displayed_hardware_x = current_hardware_x
                        self._last_displayed_hardware_y = current_hardware_y
                        # Update display with new positions
                        sensor_manager.update_sensor_position_display()
                        return
                
                # No significant hardware movement - maintain current sensor override
                sensor_manager.update_sensor_position_display()
                return
            
            # Get current position from hardware
            hardware_x = get_current_x()
            hardware_y = get_current_y()
            
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
                                 workspace_left + 50, motor_y_canvas - 15)
                
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
            
        except Exception as e:
            print(f"Error updating position display: {e}")
    
    def _update_position_indicators(self, canvas_x, canvas_y, current_x, current_y):
        """Update position indicators on canvas"""
        # Update intersection point
        if 'motor_intersection' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['motor_intersection'],
                                       canvas_x - 4, canvas_y - 4,
                                       canvas_x + 4, canvas_y + 4)
        
        # Determine operation context for visual feedback
        self.update_operation_context_display(canvas_x, canvas_y, current_x, current_y)
    
    def update_operation_context_display(self, canvas_x, canvas_y, current_x, current_y):
        """Update operation context display based on current position"""
        if not self.main_app.current_program:
            return
        
        # Determine what operation context we're in
        context = self.determine_operation_context(current_x, current_y)
        
        # Create or update context indicator
        if 'operation_context' not in self.canvas_objects:
            self.canvas_objects['operation_context'] = self.main_app.canvas.create_text(
                canvas_x, canvas_y - 20,
                text="", font=('Arial', 10, 'bold'), tags="position_indicators"
            )
        
        # Update context display
        if context['type'] == 'line_marking':
            color = '#FF8800'  # Orange for line marking
            text = f"📏 Line {context['line_number']} Marking"
        elif context['type'] == 'cutting':
            color = '#AA00AA'  # Magenta for cutting
            text = f"✂️ {context['cut_type']} Cut"
        else:
            color = '#888888'  # Gray for idle/moving
            text = "🔧 Moving/Idle"
        
        self.main_app.canvas.itemconfig(self.canvas_objects['operation_context'],
                               text=text, fill=color)
        self.main_app.canvas.coords(self.canvas_objects['operation_context'],
                           canvas_x, canvas_y - 20)
        
        # Add position circle indicator with context-based color
        if 'position_circle' not in self.canvas_objects:
            self.canvas_objects['position_circle'] = self.main_app.canvas.create_oval(
                canvas_x - 8, canvas_y - 8, canvas_x + 8, canvas_y + 8,
                outline=color, width=3, dash=(4, 4), tags="position_indicators"
            )
        else:
            self.main_app.canvas.itemconfig(self.canvas_objects['position_circle'],
                                   outline=color)
            self.main_app.canvas.coords(self.canvas_objects['position_circle'],
                               canvas_x - 8, canvas_y - 8, canvas_x + 8, canvas_y + 8)
        
        # Add position coordinates text
        if 'position_coords' not in self.canvas_objects:
            self.canvas_objects['position_coords'] = self.main_app.canvas.create_text(
                canvas_x, canvas_y + 25,
                text=f"({current_x:.1f}, {current_y:.1f})",
                font=('Arial', 8, 'bold'), fill=color, tags="position_indicators"
            )
        else:
            self.main_app.canvas.itemconfig(self.canvas_objects['position_coords'],
                                   text=f"({current_x:.1f}, {current_y:.1f})", fill=color)
            self.main_app.canvas.coords(self.canvas_objects['position_coords'],
                               canvas_x, canvas_y + 25)
    
    def determine_operation_context(self, x, y):
        """Determine what operation context we're in based on position"""
        if not self.main_app.current_program:
            return {'type': 'idle'}
        
        p = self.main_app.current_program
        
        # Paper boundaries
        paper_left = 15.0
        paper_right = paper_left + (p.width * p.repeat_rows)
        paper_bottom = 15.0  
        paper_top = paper_bottom + (p.high * p.repeat_lines)
        
        # Check if we're within paper boundaries
        if paper_left <= x <= paper_right and paper_bottom <= y <= paper_top:
            # We're inside the paper area
            
            # Check if we're near a line position (with some tolerance)
            tolerance = 1.0  # cm
            
            # Calculate all line positions across repeated sections
            for section_num in range(p.repeat_lines):
                section_start_y = paper_bottom + (p.repeat_lines - section_num) * p.high
                section_end_y = paper_bottom + (p.repeat_lines - section_num - 1) * p.high
                
                first_line_y = section_start_y - p.top_padding
                last_line_y = section_end_y + p.bottom_padding
                
                if p.number_of_lines > 1:
                    line_spacing = (first_line_y - last_line_y) / (p.number_of_lines - 1)
                else:
                    line_spacing = 0
                
                for line_in_section in range(p.number_of_lines):
                    line_y = first_line_y - (line_in_section * line_spacing)
                    
                    if abs(y - line_y) <= tolerance:
                        overall_line_num = section_num * p.number_of_lines + line_in_section + 1
                        return {
                            'type': 'line_marking',
                            'line_number': overall_line_num,
                            'section': section_num + 1
                        }
            
            # Check if we're near cutting positions
            if abs(y - paper_top) <= tolerance:
                return {'type': 'cutting', 'cut_type': 'Top'}
            elif abs(y - paper_bottom) <= tolerance:
                return {'type': 'cutting', 'cut_type': 'Bottom'}
            elif abs(x - paper_left) <= tolerance:
                return {'type': 'cutting', 'cut_type': 'Left'}
            elif abs(x - paper_right) <= tolerance:
                return {'type': 'cutting', 'cut_type': 'Right'}
        
        return {'type': 'idle'}
import tkinter as tk
import re
import json

# Load settings
def load_settings():
    try:
        with open('config/settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

settings = load_settings()
sensor_timeout_settings = settings.get("sensor_timeouts", {})


class CanvasSensors:
    """Handles sensor visualization, triggers, and position tracking"""

    def __init__(self, main_app, canvas_manager):
        self.main_app = main_app
        self.canvas_manager = canvas_manager
        # Access hardware through canvas_manager
        self.hardware = canvas_manager.hardware
        self.canvas_objects = main_app.canvas_objects
    
    def trigger_sensor_visualization(self, sensor_type):
        """Highlight sensor trigger and move pointer to sensor position with independent motor display"""
        if not hasattr(self.main_app, 'current_program') or not self.main_app.current_program:
            return
        
        # Clear any existing sensor override first to prevent conflicts
        if self.canvas_manager.sensor_override_active:
            print(f"🔄 CLEARING previous sensor override for new sensor: {sensor_type}")
            self.clear_sensor_override()
        
        program = self.main_app.current_program
        
        # Calculate sensor positions from settings
        hardware_limits = self.main_app.settings.get("hardware_limits", {})
        PAPER_OFFSET_X = hardware_limits.get("paper_start_x", 15.0)
        PAPER_OFFSET_Y = PAPER_OFFSET_X  # Use same value for Y start
        
        # Store current hardware positions
        current_x = get_current_x()
        current_y = get_current_y()
        
        print(f"🎯 SENSOR TRIGGER: {sensor_type}")
        current_hardware_x = get_current_x()
        current_hardware_y = get_current_y()
        
        if sensor_type == 'x_left':
            sensor_x = PAPER_OFFSET_X  # Left edge at paper offset (15.0)
            self.canvas_manager.sensor_position_x = sensor_x
            self.canvas_manager.sensor_position_y = current_y  # PRESERVE current Y position
            print(f"🔴 X_LEFT SENSOR TRIGGERED: Setting sensor_position_x = {sensor_x:.1f} (left paper edge)")
            # Highlight left sensor
            if 'x_left_sensor' in self.canvas_objects:
                self.main_app.canvas.itemconfig(self.canvas_objects['x_left_sensor'], 
                                               fill='red', outline='darkred', width=3)
            # Move pointer to left edge
            self.animate_pointer_to_sensor('x', sensor_x)
            
        elif sensor_type == 'x_right':
            # Calculate ACTUAL width with repeats
            actual_width = program.width * program.repeat_rows
            sensor_x = PAPER_OFFSET_X + actual_width  # Right edge at paper offset + ACTUAL width
            self.canvas_manager.sensor_position_x = sensor_x
            self.canvas_manager.sensor_position_y = current_y  # PRESERVE current Y position
            print(f"🔴 X_RIGHT SENSOR TRIGGERED: Setting sensor_position_x = {sensor_x:.1f} (right paper edge, actual_width={actual_width})")
            # Highlight right sensor
            if 'x_right_sensor' in self.canvas_objects:
                self.main_app.canvas.itemconfig(self.canvas_objects['x_right_sensor'],
                                               fill='red', outline='darkred', width=3)
            # Move pointer to right edge
            self.animate_pointer_to_sensor('x', sensor_x)

        elif sensor_type == 'y_top':
            # Y_TOP sensor always triggers at the actual sensor position on paper
            # Calculate ACTUAL height with repeats
            actual_height = program.high * program.repeat_lines
            sensor_y = PAPER_OFFSET_Y + actual_height  # Top edge of ACTUAL paper
            self.canvas_manager.sensor_position_x = current_x
            self.canvas_manager.sensor_position_y = sensor_y
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
            self.canvas_manager.sensor_position_x = current_x
            self.canvas_manager.sensor_position_y = sensor_y
            print(f"🔵 Y_BOTTOM SENSOR TRIGGERED: Pointer moves to actual sensor position ({current_x:.1f}, {sensor_y:.1f})")
                
            # Highlight bottom sensor
            if 'y_bottom_sensor' in self.canvas_objects:
                self.main_app.canvas.itemconfig(self.canvas_objects['y_bottom_sensor'],
                                               fill='red', outline='darkred', width=3)
            # Move pointer to actual sensor position
            self.animate_pointer_to_sensor('y', sensor_y)
        
        # Set sensor override to prevent position updates from moving pointer
        self.canvas_manager.sensor_override_active = True
        print(f"🔒 SENSOR OVERRIDE ACTIVATED: Pointer locked at ({self.canvas_manager.sensor_position_x:.1f}, {self.canvas_manager.sensor_position_y:.1f})")
        
        # Initialize hardware position tracking for move detection
        self.canvas_manager._last_displayed_hardware_x = get_current_x()
        self.canvas_manager._last_displayed_hardware_y = get_current_y()
        
        # Clear sensor override timer - extend for rows operations to keep pointer at sensor positions
        # During rows operations, extend timer to prevent pointer from returning to 0 too quickly
        timeout_ms = sensor_timeout_settings.get("sensor_override_timeout_rows", 3000) if self.canvas_manager.motor_operation_mode == "rows" else sensor_timeout_settings.get("sensor_override_timeout_lines", 1000)
        
        if self.canvas_manager.sensor_override_timer:
            self.main_app.root.after_cancel(self.canvas_manager.sensor_override_timer)
        self.canvas_manager.sensor_override_timer = self.main_app.root.after(timeout_ms, self.clear_sensor_override)
        
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
        if self.canvas_manager.motor_operation_mode == "lines":
            # During lines: X motor line at 0, Y motor line at actual position
            motor_line_x = 0.0
            motor_line_y = pointer_y
            x_label_text = "X=0.0cm (HOLD)"
            x_label_color = "gray"
            y_label_text = f"Y={pointer_y:.1f}cm (SENSOR)" if axis == 'y' else f"Y={pointer_y:.1f}cm (ACTIVE)"
            y_label_color = "blue"
            
        elif self.canvas_manager.motor_operation_mode == "rows":
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
        pointer_x = self.canvas_manager.sensor_position_x
        pointer_y = self.canvas_manager.sensor_position_y
        
        print(f"🎯 POINTER DISPLAY: sensor override active, showing pointer at ({pointer_x:.1f}, {pointer_y:.1f})")
        
        # Motor lines display based on operation mode (independent motor behavior)
        if self.canvas_manager.motor_operation_mode == "lines":
            # During lines: X motor line at 0, Y motor line follows sensor Y position
            motor_line_x = 0.0
            motor_line_y = pointer_y
            x_label_text = "X=0.0cm (HOLD)"
            x_label_color = "gray"
            y_label_text = f"Y={pointer_y:.1f}cm (SENSOR)"
            y_label_color = "blue"
            
        elif self.canvas_manager.motor_operation_mode == "rows":
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
        """Clear sensor override and resume normal position tracking"""
        self.canvas_manager.sensor_override_active = False
        print("🔓 SENSOR OVERRIDE CLEARED: Position tracking resumed")
        
        # Cancel any pending timer
        if self.canvas_manager.sensor_override_timer:
            self.main_app.root.after_cancel(self.canvas_manager.sensor_override_timer)
            self.canvas_manager.sensor_override_timer = None
        
        # Reset sensor highlights immediately
        self.reset_sensor_highlights()
    
    def smart_sensor_override_clear(self, step_description):
        """Intelligently clear sensor override based on operation context"""
        if not self.canvas_manager.sensor_override_active:
            return
            
        step_desc = step_description.lower() if step_description else ""
        
        # Don't clear during rows operations that depend on sensor positioning
        if any(keyword in step_desc for keyword in [
            "move to rightmost page", "move to page", "rows operation", "row marking",
            "cut first row", "cut last row", "mark row", "right to left"
        ]):
            # Extend sensor override time for rows operations  
            timeout_ms = sensor_timeout_settings.get("sensor_override_timeout_rows", 3000)
            if self.canvas_manager.sensor_override_timer:
                self.main_app.root.after_cancel(self.canvas_manager.sensor_override_timer)
            self.canvas_manager.sensor_override_timer = self.main_app.root.after(timeout_ms, self.clear_sensor_override)
            print(f"🔒 SENSOR OVERRIDE EXTENDED for rows operation: {step_description}")
            return
        
        # Clear immediately for lines operations or other non-sensor dependent operations
        if any(keyword in step_desc for keyword in [
            "lines operation", "line marking", "cut top edge", "cut bottom edge", 
            "mark line", "lines complete", "home position"
        ]):
            self.clear_sensor_override()
            print(f"🔓 SENSOR OVERRIDE CLEARED for operation: {step_description}")
    
    def reset_sensor_highlights(self):
        """Reset all sensor indicators to default colors"""
        # Reset X sensor colors
        if 'x_left_sensor' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['x_left_sensor'],
                                           fill='orange', outline='darkorange', width=2)
        if 'x_right_sensor' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['x_right_sensor'],
                                           fill='orange', outline='darkorange', width=2)
        
        # Reset Y sensor colors
        if 'y_bottom_sensor' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['y_bottom_sensor'],
                                           fill='green', outline='darkgreen', width=2)
        if 'y_top_sensor' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['y_top_sensor'],
                                           fill='green', outline='darkgreen', width=2)
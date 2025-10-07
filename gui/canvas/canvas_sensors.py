import tkinter as tk
from mock_hardware import get_current_x, get_current_y


class CanvasSensors:
    """Handles sensor visualization, triggers, and position management"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.canvas_objects = main_app.canvas_objects
        
        # Sensor trigger state tracking
        self.sensor_override_active = False  # True when sensor position should be maintained
        self.sensor_override_timer = None    # Timer to clear sensor override
        self.sensor_position_x = 0.0         # Store sensor triggered X position
        self.sensor_position_y = 0.0         # Store sensor triggered Y position
    
    def create_sensor_indicators(self, sim_settings):
        """Create sensor indicators on the canvas"""
        max_x_cm = sim_settings.get("max_display_x", 100)
        max_y_cm = sim_settings.get("max_display_y", 80)
        
        # Sensor positions (in cm)
        x_left_pos = 20  # Left X sensor
        x_right_pos = 80  # Right X sensor
        y_top_pos = 60   # Top Y sensor  
        y_bottom_pos = 20  # Bottom Y sensor
        
        # Convert to canvas coordinates
        x_left_canvas = self.main_app.offset_x + x_left_pos * self.main_app.scale_x
        x_right_canvas = self.main_app.offset_x + x_right_pos * self.main_app.scale_x
        y_top_canvas = self.main_app.offset_y + (max_y_cm - y_top_pos) * self.main_app.scale_y
        y_bottom_canvas = self.main_app.offset_y + (max_y_cm - y_bottom_pos) * self.main_app.scale_y
        
        # X sensors (vertical lines)
        self.canvas_objects['x_left_sensor'] = self.main_app.canvas.create_line(
            x_left_canvas, self.main_app.offset_y,
            x_left_canvas, self.main_app.canvas_height - self.main_app.offset_y,
            fill='orange', width=4, dash=(3, 3), tags="sensors"
        )
        
        self.canvas_objects['x_right_sensor'] = self.main_app.canvas.create_line(
            x_right_canvas, self.main_app.offset_y,
            x_right_canvas, self.main_app.canvas_height - self.main_app.offset_y,
            fill='orange', width=4, dash=(3, 3), tags="sensors"
        )
        
        # Y sensors (horizontal lines)
        self.canvas_objects['y_top_sensor'] = self.main_app.canvas.create_line(
            self.main_app.offset_x, y_top_canvas,
            self.main_app.canvas_width - self.main_app.offset_x, y_top_canvas,
            fill='cyan', width=4, dash=(3, 3), tags="sensors"
        )
        
        self.canvas_objects['y_bottom_sensor'] = self.main_app.canvas.create_line(
            self.main_app.offset_x, y_bottom_canvas,
            self.main_app.canvas_width - self.main_app.offset_x, y_bottom_canvas,
            fill='cyan', width=4, dash=(3, 3), tags="sensors"
        )
        
        # Sensor labels
        self.main_app.canvas.create_text(x_left_canvas - 15, self.main_app.offset_y + 20, 
                                        text="X LEFT", font=('Arial', 8, 'bold'), 
                                        fill='orange', tags="sensors")
        
        self.main_app.canvas.create_text(x_right_canvas + 15, self.main_app.offset_y + 20, 
                                        text="X RIGHT", font=('Arial', 8, 'bold'), 
                                        fill='orange', tags="sensors")
        
        self.main_app.canvas.create_text(self.main_app.offset_x + 30, y_top_canvas - 10, 
                                        text="Y TOP", font=('Arial', 8, 'bold'), 
                                        fill='cyan', tags="sensors")
        
        self.main_app.canvas.create_text(self.main_app.offset_x + 30, y_bottom_canvas + 15, 
                                        text="Y BOTTOM", font=('Arial', 8, 'bold'), 
                                        fill='cyan', tags="sensors")
    
    def trigger_sensor_visualization(self, sensor_type):
        """Trigger sensor visualization with enhanced position tracking"""
        print(f"🎯 SENSOR TRIGGER: {sensor_type}")
        
        # Get current hardware positions
        current_hardware_x = get_current_x()
        current_hardware_y = get_current_y()
        
        # CRITICAL: Store the CURRENT position when sensor is triggered
        # This preserves the exact position at the moment of sensor activation
        if sensor_type in ['x_left', 'x_right']:
            # X sensor triggered - store current Y position but update X to sensor position
            self.sensor_position_y = current_hardware_y  # PRESERVE current Y position
            if sensor_type == 'x_left':
                self.sensor_position_x = 20.0  # X LEFT sensor position
            else:  # x_right
                self.sensor_position_x = 80.0  # X RIGHT sensor position
        
        elif sensor_type in ['y_top', 'y_bottom']:
            # Y sensor triggered - store current X position but update Y to sensor position  
            self.sensor_position_x = current_hardware_x  # PRESERVE current X position
            if sensor_type == 'y_top':
                self.sensor_position_y = 60.0  # Y TOP sensor position
            else:  # y_bottom
                self.sensor_position_y = 20.0  # Y BOTTOM sensor position
        
        print(f"📍 SENSOR POSITION SET: ({self.sensor_position_x:.1f}, {self.sensor_position_y:.1f})")
        print(f"🏭 HARDWARE POSITION: ({current_hardware_x:.1f}, {current_hardware_y:.1f})")
        
        # Activate sensor override mode
        self.sensor_override_active = True
        
        # Visual feedback
        self.highlight_triggered_sensor(sensor_type)
        
        # Update display to show sensor position
        self.update_sensor_position_display()
        
        # Clear sensor highlight after delay
        if self.sensor_override_timer:
            self.main_app.root.after_cancel(self.sensor_override_timer)
        self.sensor_override_timer = self.main_app.root.after(1000, self.reset_sensor_highlights)
    
    def highlight_triggered_sensor(self, sensor_type):
        """Highlight the triggered sensor"""
        sensor_colors = {
            'x_left': 'red',
            'x_right': 'red',
            'y_top': 'blue', 
            'y_bottom': 'blue'
        }
        
        color = sensor_colors.get(sensor_type, 'yellow')
        sensor_key = f'{sensor_type}_sensor'
        
        if sensor_key in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects[sensor_key], 
                                           fill=color, width=6)
    
    def animate_pointer_to_sensor(self, axis, position):
        """Animate pointer moving to sensor position with enhanced tracking"""
        max_y_cm = self.main_app.settings.get("simulation", {}).get("max_display_y", 80)
        
        # Calculate target canvas coordinates
        if axis == 'x':
            target_x_canvas = self.main_app.offset_x + position * self.main_app.scale_x
            target_y_canvas = self.main_app.offset_y + (max_y_cm - get_current_y()) * self.main_app.scale_y
        else:  # y axis
            target_x_canvas = self.main_app.offset_x + get_current_x() * self.main_app.scale_x
            target_y_canvas = self.main_app.offset_y + (max_y_cm - position) * self.main_app.scale_y
        
        # Get current pointer position
        if 'motor_intersection' in self.canvas_objects:
            coords = self.main_app.canvas.coords(self.canvas_objects['motor_intersection'])
            current_x_canvas = (coords[0] + coords[2]) / 2
            current_y_canvas = (coords[1] + coords[3]) / 2
            
            # Animate to sensor position
            steps = 10
            dx = (target_x_canvas - current_x_canvas) / steps
            dy = (target_y_canvas - current_y_canvas) / steps
            
            def animate_step(step):
                if step < steps:
                    new_x = current_x_canvas + dx * step
                    new_y = current_y_canvas + dy * step
                    
                    # Update intersection point
                    self.main_app.canvas.coords(self.canvas_objects['motor_intersection'],
                                               new_x - 4, new_y - 4, new_x + 4, new_y + 4)
                    
                    # Continue animation
                    self.main_app.root.after(30, lambda: animate_step(step + 1))
                else:
                    # Animation complete - final position
                    self.main_app.canvas.coords(self.canvas_objects['motor_intersection'],
                                               target_x_canvas - 4, target_y_canvas - 4,
                                               target_x_canvas + 4, target_y_canvas + 4)
            
            animate_step(0)
    
    def update_sensor_position_display(self):
        """Update position display with sensor-triggered coordinates"""
        if not self.sensor_override_active:
            return
            
        # Show sensor position instead of hardware position
        max_y_cm = self.main_app.settings.get("simulation", {}).get("max_display_y", 80)
        
        # Update position label
        if hasattr(self.main_app, 'position_label'):
            self.main_app.position_label.config(
                text=f"Position: X={self.sensor_position_x:.1f}, Y={self.sensor_position_y:.1f} (SENSOR)")
        
        # Update visual indicators using sensor position
        sensor_x_canvas = self.main_app.offset_x + self.sensor_position_x * self.main_app.scale_x
        sensor_y_canvas = self.main_app.offset_y + (max_y_cm - self.sensor_position_y) * self.main_app.scale_y
        
        # Get workspace boundaries
        workspace_left = self.main_app.offset_x
        workspace_right = self.main_app.canvas_width - self.main_app.offset_x
        workspace_top = self.main_app.offset_y
        workspace_bottom = self.main_app.canvas_height - self.main_app.offset_y
        
        # Update motor lines to show sensor position
        if 'x_motor_line' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['x_motor_line'],
                                       sensor_x_canvas, workspace_top,
                                       sensor_x_canvas, workspace_bottom)
        
        if 'y_motor_line' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['y_motor_line'],
                                       workspace_left, sensor_y_canvas,
                                       workspace_right, sensor_y_canvas)
        
        if 'motor_intersection' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['motor_intersection'],
                                       sensor_x_canvas - 4, sensor_y_canvas - 4,
                                       sensor_x_canvas + 4, sensor_y_canvas + 4)
        
        # Update motor labels
        if 'x_motor_label' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['x_motor_label'],
                                       sensor_x_canvas + 15, workspace_top + 15)
            self.main_app.canvas.itemconfig(self.canvas_objects['x_motor_label'],
                                           text=f"X={self.sensor_position_x:.1f}cm (SENSOR)", fill='red')
        
        if 'y_motor_label' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['y_motor_label'],
                                       workspace_left + 50, sensor_y_canvas - 15)
            self.main_app.canvas.itemconfig(self.canvas_objects['y_motor_label'],
                                           text=f"Y={self.sensor_position_y:.1f}cm (SENSOR)", fill='blue')
    
    def clear_sensor_override(self):
        """Clear sensor override and return to hardware position tracking"""
        print("🔓 CLEARING SENSOR OVERRIDE - returning to hardware position")
        self.sensor_override_active = False
        if self.sensor_override_timer:
            self.main_app.root.after_cancel(self.sensor_override_timer)
            self.sensor_override_timer = None
    
    def smart_sensor_override_clear(self, step_description):
        """Intelligently clear sensor override based on step context"""
        if not self.sensor_override_active:
            return
        
        step_desc = step_description.lower()
        
        # Clear sensor override when starting to move away from sensor
        if 'move' in step_desc:
            print(f"🔄 MOVE DETECTED during sensor override: {step_description}")
            # Clear sensor override to allow hardware position tracking
            self.clear_sensor_override()
    
    def reset_sensor_highlights(self):
        """Reset sensor indicators to normal colors"""
        # Reset X sensors to orange
        for sensor in ['x_left_sensor', 'x_right_sensor']:
            if sensor in self.canvas_objects:
                self.main_app.canvas.itemconfig(self.canvas_objects[sensor], 
                                               fill='orange', width=4)
        
        # Reset Y sensors to cyan
        for sensor in ['y_top_sensor', 'y_bottom_sensor']:
            if sensor in self.canvas_objects:
                self.main_app.canvas.itemconfig(self.canvas_objects[sensor], 
                                               fill='cyan', width=4)
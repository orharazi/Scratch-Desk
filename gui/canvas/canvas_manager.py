import tkinter as tk
import re
from mock_hardware import get_current_x, get_current_y, move_x, move_y, get_hardware_status

from .canvas_setup import CanvasSetup
from .canvas_sensors import CanvasSensors
from .canvas_operations import CanvasOperations
from .canvas_position import CanvasPosition
from .canvas_tools import CanvasTools


class CanvasManager:
    """Main canvas manager that coordinates all canvas modules with original functionality"""
    
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
        
        # Initialize all canvas modules with shared state
        self.canvas_sensors = CanvasSensors(main_app, self)
        self.canvas_setup = CanvasSetup(main_app, self)
        self.canvas_operations = CanvasOperations(main_app, self)
        self.canvas_position = CanvasPosition(main_app, self)
        self.canvas_tools = CanvasTools(main_app, self)
        
        # Store references to modules in main app for easy access
        main_app.canvas_setup = self.canvas_setup
        main_app.canvas_sensors = self.canvas_sensors
        main_app.canvas_operations = self.canvas_operations
        main_app.canvas_position = self.canvas_position
        main_app.canvas_tools = self.canvas_tools
    
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
    
    # === SETUP METHODS ===
    def setup_canvas(self):
        """Set up the canvas with all visual elements"""
        return self.canvas_setup.setup_canvas()
    
    # === SENSOR METHODS ===
    def trigger_sensor_visualization(self, sensor_type):
        """Trigger sensor visualization with original logic"""
        return self.canvas_sensors.trigger_sensor_visualization(sensor_type)
    
    def animate_pointer_to_sensor(self, axis, position):
        """Animate pointer to sensor position"""
        return self.canvas_sensors.animate_pointer_to_sensor(axis, position)
    
    def clear_sensor_override(self):
        """Clear sensor override"""
        return self.canvas_sensors.clear_sensor_override()
    
    def smart_sensor_override_clear(self, step_description):
        """Smart sensor override clearing"""
        return self.canvas_sensors.smart_sensor_override_clear(step_description)
    
    def reset_sensor_highlights(self):
        """Reset sensor highlights"""
        return self.canvas_sensors.reset_sensor_highlights()
    
    def update_sensor_position_display(self):
        """Update display while maintaining sensor trigger position"""
        return self.canvas_sensors.update_sensor_position_display()
    
    # === OPERATION METHODS ===
    def update_canvas_paper_area(self):
        """Update canvas paper area"""
        return self.canvas_operations.update_canvas_paper_area()
    
    def draw_work_lines(self, program, paper_x, paper_y, max_y_cm):
        """Draw work lines"""
        return self.canvas_operations.draw_work_lines(program, paper_x, paper_y, max_y_cm)
    
    def initialize_operation_states(self, program):
        """Initialize operation states"""
        return self.canvas_operations.initialize_operation_states(program)
    
    def update_operation_state(self, operation_type, operation_id, new_state):
        """Update operation state"""
        return self.canvas_operations.update_operation_state(operation_type, operation_id, new_state)
    
    def track_operation_from_step(self, step_description):
        """Track operation from step"""
        return self.canvas_operations.track_operation_from_step(step_description)
    
    def refresh_work_lines_colors(self):
        """Refresh work line colors"""
        return self.canvas_operations.refresh_work_lines_colors()
    
    def draw_enhanced_legend(self):
        """Draw enhanced legend"""
        return self.canvas_operations.draw_enhanced_legend()
    
    def test_color_changes(self):
        """Test color changes"""
        return self.canvas_operations.test_color_changes()
    
    def add_debug_keybindings(self):
        """Add debug keybindings"""
        return self.canvas_operations.add_debug_keybindings()
    
    # === POSITION METHODS ===
    def move_tool_to_first_line(self):
        """Move tool to first line"""
        return self.canvas_position.move_tool_to_first_line()
    
    def update_position_display(self):
        """Update position display with original logic"""
        return self.canvas_position.update_position_display()
    
    def determine_operation_context(self, x, y):
        """Determine operation context"""
        return self.canvas_position.determine_operation_context(x, y)
    
    # === TOOL METHODS ===
    def update_tool_status_from_step(self, step_description):
        """Update tool status from step"""
        return self.canvas_tools.update_tool_status_from_step(step_description)
    
    def ensure_all_tools_up(self):
        """Ensure all tools are up"""
        return self.canvas_tools.ensure_all_tools_up()
    
    def refresh_tool_status_display(self):
        """Refresh tool status display"""
        return self.canvas_tools.refresh_tool_status_display()
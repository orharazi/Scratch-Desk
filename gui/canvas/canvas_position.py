import tkinter as tk
import re
import json
from core.logger import get_logger

# Load settings
def load_settings():
    try:
        with open('config/settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

settings = load_settings()
validation_settings = settings.get("validation", {})


class CanvasPosition:
    """Handles position tracking, motor visualization, and movement operations"""

    def __init__(self, main_app, canvas_manager):
        self.main_app = main_app
        self.canvas_manager = canvas_manager
        self.logger = get_logger()
        # Access hardware through canvas_manager
        self.hardware = canvas_manager.hardware
        self.canvas_objects = main_app.canvas_objects
    
    def move_tool_to_first_line(self):
        """Move tool to first line of work area"""
        if not hasattr(self.main_app, 'current_program') or not self.main_app.current_program:
            self.logger.info("No program loaded - cannot move to first line", category="gui")
            return
        
        program = self.main_app.current_program
        
        # Paper coordinates from settings
        hardware_limits = self.main_app.settings.get("hardware_limits", {})
        PAPER_OFFSET_X = hardware_limits.get("paper_start_x", 15.0)
        PAPER_OFFSET_Y = hardware_limits.get("paper_start_y", 15.0)

        # Move to first line position
        first_line_x = PAPER_OFFSET_X + (program.width / 2)  # Center of paper width
        first_line_y = PAPER_OFFSET_Y + program.top_margin  # First line position

        self.logger.debug(f"Moving tool to first line at ({first_line_x:.1f}, {first_line_y:.1f})", category="gui")
        self.hardware.move_x(first_line_x)
        self.hardware.move_y(first_line_y)
        
        # Update canvas display
        self.update_position_display()
    
    def update_position_display(self):
        """Update position display based on motor operation mode and sensor state"""
        self.logger.debug(f" update_position_display() called", category="gui")
        self.logger.debug(f" sensor_override_active: {self.canvas_manager.sensor_override_active}", category="gui")
        self.logger.debug(f" motor_operation_mode: {self.canvas_manager.motor_operation_mode}", category="gui")

        # Check if sensor override is active - if so, use sensor display logic
        if self.canvas_manager.sensor_override_active:
            self.logger.debug(f" Sensor override active - using sensor display logic instead", category="gui")
            return self.canvas_manager.canvas_sensors.update_sensor_position_display()

        # Get current hardware positions
        current_x = self.hardware.get_current_x()
        current_y = self.hardware.get_current_y()
        self.logger.debug(f" Hardware position: X={current_x:.1f}, Y={current_y:.1f}", category="gui")

        # Check if position OR mode changed to avoid unnecessary updates
        mode_changed = False
        if hasattr(self.canvas_manager, '_last_displayed_mode'):
            last_mode = self.canvas_manager._last_displayed_mode
            if last_mode != self.canvas_manager.motor_operation_mode:
                mode_changed = True
                self.logger.debug(f" Mode changed: {last_mode} → {self.canvas_manager.motor_operation_mode}", category="gui")

        if (hasattr(self.canvas_manager, '_last_displayed_hardware_x') and
            hasattr(self.canvas_manager, '_last_displayed_hardware_y')):
            last_x = self.canvas_manager._last_displayed_hardware_x
            last_y = self.canvas_manager._last_displayed_hardware_y
            self.logger.debug(f" Last displayed: X={last_x:.1f}, Y={last_y:.1f}", category="gui")
            tolerance = validation_settings.get("tolerance", 0.01)
            if (abs(current_x - last_x) < tolerance and abs(current_y - last_y) < tolerance and not mode_changed):
                self.logger.debug(f" No meaningful position/mode change - skipping update", category="gui")
                return  # No meaningful position or mode change
        else:
            self.logger.debug(f" First position update (no previous position)", category="gui")
        
        # Update last displayed positions and mode
        self.canvas_manager._last_displayed_hardware_x = current_x
        self.canvas_manager._last_displayed_hardware_y = current_y
        self.canvas_manager._last_displayed_mode = self.canvas_manager.motor_operation_mode

        max_y_cm = self.main_app.settings.get("simulation", {}).get("max_display_y", 80)
        
        # Determine display positions based on operation mode
        if self.canvas_manager.motor_operation_mode == "lines":
            # During lines operations: X motor at 0, Y motor shows actual position
            display_x = 0.0
            display_y = current_y
            x_label_text = "\u05e2\u05de\u05d5\u05d3\u05d5\u05ea=0.0cm (HOLD)"
            x_label_color = "gray"
            y_label_text = f"\u05e9\u05d5\u05e8\u05d5\u05ea={current_y:.1f}cm"
            y_label_color = "blue"

        elif self.canvas_manager.motor_operation_mode == "rows":
            # During rows operations: Y motor at 0, X motor shows actual position
            display_x = current_x
            display_y = 0.0
            x_label_text = f"\u05e2\u05de\u05d5\u05d3\u05d5\u05ea={current_x:.1f}cm"
            x_label_color = "red"
            y_label_text = "\u05e9\u05d5\u05e8\u05d5\u05ea=0.0cm (HOLD)"
            y_label_color = "gray"

        else:
            # Idle mode: Both motors show actual positions
            display_x = current_x
            display_y = current_y
            x_label_text = f"\u05e2\u05de\u05d5\u05d3\u05d5\u05ea={current_x:.1f}cm"
            x_label_color = "red"
            y_label_text = f"\u05e9\u05d5\u05e8\u05d5\u05ea={current_y:.1f}cm"
            y_label_color = "blue"
        
        # Convert to canvas coordinates
        display_x_canvas = self.main_app.offset_x + display_x * self.main_app.scale_x
        display_y_canvas = self.main_app.offset_y + (max_y_cm - display_y) * self.main_app.scale_y
        pointer_x_canvas = self.main_app.offset_x + current_x * self.main_app.scale_x
        pointer_y_canvas = self.main_app.offset_y + (max_y_cm - current_y) * self.main_app.scale_y
        
        # Get workspace boundaries
        workspace_left = self.main_app.offset_x
        workspace_right = self.main_app.canvas_width - self.main_app.offset_x
        workspace_top = self.main_app.offset_y
        workspace_bottom = self.main_app.canvas_height - self.main_app.offset_y
        
        # Update X motor line
        if 'x_motor_line' in self.canvas_objects:
            self.logger.debug(f" Updating X motor line: display_x={display_x:.1f}cm, canvas_x={display_x_canvas:.1f}px", category="gui")
            self.main_app.canvas.coords(self.canvas_objects['x_motor_line'],
                                       display_x_canvas, workspace_top,
                                       display_x_canvas, workspace_bottom)
            self.logger.debug(f" X motor line coords updated", category="gui")
        else:
            self.logger.debug(f" x_motor_line not found in canvas_objects!", category="gui")
        
        # Update Y motor line
        if 'y_motor_line' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['y_motor_line'],
                                       workspace_left, display_y_canvas,
                                       workspace_right, display_y_canvas)
        
        # Update intersection point (pointer) - ALWAYS at actual hardware position
        if 'motor_intersection' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['motor_intersection'],
                                       pointer_x_canvas - 4, pointer_y_canvas - 4,
                                       pointer_x_canvas + 4, pointer_y_canvas + 4)
        
        # Update motor labels (RTL: labels anchored to right side)
        if 'x_motor_label' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['x_motor_label'],
                                       display_x_canvas - 15, workspace_top + 15)
            self.main_app.canvas.itemconfig(self.canvas_objects['x_motor_label'],
                                           text=x_label_text, fill=x_label_color)

        if 'y_motor_label' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['y_motor_label'],
                                       workspace_right - 15, display_y_canvas - 15)
            self.main_app.canvas.itemconfig(self.canvas_objects['y_motor_label'],
                                           text=y_label_text, fill=y_label_color)
    
    def determine_operation_context(self, x, y):
        """Determine what operation is happening based on position"""
        if not hasattr(self.main_app, 'current_program') or not self.main_app.current_program:
            return "idle"
        
        program = self.main_app.current_program
        hardware_limits = self.main_app.settings.get("hardware_limits", {})
        PAPER_OFFSET_X = hardware_limits.get("paper_start_x", 15.0)
        PAPER_OFFSET_Y = hardware_limits.get("paper_start_y", 15.0)

        # Check if within paper boundaries
        paper_left = PAPER_OFFSET_X
        paper_right = PAPER_OFFSET_X + program.width
        paper_bottom = PAPER_OFFSET_Y
        paper_top = PAPER_OFFSET_Y + program.high
        
        if paper_left <= x <= paper_right and paper_bottom <= y <= paper_top:
            # Determine if in line marking area or cutting area
            line_start_y = paper_bottom + program.top_margin
            line_end_y = paper_top - program.bottom_margin
            
            if line_start_y <= y <= line_end_y:
                return "line_marking"
            elif y < line_start_y:
                return "bottom_cutting"
            elif y > line_end_y:
                return "top_cutting"
            else:
                return "paper_area"
        else:
            return "outside_paper"
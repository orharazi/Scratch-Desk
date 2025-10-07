import tkinter as tk
from mock_hardware import get_current_x, get_current_y, move_x, move_y, get_hardware_status


class CanvasSetup:
    """Handles canvas setup, grid drawing, and basic visual elements"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.canvas_objects = main_app.canvas_objects
    
    def setup_canvas(self):
        """Set up the canvas with grid, labels, default elements"""
        # Get simulation settings
        sim_settings = self.main_app.settings.get("simulation", {})
        
        # Clear canvas
        self.main_app.canvas.delete("all")
        self.canvas_objects.clear()
        
        # Draw coordinate grid
        self.draw_coordinate_grid(sim_settings)
        
        # Draw axis labels
        self.draw_axis_labels()
        
        # Draw default paper area
        self.draw_default_paper_area(sim_settings)
        
        # Draw motor position lines
        self.draw_motor_position_lines(sim_settings)
        
        # Create sensor indicators (delegate to sensors module)
        from .canvas_sensors import CanvasSensors
        sensors = CanvasSensors(self.main_app)
        sensors.create_sensor_indicators(sim_settings)
        
        # Draw tool status indicators
        self.draw_tool_status_indicators()
    
    def draw_coordinate_grid(self, sim_settings):
        """Draw coordinate grid on canvas"""
        # Grid settings
        grid_spacing_cm = sim_settings.get("grid_spacing", 5)
        show_grid = sim_settings.get("show_grid", True)
        max_x_cm = sim_settings.get("max_display_x", 100)  
        max_y_cm = sim_settings.get("max_display_y", 80)
        
        if not show_grid:
            return
        
        # Vertical lines (X coordinates)
        for x_cm in range(0, max_x_cm + 1, grid_spacing_cm):
            canvas_x = self.main_app.offset_x + x_cm * self.main_app.scale_x
            self.main_app.canvas.create_line(
                canvas_x, self.main_app.offset_y,
                canvas_x, self.main_app.canvas_height - self.main_app.offset_y,
                fill='lightgray', dash=(2, 4), tags="grid"
            )
            # X labels
            if x_cm % 10 == 0 or x_cm == 0:  # Label every 10cm + origin
                self.main_app.canvas.create_text(
                    canvas_x, self.main_app.canvas_height - self.main_app.offset_y + 15,
                    text=str(x_cm), font=('Arial', 8), fill='gray', tags="grid"
                )
        
        # Horizontal lines (Y coordinates) 
        for y_cm in range(0, max_y_cm + 1, grid_spacing_cm):
            canvas_y = self.main_app.offset_y + (max_y_cm - y_cm) * self.main_app.scale_y
            self.main_app.canvas.create_line(
                self.main_app.offset_x, canvas_y,
                self.main_app.canvas_width - self.main_app.offset_x, canvas_y,
                fill='lightgray', dash=(2, 4), tags="grid"
            )
            # Y labels
            if y_cm % 10 == 0 or y_cm == 0:  # Label every 10cm + origin
                self.main_app.canvas.create_text(
                    self.main_app.offset_x - 15, canvas_y,
                    text=str(y_cm), font=('Arial', 8), fill='gray', tags="grid"
                )
    
    def draw_axis_labels(self):
        """Draw X and Y axis labels"""
        # X-axis label
        self.main_app.canvas.create_text(
            self.main_app.canvas_width // 2, 
            self.main_app.canvas_height - 10,
            text="X (cm)", font=('Arial', 12, 'bold'), fill='black'
        )
        
        # Y-axis label
        self.main_app.canvas.create_text(
            15, self.main_app.canvas_height // 2,
            text="Y (cm)", font=('Arial', 12, 'bold'), fill='black', angle=90
        )
    
    def draw_default_paper_area(self, sim_settings):
        """Draw default paper area placeholder"""
        paper_x = 15  # Default paper position
        paper_y = 15
        paper_width = 50  # Default size
        paper_height = 30
        max_y_cm = sim_settings.get("max_display_y", 80)
        
        # Canvas coordinates
        canvas_x1 = self.main_app.offset_x + paper_x * self.main_app.scale_x
        canvas_y1 = self.main_app.offset_y + (max_y_cm - (paper_y + paper_height)) * self.main_app.scale_y
        canvas_x2 = self.main_app.offset_x + (paper_x + paper_width) * self.main_app.scale_x
        canvas_y2 = self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y
        
        self.canvas_objects['default_paper'] = self.main_app.canvas.create_rectangle(
            canvas_x1, canvas_y1, canvas_x2, canvas_y2,
            outline='darkblue', fill='lightblue', width=2, stipple='gray25', tags="paper_area"
        )
        
        # Label
        self.main_app.canvas.create_text(
            (canvas_x1 + canvas_x2) / 2, (canvas_y1 + canvas_y2) / 2,
            text="Default Paper Area\n(Load CSV for program)", 
            font=('Arial', 10), fill='darkblue', tags="paper_area"
        )
    
    def draw_motor_position_lines(self, sim_settings):
        """Draw motor position indicator lines"""
        max_y_cm = sim_settings.get("max_display_y", 80)
        
        # Get current positions
        current_x = get_current_x()
        current_y = get_current_y()
        
        # Canvas coordinates
        motor_x_canvas = self.main_app.offset_x + current_x * self.main_app.scale_x
        motor_y_canvas = self.main_app.offset_y + (max_y_cm - current_y) * self.main_app.scale_y
        
        workspace_left = self.main_app.offset_x
        workspace_right = self.main_app.canvas_width - self.main_app.offset_x
        workspace_top = self.main_app.offset_y
        workspace_bottom = self.main_app.canvas_height - self.main_app.offset_y
        
        # X motor line (vertical)
        self.canvas_objects['x_motor_line'] = self.main_app.canvas.create_line(
            motor_x_canvas, workspace_top,
            motor_x_canvas, workspace_bottom,
            fill='red', width=2, dash=(5, 3), tags="motor_lines"
        )
        
        # Y motor line (horizontal)
        self.canvas_objects['y_motor_line'] = self.main_app.canvas.create_line(
            workspace_left, motor_y_canvas,
            workspace_right, motor_y_canvas,
            fill='blue', width=2, dash=(5, 3), tags="motor_lines"
        )
        
        # Intersection point
        self.canvas_objects['motor_intersection'] = self.main_app.canvas.create_oval(
            motor_x_canvas - 4, motor_y_canvas - 4,
            motor_x_canvas + 4, motor_y_canvas + 4,
            fill='purple', outline='purple', width=2, tags="motor_lines"
        )
        
        # Position labels
        self.canvas_objects['x_motor_label'] = self.main_app.canvas.create_text(
            motor_x_canvas + 15, workspace_top + 15,
            text=f"X={current_x:.1f}cm", font=('Arial', 9, 'bold'), 
            fill='red', tags="motor_lines"
        )
        
        self.canvas_objects['y_motor_label'] = self.main_app.canvas.create_text(
            workspace_left + 50, motor_y_canvas - 15,
            text=f"Y={current_y:.1f}cm", font=('Arial', 9, 'bold'), 
            fill='blue', tags="motor_lines"
        )
    
    def draw_tool_status_indicators(self):
        """Draw tool status indicators on canvas"""
        # Position for tool status display
        status_x = 20
        status_y = 60
        
        # Tool status title
        self.main_app.canvas.create_text(status_x, status_y - 20, 
                                        text="🔧 TOOL STATUS", 
                                        font=('Arial', 10, 'bold'), fill='darkblue')
        
        # Get current hardware status
        status = get_hardware_status()
        
        # Line Marker status
        marker_status = "DOWN" if status['line_marker'] == 'down' else "UP"
        marker_color = "red" if status['line_marker'] == 'down' else "green"
        self.canvas_objects['line_marker'] = self.main_app.canvas.create_text(
            status_x, status_y, 
            text=f"Line Marker: {marker_status}", fill=marker_color)
        
        # Line Marker Piston status
        piston_status = "UP" if status['line_marker_piston'] == 'up' else "DOWN"
        piston_color = "blue" if status['line_marker_piston'] == 'up' else "red"
        self.canvas_objects['line_marker_piston'] = self.main_app.canvas.create_text(
            status_x, status_y + 20,
            text=f"Line Marker State: {piston_status}", fill=piston_color)
        
        # Line Cutter status
        cutter_status = "DOWN" if status['line_cutter'] == 'down' else "UP"
        cutter_color = "red" if status['line_cutter'] == 'down' else "green"
        self.canvas_objects['line_cutter'] = self.main_app.canvas.create_text(
            status_x, status_y + 40,
            text=f"Line Cutter: {cutter_status}", fill=cutter_color)
        
        # Row Marker status
        marker_status = "DOWN" if status['row_marker'] == 'down' else "UP"
        marker_color = "red" if status['row_marker'] == 'down' else "green"
        self.canvas_objects['row_marker'] = self.main_app.canvas.create_text(
            status_x + 200, status_y,
            text=f"Row Marker: {marker_status}", fill=marker_color)
        
        # Row Marker Limit Switch status
        limit_status = "DOWN" if status['row_marker_limit_switch'] == 'down' else "UP"
        limit_color = "darkred" if status['row_marker_limit_switch'] == 'down' else "darkgreen"
        self.canvas_objects['row_marker_limit_switch'] = self.main_app.canvas.create_text(
            status_x + 200, status_y + 20,
            text=f"Row Marker State: {limit_status}", fill=limit_color)
        
        # Row Cutter status
        cutter_status = "DOWN" if status['row_cutter'] == 'down' else "UP"
        cutter_color = "red" if status['row_cutter'] == 'down' else "green"
        self.canvas_objects['row_cutter'] = self.main_app.canvas.create_text(
            status_x + 200, status_y + 40,
            text=f"Row Cutter: {cutter_status}", fill=cutter_color)
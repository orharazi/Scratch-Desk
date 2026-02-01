import tkinter as tk
from core.logger import get_logger


class CanvasSetup:
    """Handles canvas setup, grid drawing, and basic visual elements"""

    def __init__(self, main_app, canvas_manager):
        self.main_app = main_app
        self.canvas_manager = canvas_manager
        self.canvas_objects = main_app.canvas_objects
        self.logger = get_logger()
        # Access hardware through canvas_manager
        self.hardware = canvas_manager.hardware
    
    def setup_canvas(self):
        """Setup canvas elements for desk simulation using settings"""
        # Check if canvas is ready (center_panel has initialized it)
        if hasattr(self.main_app, 'center_panel') and hasattr(self.main_app.center_panel, '_canvas_initialized'):
            if not self.main_app.center_panel._canvas_initialized:
                self.logger.debug(" setup_canvas() called before canvas initialization - skipping", category="gui")
                return

        # Get settings or use defaults
        sim_settings = self.main_app.settings.get("simulation", {})
        gui_settings = self.main_app.settings.get("gui_settings", {})
        hardware_limits = self.main_app.settings.get("hardware_limits", {})

        # Use the actual canvas dimensions that were set by responsive scaling
        # These values are calculated dynamically based on window size by center_panel
        if not hasattr(self.main_app, 'canvas_width') or self.main_app.canvas_width == 600:
            self.main_app.canvas_width = getattr(self.main_app, 'actual_canvas_width', 900)
            self.main_app.canvas_height = getattr(self.main_app, 'actual_canvas_height', 700)

        # Clear canvas first and reset canvas objects references
        self.main_app.canvas.delete("all")
        self.canvas_objects.clear()  # Clear canvas object references since they were deleted
        
        # Draw workspace boundary - use max display dimensions from settings
        max_x_cm = sim_settings.get("max_display_x", 120)
        max_y_cm = sim_settings.get("max_display_y", 80)

        workspace_width = max_x_cm * self.main_app.scale_x
        workspace_height = max_y_cm * self.main_app.scale_y

        workspace_rect = self.main_app.canvas.create_rectangle(
            self.main_app.offset_x, self.main_app.offset_y,
            self.main_app.offset_x + workspace_width, self.main_app.offset_y + workspace_height,
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
        """Draw axis labels - positioned outside workspace area"""
        # Get actual workspace dimensions
        sim_settings = self.main_app.settings.get("simulation", {})
        max_x_cm = sim_settings.get("max_display_x", 120)
        max_y_cm = sim_settings.get("max_display_y", 80)
        workspace_height = max_y_cm * self.main_app.scale_y

        # X axis label below workspace
        x_label_y = self.main_app.offset_y + workspace_height + 25
        self.main_app.canvas.create_text(
            self.main_app.canvas_width // 2, x_label_y,
            text="X Axis (cm)", font=('Arial', 10, 'bold'), fill='darkblue'
        )

        # Y axis label on left side
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
        current_x = self.hardware.get_current_x()
        current_y = self.hardware.get_current_y()
        
        max_y_cm = sim_settings.get("max_display_y", 80)
        max_x_cm = sim_settings.get("max_display_x", 120)
        
        # Calculate canvas coordinates for motor positions
        motor_x_canvas = self.main_app.offset_x + current_x * self.main_app.scale_x
        motor_y_canvas = self.main_app.offset_y + (max_y_cm - current_y) * self.main_app.scale_y

        # Get workspace boundaries - use calculated dimensions from settings
        workspace_width = max_x_cm * self.main_app.scale_x
        workspace_height = max_y_cm * self.main_app.scale_y
        workspace_left = self.main_app.offset_x
        workspace_right = self.main_app.offset_x + workspace_width
        workspace_top = self.main_app.offset_y
        workspace_bottom = self.main_app.offset_y + workspace_height
        
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
        PAPER_OFFSET_Y = hardware_limits.get("paper_start_y", 15.0)

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

        # Get workspace boundaries - use calculated dimensions from settings
        max_x_cm = sim_settings.get("max_display_x", 120)
        workspace_width = max_x_cm * self.main_app.scale_x
        workspace_height = max_y_cm * self.main_app.scale_y
        workspace_top = self.main_app.offset_y
        workspace_bottom = self.main_app.offset_y + workspace_height
        workspace_left = self.main_app.offset_x
        workspace_right = self.main_app.offset_x + workspace_width
        
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
        """Draw tool status indicators - removed, now in hardware status monitor"""
        # All tool status indicators have been moved to the hardware status monitor panel
        # This keeps the canvas clean and focused on the work visualization
        pass

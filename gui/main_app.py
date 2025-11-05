#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import json

# Import our modules
from core.csv_parser import CSVParser
from core.step_generator import generate_complete_program_steps, get_step_count_summary
from core.execution_engine import ExecutionEngine
from core.mock_hardware import (
    trigger_x_left_sensor, trigger_x_right_sensor,
    trigger_y_top_sensor, trigger_y_bottom_sensor,
    get_current_x, get_current_y, reset_hardware
)

# Import GUI components
from gui.panels.left_panel import LeftPanel
from gui.panels.center_panel import CenterPanel
from gui.panels.right_panel import RightPanel
from gui.panels.hardware_status_panel import HardwareStatusPanel
from gui.canvas.canvas_manager import CanvasManager
from gui.execution.execution_controller import ExecutionController


class ScratchDeskGUI:
    """Main GUI application class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Scratch Desk Control System")
        self.root.geometry("1500x1000")
        self.root.minsize(1400, 950)
        self.root.resizable(True, True)

        # Try to maximize window if possible
        try:
            self.root.state('zoomed')  # Windows/Linux maximize
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)  # Alternative maximize
            except tk.TclError:
                pass  # Fall back to normal size
        
        # Load settings
        self.settings = self.load_settings()
        
        # Data storage
        self.programs = []
        self.current_program = None
        self.steps = []
        self.csv_parser = CSVParser()
        self.execution_engine = ExecutionEngine()
        self.current_file = None
        
        # GUI state
        self.operation_states = {
            'lines': {},      # Track line marking states: {1: 'pending', 2: 'completed', ...}
            'cuts': {},       # Track cutting states: {'top'/'bottom'/'left'/'right': 'pending'/'completed'}
            'pages': {}       # Track page states: {0: 'pending', 1: 'completed', ...}
        }
        
        # Canvas and drawing objects
        self.work_line_objects = {}  # Store line objects for dynamic updates
        self.canvas_objects = {}  # Store canvas objects for efficient updates
        self.canvas = None

        # Load canvas settings from settings.json (will be used by canvas_setup)
        sim_settings = self.settings.get("simulation", {})
        gui_settings = self.settings.get("gui_settings", {})

        # Scale and offset will be calculated dynamically by center_panel based on actual canvas size
        # Initialize with placeholder values - will be overwritten by responsive scaling
        self.offset_x = 50
        self.offset_y = 50
        self.scale_x = 5.0
        self.scale_y = 5.0
        self.grid_spacing = sim_settings.get("grid_spacing", 20)

        # Canvas dimensions will be set by center panel based on actual window size
        # Initialize with placeholder values - will be overwritten immediately
        self.canvas_width = 900
        self.canvas_height = 700
        self.actual_canvas_width = 900
        self.actual_canvas_height = 700
        
        # Position tracking
        self.position_update_scheduled = False
        
        # Initialize GUI components
        self.canvas_manager = CanvasManager(self)
        self.execution_controller = ExecutionController(self)
        
        # Create main layout and panels
        self.create_main_layout()
        self.create_panels()
        
        # Set up execution engine callback
        self.execution_engine.set_status_callback(self.on_execution_status)
        
        # Connect canvas manager to execution engine for GUI updates
        self.execution_engine.canvas_manager = self.canvas_manager
        
        # Set execution engine reference in mock hardware for sensor positioning
        from core.mock_hardware import set_execution_engine_reference
        set_execution_engine_reference(self.execution_engine)

        # Set initial position to motor home positions (0, 0)
        # Motors start at home positions, not paper positions
        from core.mock_hardware import move_x, move_y
        move_x(0.0)  # Rows motor home position
        move_y(0.0)  # Lines motor home position
        self.canvas_manager.update_position_display()
        
        # Start position update timer
        self.schedule_position_update()
        
        # Initial load
        self.load_csv_file_by_path("data/sample_programs.csv")
    
    def load_settings(self):
        """Load settings from config/settings.json"""
        try:
            with open('config/settings.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "gui_settings": {
                    "auto_load_csv": "sample_programs.csv",
                    "canvas_margin_left": 60,
                    "canvas_margin_right": 30,
                    "canvas_margin_top": 40,
                    "canvas_margin_bottom": 50,
                    "canvas_min_scale": 3.5
                },
                "simulation": {
                    "grid_spacing": 20,
                    "show_grid": True,
                    "max_display_x": 120,
                    "max_display_y": 80
                }
            }
    
    def load_csv_file_by_path(self, file_path):
        """Load CSV file by path"""
        if os.path.exists(file_path):
            programs, errors = self.csv_parser.load_programs_from_csv(file_path)
            
            if errors:
                error_msg = "\\n".join(errors[:5])
                if len(errors) > 5:
                    error_msg += f"\\n... and {len(errors) - 5} more errors"
                messagebox.showerror("CSV Validation Errors", 
                                   f"Found {len(errors)} validation errors:\\n{error_msg}")
            
            if programs:
                self.programs = programs
                self.current_file = file_path
                self.left_panel.update_program_list()
                if programs:
                    self.left_panel.select_program(0)
            else:
                messagebox.showerror("Error", f"No valid programs found in {file_path}")
    
    def create_main_layout(self):
        """Create the main window layout - responsive design"""
        # Create main frames with responsive sizing
        self.left_frame = tk.Frame(self.root, bg='lightgray')
        self.center_frame = tk.Frame(self.root, bg='white')
        self.right_frame = tk.Frame(self.root, bg='lightblue')

        # Configure responsive column and row weights - single row spanning full height
        self.root.grid_rowconfigure(0, weight=1)  # Single row spans full height
        self.root.grid_columnconfigure(0, minsize=250, weight=1)  # Left: min 250px
        self.root.grid_columnconfigure(1, minsize=920, weight=4)  # Center: larger weight for canvas
        self.root.grid_columnconfigure(2, minsize=200, weight=1)  # Right: reduced to 200px min

        # Grid frames for responsive layout - all in single row
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(5,3), pady=5)
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=3, pady=5)
        self.right_frame.grid(row=0, column=2, sticky="nsew", padx=(3,5), pady=5)
    
    def create_panels(self):
        """Create and initialize all GUI panels"""
        self.left_panel = LeftPanel(self, self.left_frame)
        # Create center panel - store reference immediately for canvas setup checks
        self.center_panel = CenterPanel(self, self.center_frame)

        # Right frame now contains both control panel and hardware status
        # Create container frames in right panel
        right_top_frame = tk.Frame(self.right_frame, bg='lightblue')
        right_top_frame.pack(fill=tk.BOTH, expand=True)

        right_bottom_frame = tk.Frame(self.right_frame, bg='#2C3E50')
        right_bottom_frame.pack(fill=tk.BOTH, expand=False)

        self.right_panel = RightPanel(self, right_top_frame)
        self.hardware_status_panel = HardwareStatusPanel(self, right_bottom_frame)

        # NOW finalize canvas setup after all panels are created and laid out
        print("📦 All panels created, calling finalize_canvas_setup()")
        self.center_panel.finalize_canvas_setup()
    
    def schedule_position_update(self):
        """Schedule regular position updates"""
        self.canvas_manager.update_position_display()
        self.root.after(500, self.schedule_position_update)  # Update every 500ms
    
    def on_execution_status(self, status, info=None):
        """Handle execution status updates"""
        self.execution_controller.on_execution_status(status, info)
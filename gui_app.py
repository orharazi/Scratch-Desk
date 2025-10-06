#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import json

# Import our modules
from csv_parser import CSVParser
from step_generator import generate_complete_program_steps, get_step_count_summary
from execution_engine import ExecutionEngine
from mock_hardware import (
    trigger_x_left_sensor, trigger_x_right_sensor, 
    trigger_y_top_sensor, trigger_y_bottom_sensor,
    get_current_x, get_current_y, reset_hardware
)

class ScratchDeskGUI:
    """Lightweight tkinter GUI optimized for Raspberry Pi"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Scratch Desk Control System")
        self.root.geometry("1400x900")  # Optimized size to fit canvas + controls
        self.root.minsize(1000, 700)  # Minimum window size
        self.root.resizable(True, True)  # Make window resizable
        
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
        
        # Data storage - simple variables for Pi optimization
        self.programs = []
        self.current_program = None
        self.steps = []
        self.csv_parser = CSVParser()
        self.execution_engine = ExecutionEngine()
        self.current_file = None
        
        # GUI state
        self.tool_position = {"x": 0.0, "y": 0.0}  # Current tool position
        self.canvas_objects = {}  # Store canvas objects for efficient updates
        
        # Program input fields for editing
        self.program_fields = {}
        
        # Operation state tracking for dynamic colors
        self.operation_states = {
            'lines': {},      # Track line marking states: {line_num: 'pending'/'completed'}
            'cuts': {},       # Track cutting states: {'top'/'bottom'/'left'/'right': 'pending'/'completed'}
            'pages': {}       # Track page separation states: {page_num: 'pending'/'completed'}
        }
        
        # Setup execution engine callback
        self.execution_engine.set_status_callback(self.on_execution_status)
        
        # Create GUI layout
        self.create_main_layout()
        self.create_left_panel()
        self.create_center_panel()
        self.create_right_panel()
        self.create_bottom_panel()
        
        # Initialize hardware at paper starting position
        reset_hardware()
        # Set initial position to paper starting point (15, 15)
        from mock_hardware import move_x, move_y
        move_x(15.0)
        move_y(15.0)
        self.update_position_display()
        
        # Auto-load CSV if specified in settings
        auto_load_csv = self.settings.get("gui_settings", {}).get("auto_load_csv")
        if auto_load_csv and os.path.exists(auto_load_csv):
            self.load_csv_file_by_path(auto_load_csv)
        
        # Start position update timer
        self.schedule_position_update()
    
    def load_settings(self):
        """Load settings from settings.json"""
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "gui_settings": {"auto_load_csv": "sample_programs.csv"},
                "simulation": {"scale_x": 5.0, "scale_y": 3.5, "offset_x": 50, "offset_y": 50}
            }
    
    def load_csv_file_by_path(self, file_path):
        """Load CSV file by path (for auto-loading)"""
        try:
            programs, errors = self.csv_parser.load_programs_from_csv(file_path)
            
            if programs:
                self.programs = programs
                self.current_file = os.path.basename(file_path)
                self.current_file_label.config(text=f"File: {self.current_file}")
                
                # Update program dropdown
                program_names = [f"{p.program_number}: {p.program_name}" for p in programs]
                self.program_combo['values'] = program_names
                
                if program_names:
                    self.program_combo.set(program_names[0])
                    self.on_program_selected()
                
                print(f"Auto-loaded {len(programs)} programs from {file_path}")
                
        except Exception as e:
            print(f"Failed to auto-load CSV: {e}")
    
    def create_main_layout(self):
        """Create main window layout with panels"""
        
        # Main container with horizontal layout
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top section (left, center, right panels)
        top_section = tk.Frame(main_container)
        top_section.pack(fill=tk.BOTH, expand=True)
        
        # Left panel (fixed width) - narrower for more canvas space
        self.left_frame = tk.Frame(top_section, width=300, bg='lightgray')
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0,3))
        self.left_frame.pack_propagate(False)
        
        # Center panel (flexible width) - adapts to window size
        self.center_frame = tk.Frame(top_section, bg='white')
        self.center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        # Right panel (fixed width) - wider to accommodate controls
        self.right_frame = tk.Frame(top_section, width=320, bg='lightblue')
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(3,0))
        self.right_frame.pack_propagate(False)
        
        # Bottom panel (status bar - fixed height)
        self.bottom_frame = tk.Frame(main_container, height=80, bg='lightyellow')
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))
        self.bottom_frame.pack_propagate(False)
    
    def create_left_panel(self):
        """Program Control Panel (Left) with Input Fields"""
        tk.Label(self.left_frame, text="PROGRAM CONTROL", font=('Arial', 12, 'bold'), 
                bg='lightgray').pack(pady=5)
        
        # File Menu
        file_frame = tk.Frame(self.left_frame, bg='lightgray')
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(file_frame, text="Load CSV", command=self.load_csv_file,
                 bg='darkgreen', fg='white', font=('Arial', 10, 'bold')).pack(fill=tk.X)
        
        self.current_file_label = tk.Label(file_frame, text="No file loaded", 
                                          wraplength=200, bg='lightgray')
        self.current_file_label.pack(pady=(5,0))
        
        # Program Selection
        tk.Label(self.left_frame, text="Program Selection:", font=('Arial', 10, 'bold'),
                bg='lightgray').pack(pady=(10,5))
        
        self.program_var = tk.StringVar()
        self.program_combo = ttk.Combobox(self.left_frame, textvariable=self.program_var, 
                                         state='readonly', width=25)
        self.program_combo.pack(padx=10, pady=5)
        self.program_combo.bind('<<ComboboxSelected>>', self.on_program_selected)
        
        # Create scrollable frame for input fields
        canvas_frame = tk.Frame(self.left_frame, bg='lightgray')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create canvas with scrollbar
        self.input_canvas = tk.Canvas(canvas_frame, bg='lightgray', highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.input_canvas.yview)
        self.input_frame = tk.Frame(self.input_canvas, bg='lightgray')
        
        self.input_frame.bind(
            "<Configure>",
            lambda e: self.input_canvas.configure(scrollregion=self.input_canvas.bbox("all"))
        )
        
        self.input_canvas.create_window((0, 0), window=self.input_frame, anchor="nw")
        self.input_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.input_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Program Details Header
        tk.Label(self.input_frame, text="Program Parameters:", font=('Arial', 10, 'bold'),
                bg='lightgray').grid(row=0, column=0, columnspan=2, pady=(0,10), sticky="w")
        
        # Create input fields with new CSV structure
        fields = [
            ("Program Name:", "program_name", 25),
            ("Program Number:", "program_number", 25),
            # Lines Pattern Settings
            ("High (cm):", "high", 25),
            ("Number of Lines:", "number_of_lines", 25),
            ("Top Padding (cm):", "top_padding", 25),
            ("Bottom Padding (cm):", "bottom_padding", 25),
            # Row Pattern Settings  
            ("Width (cm):", "width", 25),
            ("Left Margin (cm):", "left_margin", 25),
            ("Right Margin (cm):", "right_margin", 25),
            ("Left Padding (cm):", "left_padding", 25),
            ("Right Padding (cm):", "right_padding", 25),
            ("Page Width (cm):", "page_width", 25),
            ("Number of Pages:", "number_of_pages", 25),
            ("Buffer Between Pages (cm):", "buffer_between_pages", 25),
            # Generate Settings
            ("Repeat Rows:", "repeat_rows", 25),
            ("Repeat Lines:", "repeat_lines", 25)
        ]
        
        row = 1
        for label_text, field_name, width in fields:
            tk.Label(self.input_frame, text=label_text, font=('Arial', 9),
                    bg='lightgray').grid(row=row, column=0, sticky="w", pady=2)
            
            entry = tk.Entry(self.input_frame, width=12, font=('Arial', 9))
            entry.grid(row=row, column=1, sticky="ew", pady=2, padx=(5,0))
            entry.bind('<KeyRelease>', self.on_field_change)
            
            self.program_fields[field_name] = entry
            row += 1
        
        # Configure grid weights
        self.input_frame.grid_columnconfigure(1, weight=1)
        
        # Update and Apply buttons
        button_frame = tk.Frame(self.input_frame, bg='lightgray')
        button_frame.grid(row=row, column=0, columnspan=2, pady=(10,5), sticky="ew")
        
        tk.Button(button_frame, text="Update Program", command=self.update_current_program,
                 bg='darkorange', fg='white', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=(0,5))
        
        tk.Button(button_frame, text="Validate", command=self.validate_program,
                 bg='blue', fg='white', font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        
        # Validation Status
        self.validation_frame = tk.Frame(self.left_frame, bg='lightgray')
        self.validation_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.validation_indicator = tk.Label(self.validation_frame, text="●", 
                                           font=('Arial', 14), fg='gray', bg='lightgray')
        self.validation_indicator.pack(side=tk.LEFT)
        
        self.validation_text = tk.Label(self.validation_frame, text="No program selected", 
                                       bg='lightgray', font=('Arial', 9))
        self.validation_text.pack(side=tk.LEFT, padx=(5,0))
    
    def create_center_panel(self):
        """Visual Desk Simulation (Center - Main Feature)"""
        tk.Label(self.center_frame, text="DESK SIMULATION", font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Create scrollable canvas frame
        canvas_container = tk.Frame(self.center_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Canvas for desk simulation - use settings dimensions but make scrollable
        canvas_width = self.settings.get("gui_settings", {}).get("canvas_width", 600)
        canvas_height = self.settings.get("gui_settings", {}).get("canvas_height", 400)
        
        # Limit canvas size to fit in window
        max_canvas_width = 900  # Leave room for panels
        max_canvas_height = 600  # Leave room for bottom controls
        
        display_width = min(canvas_width, max_canvas_width)
        display_height = min(canvas_height, max_canvas_height)
        
        # Create canvas with scrollbars if needed
        self.canvas = tk.Canvas(canvas_container, width=display_width, height=display_height, 
                               bg='white', relief=tk.SUNKEN, bd=1,
                               scrollregion=(0, 0, canvas_width, canvas_height))
        
        # Add scrollbars if canvas is larger than display
        if canvas_width > max_canvas_width:
            h_scrollbar = tk.Scrollbar(canvas_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            self.canvas.config(xscrollcommand=h_scrollbar.set)
        
        if canvas_height > max_canvas_height:
            v_scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=self.canvas.yview)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.canvas.config(yscrollcommand=v_scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Store actual canvas dimensions for calculations
        self.actual_canvas_width = canvas_width
        self.actual_canvas_height = canvas_height
        
        # Initialize canvas elements
        self.setup_canvas()
        
        # Current Operation Display (moved sensor triggers to right panel)
        self.operation_label = tk.Label(self.center_frame, text="System Ready", 
                                       font=('Arial', 11, 'bold'), fg='blue')
        self.operation_label.pack(pady=5)
        
    
    def setup_canvas(self):
        """Setup canvas elements for desk simulation using settings"""
        # Get settings or use defaults
        sim_settings = self.settings.get("simulation", {})
        gui_settings = self.settings.get("gui_settings", {})
        
        # Canvas dimensions from settings (use actual dimensions for calculations)
        self.canvas_width = getattr(self, 'actual_canvas_width', gui_settings.get("canvas_width", 600))
        self.canvas_height = getattr(self, 'actual_canvas_height', gui_settings.get("canvas_height", 400))
        
        # Coordinate conversion from settings
        self.scale_x = sim_settings.get("scale_x", 5.0)  # pixels per cm
        self.scale_y = sim_settings.get("scale_y", 3.5)  # pixels per cm
        self.offset_x = sim_settings.get("offset_x", 50)  # Left margin
        self.offset_y = sim_settings.get("offset_y", 50)  # Top margin
        self.grid_spacing = sim_settings.get("grid_spacing", 20)
        
        # Clear canvas first
        self.canvas.delete("all")
        
        # Draw workspace boundary
        workspace_rect = self.canvas.create_rectangle(
            self.offset_x, self.offset_y,
            self.canvas_width - self.offset_x, self.canvas_height - self.offset_y,
            outline='black', width=2, fill='lightgray', stipple='gray12'
        )
        
        # Draw coordinate grid if enabled
        if sim_settings.get("show_grid", True):
            max_x_cm = sim_settings.get("max_display_x", 800)  # Maximum X in cm from settings
            max_y_cm = sim_settings.get("max_display_y", 400)  # Maximum Y in cm from settings
            
            # Vertical grid lines (X axis)
            for i in range(0, max_x_cm  , self.grid_spacing):
                x_pixel = self.offset_x + i * self.scale_x
                if x_pixel <= self.canvas_width - self.offset_x:
                    self.canvas.create_line(
                        x_pixel, self.offset_y, 
                        x_pixel, self.canvas_height - self.offset_y,
                        fill='lightgray', width=1, dash=(3,3)
                    )
                    # X axis labels (show every other to avoid clutter)
                    if i % (self.grid_spacing * 2) == 0:
                        self.canvas.create_text(
                            x_pixel, self.offset_y - 15, 
                            text=f'{i}cm', font=('Arial', 7), fill='darkblue'
                        )
            
            # Horizontal grid lines (Y axis) - note Y is inverted for display
            for i in range(0, max_y_cm  , self.grid_spacing):
                y_pixel = self.offset_y + (max_y_cm - i) * self.scale_y  # Invert Y
                if y_pixel >= self.offset_y and y_pixel <= self.canvas_height - self.offset_y:
                    self.canvas.create_line(
                        self.offset_x, y_pixel, 
                        self.canvas_width - self.offset_x, y_pixel,
                        fill='lightgray', width=1, dash=(3,3)
                    )
                    # Y axis labels (show every other to avoid clutter)
                    if i % (self.grid_spacing * 2) == 0:
                        self.canvas.create_text(
                            self.offset_x - 25, y_pixel, 
                            text=f'{i}cm', font=('Arial', 7), fill='darkblue'
                        )
        
        # Axis labels
        self.canvas.create_text(
            self.canvas_width // 2, self.canvas_height - 10, 
            text="X Axis (cm)", font=('Arial', 10, 'bold'), fill='darkblue'
        )
        self.canvas.create_text(
            10, self.canvas_height // 2, 
            text="Y Axis (cm)", font=('Arial', 10, 'bold'), fill='darkblue', angle=90
        )
        
        # Paper area placeholder (will be updated when program is selected)
        # Default paper area with bottom-left at (15, 15) - size 200x250cm
        paper_bottom_left_x = 15.0
        paper_bottom_left_y = 15.0
        default_paper_width = 200.0
        default_paper_height = 250.0
        
        # Convert to canvas coordinates - Y axis is inverted
        max_y_cm = sim_settings.get("max_display_y", 400)
        canvas_x1 = self.offset_x + paper_bottom_left_x * self.scale_x
        canvas_y1 = self.offset_y + (max_y_cm - paper_bottom_left_y - default_paper_height) * self.scale_y  # Top of paper
        canvas_x2 = self.offset_x + (paper_bottom_left_x + default_paper_width) * self.scale_x
        canvas_y2 = self.offset_y + (max_y_cm - paper_bottom_left_y) * self.scale_y  # Bottom of paper
        
        self.canvas_objects['paper'] = self.canvas.create_rectangle(
            canvas_x1, canvas_y1, canvas_x2, canvas_y2,
            outline='blue', width=3, fill='lightblue', stipple='gray50'
        )
        
        # Paper area label - position at top of paper
        self.canvas.create_text(
            canvas_x1 + (canvas_x2 - canvas_x1) / 2, canvas_y1 - 10,
            text="Paper Area", font=('Arial', 9, 'bold'), fill='blue'
        )
        
        # Add a marker at (15, 15) to show paper start position
        marker_x = self.offset_x + 15 * self.scale_x
        marker_y = self.offset_y + (max_y_cm - 15) * self.scale_y
        self.canvas.create_oval(
            marker_x - 3, marker_y - 3, marker_x + 3, marker_y + 3,
            fill='red', outline='darkred', width=2
        )
        self.canvas.create_text(
            marker_x + 15, marker_y - 10,
            text="(15,15)", font=('Arial', 8, 'bold'), fill='red'
        )
        
        # Current tool position (red circle with cross) - start at paper position (15, 15)
        max_y_cm = sim_settings.get("max_display_y", 80)
        start_x = 15.0  # Start at paper position
        start_y = 15.0  # Start at paper position  
        tool_x = self.offset_x + start_x * self.scale_x
        tool_y = self.offset_y + (max_y_cm - start_y) * self.scale_y
        
        # Enhanced tool position indicator - larger and more visible
        self.canvas_objects['tool_position'] = self.canvas.create_oval(
            tool_x - 6, tool_y - 6, tool_x + 6, tool_y + 6,
            fill='red', outline='darkred', width=3
        )
        
        # Tool position crosshair - more prominent
        self.canvas_objects['tool_crosshair_h'] = self.canvas.create_line(
            tool_x - 10, tool_y, tool_x + 10, tool_y,
            fill='darkred', width=3
        )
        self.canvas_objects['tool_crosshair_v'] = self.canvas.create_line(
            tool_x, tool_y - 10, tool_x, tool_y + 10,
            fill='darkred', width=3
        )
        
        # Tool status indicators (top of canvas)
        status_y = 15
        self.canvas_objects['line_marker'] = self.canvas.create_text(
            120, status_y, text="Line Marker: UP", fill='green', font=('Arial', 9, 'bold')
        )
        
        self.canvas_objects['line_cutter'] = self.canvas.create_text(
            280, status_y, text="Line Cutter: UP", fill='green', font=('Arial', 9, 'bold')
        )
        
        self.canvas_objects['row_marker'] = self.canvas.create_text(
            430, status_y, text="Row Marker: UP", fill='green', font=('Arial', 9, 'bold')
        )
        
        self.canvas_objects['row_cutter'] = self.canvas.create_text(
            550, status_y, text="Row Cutter: UP", fill='green', font=('Arial', 9, 'bold')
        )
    
    def create_right_panel(self):
        """Control and Status Panel (Right)"""
        tk.Label(self.right_frame, text="CONTROLS & STATUS", font=('Arial', 12, 'bold'), 
                bg='lightblue').pack(pady=5)
        
        # Generate Steps Button with better visibility
        tk.Button(self.right_frame, text="Generate Steps", command=self.generate_steps,
                 bg='yellow', fg='darkblue', font=('Arial', 10, 'bold'), height=2).pack(fill=tk.X, padx=10, pady=5)
        
        
        # Step Navigation
        nav_frame = tk.Frame(self.right_frame, bg='lightblue')
        nav_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(nav_frame, text="Step Navigation:", font=('Arial', 10, 'bold'), 
                bg='lightblue').pack()
        
        nav_buttons = tk.Frame(nav_frame, bg='lightblue')
        nav_buttons.pack(fill=tk.X, pady=5)
        
        self.prev_btn = tk.Button(nav_buttons, text="◄ Prev", command=self.prev_step,
                                 state=tk.DISABLED, width=8)
        self.prev_btn.pack(side=tk.LEFT)
        
        self.next_btn = tk.Button(nav_buttons, text="Next ►", command=self.next_step,
                                 state=tk.DISABLED, width=8)
        self.next_btn.pack(side=tk.RIGHT)
        
        self.step_info_label = tk.Label(nav_frame, text="No steps loaded", 
                                       bg='lightblue', font=('Arial', 9))
        self.step_info_label.pack(pady=5)
        
        # Step Details - Improved visibility and layout
        details_frame = tk.Frame(self.right_frame, bg='lightblue')
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Label(details_frame, text="Steps Queue:", font=('Arial', 10, 'bold'), 
                bg='lightblue', fg='darkblue').pack()
        
        # Create tabbed view for current step vs all steps
        notebook = ttk.Notebook(details_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Current Step Tab
        current_tab = tk.Frame(notebook, bg='white')
        notebook.add(current_tab, text='Current')
        
        # Current step info with better formatting
        current_info_frame = tk.Frame(current_tab, bg='lightgray', relief=tk.RAISED, bd=2)
        current_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.current_step_label = tk.Label(current_info_frame, text="No step selected", 
                                          font=('Arial', 9, 'bold'), bg='lightgray', fg='darkblue',
                                          wraplength=250)
        self.current_step_label.pack(pady=5)
        
        self.step_details = tk.Text(current_tab, height=6, width=25, font=('Arial', 9), 
                                   wrap=tk.WORD, bg='white', fg='black', relief=tk.SUNKEN, bd=2)
        step_scroll = tk.Scrollbar(current_tab, orient=tk.VERTICAL)
        step_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.step_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)
        self.step_details.config(yscrollcommand=step_scroll.set)
        step_scroll.config(command=self.step_details.yview)
        
        # All Steps Tab
        all_steps_tab = tk.Frame(notebook, bg='white')
        notebook.add(all_steps_tab, text='All Steps')
        
        # Steps queue listbox with better visibility
        queue_frame = tk.Frame(all_steps_tab, bg='white')
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.steps_listbox = tk.Listbox(queue_frame, font=('Arial', 8), height=15,
                                       bg='white', fg='black', selectbackground='lightblue',
                                       selectforeground='darkblue', relief=tk.SUNKEN, bd=2)
        queue_scroll = tk.Scrollbar(queue_frame, orient=tk.VERTICAL)
        queue_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.steps_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.steps_listbox.config(yscrollcommand=queue_scroll.set)
        queue_scroll.config(command=self.steps_listbox.yview)
        
        # Bind listbox selection to show step details
        self.steps_listbox.bind('<<ListboxSelect>>', self.on_step_select)
        
        # Store notebook reference
        self.step_notebook = notebook
        
        # Status Panel
        status_frame = tk.Frame(self.right_frame, bg='lightblue')
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(status_frame, text="System Status:", font=('Arial', 10, 'bold'), 
                bg='lightblue', fg='darkblue').pack()
        
        # Current Position with better visibility
        self.position_label = tk.Label(status_frame, text="Position: X=0.0, Y=0.0", 
                                      bg='lightblue', fg='darkblue', font=('Arial', 9))
        self.position_label.pack(anchor=tk.W)
        
        # Sensor Status with better visibility
        self.sensor_label = tk.Label(status_frame, text="Sensor: Ready", 
                                    bg='lightblue', fg='darkgreen', font=('Arial', 9))
        self.sensor_label.pack(anchor=tk.W)
        
        # System State with better visibility
        self.state_label = tk.Label(status_frame, text="State: Idle", 
                                   bg='lightblue', fg='darkred', font=('Arial', 9))
        self.state_label.pack(anchor=tk.W)
        
        # Execution Controls (moved from bottom panel)
        exec_frame = tk.Frame(self.right_frame, bg='lightblue')
        exec_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(exec_frame, text="Execution:", font=('Arial', 10, 'bold'), 
                bg='lightblue', fg='darkblue').pack()
        
        # Execution buttons in 2x2 grid
        button_grid = tk.Frame(exec_frame, bg='lightblue')
        button_grid.pack(pady=5)
        
        self.run_btn = tk.Button(button_grid, text="▶ RUN", command=self.run_execution,
                                bg='green', fg='white', font=('Arial', 10, 'bold'), 
                                width=10, height=1, state=tk.DISABLED)
        self.run_btn.grid(row=0, column=0, padx=2, pady=2)
        
        self.pause_btn = tk.Button(button_grid, text="⏸ PAUSE", command=self.pause_execution,
                                  bg='orange', fg='white', font=('Arial', 10, 'bold'), 
                                  width=10, height=1, state=tk.DISABLED)
        self.pause_btn.grid(row=0, column=1, padx=2, pady=2)
        
        self.stop_btn = tk.Button(button_grid, text="⏹ STOP", command=self.stop_execution,
                                 bg='red', fg='white', font=('Arial', 10, 'bold'), 
                                 width=10, height=1, state=tk.DISABLED)
        self.stop_btn.grid(row=1, column=0, padx=2, pady=2)
        
        self.reset_btn = tk.Button(button_grid, text="🔄 RESET", command=self.reset_execution,
                                  bg='blue', fg='white', font=('Arial', 10, 'bold'), 
                                  width=10, height=1)
        self.reset_btn.grid(row=1, column=1, padx=2, pady=2)
        
        # Progress indicator (compact) with better visibility
        self.progress_label = tk.Label(exec_frame, text="Ready", 
                                      bg='lightblue', fg='darkblue', font=('Arial', 8, 'bold'))
        self.progress_label.pack(pady=2)
        
        # Manual Sensor Triggers (moved from center panel)
        sensor_frame = tk.Frame(self.right_frame, bg='lightblue')
        sensor_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(sensor_frame, text="Manual Sensors:", font=('Arial', 10, 'bold'), 
                bg='lightblue', fg='darkblue').pack()
        
        # X sensors in compact layout
        x_frame = tk.Frame(sensor_frame, bg='lightblue')
        x_frame.pack(fill=tk.X, pady=3)
        
        tk.Label(x_frame, text="X:", bg='lightblue', fg='darkblue', font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        
        self.x_left_btn = tk.Button(x_frame, text="Left", bg='orange', fg='white',
                                   command=self.trigger_x_left, width=6, font=('Arial', 9, 'bold'))
        self.x_left_btn.pack(side=tk.LEFT, padx=2)
        
        self.x_right_btn = tk.Button(x_frame, text="Right", bg='orange', fg='white',
                                    command=self.trigger_x_right, width=6, font=('Arial', 9, 'bold'))
        self.x_right_btn.pack(side=tk.LEFT, padx=2)
        
        # Y sensors in compact layout
        y_frame = tk.Frame(sensor_frame, bg='lightblue')
        y_frame.pack(fill=tk.X, pady=3)
        
        tk.Label(y_frame, text="Y:", bg='lightblue', fg='darkblue', font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        
        self.y_top_btn = tk.Button(y_frame, text="Top", bg='purple', fg='white',
                                  command=self.trigger_y_top, width=6, font=('Arial', 9, 'bold'))
        self.y_top_btn.pack(side=tk.LEFT, padx=2)
        
        self.y_bottom_btn = tk.Button(y_frame, text="Bottom", bg='purple', fg='white',
                                     command=self.trigger_y_bottom, width=6, font=('Arial', 9, 'bold'))
        self.y_bottom_btn.pack(side=tk.LEFT, padx=2)
    
    def create_bottom_panel(self):
        """Status Information Panel (Bottom - simplified)"""
        # Simple status bar instead of execution controls
        tk.Label(self.bottom_frame, text="STATUS:", font=('Arial', 10, 'bold'), 
                bg='lightyellow', fg='darkgreen').pack(side=tk.LEFT, padx=8)
        
        # Progress bar (compact version)
        progress_frame = tk.Frame(self.bottom_frame, bg='lightyellow')
        progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=8)
        
        # System status summary
        self.system_status_label = tk.Label(self.bottom_frame, text="System Ready - Load program to begin", 
                                           bg='lightyellow', fg='darkblue', font=('Arial', 9, 'bold'))
        self.system_status_label.pack(side=tk.RIGHT, padx=8)
    
    # Event Handlers
    def load_csv_file(self):
        """Load CSV file with programs"""
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                programs, errors = self.csv_parser.load_programs_from_csv(file_path)
                
                if errors:
                    messagebox.showwarning("CSV Errors", f"Errors found:\\n\\n" + "\\n".join(errors))
                
                if programs:
                    self.programs = programs
                    self.current_file = os.path.basename(file_path)
                    self.current_file_label.config(text=f"File: {self.current_file}")
                    
                    # Update program dropdown
                    program_names = [f"{p.program_number}: {p.program_name}" for p in programs]
                    self.program_combo['values'] = program_names
                    
                    if program_names:
                        self.program_combo.set(program_names[0])
                        self.on_program_selected()
                    
                    messagebox.showinfo("Success", f"Loaded {len(programs)} programs successfully!")
                else:
                    messagebox.showerror("Error", "No valid programs found in CSV file")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV file:\\n{str(e)}")
    
    def on_program_selected(self, event=None):
        """Handle program selection"""
        if not self.programs:
            return
        
        # Get selected program index
        selection = self.program_combo.current()
        if selection >= 0 and selection < len(self.programs):
            self.current_program = self.programs[selection]
            self.update_program_details()
            self.update_canvas_paper_area()
            
            # Move tool to first working position for this program
            self.move_tool_to_first_line()
    
    def update_program_details(self):
        """Update program details by populating input fields"""
        if not self.current_program:
            # Clear all fields
            for field_name, entry in self.program_fields.items():
                entry.delete(0, tk.END)
            self.validation_indicator.config(fg='gray')
            self.validation_text.config(text="No program selected")
            return
        
        p = self.current_program
        
        # Populate input fields with new field names
        field_values = {
            'program_name': p.program_name,
            'program_number': str(p.program_number),
            # Lines Pattern Settings
            'high': str(p.high),
            'number_of_lines': str(p.number_of_lines),
            'top_padding': str(p.top_padding),
            'bottom_padding': str(p.bottom_padding),
            # Row Pattern Settings
            'width': str(p.width),
            'left_margin': str(p.left_margin),
            'right_margin': str(p.right_margin),
            'left_padding': str(p.left_padding),
            'right_padding': str(p.right_padding),
            'page_width': str(p.page_width),
            'number_of_pages': str(p.number_of_pages),
            'buffer_between_pages': str(p.buffer_between_pages),
            # Generate Settings
            'repeat_rows': str(p.repeat_rows),
            'repeat_lines': str(p.repeat_lines)
        }
        
        for field_name, value in field_values.items():
            if field_name in self.program_fields:
                entry = self.program_fields[field_name]
                entry.delete(0, tk.END)
                entry.insert(0, value)
        
        # Validate program
        self.validate_program()
    
    def validate_program(self):
        """Validate current program and update status"""
        if not self.current_program:
            self.validation_indicator.config(fg='gray')
            self.validation_text.config(text="No program selected")
            return
        
        validation_errors = self.current_program.validate()
        if validation_errors:
            self.validation_indicator.config(fg='red')
            self.validation_text.config(text=f"{len(validation_errors)} errors")
        else:
            self.validation_indicator.config(fg='green')
            self.validation_text.config(text="Program valid ✓")
    
    def on_field_change(self, event=None):
        """Handle field changes"""
        # Update validation when fields change
        if self.current_program:
            self.validate_program()
    
    def update_current_program(self):
        """Update current program with values from input fields"""
        if not self.current_program:
            messagebox.showwarning("Warning", "No program selected to update")
            return
        
        try:
            # Get values from input fields
            from program_model import ScratchDeskProgram
            
            updated_program = ScratchDeskProgram(
                program_number=int(self.program_fields['program_number'].get()),
                program_name=self.program_fields['program_name'].get(),
                # Lines Pattern Settings
                high=float(self.program_fields['high'].get()),
                number_of_lines=int(self.program_fields['number_of_lines'].get()),
                top_padding=float(self.program_fields['top_padding'].get()),
                bottom_padding=float(self.program_fields['bottom_padding'].get()),
                # Row Pattern Settings
                width=float(self.program_fields['width'].get()),
                left_margin=float(self.program_fields['left_margin'].get()),
                right_margin=float(self.program_fields['right_margin'].get()),
                left_padding=float(self.program_fields['left_padding'].get()),
                right_padding=float(self.program_fields['right_padding'].get()),
                page_width=float(self.program_fields['page_width'].get()),
                number_of_pages=int(self.program_fields['number_of_pages'].get()),
                buffer_between_pages=float(self.program_fields['buffer_between_pages'].get()),
                # Generate Settings
                repeat_rows=int(self.program_fields['repeat_rows'].get()),
                repeat_lines=int(self.program_fields['repeat_lines'].get())
            )
            
            self.current_program = updated_program
            
            # Update the program in the programs list
            selection = self.program_combo.current()
            if 0 <= selection < len(self.programs):
                self.programs[selection] = updated_program
            
            self.validate_program()
            self.update_canvas_paper_area()
            
            messagebox.showinfo("Success", "Program updated successfully!")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input values:\n{str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update program:\n{str(e)}")
    
    def update_canvas_paper_area(self):
        """Update paper area visualization based on current program with bottom-left at (15,15)"""
        if not self.current_program:
            return
        
        p = self.current_program
        
        # Paper position: bottom-left corner at (15, 15)
        paper_bottom_left_x = 15.0
        paper_bottom_left_y = 15.0
        paper_width = p.width  # Updated field name
        paper_height = p.high  # Updated field name
        
        # Calculate paper boundaries in real coordinates
        paper_x1 = paper_bottom_left_x  # Left edge
        paper_x2 = paper_bottom_left_x + paper_width  # Right edge
        paper_y1 = paper_bottom_left_y  # Bottom edge (in real coordinates)
        paper_y2 = paper_bottom_left_y + paper_height  # Top edge (in real coordinates)
        
        # Convert to canvas coordinates - Y axis is inverted for display
        max_y_cm = self.settings.get("simulation", {}).get("max_display_y", 400)
        
        canvas_x1 = self.offset_x + paper_x1 * self.scale_x
        canvas_y1 = self.offset_y + (max_y_cm - paper_y2) * self.scale_y  # Top of paper (inverted)
        canvas_x2 = self.offset_x + paper_x2 * self.scale_x
        canvas_y2 = self.offset_y + (max_y_cm - paper_y1) * self.scale_y  # Bottom of paper (inverted)
        
        # Update paper rectangle
        if 'paper' in self.canvas_objects:
            self.canvas.coords(self.canvas_objects['paper'], canvas_x1, canvas_y1, canvas_x2, canvas_y2)
            
        # Update the paper label
        try:
            self.canvas.delete("paper_label")
            self.canvas.delete("work_lines")
        except:
            pass
        self.canvas.create_text(
            canvas_x1 + (canvas_x2 - canvas_x1) / 2, canvas_y1 - 10,
            text=f"{p.program_name} ({paper_width:.0f}x{paper_height:.0f}cm)", 
            font=('Arial', 9, 'bold'), fill='blue', tags="paper_label"
        )
        
        # Add line marking and cutting visualizations
        self.draw_work_lines(p, paper_bottom_left_x, paper_bottom_left_y, max_y_cm)
        
        # Draw legend outside the canvas area
        self.draw_enhanced_legend()
    
    def draw_work_lines(self, program, paper_x, paper_y, max_y_cm):
        """Draw visualization of lines that will be marked and cut with dynamic colors"""
        
        # Initialize operation states when program changes
        self.initialize_operation_states(program)
        
        # Clear previous work line objects
        self.work_line_objects = {}
        
        # Calculate line positions for Lines Pattern - match step generator logic
        # Use exact number of lines user requested
        first_line_y = paper_y + program.high - program.top_padding
        last_line_y = paper_y + program.bottom_padding  # Last line above bottom edge
        actual_lines_to_draw = program.number_of_lines  
        
        if actual_lines_to_draw > 1:
            line_spacing = (first_line_y - last_line_y) / (actual_lines_to_draw - 1)
        else:
            line_spacing = 0
        
        for line_num in range(actual_lines_to_draw):
            line_display_num = line_num + 1  # Display numbers starting from 1
            line_y_real = first_line_y - (line_num * line_spacing)
            
            # Convert to canvas coordinates
            line_y_canvas = self.offset_y + (max_y_cm - line_y_real) * self.scale_y
            line_x1_canvas = self.offset_x + paper_x * self.scale_x
            line_x2_canvas = self.offset_x + (paper_x + program.width) * self.scale_x
            
            # Dynamic color based on state
            state = self.operation_states['lines'].get(line_display_num, 'pending')
            if state == 'completed':
                line_color = '#00AA00'  # Bright green for completed
                dash_pattern = (10, 2)  # Solid-like for completed
                width = 3
            elif state == 'in_progress':
                line_color = '#FF8800'  # Orange for in progress
                dash_pattern = (8, 4)
                width = 3
            else:  # pending
                line_color = '#FF4444'  # Bright red for pending
                dash_pattern = (5, 3)
                width = 2
            
            # Draw line marking line and store object ID for updates
            line_id = self.canvas.create_line(
                line_x1_canvas, line_y_canvas, line_x2_canvas, line_y_canvas,
                fill=line_color, width=width, dash=dash_pattern, tags="work_lines"
            )
            
            # Store line object for dynamic updates
            self.work_line_objects[f'line_{line_display_num}'] = {
                'id': line_id,
                'type': 'line',
                'color_pending': '#FF4444',
                'color_progress': '#FF8800',
                'color_completed': '#00AA00'
            }
            
            # Add line number label with matching color
            label_id = self.canvas.create_text(
                line_x1_canvas - 25, line_y_canvas,
                text=f"L{line_display_num}", font=('Arial', 9, 'bold'), fill=line_color, tags="work_lines"
            )
            self.work_line_objects[f'line_{line_display_num}']['label_id'] = label_id
        
        # Draw vertical lines (Row Pattern) - Show ALL page start and end marks
        first_page_start = paper_x + program.left_margin + program.left_padding
        
        # Draw each page's start and end marks (like the step generator does)
        page_mark_id = 1  # For tracking state
        
        for page_num in range(program.number_of_pages):
            # Calculate page start position
            page_start_x = first_page_start + page_num * (program.page_width + program.buffer_between_pages)
            
            # Calculate page end position  
            page_end_x = page_start_x + program.page_width
            
            # Draw page START mark
            page_start_canvas = self.offset_x + page_start_x * self.scale_x
            page_y1_canvas = self.offset_y + (max_y_cm - (paper_y + program.high)) * self.scale_y
            page_y2_canvas = self.offset_y + (max_y_cm - paper_y) * self.scale_y
            
            # Page start state (each page gets its own state tracking)
            state = self.operation_states['pages'].get(page_num  , 'pending')
            if state == 'completed':
                page_color = '#0088AA'  # Cyan for completed
                dash_pattern = (8, 2)
                width = 3
            elif state == 'in_progress':
                page_color = '#8800FF'  # Purple for in progress
                dash_pattern = (6, 3)
                width = 3
            else:  # pending
                page_color = '#FF6600'  # Orange for pending
                dash_pattern = (4, 2)
                width = 2
            
            # Draw page start line
            start_line_id = self.canvas.create_line(
                page_start_canvas, page_y1_canvas, page_start_canvas, page_y2_canvas,
                fill=page_color, width=width, dash=dash_pattern, tags="work_lines"
            )
            
            # Store page start object for dynamic updates  
            self.work_line_objects[f'page_{page_num  }_start'] = {
                'id': start_line_id,
                'type': 'page',
                'color_pending': '#FF6600',  # Orange for pending
                'color_progress': '#8800FF',  # Purple for in progress
                'color_completed': '#0088AA'  # Cyan for completed
            }
            
            # Add page start label
            start_label_id = self.canvas.create_text(
                page_start_canvas, page_y2_canvas + 15,
                text=f"P{page_num  }S", font=('Arial', 7, 'bold'), fill=page_color, tags="work_lines"
            )
            self.work_line_objects[f'page_{page_num  }_start']['label_id'] = start_label_id
            
            # Draw page END mark
            page_end_canvas = self.offset_x + page_end_x * self.scale_x
            
            # Page end uses same state as start (they belong to same page)
            end_line_id = self.canvas.create_line(
                page_end_canvas, page_y1_canvas, page_end_canvas, page_y2_canvas,
                fill=page_color, width=width, dash=dash_pattern, tags="work_lines"
            )
            
            # Store page end object for dynamic updates
            self.work_line_objects[f'page_{page_num  }_end'] = {
                'id': end_line_id,
                'type': 'page',
                'color_pending': '#FF6600',  # Orange for pending
                'color_progress': '#8800FF',  # Purple for in progress  
                'color_completed': '#0088AA'  # Cyan for completed
            }
            
            # Add page end label
            end_label_id = self.canvas.create_text(
                page_end_canvas, page_y2_canvas + 15,
                text=f"P{page_num  }E", font=('Arial', 7, 'bold'), fill=page_color, tags="work_lines"
            )
            self.work_line_objects[f'page_{page_num  }_end']['label_id'] = end_label_id
        
        # Draw cutting edges with dynamic colors - position cuts on actual paper edges
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
            state = self.operation_states['cuts'].get(cut_name, 'pending')
            
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
                cut_y_canvas = self.offset_y + (max_y_cm - cut_pos) * self.scale_y
                cut_id = self.canvas.create_line(
                    self.offset_x + paper_x * self.scale_x, cut_y_canvas,
                    self.offset_x + (paper_x + program.width) * self.scale_x, cut_y_canvas,
                    fill=cut_color, width=width, tags="work_lines"
                )
                
                # Store cut object for dynamic updates
                self.work_line_objects[f'cut_{cut_name}'] = {
                    'id': cut_id,
                    'type': 'cut',
                    'color_pending': '#8800FF',
                    'color_progress': '#FF0088',
                    'color_completed': '#AA00AA'
                }
                
                # Label position
                label_y = cut_y_canvas - 12 if i == 0 else cut_y_canvas + 20
                label_id = self.canvas.create_text(
                    self.offset_x + (paper_x + program.width/2) * self.scale_x, label_y,
                    text=cut_labels[i], font=('Arial', 8, 'bold'), fill=cut_color, tags="work_lines"
                )
                self.work_line_objects[f'cut_{cut_name}']['label_id'] = label_id
            else:  # vertical
                cut_x_canvas = self.offset_x + cut_pos * self.scale_x
                cut_id = self.canvas.create_line(
                    cut_x_canvas, self.offset_y + (max_y_cm - (paper_y + program.high)) * self.scale_y,
                    cut_x_canvas, self.offset_y + (max_y_cm - paper_y) * self.scale_y,
                    fill=cut_color, width=width, tags="work_lines"
                )
                
                # Store cut object for dynamic updates
                self.work_line_objects[f'cut_{cut_name}'] = {
                    'id': cut_id,
                    'type': 'cut',
                    'color_pending': '#8800FF',
                    'color_progress': '#FF0088',
                    'color_completed': '#AA00AA'
                }
        
        # Enhanced legend with state colors
        self.draw_enhanced_legend()
    
    def initialize_operation_states(self, program):
        """Initialize operation states for a new program"""
        # Clear existing states
        self.operation_states = {
            'lines': {},
            'cuts': {},
            'pages': {}
        }
        
        # Initialize all lines as pending (N lines = N internal markings)
        for line_num in range(1, program.number_of_lines + 1):
            self.operation_states['lines'][line_num] = 'pending'
        
        # Initialize all cuts as pending
        for cut_name in ['top', 'bottom', 'left', 'right']:
            self.operation_states['cuts'][cut_name] = 'pending'
        
        # Initialize all page starts and ends as pending (individual tracking)
        for page_num in range(1, program.number_of_pages  ):
            self.operation_states['pages'][f'{page_num}_start'] = 'pending'
            self.operation_states['pages'][f'{page_num}_end'] = 'pending'
    
    def draw_enhanced_legend(self):
        """Draw user-friendly work operations status display"""
        # Position at bottom of desk area, below the simulation
        sim_settings = self.settings.get("simulation", {})
        max_y_cm = sim_settings.get("max_display_y", 80)
        
        # Create a nice bordered box for the legend
        desk_bottom = self.offset_y + (max_y_cm * self.scale_y) + 40
        legend_x = self.offset_x + 20
        legend_y = desk_bottom
        
        # Main title with better styling
        title_y = legend_y - 10
        self.canvas.create_text(legend_x + 150, title_y, text="📋 WORK OPERATIONS STATUS", 
                               font=('Arial', 12, 'bold'), fill='darkblue', tags="work_lines", anchor='center')
        
        # Create background box for better visual separation
        box_width = 420
        box_height = 80
        self.canvas.create_rectangle(legend_x - 5, legend_y, legend_x + box_width, legend_y + box_height,
                                   outline='darkblue', width=2, fill='#f8f8f8', tags="work_lines")
        
        # Organize in a clean grid layout - 2 main columns
        col_width = 200
        start_x = legend_x + 10
        
        # Column 1: All Marking Operations (Lines + Pages)
        self.draw_operation_column(start_x, legend_y + 10, "✏️ MARK", [
            ("⏳ Ready", '#FF6600', "Waiting to mark"),
            ("🔄 Working", '#FF8800', "Currently marking"), 
            ("✅ Done", '#00AA00', "Marking complete")
        ])
        
        # Column 2: All Cutting Operations  
        self.draw_operation_column(start_x + col_width, legend_y + 10, "✂️ CUT", [
            ("⏳ Ready", '#8800FF', "Ready to cut"),
            ("🔄 Working", '#FF0088', "Currently cutting"),
            ("✅ Done", '#AA00AA', "Cutting complete")
        ])
        
        # Add dynamic progress summary at the bottom
        self.draw_progress_summary(legend_x, legend_y + box_height + 10, box_width)
    
    def draw_operation_column(self, x, y, title, states):
        """Draw a column of operation states with icons and descriptions"""
        # Column title
        self.canvas.create_text(x, y, text=title, font=('Arial', 9, 'bold'), 
                               fill='darkblue', tags="work_lines", anchor='w')
        
        # Draw each state
        y_pos = y + 20
        for emoji_text, color, description in states:
            # Create colored indicator circle
            self.canvas.create_oval(x, y_pos - 3, x + 8, y_pos + 5, 
                                  fill=color, outline='darkgray', tags="work_lines")
            
            # Status text with emoji
            self.canvas.create_text(x + 12, y_pos, text=emoji_text, 
                                   font=('Arial', 8), fill=color, tags="work_lines", anchor='w')
            
            y_pos += 15
    
    def draw_progress_summary(self, x, y, width):
        """Draw a dynamic progress summary showing current operation counts"""
        if not self.current_program:
            return
            
        # Count operations by state
        lines_stats = self.count_operation_states('lines')
        pages_stats = self.count_operation_states('pages') 
        cuts_stats = self.count_operation_states('cuts')
        
        # Combine lines and pages into "MARK" category
        mark_total = lines_stats['total'] + pages_stats['total']
        mark_done = lines_stats['done'] + pages_stats['done']
        
        # Create simplified progress summary text
        summary_text = f"📊 Progress: Mark {mark_done}/{mark_total} • Cut {cuts_stats['done']}/{cuts_stats['total']}"
        
        # Calculate overall completion percentage using combined totals
        total_ops = mark_total + cuts_stats['total']
        done_ops = mark_done + cuts_stats['done']
        
        if total_ops > 0:
            completion_pct = (done_ops / total_ops) * 100
            
            # Create progress bar
            bar_width = width - 20
            bar_height = 12
            bar_x = x + 10
            bar_y = y + 20
            
            # Background bar
            self.canvas.create_rectangle(bar_x, bar_y, bar_x + bar_width, bar_y + bar_height,
                                       fill='lightgray', outline='gray', tags="work_lines")
            
            # Progress fill
            fill_width = (bar_width * completion_pct) / 100
            fill_color = '#4CAF50' if completion_pct == 100 else '#2196F3' if completion_pct > 50 else '#FF9800'
            
            if fill_width > 0:
                self.canvas.create_rectangle(bar_x, bar_y, bar_x + fill_width, bar_y + bar_height,
                                           fill=fill_color, outline='', tags="work_lines")
            
            # Progress text
            progress_text = f"{completion_pct:.1f}% Complete ({done_ops}/{total_ops} operations)"
            self.canvas.create_text(x + width/2, bar_y - 8, text=progress_text, 
                                   font=('Arial', 9, 'bold'), fill='darkblue', tags="work_lines", anchor='center')
        
        # Summary text
        self.canvas.create_text(x + 10, y, text=summary_text, 
                               font=('Arial', 8), fill='darkslategray', tags="work_lines", anchor='w')
    
    def count_operation_states(self, operation_type):
        """Count operations by state for progress tracking"""
        if operation_type not in self.operation_states:
            return {'total': 0, 'done': 0, 'in_progress': 0, 'pending': 0}
        
        states = self.operation_states[operation_type]
        stats = {'total': len(states), 'done': 0, 'in_progress': 0, 'pending': 0}
        
        for state in states.values():
            if state == 'completed':
                stats['done'] += 1
            elif state == 'in_progress':
                stats['in_progress'] += 1
            else:
                stats['pending'] += 1
                
        return stats
    
    def update_operation_state(self, operation_type, operation_id, new_state):
        """Update the state of a specific operation and refresh visualization"""
        if operation_type in self.operation_states:
            self.operation_states[operation_type][operation_id] = new_state
            # Refresh only the work lines without redrawing everything
            if self.current_program:
                self.refresh_work_lines_colors()
    
    def simulate_operation_progress(self):
        """REMOVED: Demo method was for testing only - now colors update automatically during execution"""
        pass  # Function removed - colors now update automatically during execution
    
    def track_operation_from_step(self, step_description):
        """Track operations from step descriptions for real-time updates"""
        if not self.current_program:
            return
            
        desc = step_description.lower()
        import re
        
        # Track line marking operations - pattern: "Mark line X/Y: Open/Close line marker"
        if 'lines' in desc and 'line marker' in desc:
            line_match = re.search(r'mark line (\d+)/\d+', desc)
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
        
        # Track row marking operations - pattern: "Mark page X/Y: Open/Close row marker (page start/end)"
        elif 'rows' in desc and 'row marker' in desc:
            page_match = re.search(r'mark page (\d+)/\d+', desc)
            if page_match:
                page_num = int(page_match.group(1))
                
                # Determine if it's start or end marking
                if '(page start)' in desc:
                    page_key = f'{page_num}_start'
                    if 'open row marker' in desc:
                        self.update_operation_state('pages', page_key, 'in_progress')
                        print(f"🟠 Page {page_num} START marking started (IN PROGRESS)")
                    elif 'close row marker' in desc:
                        self.update_operation_state('pages', page_key, 'completed')
                        print(f"🔵 Page {page_num} START marking completed (COMPLETED)")
                elif '(page end)' in desc:
                    page_key = f'{page_num}_end'
                    if 'open row marker' in desc:
                        self.update_operation_state('pages', page_key, 'in_progress')
                        print(f"🟠 Page {page_num} END marking started (IN PROGRESS)")
                    elif 'close row marker' in desc:
                        self.update_operation_state('pages', page_key, 'completed')
                        print(f"🔵 Page {page_num} END marking completed (COMPLETED)")
        
        # Track row cutting operations - pattern: "Cut left/right edge: Open/Close row cutter"
        elif 'rows' in desc and 'row cutter' in desc:
            if 'cut left edge' in desc:
                if 'open row cutter' in desc:
                    self.update_operation_state('cuts', 'left', 'in_progress')
                    print("🟠 Left cut started (IN PROGRESS)")
                elif 'close row cutter' in desc:
                    self.update_operation_state('cuts', 'left', 'completed')
                    print("🟣 Left cut completed (COMPLETED)")
            elif 'cut right edge' in desc:
                if 'open row cutter' in desc:
                    self.update_operation_state('cuts', 'right', 'in_progress')
                    print("🟠 Right cut started (IN PROGRESS)")
                elif 'close row cutter' in desc:
                    self.update_operation_state('cuts', 'right', 'completed')
                    print("🟣 Right cut completed (COMPLETED)")
    
    def refresh_work_lines_colors(self):
        """Refresh work line colors based on current operation states without redrawing"""
        if not hasattr(self, 'work_line_objects') or not self.current_program:
            return
            
        # Update line colors (including extra line)
        actual_lines = self.current_program.number_of_lines  
        for line_num in range(1, actual_lines  ):
            obj_key = f'line_{line_num}'
            if obj_key in self.work_line_objects:
                obj = self.work_line_objects[obj_key]
                state = self.operation_states['lines'].get(line_num, 'pending')
                
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
                self.canvas.itemconfig(obj['id'], fill=color, width=width)
                if 'label_id' in obj:
                    self.canvas.itemconfig(obj['label_id'], fill=color)
        
        # Update cut colors
        for cut_name in ['top', 'bottom', 'left', 'right']:
            obj_key = f'cut_{cut_name}'
            if obj_key in self.work_line_objects:
                obj = self.work_line_objects[obj_key]
                state = self.operation_states['cuts'].get(cut_name, 'pending')
                
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
                self.canvas.itemconfig(obj['id'], fill=color, width=width)
                if 'label_id' in obj:
                    self.canvas.itemconfig(obj['label_id'], fill=color)
        
        # Update page colors (individual start and end tracking for each page)
        for page_num in range(1, self.current_program.number_of_pages  ):
            # Update page start (independent state)
            start_state_key = f'{page_num}_start'
            start_obj_key = f'page_{page_num}_start'
            start_state = self.operation_states['pages'].get(start_state_key, 'pending')
            
            if start_obj_key in self.work_line_objects:
                obj = self.work_line_objects[start_obj_key]
                
                if start_state == 'completed':
                    color = obj['color_completed']
                    width = 3
                elif start_state == 'in_progress':
                    color = obj['color_progress']
                    width = 3
                else:
                    color = obj['color_pending']
                    width = 2
                
                # Update page start color
                self.canvas.itemconfig(obj['id'], fill=color, width=width)
                if 'label_id' in obj:
                    self.canvas.itemconfig(obj['label_id'], fill=color)
            
            # Update page end (independent state)
            end_state_key = f'{page_num}_end'
            end_obj_key = f'page_{page_num}_end'
            end_state = self.operation_states['pages'].get(end_state_key, 'pending')
            
            if end_obj_key in self.work_line_objects:
                obj = self.work_line_objects[end_obj_key]
                
                if end_state == 'completed':
                    color = obj['color_completed']
                    width = 3
                elif end_state == 'in_progress':
                    color = obj['color_progress']
                    width = 3
                else:
                    color = obj['color_pending']
                    width = 2
                
                # Update page end color
                self.canvas.itemconfig(obj['id'], fill=color, width=width)
                if 'label_id' in obj:
                    self.canvas.itemconfig(obj['label_id'], fill=color)
    
    def move_tool_to_first_line(self):
        """Move tool to the first line position when program is selected"""
        if not self.current_program:
            return
            
        # Calculate first line position based on program (matches step generator)
        PAPER_OFFSET_X = 15.0  # Paper starts at (15, 15)
        PAPER_OFFSET_Y = 15.0
        
        # First line Y position: PAPER_OFFSET_Y + program.high - program.top_padding
        first_line_y = PAPER_OFFSET_Y + self.current_program.high - self.current_program.top_padding
        
        # Move to left edge of paper for X position  
        tool_x = PAPER_OFFSET_X
        
        # Move hardware to first line position
        from mock_hardware import move_x, move_y
        move_x(tool_x)
        move_y(first_line_y)
        
        # Update display
        self.update_position_display()
        
        print(f"Tool moved to first line position: ({tool_x:.1f}, {first_line_y:.1f}) - Paper offset + program coordinates")
    
    def generate_steps(self):
        """Generate steps from current program"""
        if not self.current_program:
            messagebox.showwarning("Warning", "Please select a program first")
            return
        
        try:
            # Show step count summary first
            summary = get_step_count_summary(self.current_program)
            
            result = messagebox.askquestion(
                "Generate Steps",
                f"Generate steps for '{self.current_program.program_name}'?\\n\\n"
                f"Lines steps: {summary['lines_steps']}\\n"
                f"Row steps: {summary['row_steps']}\\n"
                f"Total steps: {summary['total_steps']}\\n"
                f"Repetitions: {summary['total_repetitions']}"
            )
            
            if result == 'yes':
                self.steps = generate_complete_program_steps(self.current_program)
                self.execution_engine.load_steps(self.steps)
                
                # Update navigation controls
                self.prev_btn.config(state=tk.NORMAL)
                self.next_btn.config(state=tk.NORMAL)
                self.run_btn.config(state=tk.NORMAL)
                
                self.update_step_display()
                
                # Auto-switch to All Steps tab to show the full queue
                self.step_notebook.select(1)
                
                messagebox.showinfo("Success", f"Generated {len(self.steps)} steps successfully!")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate steps:\\n{str(e)}")
    
    def update_step_display(self):
        """Update step navigation display and populate steps queue"""
        if not self.steps:
            self.step_info_label.config(text="No steps loaded")
            self.current_step_label.config(text="No step selected")
            self.step_details.delete(1.0, tk.END)
            self.steps_listbox.delete(0, tk.END)
            return
        
        current_index = self.execution_engine.current_step_index
        total_steps = len(self.steps)
        
        self.step_info_label.config(text=f"Step {current_index  } of {total_steps}")
        
        # Update current step display
        if 0 <= current_index < total_steps:
            step = self.steps[current_index]
            
            # Update current step label
            self.current_step_label.config(text=f"Step {current_index  }: {step['operation'].upper()}")
            
            step_text = f"""Description:
{step['description']}

Parameters:
"""
            
            for key, value in step.get('parameters', {}).items():
                step_text += f"  • {key}: {value}\\n"
            
            self.step_details.delete(1.0, tk.END)
            self.step_details.insert(1.0, step_text)
        
        # Populate all steps in the listbox
        self.steps_listbox.delete(0, tk.END)
        for i, step in enumerate(self.steps):
            status_icon = "▶" if i == current_index else ("✓" if i < current_index else "○")
            step_summary = f"{status_icon} {i+1:3d}. {step['operation']}: {step['description'][:40]}..."
            self.steps_listbox.insert(tk.END, step_summary)
            
            # Color code the items
            if i == current_index:
                self.steps_listbox.itemconfig(i, {'bg': 'lightgreen', 'fg': 'darkgreen'})
            elif i < current_index:
                self.steps_listbox.itemconfig(i, {'bg': 'lightgray', 'fg': 'darkblue'})
            else:
                self.steps_listbox.itemconfig(i, {'bg': 'white', 'fg': 'black'})
        
        # Scroll to current step
        if current_index < total_steps:
            self.steps_listbox.see(current_index)
            self.steps_listbox.selection_clear(0, tk.END)
            self.steps_listbox.selection_set(current_index)
        
        # Update button states
        self.prev_btn.config(state=tk.NORMAL if current_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if current_index < total_steps - 1 else tk.DISABLED)
    
    def prev_step(self):
        """Navigate to previous step"""
        if self.execution_engine.step_backward():
            self.update_step_display()
    
    def next_step(self):
        """Navigate to next step and execute it"""
        if self.execution_engine.step_forward():
            # Execute the current step to move hardware to correct position
            result = self.execution_engine.execute_current_step()
            
            # Track operation states for visual updates
            if (self.execution_engine.current_step_index < len(self.steps)):
                current_step = self.steps[self.execution_engine.current_step_index]
                step_desc = current_step.get('description', '')
                self.track_operation_from_step(step_desc)
            
            self.update_step_display()
    
    def run_execution(self):
        """Start execution"""
        if not self.steps:
            messagebox.showwarning("Warning", "Please generate steps first")
            return
        
        if self.execution_engine.start_execution():
            self.run_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            
            self.operation_label.config(text="Execution Started", fg='green')
    
    def pause_execution(self):
        """Pause execution"""
        if self.execution_engine.pause_execution():
            self.run_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            
            self.operation_label.config(text="Execution Paused", fg='orange')
        
        elif self.execution_engine.resume_execution():
            self.run_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            
            self.operation_label.config(text="Execution Resumed", fg='green')
    
    def stop_execution(self):
        """Stop execution"""
        if self.execution_engine.stop_execution():
            self.run_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            
            self.operation_label.config(text="Execution Stopped", fg='red')
    
    def reset_execution(self):
        """Reset execution and simulation"""
        self.stop_execution()  # Stop if running
        
        if self.execution_engine.reset_execution():
            self.update_step_display()
            reset_hardware()
            
            # Reset hardware position to paper starting point (15, 15)
            from mock_hardware import move_x, move_y
            move_x(15.0)
            move_y(15.0)
            self.update_position_display()
            
            # Reset simulation - clear all operation states
            if self.current_program:
                self.initialize_operation_states(self.current_program)
                self.refresh_work_lines_colors()  # Reset all colors to pending
            
            self.operation_label.config(text="System Reset - Simulation Cleared", fg='blue')
            
            # Clear steps display
            self.current_step_label.config(text="No step selected")
            self.steps_listbox.delete(0, tk.END)
    
    # Sensor trigger handlers
    def trigger_x_left(self):
        """Trigger X left sensor"""
        trigger_x_left_sensor()
        self.x_left_btn.config(bg='red')
        self.root.after(200, lambda: self.x_left_btn.config(bg='orange'))
    
    def trigger_x_right(self):
        """Trigger X right sensor"""  
        trigger_x_right_sensor()
        self.x_right_btn.config(bg='red')
        self.root.after(200, lambda: self.x_right_btn.config(bg='orange'))
    
    def trigger_y_top(self):
        """Trigger Y top sensor"""
        trigger_y_top_sensor()
        self.y_top_btn.config(bg='red')
        self.root.after(200, lambda: self.y_top_btn.config(bg='purple'))
    
    def trigger_y_bottom(self):
        """Trigger Y bottom sensor"""
        trigger_y_bottom_sensor()
        self.y_bottom_btn.config(bg='red')
        self.root.after(200, lambda: self.y_bottom_btn.config(bg='purple'))
    
    def on_execution_status(self, status, info=None):
        """Handle execution status updates"""
        if info:
            progress = info.get('progress', 0)
            step_desc = info.get('step_description', '')
            
            # Update progress bar
            self.progress['value'] = progress
            self.progress_label.config(text=f"{progress:.1f}% - {step_desc[:20]}...")
            self.system_status_label.config(text=f"{progress:.1f}% - {step_desc[:40]}...")
            
            # Update operation label
            if status == "executing":
                self.operation_label.config(text=f"Executing: {step_desc[:40]}...", fg='green')
                
                # Track operation states during execution for real-time color updates
                self.track_operation_from_step(step_desc)
            
            # Update step display if not manually navigating
            self.update_step_display()
        
        # Update button states based on execution status
        if status == "completed":
            self.run_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.operation_label.config(text="Execution Completed!", fg='blue')
            self.progress_label.config(text="Complete!")
            self.system_status_label.config(text="Execution completed successfully!")
        
        elif status == "stopped":
            self.run_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.operation_label.config(text="Execution Stopped", fg='red')
            self.system_status_label.config(text="Execution stopped by user")
    
    def update_position_display(self):
        """Update position display and canvas"""
        try:
            # Get current position from hardware
            current_x = get_current_x()
            current_y = get_current_y()
            
            # Update position label
            self.position_label.config(text=f"Position: X={current_x:.1f}, Y={current_y:.1f}")
            
            # Update canvas tool position
            max_y_cm = self.settings.get("simulation", {}).get("max_display_y", 80)
            canvas_x = self.offset_x + current_x * self.scale_x
            canvas_y = self.offset_y + (max_y_cm - current_y) * self.scale_y  # Invert Y for canvas
            
            # Update main tool position circle
            if 'tool_position' in self.canvas_objects:
                self.canvas.coords(self.canvas_objects['tool_position'], 
                                 canvas_x - 6, canvas_y - 6, canvas_x + 6, canvas_y + 6)
            
            # Update tool crosshair
            if 'tool_crosshair_h' in self.canvas_objects:
                self.canvas.coords(self.canvas_objects['tool_crosshair_h'], 
                                 canvas_x - 10, canvas_y, canvas_x + 10, canvas_y)
            if 'tool_crosshair_v' in self.canvas_objects:
                self.canvas.coords(self.canvas_objects['tool_crosshair_v'], 
                                 canvas_x, canvas_y - 10, canvas_x, canvas_y + 10)
            
            # Enhanced position indicators with operation context
            # X-axis position indicator (vertical line on bottom edge) - BLUE for X
            if 'x_position_line' in self.canvas_objects:
                self.canvas.delete(self.canvas_objects['x_position_line'])
            if 'x_position_label' in self.canvas_objects:
                self.canvas.delete(self.canvas_objects['x_position_label'])
                
            # X position line on bottom edge
            x_line_y = self.canvas_height - self.offset_y
            self.canvas_objects['x_position_line'] = self.canvas.create_line(
                canvas_x, x_line_y - 10, canvas_x, x_line_y + 10,
                fill='blue', width=3, tags="position_indicators"
            )
            self.canvas_objects['x_position_label'] = self.canvas.create_text(
                canvas_x, x_line_y + 20, text=f"X: {current_x:.1f}cm",
                font=('Arial', 8, 'bold'), fill='blue', tags="position_indicators"
            )
            
            # Y-axis position indicator (horizontal line on left edge) - RED for Y  
            if 'y_position_line' in self.canvas_objects:
                self.canvas.delete(self.canvas_objects['y_position_line'])
            if 'y_position_label' in self.canvas_objects:
                self.canvas.delete(self.canvas_objects['y_position_label'])
                
            # Y position line on left edge
            y_line_x = self.offset_x
            self.canvas_objects['y_position_line'] = self.canvas.create_line(
                y_line_x - 10, canvas_y, y_line_x + 10, canvas_y,
                fill='red', width=3, tags="position_indicators"
            )
            self.canvas_objects['y_position_label'] = self.canvas.create_text(
                y_line_x - 30, canvas_y, text=f"Y: {current_y:.1f}cm",
                font=('Arial', 8, 'bold'), fill='red', tags="position_indicators"
            )
            
            # Add operation context indicator
            self.update_operation_context_display(canvas_x, canvas_y, current_x, current_y)
            
            # Update tool status indicators (get from hardware state)
            from mock_hardware import get_hardware_status
            status = get_hardware_status()
            
            # Update canvas tool status texts
            if 'line_marker' in self.canvas_objects:
                marker_status = "DOWN" if status['line_marker'] == 'down' else "UP"
                marker_color = "red" if status['line_marker'] == 'down' else "green"
                self.canvas.itemconfig(self.canvas_objects['line_marker'], 
                                     text=f"Line Marker: {marker_status}", fill=marker_color)
            
            if 'line_cutter' in self.canvas_objects:
                cutter_status = "DOWN" if status['line_cutter'] == 'down' else "UP"
                cutter_color = "red" if status['line_cutter'] == 'down' else "green"
                self.canvas.itemconfig(self.canvas_objects['line_cutter'], 
                                     text=f"Line Cutter: {cutter_status}", fill=cutter_color)
            
            if 'row_marker' in self.canvas_objects:
                marker_status = "DOWN" if status['row_marker'] == 'down' else "UP"
                marker_color = "red" if status['row_marker'] == 'down' else "green"
                self.canvas.itemconfig(self.canvas_objects['row_marker'], 
                                     text=f"Row Marker: {marker_status}", fill=marker_color)
            
            if 'row_cutter' in self.canvas_objects:
                cutter_status = "DOWN" if status['row_cutter'] == 'down' else "UP"
                cutter_color = "red" if status['row_cutter'] == 'down' else "green"
                self.canvas.itemconfig(self.canvas_objects['row_cutter'], 
                                     text=f"Row Cutter: {cutter_status}", fill=cutter_color)
        
        except Exception as e:
            # Handle any errors silently for Pi optimization
            pass
    
    def update_operation_context_display(self, canvas_x, canvas_y, current_x, current_y):
        """Display operation context and position indicators"""
        if not self.current_program:
            return
            
        # Clear previous context indicators
        if 'context_indicator' in self.canvas_objects:
            self.canvas.delete(self.canvas_objects['context_indicator'])
        if 'context_label' in self.canvas_objects:
            self.canvas.delete(self.canvas_objects['context_label'])
            
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
        self.canvas_objects['context_indicator'] = self.canvas.create_oval(
            canvas_x - indicator_size, canvas_y - indicator_size, 
            canvas_x + indicator_size, canvas_y + indicator_size,
            outline=color, width=3, dash=(4, 4), tags="position_indicators"
        )
        
        # Context label with operation info
        self.canvas_objects['context_label'] = self.canvas.create_text(
            canvas_x, canvas_y - 25, text=f"{symbol} {context['description']}",
            font=('Arial', 8, 'bold'), fill=color, tags="position_indicators"
        )
    
    def determine_operation_context(self, x, y):
        """Determine what operation the tool is positioned for"""
        if not self.current_program:
            return {'type': 'idle', 'description': 'No program'}
            
        PAPER_OFFSET_Y = 15.0
        
        # Check current step to determine operation phase
        current_step_desc = ""
        if (self.execution_engine and 
            self.execution_engine.current_step_index < len(self.steps)):
            current_step = self.steps[self.execution_engine.current_step_index]
            current_step_desc = current_step.get('description', '').lower()
        
        # Check if at cutting positions first, but be position-accurate
        top_cut_pos = PAPER_OFFSET_Y + self.current_program.high
        bottom_cut_pos = PAPER_OFFSET_Y  # Bottom cut at paper starting position
        
        if abs(y - top_cut_pos) < 0.5:
            return {'type': 'cutting', 'description': 'Top Edge Cut'}
        elif abs(y - bottom_cut_pos) < 0.5:
            # Check if we're currently in a bottom cutting step AND actually at bottom position
            if ('cut bottom edge' in current_step_desc or 'bottom cut' in current_step_desc):
                return {'type': 'cutting', 'description': 'Bottom Edge Cut'}
            # If at bottom position but not in cutting step, treat as line marking
        
        # Check if at line marking positions
        first_line_y = PAPER_OFFSET_Y + self.current_program.high - self.current_program.top_padding
        last_line_y = PAPER_OFFSET_Y  # Last line at paper starting position
        
        if first_line_y >= y >= last_line_y:
            # Calculate which line this might be based on actual position
            actual_lines = self.current_program.number_of_lines  
            if actual_lines > 1:
                line_spacing = (first_line_y - last_line_y) / (actual_lines - 1)
                line_index = round((first_line_y - y) / line_spacing) + 1
                if 1 <= line_index <= actual_lines:
                    return {'type': 'line_marking', 'description': f'Line {line_index}/{actual_lines}'}
        
        return {'type': 'moving', 'description': 'Moving/Positioning'}
    
    def schedule_position_update(self):
        """Schedule regular position updates"""
        self.update_position_display()
        self.root.after(500, self.schedule_position_update)  # Update every 500ms
    
    def on_step_select(self, event):
        """Handle step selection from the steps listbox"""
        if not self.steps:
            return
            
        selection = self.steps_listbox.curselection()
        if selection:
            step_index = selection[0]
            if 0 <= step_index < len(self.steps):
                step = self.steps[step_index]
                
                # Show step details in current tab
                self.step_notebook.select(0)  # Switch to Current tab
                self.current_step_label.config(text=f"Preview Step {step_index  }: {step['operation'].upper()}")
                
                step_text = f"""Description:
{step['description']}

Parameters:
"""
                
                for key, value in step.get('parameters', {}).items():
                    step_text += f"  • {key}: {value}\n"
                
                self.step_details.delete(1.0, tk.END)
                self.step_details.insert(1.0, step_text)

def main():
    """Main application entry point"""
    root = tk.Tk()
    
    try:
        app = ScratchDeskGUI(root)
        root.mainloop()
    except KeyboardInterrupt:
        print("\\nApplication interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")
        messagebox.showerror("Fatal Error", f"Application error:\\n{str(e)}")

if __name__ == "__main__":
    main()
import tkinter as tk
from tkinter import ttk


class CenterPanel:
    """Center panel for desk simulation canvas"""
    
    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create the canvas and related widgets"""
        # Title
        tk.Label(self.parent_frame, text="DESK SIMULATION", font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Create scrollable canvas frame
        canvas_container = tk.Frame(self.parent_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Canvas for desk simulation - use settings dimensions but make scrollable
        canvas_width = self.main_app.settings.get("gui_settings", {}).get("canvas_width", 600)
        canvas_height = self.main_app.settings.get("gui_settings", {}).get("canvas_height", 400)
        
        # Limit canvas size to fit in window
        max_canvas_width = 900  # Leave room for panels
        max_canvas_height = 600  # Leave room for bottom controls
        
        display_width = min(canvas_width, max_canvas_width)
        display_height = min(canvas_height, max_canvas_height)
        
        # Create canvas with scrollbars if needed
        self.main_app.canvas = tk.Canvas(canvas_container, width=display_width, height=display_height, 
                               bg='white', relief=tk.SUNKEN, bd=1,
                               scrollregion=(0, 0, canvas_width, canvas_height))
        
        # Add scrollbars if canvas is larger than display
        if canvas_width > max_canvas_width:
            h_scrollbar = tk.Scrollbar(canvas_container, orient=tk.HORIZONTAL, command=self.main_app.canvas.xview)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            self.main_app.canvas.config(xscrollcommand=h_scrollbar.set)
        
        if canvas_height > max_canvas_height:
            v_scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=self.main_app.canvas.yview)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.main_app.canvas.config(yscrollcommand=v_scrollbar.set)
        
        self.main_app.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Store actual canvas dimensions for calculations
        self.main_app.actual_canvas_width = canvas_width
        self.main_app.actual_canvas_height = canvas_height
        
        # Initialize canvas elements
        self.main_app.canvas_manager.setup_canvas()
        
        # Work Operations Status Box (above System Ready)
        self.create_work_operations_status()
        
        # Current Operation Display
        self.operation_label = tk.Label(self.parent_frame, text="System Ready", 
                                       font=('Arial', 11, 'bold'), fg='blue')
        self.operation_label.pack(pady=5)
        
        # Progress Bar (under System Ready)
        self.create_progress_section()
        
        # Store references in main app for other components
        self.main_app.operation_label = self.operation_label
    
    def create_work_operations_status(self):
        """Create work operations status row-box above System Ready"""
        # Work operations frame
        ops_frame = tk.Frame(self.parent_frame, relief=tk.RIDGE, bd=2, bg='lightblue')
        ops_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Title
        tk.Label(ops_frame, text="📋 WORK OPERATIONS STATUS", 
                font=('Arial', 10, 'bold'), bg='lightblue', fg='darkblue').pack(pady=2)
        
        # Operations row
        ops_row = tk.Frame(ops_frame, bg='lightblue')
        ops_row.pack(fill=tk.X, padx=5, pady=2)
        
        # MARK Operations Column
        mark_frame = tk.Frame(ops_row, bg='lightblue')
        mark_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        operation_colors = self.main_app.settings.get("operation_colors", {})
        mark_colors = operation_colors.get("mark", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })
        cut_colors = operation_colors.get("cuts", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })
        
        tk.Label(mark_frame, text="✏️ MARK", font=('Arial', 9, 'bold'), 
                bg='lightblue', fg='darkblue').pack()
        
        self.mark_status_frame = tk.Frame(mark_frame, bg='lightblue')
        self.mark_status_frame.pack(pady=2)
        
        # Create colored indicators for mark operations
        self.create_status_indicators(self.mark_status_frame, [
            ("Ready", mark_colors['pending']), ("Working", mark_colors['in_progress']), ("Done", mark_colors['completed'])
        ])
        
        # CUT Operations Column  
        cut_frame = tk.Frame(ops_row, bg='lightblue')
        cut_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(cut_frame, text="✂️ CUT", font=('Arial', 9, 'bold'), 
                bg='lightblue', fg='darkblue').pack()
        
        self.cut_status_frame = tk.Frame(cut_frame, bg='lightblue')
        self.cut_status_frame.pack(pady=2)
        
        # Create colored indicators for cut operations
        self.create_status_indicators(self.cut_status_frame, [
            ("Ready", cut_colors['pending']), ("Working", cut_colors['in_progress']), ("Done", cut_colors['completed'])
        ])
    
    def create_status_indicators(self, parent, status_list):
        """Create colored line indicators for operation statuses"""
        for status_text, color in status_list:
            indicator_frame = tk.Frame(parent, bg='lightblue')
            indicator_frame.pack(side=tk.LEFT, padx=3)
            
            # Colored line indicator
            canvas = tk.Canvas(indicator_frame, width=15, height=8, bg='lightblue', highlightthickness=0)
            canvas.pack()
            canvas.create_line(2, 4, 13, 4, fill=color, width=3)
            
            # Status text
            tk.Label(indicator_frame, text=status_text, font=('Arial', 7), 
                    bg='lightblue', fg=color).pack()
    
    def create_progress_section(self):
        """Create progress bar section under System Ready"""
        # Progress frame
        progress_frame = tk.Frame(self.parent_frame, bg='white')
        progress_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X)
        
        # Progress text
        self.progress_text = tk.Label(progress_frame, text="0% Complete", 
                                     font=('Arial', 9), fg='darkblue', bg='white')
        self.progress_text.pack(pady=2)
        
        # Store references in main app
        self.main_app.progress = self.progress
        self.main_app.progress_text = self.progress_text
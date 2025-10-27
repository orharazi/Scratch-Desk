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

        # Work Operations Status Box (moved above canvas for visibility)
        self.create_work_operations_status()

        # Create canvas frame - will expand to fill available space
        canvas_container = tk.Frame(self.parent_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True, pady=5)

        # Canvas for desk simulation - use settings dimensions as defaults
        canvas_width = self.main_app.settings.get("gui_settings", {}).get("canvas_width", 900)
        canvas_height = self.main_app.settings.get("gui_settings", {}).get("canvas_height", 700)

        # Create canvas that fills available space
        self.main_app.canvas = tk.Canvas(canvas_container, bg='white', relief=tk.SUNKEN, bd=2)
        self.main_app.canvas.pack(fill=tk.BOTH, expand=True)

        # Store actual canvas dimensions - will be updated after window is sized
        self.main_app.actual_canvas_width = canvas_width
        self.main_app.actual_canvas_height = canvas_height

        # Bind canvas resize event to update dimensions and redraw
        self.main_app.canvas.bind('<Configure>', self.on_canvas_resize)
        
        # Initialize canvas elements
        self.main_app.canvas_manager.setup_canvas()

        # Current Operation Display (below canvas)
        self.operation_label = tk.Label(self.parent_frame, text="System Ready",
                                       font=('Arial', 11, 'bold'), fg='blue')
        self.operation_label.pack(pady=5)

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

    def on_canvas_resize(self, event):
        """Handle canvas resize - update dimensions and scaling"""
        if not hasattr(self, '_resize_pending') or not self._resize_pending:
            self._resize_pending = True
            # Debounce rapid resize events
            self.main_app.root.after(200, self._handle_canvas_resize, event.width, event.height)

    def _handle_canvas_resize(self, width, height):
        """Actually handle the canvas resize after debounce"""
        self._resize_pending = False

        # Update canvas dimensions
        old_width = self.main_app.actual_canvas_width
        old_height = self.main_app.actual_canvas_height

        self.main_app.actual_canvas_width = width
        self.main_app.actual_canvas_height = height
        self.main_app.canvas_width = width
        self.main_app.canvas_height = height

        # Only redraw if size changed significantly (more than 10 pixels)
        if abs(width - old_width) > 10 or abs(height - old_height) > 10:
            # Recalculate scale factors to fit workspace in available space
            sim_settings = self.main_app.settings.get("simulation", {})
            max_x_cm = sim_settings.get("max_display_x", 120)
            max_y_cm = sim_settings.get("max_display_y", 80)

            # Calculate scale factors to fit workspace with margins
            margin_x = 100  # Leave 50px on each side
            margin_y = 100  # Leave 50px top and bottom

            available_width = width - margin_x
            available_height = height - margin_y

            # Calculate scale to fit both dimensions
            scale_x = available_width / max_x_cm
            scale_y = available_height / max_y_cm

            # Use the smaller scale to ensure both dimensions fit
            scale = min(scale_x, scale_y)

            # Update scale factors
            self.main_app.scale_x = max(3.0, scale)  # Minimum scale of 3.0
            self.main_app.scale_y = max(3.0, scale)

            # Update offsets to center the workspace
            workspace_width = max_x_cm * self.main_app.scale_x
            workspace_height = max_y_cm * self.main_app.scale_y
            self.main_app.offset_x = (width - workspace_width) / 2
            self.main_app.offset_y = (height - workspace_height) / 2

            # Redraw canvas
            self.main_app.canvas_manager.setup_canvas()

            # Update work lines if program is loaded
            if self.main_app.current_program:
                self.main_app.canvas_manager.update_work_lines_display(self.main_app.current_program)
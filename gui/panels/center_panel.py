import tkinter as tk
from tkinter import ttk
from core.logger import get_logger


class CenterPanel:
    """Center panel for desk simulation canvas"""
    
    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        self.logger = get_logger()
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create the canvas and related widgets"""
        # Title
        tk.Label(self.parent_frame, text="DESK SIMULATION", font=('Arial', 12, 'bold')).pack(pady=5)

        # Create canvas container with horizontal layout
        canvas_container = tk.Frame(self.parent_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create responsive canvas that fills available space
        self.main_app.canvas = tk.Canvas(canvas_container, bg='white', relief=tk.SUNKEN, bd=2)
        self.main_app.canvas.pack(fill=tk.BOTH, expand=True)

        # Initialize dimensions - will be updated immediately by responsive scaling
        # Don't use settings.json values - calculate based on actual window size
        self.main_app.actual_canvas_width = 900  # Placeholder, will be overwritten
        self.main_app.actual_canvas_height = 700  # Placeholder, will be overwritten

        # Flag to prevent canvas setup until we calculate proper scaling
        self._canvas_initialized = False

        # Flag to ignore Configure events during initialization
        self._ignore_configure_events = True

        # Bind resize event to update canvas when window size changes
        self.main_app.canvas.bind('<Configure>', self._on_canvas_resize)

        # Flag to prevent resize loop
        self._resize_scheduled = False

        # Current Operation Display (below canvas)
        self.operation_label = tk.Label(self.parent_frame, text="System Ready",
                                       font=('Arial', 11, 'bold'), fg='blue')
        self.operation_label.pack(pady=5)

        # Store references in main app for other components
        self.main_app.operation_label = self.operation_label

    def finalize_canvas_setup(self):
        """Called after all panels are created - wait for window to be fully visible"""
        self.logger.debug(" finalize_canvas_setup() called - waiting for window visibility", category="gui")

        def wait_for_window_visible():
            # Check if window is fully visible/mapped
            if self.main_app.root.winfo_viewable():
                self.logger.debug(" Window is visible - getting canvas dimensions", category="gui")
                # Get canvas dimensions
                width = self.main_app.canvas.winfo_width()
                height = self.main_app.canvas.winfo_height()
                self.logger.debug(f" Canvas dimensions: {width}x{height}", category="gui")

                # If we have good dimensions, initialize now
                # Lower threshold to accommodate various screen sizes
                if width > 1 and height > 200:
                    self.logger.debug(" Good dimensions - initializing canvas", category="gui")
                    self._canvas_initialized = True
                    self._update_canvas_scaling(width, height)
                    self.main_app.canvas_manager.setup_canvas()
                    self.logger.debug(f" Canvas initialized with scale={self.main_app.scale_x:.2f}", category="gui")

                    # Create Work Operations Status overlay AFTER canvas is fully initialized
                    self.create_work_operations_overlay()
                    self.logger.debug(" Work Operations Status overlay created", category="gui")

                    # Enable Configure events for future window resizes
                    self._ignore_configure_events = False
                else:
                    # Dimensions not ready yet, try again
                    self.logger.debug(f" Dimensions not ready - checking again in 50ms", category="gui")
                    self.main_app.root.after(50, wait_for_window_visible)
            else:
                # Window not visible yet, check again
                self.logger.debug(" Window not visible yet - checking again in 50ms", category="gui")
                self.main_app.root.after(50, wait_for_window_visible)

        # Start checking for window visibility
        self.main_app.root.after(50, wait_for_window_visible)
    
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
    
    def create_work_operations_status(self, parent):
        """Create work operations status box on left side of canvas"""
        # Work operations frame - vertical on left side
        ops_frame = tk.Frame(parent, relief=tk.RIDGE, bd=2, bg='lightblue', width=150)
        ops_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        ops_frame.pack_propagate(False)  # Maintain fixed width

        # Title
        tk.Label(ops_frame, text="📋 WORK\nOPERATIONS\nSTATUS",
                font=('Arial', 8, 'bold'), bg='lightblue', fg='darkblue').pack(pady=5)

        operation_colors = self.main_app.settings.get("operation_colors", {})
        mark_colors = operation_colors.get("mark", {
            "pending": "#880808",
            "in_progress": "#FF8800",
            "completed": "#00AA00"
        })
        cut_colors = operation_colors.get("cuts", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })

        # MARK Operations
        mark_frame = tk.Frame(ops_frame, bg='lightblue')
        mark_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(mark_frame, text="✏️ MARK", font=('Arial', 8, 'bold'),
                bg='lightblue', fg='darkblue').pack()

        self.mark_status_frame = tk.Frame(mark_frame, bg='lightblue')
        self.mark_status_frame.pack(pady=2)

        self.create_status_indicators(self.mark_status_frame, [
            ("Ready", mark_colors['pending']),
            ("Work", mark_colors['in_progress']),
            ("Done", mark_colors['completed'])
        ])

        # CUT Operations
        cut_frame = tk.Frame(ops_frame, bg='lightblue')
        cut_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(cut_frame, text="✂️ CUT", font=('Arial', 8, 'bold'),
                bg='lightblue', fg='darkblue').pack()

        self.cut_status_frame = tk.Frame(cut_frame, bg='lightblue')
        self.cut_status_frame.pack(pady=2)

        self.create_status_indicators(self.cut_status_frame, [
            ("Ready", cut_colors['pending']),
            ("Work", cut_colors['in_progress']),
            ("Done", cut_colors['completed'])
        ])

    def create_status_indicators(self, parent, status_list):
        """Create colored line indicators for operation statuses - vertical layout"""
        for status_text, color in status_list:
            indicator_frame = tk.Frame(parent, bg='lightblue')
            indicator_frame.pack(pady=2)

            # Colored line indicator
            canvas = tk.Canvas(indicator_frame, width=80, height=4, bg='lightblue', highlightthickness=0)
            canvas.pack()
            canvas.create_line(2, 2, 78, 2, fill=color, width=3)

            # Status text
            tk.Label(indicator_frame, text=status_text, font=('Arial', 7),
                    bg='lightblue', fg=color).pack()

    def create_work_operations_overlay(self):
        """Create Work Operations Status as compact overlay at top of canvas"""
        # Get operation colors from settings
        operation_colors = self.main_app.settings.get("operation_colors", {})
        mark_colors = operation_colors.get("mark", {
            "pending": "#880808",
            "in_progress": "#FF8800",
            "completed": "#00AA00"
        })
        cut_colors = operation_colors.get("cuts", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })

        # Create overlay frame at top-left of canvas using canvas window
        # Use slightly larger fonts and padding for better visibility
        overlay_frame = tk.Frame(self.main_app.canvas, bg='#E8F4F8', relief=tk.RAISED, bd=3)

        # Title row - slightly larger
        title_label = tk.Label(
            overlay_frame,
            text="📋 WORK OPERATIONS STATUS",
            font=('Arial', 9, 'bold'),
            bg='#E8F4F8',
            fg='black',
            padx=8,
            pady=3
        )
        title_label.pack()

        # Operations in horizontal row
        ops_row = tk.Frame(overlay_frame, bg='#E8F4F8')
        ops_row.pack(padx=8, pady=4)

        # MARK Operations
        mark_frame = tk.Frame(ops_row, bg='#E8F4F8')
        mark_frame.pack(side=tk.LEFT, padx=8)

        tk.Label(mark_frame, text="✏️ MARK", font=('Arial', 8, 'bold'),
                bg='#E8F4F8', fg='black').pack()

        mark_indicators = tk.Frame(mark_frame, bg='#E8F4F8')
        mark_indicators.pack(pady=2)

        # Horizontal compact indicators for MARK - slightly larger
        for status_text, color in [("Ready", mark_colors['pending']),
                                   ("Work", mark_colors['in_progress']),
                                   ("Done", mark_colors['completed'])]:
            ind = tk.Frame(mark_indicators, bg='#E8F4F8')
            ind.pack(side=tk.LEFT, padx=3)

            # Small colored line - slightly larger
            c = tk.Canvas(ind, width=20, height=4, bg='#E8F4F8', highlightthickness=0)
            c.pack()
            c.create_line(2, 2, 18, 2, fill=color, width=3)

            # Label - slightly larger
            tk.Label(ind, text=status_text, font=('Arial', 7),
                    bg='#E8F4F8', fg=color).pack()

        # Separator
        tk.Frame(ops_row, width=2, bg='gray').pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # CUT Operations
        cut_frame = tk.Frame(ops_row, bg='#E8F4F8')
        cut_frame.pack(side=tk.LEFT, padx=8)

        tk.Label(cut_frame, text="✂️ CUT", font=('Arial', 8, 'bold'),
                bg='#E8F4F8', fg='black').pack()

        cut_indicators = tk.Frame(cut_frame, bg='#E8F4F8')
        cut_indicators.pack(pady=2)

        # Horizontal compact indicators for CUT - slightly larger
        for status_text, color in [("Ready", cut_colors['pending']),
                                   ("Work", cut_colors['in_progress']),
                                   ("Done", cut_colors['completed'])]:
            ind = tk.Frame(cut_indicators, bg='#E8F4F8')
            ind.pack(side=tk.LEFT, padx=3)

            # Small colored line - slightly larger
            c = tk.Canvas(ind, width=20, height=4, bg='#E8F4F8', highlightthickness=0)
            c.pack()
            c.create_line(2, 2, 18, 2, fill=color, width=3)

            # Label - slightly larger
            tk.Label(ind, text=status_text, font=('Arial', 7),
                    bg='#E8F4F8', fg=color).pack()

        # Place overlay at top-left corner of canvas - moved down and right slightly to be more visible
        self.ops_overlay_window = self.main_app.canvas.create_window(
            15, 15,
            window=overlay_frame,
            anchor='nw',
            tags='work_ops_overlay'
        )

        # Store reference for potential updates
        self.main_app.work_ops_overlay = overlay_frame

        # Raise overlay to ensure it's on top of all other canvas objects
        self.main_app.canvas.tag_raise('work_ops_overlay')

        self.logger.debug(" Work Operations Status overlay created and raised to top", category="gui")

    def _on_canvas_resize(self, event):
        """Handle canvas resize events - both initial setup and user-initiated resizes"""
        # Ignore all Configure events until window is visible
        if self._ignore_configure_events:
            return

        # Ignore tiny or bad dimensions
        # Lower threshold to accommodate various screen sizes
        if event.width <= 1 or event.height <= 1 or event.height < 200:
            return

        # Handle initial canvas setup (first time we get good dimensions)
        if not self._canvas_initialized:
            self.logger.debug(f" Initial canvas setup with dimensions: {event.width}x{event.height}", category="gui")
            self._canvas_initialized = True
            self._update_canvas_scaling(event.width, event.height)
            self.main_app.canvas_manager.setup_canvas()
            self.logger.debug(f" Canvas initialized with scale={self.main_app.scale_x:.2f}", category="gui")
            return

        # Handle subsequent window resizes with debounce
        if self._resize_scheduled:
            return

        self._resize_scheduled = True
        self.main_app.root.after(150, lambda: self._handle_resize(event.width, event.height))

    def _handle_resize(self, width, height):
        """Actually handle canvas resize after debounce"""
        self._resize_scheduled = False

        # Ignore tiny dimensions during initialization
        if width <= 1 or height <= 1:
            return

        # Check if size actually changed significantly
        if (abs(width - self.main_app.actual_canvas_width) < 5 and
            abs(height - self.main_app.actual_canvas_height) < 5):
            return  # No significant change

        # Update canvas scaling and redraw
        self._update_canvas_scaling(width, height)
        self.main_app.canvas_manager.setup_canvas()

        # Update work lines if program is loaded
        if hasattr(self.main_app, 'current_program') and self.main_app.current_program:
            self.main_app.canvas_manager.update_canvas_paper_area()

    def _update_canvas_scaling(self, width, height):
        """Update canvas dimensions and calculate scale factors to fit entire desk"""
        # Update canvas dimensions
        self.main_app.actual_canvas_width = width
        self.main_app.actual_canvas_height = height
        self.main_app.canvas_width = width
        self.main_app.canvas_height = height

        # Get workspace dimensions and margins from settings
        sim_settings = self.main_app.settings.get("simulation", {})
        gui_settings = self.main_app.settings.get("gui_settings", {})

        max_x_cm = sim_settings.get("max_display_x", 120)
        max_y_cm = sim_settings.get("max_display_y", 80)

        # Get margins from settings
        margin_left = gui_settings.get("canvas_margin_left", 60)
        margin_right = gui_settings.get("canvas_margin_right", 30)
        margin_top = gui_settings.get("canvas_margin_top", 40)
        margin_bottom = gui_settings.get("canvas_margin_bottom", 50)
        min_scale = gui_settings.get("canvas_min_scale", 3.5)

        # Calculate available space
        available_width = max(width - margin_left - margin_right, 200)
        available_height = max(height - margin_top - margin_bottom, 200)

        # Calculate scale factors to fit entire workspace
        scale_x = available_width / max_x_cm
        scale_y = available_height / max_y_cm

        # Use same scale for both axes to maintain aspect ratio
        # Choose the smaller scale to ensure everything fits
        scale = min(scale_x, scale_y)
        scale = max(scale, min_scale)

        # Update scale factors in main app
        self.main_app.scale_x = scale
        self.main_app.scale_y = scale

        # Calculate actual workspace size with this scale
        workspace_width = max_x_cm * scale
        workspace_height = max_y_cm * scale

        # Position workspace with margins - aligned to top-left
        self.main_app.offset_x = margin_left
        self.main_app.offset_y = margin_top

        # If workspace doesn't fill available space, center it
        extra_width = available_width - workspace_width
        extra_height = available_height - workspace_height

        if extra_width > 0:
            self.main_app.offset_x += extra_width / 2
        if extra_height > 0:
            self.main_app.offset_y += extra_height / 2

        self.logger.debug(f" CANVAS SCALING: width={width}, height={height}", category="gui")
        self.logger.debug(f" Margins: L={margin_left}, R={margin_right}, T={margin_top}, B={margin_bottom}", category="gui")
        self.logger.debug(f" Available: {available_width}x{available_height}", category="gui")
        self.logger.debug(f" Workspace: {max_x_cm}x{max_y_cm}cm", category="gui")
        self.logger.debug(f" Scale: {scale:.2f} (min={min_scale})", category="gui")
        self.logger.debug(f" Workspace pixels: {workspace_width:.1f}x{workspace_height:.1f}", category="gui")
        self.logger.debug(f" Offsets: X={self.main_app.offset_x:.1f}, Y={self.main_app.offset_y:.1f}", category="gui")
        self.logger.debug(f" Workspace bottom Y: {self.main_app.offset_y + workspace_height:.1f} (canvas height={height})", category="gui")

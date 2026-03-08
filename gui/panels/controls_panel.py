import tkinter as tk
from tkinter import ttk
from core.step_generator import generate_complete_program_steps, get_step_count_summary
from core.logger import get_logger
from core.translations import t, t_title, rtl, HEBREW_TRANSLATIONS
from core.program_model import translate_validation_error
from core.safety_system import SafetyViolation, check_step_safety


class ControlsPanel:
    """Controls panel (left side in RTL layout) for step navigation and execution controls"""

    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        # Access hardware through main_app
        self.hardware = main_app.hardware
        self.logger = get_logger()

        # Track scheduled callbacks for cleanup during reset
        self.scheduled_callbacks = []

        # Track if execution was stopped mid-run (for continue functionality)
        self._stopped_mid_execution = False
        self._motor_state_at_stop = None

        # Snapshot of program state when steps were last generated (for stale detection)
        self._steps_program_snapshot = None

        # Responsive font sizing based on window width
        self.update_font_sizes()

        self.create_widgets()

    def _safe_move(self, axis, position, description="Manual move", is_setup=False):
        """Move motor with safety check. Returns True if move succeeded, False if blocked.
        Shows safety violation dialog through execution controller if blocked.
        is_setup=True bypasses position-based inter-motor collision rules (LINES_MOTOR_HOME_FOR_ROWS,
        ROWS_MOTOR_HOME_FOR_LINES) which have exclude_setup:true - safe because all tools are
        raised before any restore/navigation move."""
        operation = 'move_x' if axis == 'x' else 'move_y'
        # Prefix with "init:" so safety rules with exclude_setup:true are bypassed
        effective_description = f"init: {description}" if is_setup else description
        step = {
            'operation': operation,
            'parameters': {'position': position},
            'description': effective_description
        }
        try:
            check_step_safety(step)
        except SafetyViolation as e:
            self.logger.error(f"SAFETY BLOCK: Cannot {operation} to {position} - {e.safety_code}", category="gui")
            # Show safety dialog through execution controller
            if hasattr(self.main_app, 'execution_controller'):
                self.main_app.execution_controller.handle_safety_violation({
                    'step': step,
                    'violation_message': e.message,
                    'safety_code': e.safety_code
                })
            return False

        if axis == 'x':
            self.hardware.move_x(position)
        else:
            self.hardware.move_y(position)
        return True

        # Bind to window resize for dynamic font adjustment
        self.main_app.root.bind('<Configure>', self.on_window_resize)

        # Start periodic checkbox state synchronization
        self.schedule_checkbox_sync()
    
    def update_font_sizes(self):
        """Update font sizes based on window dimensions"""
        try:
            window_width = self.main_app.root.winfo_width()
            if window_width < 1000:
                self.title_font = ('Arial', 10, 'bold')
                self.button_font = ('Arial', 8, 'bold')
                self.label_font = ('Arial', 8, 'bold')
                self.text_font = ('Arial', 7)
            elif window_width < 1200:
                self.title_font = ('Arial', 11, 'bold')
                self.button_font = ('Arial', 9, 'bold')
                self.label_font = ('Arial', 9, 'bold')
                self.text_font = ('Arial', 8)
            else:
                self.title_font = ('Arial', 12, 'bold')
                self.button_font = ('Arial', 10, 'bold')
                self.label_font = ('Arial', 10, 'bold')
                self.text_font = ('Arial', 9)
        except:
            # Fallback if window not ready
            self.title_font = ('Arial', 12, 'bold')
            self.button_font = ('Arial', 10, 'bold')
            self.label_font = ('Arial', 10, 'bold')
            self.text_font = ('Arial', 9)
    
    def on_window_resize(self, event):
        """Handle window resize events for responsive updates"""
        if event.widget == self.main_app.root:
            old_fonts = (self.title_font, self.button_font, self.label_font, self.text_font)
            self.update_font_sizes()
            new_fonts = (self.title_font, self.button_font, self.label_font, self.text_font)
            
            # Update fonts if they changed
            if old_fonts != new_fonts:
                self.update_widget_fonts()
    
    def update_widget_fonts(self):
        """Update widget fonts after resize"""
        try:
            if hasattr(self, 'title_label'):
                self.title_label.config(font=self.title_font)
            pass  # placeholder for future font updates
            if hasattr(self, 'step_info_label'):
                self.step_info_label.config(font=self.text_font)
                # Update wraplength based on panel width
                try:
                    panel_width = self.scrollable_frame.winfo_width()
                    if panel_width > 50:  # Valid width
                        self.step_info_label.config(wraplength=max(200, panel_width - 50))
                except:
                    # Fallback if scrollable_frame not ready
                    self.step_info_label.config(wraplength=250)
        except:
            pass  # Ignore errors during font updates
    
    def create_scrollable_frame(self):
        """Create a scrollable frame for the right panel content"""
        # Create scrollbar first
        self.scrollbar = tk.Scrollbar(self.parent_frame, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")
        
        # Create canvas
        self.canvas = tk.Canvas(self.parent_frame, bg='lightblue', highlightthickness=0, 
                               yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Configure scrollbar command
        self.scrollbar.config(command=self.canvas.yview)
        
        # Create the scrollable frame inside canvas
        self.scrollable_frame = tk.Frame(self.canvas, bg='lightblue')
        
        # Create window in canvas for scrollable frame
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure scroll region when frame size changes
        def configure_scroll_region(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        self.scrollable_frame.bind("<Configure>", configure_scroll_region)
        
        # Update scrollable frame width when canvas width changes
        def configure_canvas(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
            
        self.canvas.bind('<Configure>', configure_canvas)
        
        # Bind mousewheel scrolling
        self.bind_mousewheel()
    
    def bind_mousewheel(self):
        """Bind mousewheel scrolling to canvas"""
        def on_mousewheel(event):
            # Handle different platforms
            if event.delta:
                # Windows and MacOS
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                # Linux
                if event.num == 4:
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(1, "units")
        
        def bind_to_mousewheel(event):
            # Bind for different platforms
            self.canvas.bind_all("<MouseWheel>", on_mousewheel)  # Windows/Mac
            self.canvas.bind_all("<Button-4>", on_mousewheel)    # Linux
            self.canvas.bind_all("<Button-5>", on_mousewheel)    # Linux
        
        def unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
        
        self.canvas.bind('<Enter>', bind_to_mousewheel)
        self.canvas.bind('<Leave>', unbind_from_mousewheel)
    
    
    def create_widgets(self):
        """Create all widgets for the right panel - responsive design with scrollbar"""
        # Create scrollable frame
        self.create_scrollable_frame()
        
        # Title with responsive font
        self.title_label = tk.Label(self.scrollable_frame, text=t("CONTROLS & STATUS"), font=self.title_font,
                bg='lightblue', fg='black')
        self.title_label.pack(pady=3)

        # Step Navigation with responsive frame
        nav_frame = tk.Frame(self.scrollable_frame, bg='lightblue')
        nav_frame.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(nav_frame, text=t("Step Navigation:"), font=('Arial', 9, 'bold'),
                bg='lightblue', fg='black').pack()

        nav_buttons = tk.Frame(nav_frame, bg='lightblue')
        nav_buttons.pack(fill=tk.X, pady=2)

        self.next_btn = tk.Button(nav_buttons, text=t("Next ►"), command=self.next_step,
                                 state=tk.DISABLED, width=8, font=('Arial', 8))
        self.next_btn.pack(side=tk.RIGHT)

        self.prev_btn = tk.Button(nav_buttons, text=t("◄ Prev"), command=self.prev_step,
                                 state=tk.DISABLED, width=8, font=('Arial', 8))
        self.prev_btn.pack(side=tk.RIGHT)

        self.step_info_label = tk.Label(nav_frame, text=t("No steps loaded"),
                                       bg='lightblue', fg='black', font=('Arial', 8), wraplength=250,
                                       anchor='e', justify=tk.RIGHT)
        self.step_info_label.pack(pady=2, fill=tk.X)
        
        # Step Details - Improved visibility and layout
        details_frame = tk.Frame(self.scrollable_frame, bg='lightblue')
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)

        tk.Label(details_frame, text=t("Steps Queue:"), font=('Arial', 9, 'bold'),
                bg='lightblue', fg='darkblue').pack()

        # Create tabbed view for current step vs all steps
        notebook = ttk.Notebook(details_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=2)

        # Current Step Tab
        current_tab = tk.Frame(notebook, bg='white')
        notebook.add(current_tab, text=t('Current'))
        
        # Current step info with better formatting - more compact
        current_info_frame = tk.Frame(current_tab, bg='lightgray', relief=tk.RAISED, bd=2)
        current_info_frame.pack(fill=tk.X, padx=5, pady=3)

        self.current_step_label = tk.Label(current_info_frame, text=t("No step selected"),
                                          font=('Arial', 10, 'bold'), bg='lightgray', fg='darkblue',
                                          wraplength=250, anchor='e', justify=tk.RIGHT)
        self.current_step_label.pack(pady=3, fill=tk.X)

        self.step_details = tk.Text(current_tab, height=6, width=25, font=('Arial', 10),
                                   wrap=tk.WORD, bg='white', fg='black', relief=tk.SUNKEN, bd=2)
        step_scroll = tk.Scrollbar(current_tab, orient=tk.VERTICAL)
        step_scroll.pack(side=tk.LEFT, fill=tk.Y)
        self.step_details.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0,5), pady=2)
        self.step_details.config(yscrollcommand=step_scroll.set)
        step_scroll.config(command=self.step_details.yview)
        # Configure RTL tag for Hebrew text
        self.step_details.tag_configure("rtl", justify=tk.RIGHT)

        # All Steps Tab
        all_steps_tab = tk.Frame(notebook, bg='white')
        notebook.add(all_steps_tab, text=t('All Steps'))

        # Steps queue listbox with better visibility - more compact
        queue_frame = tk.Frame(all_steps_tab, bg='white')
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        self.steps_listbox = tk.Listbox(queue_frame, font=('Arial', 9), height=8,
                                       bg='white', fg='black', selectbackground='#4A90E2',
                                       selectforeground='white', relief=tk.SUNKEN, bd=2,
                                       justify=tk.RIGHT)
        queue_scroll = tk.Scrollbar(queue_frame, orient=tk.VERTICAL)
        queue_scroll.pack(side=tk.LEFT, fill=tk.Y)
        self.steps_listbox.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.steps_listbox.config(yscrollcommand=queue_scroll.set)
        queue_scroll.config(command=self.steps_listbox.yview)

        # Selected step details (separate from current step details)
        selected_details_label = tk.Label(all_steps_tab, text=t("Selected Step Details:"),
                                         font=('Arial', 9, 'bold'), bg='white', fg='darkblue')
        selected_details_label.pack(pady=(5, 2))

        self.selected_step_details = tk.Text(all_steps_tab, height=8, width=25, font=('Arial', 10),
                                            wrap=tk.WORD, bg='#f0f0f0', fg='black', relief=tk.SUNKEN, bd=2)
        selected_scroll = tk.Scrollbar(all_steps_tab, orient=tk.VERTICAL)
        selected_scroll.pack(side=tk.LEFT, fill=tk.Y)
        self.selected_step_details.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.selected_step_details.config(yscrollcommand=selected_scroll.set)
        selected_scroll.config(command=self.selected_step_details.yview)
        # Configure RTL tag for Hebrew text
        self.selected_step_details.tag_configure("rtl", justify=tk.RIGHT)
        self.selected_step_details.insert(1.0, t("Click on a step to view details..."), "rtl")
        self.selected_step_details.config(state=tk.DISABLED)

        # Bind listbox selection to show step details
        self.steps_listbox.bind('<<ListboxSelect>>', self.on_step_select)
        
        # Store notebook reference
        self.step_notebook = notebook
        
        # Execution Controls (moved from bottom panel)
        exec_frame = tk.Frame(self.scrollable_frame, bg='lightblue')
        exec_frame.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(exec_frame, text=t("Execution:"), font=('Arial', 9, 'bold'),
                bg='lightblue', fg='darkblue').pack()

        # Execution buttons in single row - Compact
        button_row1 = tk.Frame(exec_frame, bg='lightblue')
        button_row1.pack(pady=2)

        self.reset_btn = tk.Button(button_row1, text=t("🔄 RESET"), command=self.reset_execution,
                                  bg='royalblue', fg='black', font=('Arial', 7, 'bold'),
                                  width=6, relief=tk.RAISED, bd=2,
                                  activebackground='blue', activeforeground='black')
        self.reset_btn.pack(side=tk.RIGHT, padx=1)

        self.stop_btn = tk.Button(button_row1, text=t("⏹ STOP"), command=self.stop_execution,
                                 bg='darkred', fg='black', font=('Arial', 7, 'bold'),
                                 width=6, state=tk.DISABLED, relief=tk.RAISED, bd=2,
                                 activebackground='red', activeforeground='black')
        self.stop_btn.pack(side=tk.RIGHT, padx=1)

        self.pause_btn = tk.Button(button_row1, text=t("⏸ PAUSE"), command=self.pause_execution,
                                  bg='darkorange', fg='black', font=('Arial', 7, 'bold'),
                                  width=6, state=tk.DISABLED, relief=tk.RAISED, bd=2,
                                  activebackground='orange', activeforeground='black')
        # Pause button hidden - stop/continue replaces pause/resume workflow

        self.run_btn = tk.Button(button_row1, text=t("▶ RUN"), command=self.run_execution,
                                bg='darkgreen', fg='black', font=('Arial', 7, 'bold'),
                                width=6, state=tk.DISABLED, relief=tk.RAISED, bd=2,
                                activebackground='green', activeforeground='black')
        self.run_btn.pack(side=tk.RIGHT, padx=1)

        # Progress indicator (compact) with better visibility
        self.progress_label = tk.Label(exec_frame, text=t("Ready"),
                                      bg='lightblue', fg='darkblue', font=('Arial', 7, 'bold'),
                                      anchor='e')
        self.progress_label.pack(pady=1)

        # TEST CONTROLS SECTION - Hardware testing controls (compact layout)
        # Store reference for enabling/disabling based on hardware mode
        self.test_controls_frame = tk.Frame(self.scrollable_frame, relief=tk.RIDGE, bd=2, bg='#F0F8FF')
        self.test_controls_frame.pack(fill=tk.X, padx=10, pady=5)

        # Title with mode indicator
        self.test_controls_title = tk.Label(self.test_controls_frame, text=t("🧪 TEST CONTROLS"),
                font=('Arial', 9, 'bold'), bg='#F0F8FF', fg='#003366')
        self.test_controls_title.pack(pady=(5, 2))

        # Disabled indicator label (hidden by default, shown on real hardware)
        self.test_controls_disabled_label = tk.Label(self.test_controls_frame,
                text=t("⚠️ Disabled - Real Hardware Mode"), font=('Arial', 8, 'italic'),
                bg='#F0F8FF', fg='#CC0000')
        # Don't pack yet - will be shown/hidden by update_test_controls_state()

        # EDGE SENSORS Section
        sensors_frame = tk.Frame(self.test_controls_frame, bg='#F0F8FF')
        sensors_frame.pack(fill=tk.X, padx=8, pady=(0, 5))

        tk.Label(sensors_frame, text=t("📡 Sensors"), font=('Arial', 8, 'bold'),
                bg='#F0F8FF', fg='#003366').pack(anchor='e', pady=(0, 3))

        # X and Y Sensors in separate rows
        sensors_grid = tk.Frame(sensors_frame, bg='#F0F8FF')
        sensors_grid.pack(fill=tk.X)

        # X Sensors (Rows) - Left and Right
        tk.Label(sensors_grid, text=t("X:"), bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=7, anchor='e').grid(row=0, column=0, sticky='e')
        tk.Button(sensors_grid, text=t("◄Left"), bg='#FF6600', fg='black',
                 command=self.trigger_x_left, width=7, font=('Arial', 7, 'bold'),
                 relief=tk.RAISED, bd=2).grid(row=0, column=1, padx=2)
        tk.Button(sensors_grid, text=t("Right►"), bg='#FF6600', fg='black',
                 command=self.trigger_x_right, width=7, font=('Arial', 7, 'bold'),
                 relief=tk.RAISED, bd=2).grid(row=0, column=2, padx=2)

        # Y Sensors (Lines) - Top and Bottom (separate row)
        tk.Label(sensors_grid, text=t("Y:"), bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=7, anchor='e').grid(row=1, column=0, sticky='e')
        tk.Button(sensors_grid, text=t("▲Top"), bg='#8800FF', fg='black',
                 command=self.trigger_y_top, width=7, font=('Arial', 7, 'bold'),
                 relief=tk.RAISED, bd=2).grid(row=1, column=1, padx=2)
        tk.Button(sensors_grid, text=t("Bottom▼"), bg='#8800FF', fg='black',
                 command=self.trigger_y_bottom, width=7, font=('Arial', 7, 'bold'),
                 relief=tk.RAISED, bd=2).grid(row=1, column=2, padx=2)

        # Separator
        tk.Frame(self.test_controls_frame, bg='#7F8C8D', height=2).pack(fill=tk.X, padx=8, pady=5)

        # LIMIT SWITCHES Section
        limit_switches_frame = tk.Frame(self.test_controls_frame, bg='#F0F8FF')
        limit_switches_frame.pack(fill=tk.X, padx=8, pady=(0, 5))

        tk.Label(limit_switches_frame, text=t("🔌 Limit Switches"), font=('Arial', 8, 'bold'),
                bg='#F0F8FF', fg='#003366').pack(anchor='e', pady=(0, 3))

        ls_grid = tk.Frame(limit_switches_frame, bg='#F0F8FF')
        ls_grid.pack(fill=tk.X)

        # Y-Axis Limit Switches
        tk.Label(ls_grid, text=t("Y:"), bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=7, anchor='e').grid(row=0, column=0, sticky='e')
        self.y_top_ls_var = tk.BooleanVar()
        tk.Checkbutton(ls_grid, text=t("Top"), variable=self.y_top_ls_var,
                      command=lambda: self.toggle_ls('y_top'), bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60', width=10, anchor='e').grid(row=0, column=1, padx=2, sticky='e')
        self.y_bottom_ls_var = tk.BooleanVar()
        tk.Checkbutton(ls_grid, text=t("Bottom"), variable=self.y_bottom_ls_var,
                      command=lambda: self.toggle_ls('y_bottom'), bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60', width=10, anchor='e').grid(row=0, column=2, padx=2, sticky='e')

        # X-Axis Limit Switches (separate row)
        tk.Label(ls_grid, text=t("X:"), bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=7, anchor='e').grid(row=1, column=0, sticky='e')
        self.x_right_ls_var = tk.BooleanVar()
        tk.Checkbutton(ls_grid, text=t("Right"), variable=self.x_right_ls_var,
                      command=lambda: self.toggle_ls('x_right'), bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60', width=10, anchor='e').grid(row=1, column=1, padx=2, sticky='e')
        self.x_left_ls_var = tk.BooleanVar()
        tk.Checkbutton(ls_grid, text=t("Left"), variable=self.x_left_ls_var,
                      command=lambda: self.toggle_ls('x_left'), bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60', width=10, anchor='e').grid(row=1, column=2, padx=2, sticky='e')

        # Door Sensor (separate row)
        tk.Label(ls_grid, text=t("Door:"), bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=7, anchor='e').grid(row=2, column=0, sticky='e')
        self.door_sensor_var = tk.BooleanVar(value=False)
        tk.Checkbutton(ls_grid, text=t("Door Sensor"), variable=self.door_sensor_var,
                      command=lambda: self.toggle_ls('rows_door'), bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60', width=10, anchor='e').grid(row=2, column=1, padx=2, sticky='e')

        # Separator
        tk.Frame(self.test_controls_frame, bg='#7F8C8D', height=2).pack(fill=tk.X, padx=8, pady=5)

        # PISTONS Section
        pistons_frame = tk.Frame(self.test_controls_frame, bg='#F0F8FF')
        pistons_frame.pack(fill=tk.X, padx=8, pady=(0, 5))

        tk.Label(pistons_frame, text=t("🔧 Pistons (↓=checked)"), font=('Arial', 8, 'bold'),
                bg='#F0F8FF', fg='#003366').pack(anchor='e', pady=(0, 3))

        # Lines Pistons in grid
        lines_pist_frame = tk.Frame(pistons_frame, bg='#F0F8FF')
        lines_pist_frame.pack(fill=tk.X)

        tk.Label(lines_pist_frame, text=t("Lines:"), bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=7, anchor='e').grid(row=0, column=0, sticky='e')
        self.lines_marker_var = tk.BooleanVar()
        tk.Checkbutton(lines_pist_frame, text=t("Marker"), variable=self.lines_marker_var,
                      command=self.toggle_line_marker, bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60').grid(row=0, column=1, padx=2)
        self.lines_cutter_var = tk.BooleanVar()
        tk.Checkbutton(lines_pist_frame, text=t("Cutter"), variable=self.lines_cutter_var,
                      command=self.toggle_line_cutter, bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60').grid(row=0, column=2, padx=2)
        self.lines_motor_var = tk.BooleanVar()
        tk.Checkbutton(lines_pist_frame, text=t("Motor"), variable=self.lines_motor_var,
                      command=self.toggle_line_motor, bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60').grid(row=0, column=3, padx=2)

        # Rows Pistons
        tk.Label(lines_pist_frame, text=t("Rows:"), bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=7, anchor='e').grid(row=1, column=0, sticky='e')
        self.rows_marker_var = tk.BooleanVar()
        tk.Checkbutton(lines_pist_frame, text=t("Marker"), variable=self.rows_marker_var,
                      command=self.toggle_row_marker, bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60').grid(row=1, column=1, padx=2)
        self.rows_cutter_var = tk.BooleanVar()
        tk.Checkbutton(lines_pist_frame, text=t("Cutter"), variable=self.rows_cutter_var,
                      command=self.toggle_row_cutter, bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60').grid(row=1, column=2, padx=2)

        # System row (Air Pressure)
        tk.Label(lines_pist_frame, text=t("System:"), bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=7, anchor='e').grid(row=2, column=0, sticky='e')
        self.air_pressure_var = tk.BooleanVar()
        tk.Checkbutton(lines_pist_frame, text=t("Air Pressure"), variable=self.air_pressure_var,
                      command=self.toggle_air_pressure, bg='#F0F8FF', fg='black',
                      font=('Arial', 7), selectcolor='#27AE60').grid(row=2, column=1, padx=2)

        # Create dummy labels for backward compatibility (not displayed)
        self.position_label = tk.Label(self.scrollable_frame, text="", bg='lightblue')
        self.sensor_label = tk.Label(self.scrollable_frame, text="", bg='lightblue')
        self.state_label = tk.Label(self.scrollable_frame, text="", bg='lightblue')

        # Store references in main app for other components
        self.main_app.step_info_label = self.step_info_label
        self.main_app.current_step_label = self.current_step_label
        self.main_app.step_details = self.step_details
        self.main_app.steps_listbox = self.steps_listbox
        self.main_app.position_label = self.position_label
        self.main_app.sensor_label = self.sensor_label
        self.main_app.state_label = self.state_label
        self.main_app.progress_label = self.progress_label
        self.main_app.prev_btn = self.prev_btn
        self.main_app.next_btn = self.next_btn
        self.main_app.run_btn = self.run_btn
        self.main_app.pause_btn = self.pause_btn
        self.main_app.stop_btn = self.stop_btn
        self.main_app.reset_btn = self.reset_btn

        # Disable test controls if in real hardware mode
        self.update_test_controls_state()
    
    def _snapshot_program(self, program):
        """Create a hashable snapshot of program parameters for stale detection"""
        if not program:
            return None
        return (
            program.program_number,
            program.high,
            program.number_of_lines,
            program.top_padding,
            program.bottom_padding,
            program.width,
            program.left_margin,
            program.right_margin,
            program.page_width,
            program.number_of_pages,
            program.buffer_between_pages,
            program.repeat_rows,
            program.repeat_lines,
        )

    def generate_steps(self):
        """Generate steps for current program"""
        if not self.main_app.current_program:
            return

        # Don't allow generating steps while execution is running
        if self.main_app.execution_engine.is_running:
            self.logger.warning("Cannot generate steps while execution is running - stop first", category="gui")
            self.main_app.operation_label.config(text=t("Stop execution first!"), fg='red')
            return

        # Validate program parameters (logical consistency)
        program_errors = self.main_app.current_program.validate()
        if program_errors:
            first_error = translate_validation_error(program_errors[0])
            self.logger.error(f"Program validation failed: {program_errors[0]}", category="gui")
            self.main_app.operation_label.config(text=first_error, fg='red')
            self.step_info_label.config(text=t("Program has validation errors"))
            self.run_btn.config(state=tk.DISABLED)
            return

        # Validate paper size fits within work surface
        validation_error = self._validate_paper_size(self.main_app.current_program)
        if validation_error:
            self.logger.error(validation_error, category="gui")
            self.main_app.operation_label.config(text=validation_error, fg='red')
            self.step_info_label.config(text=t("❌ Invalid program - paper too large"))
            self.run_btn.config(state=tk.DISABLED)
            return

        try:
            # Prepare canvas for fresh execution
            if hasattr(self.main_app, 'canvas_manager'):
                self.main_app.canvas_manager.prepare_for_new_program()

            # Generate complete steps for the program
            self.main_app.steps = generate_complete_program_steps(self.main_app.current_program)

            # No premature alert - let execution handle transitional safety checks

            # Reset execution engine with new steps
            self.main_app.execution_engine.load_steps(self.main_app.steps)

            # Clear stop-continue state when generating new steps
            self._stopped_mid_execution = False
            self._motor_state_at_stop = None

            # Update displays
            self.update_step_display()
            
            # Store program snapshot for stale detection
            self._steps_program_snapshot = self._snapshot_program(self.main_app.current_program)

            # Enable navigation if we have steps
            if self.main_app.steps:
                self.next_btn.config(state=tk.NORMAL)
                self.run_btn.config(state=tk.NORMAL)
                # Keep pointer at starting position (15, 15) - don't move to first line yet
            else:
                self.step_info_label.config(text=t("No steps generated"))
                self.run_btn.config(state=tk.DISABLED)
                return
            
            # Get step count summary
            summary = get_step_count_summary(self.main_app.current_program)
            self.step_info_label.config(
                text=t("Generated {steps} steps ({repeats} repetitions)",
                      steps=len(self.main_app.steps),
                      repeats=summary['total_repeats'])
            )

        except Exception as e:
            self.step_info_label.config(text=t("Error generating steps: {error}", error=e))
            self.run_btn.config(state=tk.DISABLED)
    
    def _format_param_value(self, key, value):
        """Format a parameter value with units and Hebrew translation.

        Returns raw Hebrew (logical order) — caller applies rtl() once.
        """
        # Translate the value itself for known enum values (raw Hebrew, no bidi)
        translated_value = HEBREW_TRANSLATIONS.get(str(value), str(value)) if isinstance(value, str) else value

        # Add units for dimension keys
        if key in ('position', 'actual_width', 'actual_height') and isinstance(value, (int, float)):
            return f"{value} {HEBREW_TRANSLATIONS.get('cm', 'cm')}"
        return str(translated_value)

    def _format_parameters(self, params):
        """Format step parameters as clean Hebrew key-value lines"""
        if not params:
            return ""
        lines = []
        for key, value in params.items():
            # Skip internal/description keys that duplicate the description field
            if key == 'description':
                continue
            heb_key = HEBREW_TRANSLATIONS.get(key, key)
            heb_value = self._format_param_value(key, value)
            lines.append(f"{heb_key}: {heb_value}")
        return "\n".join(lines)

    def update_step_display(self):
        """Update the step display with current steps"""
        if not self.main_app.steps:
            self.steps_listbox.delete(0, tk.END)
            self.step_details.config(state=tk.NORMAL)
            self.step_details.delete(1.0, tk.END)
            self.step_details.config(state=tk.DISABLED)
            return
        
        # Update steps listbox
        self.steps_listbox.delete(0, tk.END)
        for i, step in enumerate(self.main_app.steps):
            # Format step for display
            current_index = self.main_app.execution_engine.current_step_index

            if i < current_index:
                status_icon = "✓"  # Completed
            elif i == current_index:
                status_icon = "►"  # Current
            else:
                status_icon = " "  # Pending

            # Use Hebrew operation title and description for UI display
            heb_op = step.get('hebOperationTitle', step['operation'])
            heb_desc = step.get('hebDescription', step['description'])
            step_summary = rtl(f"{status_icon} {i+1}. {heb_op} - {heb_desc[:50]}")
            self.steps_listbox.insert(tk.END, step_summary)

            # Color-code items for better visibility
            if i < current_index:
                self.steps_listbox.itemconfig(i, fg='#28a745')  # Green for completed
            elif i == current_index:
                self.steps_listbox.itemconfig(i, fg='#007bff', selectbackground='#0056b3')  # Blue for current

        # Scroll to current step (but don't select it - let user click to view details)
        current_index = self.main_app.execution_engine.current_step_index
        if 0 <= current_index < len(self.main_app.steps):
            self.steps_listbox.see(current_index)
        
        # Update navigation buttons (only when not in automatic execution)
        engine = self.main_app.execution_engine
        if not (engine.is_running and not engine.is_paused):
            self.prev_btn.config(state=tk.NORMAL if current_index > 0 else tk.DISABLED)
            self.next_btn.config(state=tk.NORMAL if current_index < len(self.main_app.steps) - 1 else tk.DISABLED)
        
        # Update current step info
        if self.main_app.steps and 0 <= current_index < len(self.main_app.steps):
            current_step = self.main_app.steps[current_index]
            # Use Hebrew operation title for UI display
            heb_op = current_step.get('hebOperationTitle', current_step['operation'])
            self.current_step_label.config(text=t("Step {current}/{total}: {operation}",
                                                 current=current_index + 1,
                                                 total=len(self.main_app.steps),
                                                 operation=heb_op))

            # Update step details - clean Hebrew-only display
            heb_desc = current_step.get('hebDescription', current_step['description'])
            details_text = rtl(f"{heb_op}\n\n{heb_desc}\n")
            if current_step.get('parameters'):
                formatted_params = self._format_parameters(current_step['parameters'])
                if formatted_params:
                    details_text += f"\n{rtl(formatted_params)}"

            self.step_details.config(state=tk.NORMAL)
            self.step_details.delete(1.0, tk.END)
            self.step_details.insert(1.0, details_text)
            self.step_details.tag_add("rtl", "1.0", "end")
            self.step_details.config(state=tk.DISABLED)
        else:
            self.current_step_label.config(text=t("No step selected"))
            self.step_details.config(state=tk.NORMAL)
            self.step_details.delete(1.0, tk.END)
            self.step_details.config(state=tk.DISABLED)
    
    def on_step_select(self, event):
        """Handle step selection from listbox - shows in separate details area"""
        selection = self.steps_listbox.curselection()
        if selection and self.main_app.steps:
            step_index = selection[0]
            if 0 <= step_index < len(self.main_app.steps):
                step = self.main_app.steps[step_index]

                # Use Hebrew fields for UI display
                heb_op = step.get('hebOperationTitle', step['operation'])
                heb_desc = step.get('hebDescription', step['description'])

                # Show step details in the SELECTED step details widget (not current step widget)
                total = len(self.main_app.steps)
                details_text = rtl(f"{t('Step')} {step_index + 1}/{total}") + "\n\n"
                details_text += rtl(f"{heb_op}\n\n{heb_desc}\n")

                if step.get('parameters'):
                    formatted_params = self._format_parameters(step['parameters'])
                    if formatted_params:
                        details_text += f"\n{rtl(formatted_params)}\n"

                self.selected_step_details.config(state=tk.NORMAL)
                self.selected_step_details.delete(1.0, tk.END)
                self.selected_step_details.insert(1.0, details_text)
                self.selected_step_details.tag_add("rtl", "1.0", "end")
                self.selected_step_details.config(state=tk.DISABLED)
    
    # Step types that should be skipped during manual navigation (non-actionable or blocking)
    _SKIP_EXECUTE_STEP_TYPES = {'wait_sensor', 'program_start', 'program_complete', 'workflow_separator'}

    def _restore_full_machine_state_to_current(self, keep_line_motor_up=False):
        """Restore full machine state (tools + motors) to match expected state
        at current_step_index. This is the 'back in time' function.

        Scans steps 0..current_step_index-1 (steps already 'completed') to
        determine what state each tool and motor should be in, then applies
        that state in a safe order:
          1. Raise ALL tools to safe UP state
          2. Move motors to correct positions (safe with all tools up)
          3. Apply correct tool states for this point in the program

        Args:
            keep_line_motor_up: If True, skip restoring line_motor_piston to
                'down' even if the program state requires it. Used during
                stopped step navigation so the motor stays up until Continue.
        """
        engine = self.main_app.execution_engine
        current_index = engine.current_step_index
        steps = self.main_app.steps
        hw = engine.hardware

        self.logger.info(
            f"RESTORE STATE: Restoring full machine state to step "
            f"{current_index + 1}/{len(steps)}",
            category="gui"
        )

        # Step 1: Raise ALL tools to safe state before any motor movement
        self.logger.debug("RESTORE STATE: Raising all tools to safe state", category="gui")
        hw.line_marker_up()
        hw.line_cutter_up()
        hw.row_marker_up()
        hw.row_cutter_up()
        hw.line_motor_piston_up()

        # Step 2: Scan steps 0..current_index-1 to determine expected state
        # (these are steps that would have been completed before the current step)
        tool_states = {}
        last_x = None
        last_y = None

        for i in range(current_index):
            step = steps[i]
            op = step.get('operation', '')
            params = step.get('parameters', {})

            if op == 'tool_action':
                tool = params.get('tool', '')
                action = params.get('action', '')
                if tool and action in ('up', 'down'):
                    tool_states[tool] = action
            elif op == 'move_x':
                last_x = params.get('position')
            elif op == 'move_y':
                last_y = params.get('position')

        # Step 3: Move motors to correct positions (with safety check)
        if last_x is not None:
            self.logger.debug(f"RESTORE STATE: Moving X to {last_x}", category="gui")
            if not self._safe_move('x', last_x, f"Restore state: move X to {last_x}", is_setup=True):
                self.logger.error("RESTORE STATE: X move blocked by safety rule", category="gui")
                return
        if last_y is not None:
            self.logger.debug(f"RESTORE STATE: Moving Y to {last_y}", category="gui")
            if not self._safe_move('y', last_y, f"Restore state: move Y to {last_y}", is_setup=True):
                self.logger.error("RESTORE STATE: Y move blocked by safety rule", category="gui")
                return

        # Step 4: Apply correct tool states
        tool_hw_map = {
            'line_marker': {'down': hw.line_marker_down, 'up': hw.line_marker_up},
            'line_cutter': {'down': hw.line_cutter_down, 'up': hw.line_cutter_up},
            'row_marker': {'down': hw.row_marker_down, 'up': hw.row_marker_up},
            'row_cutter': {'down': hw.row_cutter_down, 'up': hw.row_cutter_up},
            'line_motor_piston': {
                'down': hw.line_motor_piston_down,
                'up': hw.line_motor_piston_up
            },
        }

        for tool, action in tool_states.items():
            if tool in tool_hw_map and action in tool_hw_map[tool]:
                # When navigating while stopped, keep line_motor_piston UP
                if keep_line_motor_up and tool == 'line_motor_piston' and action == 'down':
                    self.logger.debug(
                        "RESTORE STATE: Skipping line_motor_piston down (stopped navigation)",
                        category="gui"
                    )
                    continue
                self.logger.debug(f"RESTORE STATE: {tool} -> {action}", category="gui")
                tool_hw_map[tool][action]()

        self.logger.success(
            f"RESTORE STATE: Machine state fully restored to step {current_index + 1}",
            category="gui"
        )

    def _replay_canvas_state_to_current(self):
        """Reset all operation states to pending, then replay tracking for steps 0..current.

        This ensures the canvas accurately reflects which operations are done
        up to the current step index (used when stepping backward).
        """
        current_index = self.main_app.execution_engine.current_step_index

        # Reset all operation states to pending
        if hasattr(self.main_app, 'operation_states'):
            for state_dict in self.main_app.operation_states.values():
                for key in state_dict:
                    state_dict[key] = 'pending'

        # Replay track_operation_from_step for steps 0 through current_index
        if hasattr(self.main_app, 'canvas_manager'):
            for i in range(current_index + 1):
                step = self.main_app.steps[i]
                step_desc = step.get('description', '')
                if step_desc:
                    self.main_app.canvas_manager.detect_operation_mode_from_step(step_desc)
                    self.main_app.canvas_manager.track_operation_from_step(step_desc)

    def _replay_hardware_positions_to_current(self):
        """Replay motor positions so hardware matches the program state at
        the current step index.

        Scans steps 0..current_index, finds the last move_x / move_y targets,
        and moves the hardware there.  This is essential for backward navigation
        where intermediate non-move steps (tool actions, waits) would otherwise
        leave the motors at a stale position from a later step.
        """
        current_index = self.main_app.execution_engine.current_step_index
        steps = self.main_app.steps

        last_x = None
        last_y = None

        for i in range(current_index + 1):
            op = steps[i].get('operation', '')
            params = steps[i].get('parameters', {})
            if op == 'move_x':
                last_x = params.get('position')
            elif op == 'move_y':
                last_y = params.get('position')

        if last_x is not None:
            if not self._safe_move('x', last_x, f"Replay position: move X to {last_x}", is_setup=True):
                self.logger.error("REPLAY: X move blocked by safety rule", category="gui")
                return
        if last_y is not None:
            if not self._safe_move('y', last_y, f"Replay position: move Y to {last_y}", is_setup=True):
                self.logger.error("REPLAY: Y move blocked by safety rule", category="gui")
                return

    def _force_canvas_position_update(self):
        """Force an immediate canvas position update, bypassing cache and deferral.

        Called from manual step navigation (prev/next) which runs on the GUI
        thread, so direct canvas access is safe.  Clears the cached position
        first so the update is never skipped.
        """
        cm = getattr(self.main_app, 'canvas_manager', None)
        if cm is None:
            return
        # Clear cached position/mode so update_position_display never skips
        for attr in ('_last_displayed_hardware_x', '_last_displayed_hardware_y', '_last_displayed_mode'):
            if hasattr(cm, attr):
                delattr(cm, attr)
        # Call directly (not via root.after) — we are already on the GUI thread
        cm.canvas_position.update_position_display()
        self.main_app.root.update_idletasks()

    def prev_step(self):
        """Go to previous step - safely restore machine state (back in time)"""
        if self.main_app.execution_engine.step_backward():
            # While stopped mid-execution, keep lines motor up - only lower on Continue
            keep_up = self._stopped_mid_execution
            self._restore_full_machine_state_to_current(keep_line_motor_up=keep_up)
            # Revert canvas state: reset all operations to pending, then replay up to current step
            self._replay_canvas_state_to_current()
            # Force immediate canvas motor position update
            self._force_canvas_position_update()
            self.update_step_display()

    def next_step(self):
        """Go to next step - safely restore machine state (back in time)"""
        if self.main_app.execution_engine.step_forward():
            # While stopped mid-execution, keep lines motor up - only lower on Continue
            keep_up = self._stopped_mid_execution
            self._restore_full_machine_state_to_current(keep_line_motor_up=keep_up)
            # Replay canvas state from beginning to reflect correct visual state
            self._replay_canvas_state_to_current()
            # Force immediate canvas motor position update
            self._force_canvas_position_update()
            self.update_step_display()
    
    def _prepare_for_new_run(self):
        """Reset engine and UI to be ready for a fresh run.

        Called after completion or error to ensure the user can
        immediately press RUN to start a new execution.
        """
        try:
            # Clear stop-continue state
            self._stopped_mid_execution = False
            self._motor_state_at_stop = None

            # Reset execution engine back to step 0 (keep steps loaded)
            self.main_app.execution_engine.reset_execution(clear_steps=False)

            # Reset button states - ready to run again
            self.run_btn.config(state=tk.NORMAL if self.main_app.steps else tk.DISABLED,
                               text=t('\u25b6 RUN'), bg='darkgreen')
            self.pause_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.reset_btn.config(state=tk.NORMAL)
            # Re-enable next/prev based on step position
            self.prev_btn.config(state=tk.DISABLED)  # At step 0 after reset
            self.next_btn.config(state=tk.NORMAL if self.main_app.steps else tk.DISABLED)

            # Reset hardware state (no homing - motors stay where they are)
            self.hardware.reset_hardware()
            if hasattr(self.hardware, 'flush_all_sensor_buffers'):
                self.hardware.flush_all_sensor_buffers()

            # Reset all operation states to pending so canvas shows fresh colors
            if hasattr(self.main_app, 'operation_states'):
                for state_dict in self.main_app.operation_states.values():
                    for key in state_dict:
                        state_dict[key] = 'pending'

            # Full canvas rebuild from scratch (grid, motor lines, paper area, work lines)
            if hasattr(self.main_app, 'canvas_manager'):
                self.main_app.canvas_manager.full_reset()
                self.main_app.canvas_manager.canvas_setup.setup_canvas()
                self.main_app.canvas_manager.update_canvas_paper_area()

            # Update step display to show step 1 again
            self.update_step_display()

            # Reset progress bar
            if hasattr(self.main_app, 'progress') and hasattr(self.main_app, 'progress_text'):
                self.main_app.progress['value'] = 0
                self.main_app.progress_text.config(text=t("0% Complete"))

            # Clear any safety modals/errors
            if hasattr(self.main_app, 'execution_controller'):
                self.main_app.execution_controller.cleanup_for_reset()

        except Exception as e:
            self.logger.error(f"Error preparing for new run: {e}", category="gui")
        finally:
            # ALWAYS unlock program panel, even if other parts fail
            if hasattr(self.main_app, 'program_panel'):
                self.main_app.program_panel.set_locked(False)

    def run_execution(self):
        """Start, continue, or resume execution"""
        if self.main_app.steps:
            engine = self.main_app.execution_engine

            # CRITICAL: Block execution if real hardware has not been homed
            if getattr(self.main_app, 'is_real_hardware', False) and \
               not getattr(self.main_app, 'homing_completed', False):
                self.logger.error("Cannot run: machine not homed!", category="gui")
                self.main_app.operation_label.config(
                    text=t("Machine not homed! Run homing first"), fg='red')
                from tkinter import messagebox
                messagebox.showerror(
                    t_title("Homing Required"),
                    t("Cannot run program - machine has not been homed!\n\n"
                      "You must complete homing before running any program.\n"
                      "Use the homing button to run homing.")
                )
                return

            # CONTINUE from stop: full "back in time" state restore before continuing
            if self._stopped_mid_execution and not engine.is_running:
                # Full state restore: raise all tools, move motors to correct
                # positions, then apply correct tool states for this step
                self._restore_full_machine_state_to_current()

                self._stopped_mid_execution = False
                self._motor_state_at_stop = None

                # Start execution from current step
                engine.continue_execution()
                self.run_btn.config(state=tk.DISABLED, text=t('\u25b6 RUN'), bg='darkgreen')
                self.stop_btn.config(state=tk.NORMAL)
                self.reset_btn.config(state=tk.DISABLED)
                self.next_btn.config(state=tk.DISABLED)
                self.prev_btn.config(state=tk.DISABLED)
                if hasattr(self.main_app, 'program_panel'):
                    self.main_app.program_panel.set_locked(True)
                return

            # Check for stale steps (program changed since steps were generated)
            if not engine.is_running:
                current_snapshot = self._snapshot_program(self.main_app.current_program)
                if self._steps_program_snapshot and current_snapshot != self._steps_program_snapshot:
                    self.logger.warning("Program parameters changed since steps were generated", category="gui")
                    self.main_app.operation_label.config(
                        text=t("Program changed - regenerate steps first!"), fg='red')
                    self.step_info_label.config(text=t("Steps are stale - press Generate"))
                    self.run_btn.config(state=tk.DISABLED)
                    return

                # Verify at least one actionable step exists
                actionable_ops = {'move_x', 'move_y', 'tool_action', 'tool_positioning'}
                has_actionable = any(s.get('operation') in actionable_ops for s in self.main_app.steps)
                if not has_actionable:
                    self.logger.warning("No actionable steps in program", category="gui")
                    self.main_app.operation_label.config(
                        text=t("No actionable steps - check program"), fg='red')
                    return

            # Check if we need to RESUME (engine is running but paused)
            if engine.is_running and engine.is_paused:
                engine.resume_execution()
                self.run_btn.config(state=tk.DISABLED, text=t('\u25b6 RUN'), bg='darkgreen')
                self.pause_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.NORMAL)
                self.reset_btn.config(state=tk.DISABLED)
                # Disable next/prev during automatic execution
                self.next_btn.config(state=tk.DISABLED)
                self.prev_btn.config(state=tk.DISABLED)
                return

            # Fresh start - validate program before starting
            if not engine.is_running:
                if self.main_app.current_program:
                    program_errors = self.main_app.current_program.validate()
                    if program_errors:
                        first_error = translate_validation_error(program_errors[0])
                        self.main_app.operation_label.config(
                            text=t("Program validation failed - cannot run"), fg='red')
                        self.step_info_label.config(text=first_error)
                        self.run_btn.config(state=tk.DISABLED)
                        return

                    validation_error = self._validate_paper_size(self.main_app.current_program)
                    if validation_error:
                        self.main_app.operation_label.config(text=validation_error, fg='red')
                        self.step_info_label.config(text=t("Invalid program - paper too large"))
                        self.run_btn.config(state=tk.DISABLED)
                        return

                engine.reset_execution(clear_steps=False)

            # Reset operation states to pending before starting so colors reflect fresh run
            if hasattr(self.main_app, 'operation_states'):
                for state_dict in self.main_app.operation_states.values():
                    for key in state_dict:
                        state_dict[key] = 'pending'
                # Refresh canvas colors to show pending state
                if hasattr(self.main_app, 'canvas_manager'):
                    self.main_app.canvas_manager.refresh_work_lines_colors()

            # Attach analytics collector for this run
            if hasattr(self.main_app, 'analytics_collector'):
                self.main_app.analytics_collector.attach_to_engine(
                    self.main_app.execution_engine,
                    self.main_app.current_program
                )

            self.main_app.execution_engine.start_execution()
            self.run_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            self.reset_btn.config(state=tk.DISABLED)  # Disable reset while running
            # Disable next/prev during automatic execution
            self.next_btn.config(state=tk.DISABLED)
            self.prev_btn.config(state=tk.DISABLED)

            # Lock program panel during execution
            if hasattr(self.main_app, 'program_panel'):
                self.main_app.program_panel.set_locked(True)

            # Force immediate canvas position update when execution starts
            if hasattr(self.main_app, 'canvas_manager'):
                self.main_app.canvas_manager.update_position_display()
    
    def pause_execution(self):
        """Pause execution"""
        if self.main_app.execution_engine.pause_execution():
            self.run_btn.config(state=tk.NORMAL, text=t('\u25b6 RESUME'), bg='#006400')
            self.pause_btn.config(state=tk.DISABLED)
            # Enable next/prev for stepping while paused
            current_index = self.main_app.execution_engine.current_step_index
            self.prev_btn.config(state=tk.NORMAL if current_index > 0 else tk.DISABLED)
            self.next_btn.config(state=tk.NORMAL if current_index < len(self.main_app.steps) - 1 else tk.DISABLED)
    
    def stop_execution(self):
        """Stop execution - preserves current step for continue"""
        engine = self.main_app.execution_engine
        if engine.stop_execution():
            # Engine conditionally raised line_motor_piston based on its state
            self._stopped_mid_execution = True
            self._motor_state_at_stop = getattr(engine, '_raised_motor_on_stop', False)

            # Set up UI for continue (not reset)
            current_index = engine.current_step_index
            self.run_btn.config(state=tk.NORMAL, text=t('\u25b6 CONTINUE'), bg='#006400')
            self.stop_btn.config(state=tk.DISABLED)
            self.reset_btn.config(state=tk.NORMAL)
            # Enable navigation while stopped
            self.prev_btn.config(state=tk.NORMAL if current_index > 0 else tk.DISABLED)
            self.next_btn.config(state=tk.NORMAL if current_index < len(self.main_app.steps) - 1 else tk.DISABLED)

            # Unlock program panel
            if hasattr(self.main_app, 'program_panel'):
                self.main_app.program_panel.set_locked(False)

            self.update_step_display()
            self.main_app.operation_label.config(text=t("Stopped - press Continue to resume from current step"), fg='orange')
    
    def auto_reload_after_completion(self):
        """Reset to READY state after program completion so user can immediately re-run"""
        # Reset engine and UI for fresh run (buttons, progress, operation states, panel unlock)
        self._prepare_for_new_run()

        # Show ready state labels
        self.progress_label.config(text=t("Program ready - press Run to repeat"), fg='blue')
        self.main_app.operation_label.config(text=t("Program ready - press Run to repeat"), fg='blue')

        # Reset progress to 0%
        if hasattr(self.main_app, 'progress') and hasattr(self.main_app, 'progress_text'):
            self.main_app.progress['value'] = 0
            self.main_app.progress_text.config(text=t("0% Complete"))

    def reset_execution(self, clear_steps=False):
        """Reset execution and UI state

        Args:
            clear_steps: If True, also clears the steps list (for new program loading)
        """
        # Safety check: Don't reset while running (button should be disabled, but check anyway)
        if self.main_app.execution_engine.is_running:
            self.logger.warning("Cannot reset while execution is running - stop first", category="gui")
            self.main_app.operation_label.config(text=t("Stop execution first!"), fg='red')
            return

        # Clean up execution controller (close transition dialogs, etc.)
        if hasattr(self.main_app, 'execution_controller'):
            self.main_app.execution_controller.cleanup_for_reset()

        # Reset execution engine (with optional steps clearing)
        self.main_app.execution_engine.reset_execution(clear_steps=clear_steps)

        # Clear stop-continue state
        self._stopped_mid_execution = False
        self._motor_state_at_stop = None

        # Clear steps in main_app if requested
        if clear_steps:
            self.main_app.steps = []
            self._steps_program_snapshot = None

        # Reset hardware state (position, tools, sensors)
        self.hardware.reset_hardware()

        # Flush all hardware sensor buffers to clear stale triggers
        if hasattr(self.hardware, 'flush_all_sensor_buffers'):
            self.hardware.flush_all_sensor_buffers()

        # Move hardware to motor home positions (0, 0)
        self.hardware.move_x(0.0)  # Rows motor home position
        self.hardware.move_y(0.0)  # Lines motor home position

        # Reset operation states to pending (always clear, then repopulate if program exists)
        if hasattr(self.main_app, 'operation_states'):
            # Always clear all states first
            self.main_app.operation_states['lines'].clear()
            self.main_app.operation_states['cuts'].clear()
            self.main_app.operation_states['pages'].clear()

            # Reset cut states (always - they don't depend on program)
            for cut_name in ['top', 'bottom', 'left', 'right']:
                self.main_app.operation_states['cuts'][cut_name] = 'pending'

            # Repopulate line and page states only if program exists
            if self.main_app.current_program:
                for line_num in range(1, self.main_app.current_program.number_of_lines + 1):
                    self.main_app.operation_states['lines'][line_num] = 'pending'
                for page_num in range(self.main_app.current_program.number_of_pages):
                    self.main_app.operation_states['pages'][page_num] = 'pending'

        # Reset progress bar
        if hasattr(self.main_app, 'progress') and hasattr(self.main_app, 'progress_text'):
            self.main_app.progress['value'] = 0
            self.main_app.progress_text.config(text=t("0% Complete"))

        # Reset operation label
        self.main_app.operation_label.config(text=t("System Ready"), fg='blue')

        # Reset progress label
        self.progress_label.config(text=t("Ready"), fg='darkblue')

        # Cancel all scheduled callbacks (sensor label updates, etc.)
        for callback_id in self.scheduled_callbacks:
            try:
                self.main_app.root.after_cancel(callback_id)
            except Exception:
                pass  # Ignore if callback already executed or invalid
        self.scheduled_callbacks.clear()

        # Reset sensor status label
        self.sensor_label.config(text=t("Sensor: Ready"), fg='darkgreen')

        # Reset state label
        self.state_label.config(text=t("State: Idle"), fg='darkred')

        # Full canvas reset (clears sensor overrides, timers, motor positions, etc.)
        if hasattr(self.main_app, 'canvas_manager'):
            # Comprehensive canvas state reset
            self.main_app.canvas_manager.full_reset()

            # Update position display to show reset position
            self.main_app.canvas_manager.update_position_display()

            # Refresh all work line colors
            self.main_app.canvas_manager.refresh_work_lines_colors()

            # Update canvas with current program (pointer stays at starting position)
            self.main_app.canvas_manager.update_canvas_paper_area()

        # Update step display
        self.update_step_display()

        # Reset button states
        self.run_btn.config(state=tk.NORMAL if self.main_app.steps else tk.DISABLED)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)

        self.logger.info("Complete system reset - All components restored to initial state", category="gui")
    
    def _schedule_sensor_label_reset(self):
        """Schedule sensor label reset and track the callback for cleanup"""
        callback_id = self.main_app.root.after(
            1000, lambda: self.sensor_label.config(text=t("Sensor: Ready"), fg='darkgreen')
        )
        self.scheduled_callbacks.append(callback_id)

    def trigger_x_left(self):
        """Trigger X left sensor - only sets event, does NOT move motors or canvas"""
        self.hardware.trigger_x_left_sensor()
        # Update old sensor_label only (status is shown in hardware panel)
        if hasattr(self, 'sensor_label'):
            self.sensor_label.config(text=t("Sensor: X-Left Triggered"), fg='red')
            self._schedule_sensor_label_reset()

        # NOTE: Canvas visualization is handled automatically during execution when waiting for sensors
        # Manual triggers should only set the sensor event, not move anything

    def trigger_x_right(self):
        """Trigger X right sensor - only sets event, does NOT move motors or canvas"""
        self.hardware.trigger_x_right_sensor()
        # Update old sensor_label only (status is shown in hardware panel)
        if hasattr(self, 'sensor_label'):
            self.sensor_label.config(text=t("Sensor: X-Right Triggered"), fg='red')
            self._schedule_sensor_label_reset()

        # NOTE: Canvas visualization is handled automatically during execution when waiting for sensors
        # Manual triggers should only set the sensor event, not move anything

    def trigger_y_top(self):
        """Trigger Y top sensor - only sets event, does NOT move motors or canvas"""
        self.hardware.trigger_y_top_sensor()
        # Update old sensor_label only (status is shown in hardware panel)
        if hasattr(self, 'sensor_label'):
            self.sensor_label.config(text=t("Sensor: Y-Top Triggered"), fg='red')
            self._schedule_sensor_label_reset()

        # NOTE: Canvas visualization is handled automatically during execution when waiting for sensors
        # Manual triggers should only set the sensor event, not move anything

    def trigger_y_bottom(self):
        """Trigger Y bottom sensor - only sets event, does NOT move motors or canvas"""
        self.hardware.trigger_y_bottom_sensor()
        # Update old sensor_label only (status is shown in hardware panel)
        if hasattr(self, 'sensor_label'):
            self.sensor_label.config(text=t("Sensor: Y-Bottom Triggered"), fg='red')
            self._schedule_sensor_label_reset()

        # NOTE: Canvas visualization is handled automatically during execution when waiting for sensors
        # Manual triggers should only set the sensor event, not move anything
    
    def toggle_ls(self, switch_name):
        """Toggle a limit switch"""
        state = self.hardware.toggle_limit_switch(switch_name)
        self.logger.debug(t("Limit switch {name} toggled: {state}",
                           name=switch_name,
                           state='ON' if state else 'OFF'), category="gui")

        # Force canvas position update to refresh indicators
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_line_marker(self):
        """Toggle line marker piston"""
        if self.lines_marker_var.get():
            self.hardware.line_marker_down()
        else:
            self.hardware.line_marker_up()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_line_cutter(self):
        """Toggle line cutter piston"""
        if self.lines_cutter_var.get():
            self.hardware.line_cutter_down()
        else:
            self.hardware.line_cutter_up()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_line_motor(self):
        """Toggle line motor piston (controls Y motor assembly lift)"""
        if self.lines_motor_var.get():
            self.hardware.line_motor_piston_down()
        else:
            self.hardware.line_motor_piston_up()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_row_marker(self):
        """Toggle row marker piston"""
        if self.rows_marker_var.get():
            self.hardware.row_marker_down()
        else:
            self.hardware.row_marker_up()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_row_cutter(self):
        """Toggle row cutter piston"""
        if self.rows_cutter_var.get():
            self.hardware.row_cutter_down()
        else:
            self.hardware.row_cutter_up()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_air_pressure(self):
        """Toggle air pressure valve"""
        if self.air_pressure_var.get():
            self.hardware.air_pressure_valve_down()
        else:
            self.hardware.air_pressure_valve_up()

    def sync_checkbox_states(self):
        """Synchronize checkbox states with actual hardware states"""
        try:
            # Get actual hardware states
            line_marker_state = self.hardware.get_line_marker_state()
            line_cutter_state = self.hardware.get_line_cutter_state()
            line_motor_piston_state = self.hardware.get_line_motor_piston_state()
            row_marker_state = self.hardware.get_row_marker_state()
            row_cutter_state = self.hardware.get_row_cutter_state()

            # Update checkbox variables to match hardware (checked = down/active)
            # For line marker and cutter: checked = down
            self.lines_marker_var.set(line_marker_state == "down")
            self.lines_cutter_var.set(line_cutter_state == "down")

            # For line motor piston: checked = down (opposite of default UP)
            self.lines_motor_var.set(line_motor_piston_state == "down")

            # For row marker and cutter: checked = down
            self.rows_marker_var.set(row_marker_state == "down")
            self.rows_cutter_var.set(row_cutter_state == "down")

            # Air pressure valve: checked = down (open/air flowing)
            air_pressure_state = self.hardware.get_air_pressure_valve_state()
            self.air_pressure_var.set(air_pressure_state == "down")

            # Update limit switch checkboxes
            self.y_top_ls_var.set(self.hardware.get_limit_switch_state('y_top'))
            self.y_bottom_ls_var.set(self.hardware.get_limit_switch_state('y_bottom'))
            self.x_right_ls_var.set(self.hardware.get_limit_switch_state('x_right'))
            self.x_left_ls_var.set(self.hardware.get_limit_switch_state('x_left'))
            self.door_sensor_var.set(self.hardware.get_limit_switch_state('rows_door'))

        except Exception as e:
            # Silently ignore errors to avoid flooding console
            pass

    def schedule_checkbox_sync(self):
        """Schedule periodic checkbox state synchronization"""
        self.sync_checkbox_states()
        # Schedule next update (200ms interval)
        self.main_app.root.after(200, self.schedule_checkbox_sync)

    def update_test_controls_state(self):
        """Show/hide test controls based on hardware mode.
        On real hardware the entire test controls section is hidden."""
        # Check if we're using real hardware by checking the class type
        from hardware.implementations.real.real_hardware import RealHardware
        is_real_hardware = isinstance(self.hardware, RealHardware)

        if is_real_hardware:
            # Completely hide test controls on real hardware
            self.test_controls_frame.pack_forget()
            self.logger.info(t("Test controls HIDDEN - Real hardware mode active"), category="gui")
        else:
            # Show and enable test controls in simulation mode
            self.test_controls_frame.pack(fill=tk.X, padx=10, pady=5)
            self._set_frame_state(self.test_controls_frame, tk.NORMAL)

            # Hide disabled indicator and restore colors
            if hasattr(self, 'test_controls_disabled_label'):
                self.test_controls_disabled_label.pack_forget()
            if hasattr(self, 'test_controls_title'):
                self.test_controls_title.config(fg='#003366')
            self._set_frame_background(self.test_controls_frame, '#F0F8FF')

            self.logger.info(t("Test controls ENABLED - Simulation mode active"), category="gui")

    def _set_frame_background(self, frame, color):
        """Recursively set background color of all widgets in a frame"""
        try:
            frame.config(bg=color)
        except tk.TclError:
            pass
        for child in frame.winfo_children():
            widget_type = child.winfo_class()
            try:
                child.config(bg=color)
                if widget_type in ('Frame', 'LabelFrame'):
                    self._set_frame_background(child, color)
            except tk.TclError:
                pass  # Some widgets don't support bg

    def _set_frame_state(self, frame, state):
        """Recursively set state of all widgets in a frame"""
        for child in frame.winfo_children():
            widget_type = child.winfo_class()
            try:
                if widget_type in ('Button', 'Checkbutton', 'Radiobutton'):
                    child.config(state=state)
                elif widget_type in ('Frame', 'LabelFrame'):
                    # Recursively handle nested frames
                    self._set_frame_state(child, state)
            except tk.TclError:
                # Some widgets don't support state, skip them
                pass

    def _validate_paper_size(self, program):
        """Validate that paper size fits within the work surface.

        Returns None if valid, or an error message string if invalid.
        """
        # Get work surface limits from settings
        hardware_limits = self.main_app.settings.get("hardware_limits", {})
        simulation = self.main_app.settings.get("simulation", {})

        paper_start_x = hardware_limits.get("paper_start_x", 15.0)
        paper_start_y = hardware_limits.get("paper_start_y", 31.0)
        max_x = simulation.get("max_display_x", 120.0)
        max_y = simulation.get("max_display_y", 80.0)

        # Calculate available work area
        available_width = max_x - paper_start_x
        available_height = max_y - paper_start_y

        # Calculate total paper size (with repeats)
        paper_width = program.width * program.repeat_rows
        paper_height = program.high * program.repeat_lines

        # Check if paper fits
        errors = []

        if paper_width > available_width:
            errors.append(t("Paper width ({width}cm) exceeds surface ({available}cm)",
                          width=paper_width, available=available_width))

        if paper_height > available_height:
            errors.append(t("Paper height ({height}cm) exceeds surface ({available}cm)",
                          height=paper_height, available=available_height))

        if errors:
            return " | ".join(errors)

        return None  # Valid

    def set_controls_enabled(self, enabled: bool):
        """Enable or disable execution controls (used during homing/mode switching)"""
        state = tk.NORMAL if enabled else tk.DISABLED

        # Execution buttons
        if hasattr(self, 'run_btn') and self.main_app.steps:
            self.run_btn.config(state=state if enabled else tk.DISABLED)
        if hasattr(self, 'pause_btn'):
            self.pause_btn.config(state=tk.DISABLED)  # Always disabled unless running
        if hasattr(self, 'stop_btn'):
            self.stop_btn.config(state=tk.DISABLED)  # Always disabled unless running
        if hasattr(self, 'reset_btn'):
            self.reset_btn.config(state=state)

        # Navigation buttons - respect current step position when enabling
        if hasattr(self, 'prev_btn') and hasattr(self, 'next_btn'):
            if not enabled:
                self.prev_btn.config(state=tk.DISABLED)
                self.next_btn.config(state=tk.DISABLED)
            elif self.main_app.steps:
                current_index = self.main_app.execution_engine.current_step_index
                engine = self.main_app.execution_engine
                # Only update nav buttons if not in active (non-paused) execution
                if not (engine.is_running and not engine.is_paused):
                    self.prev_btn.config(state=tk.NORMAL if current_index > 0 else tk.DISABLED)
                    self.next_btn.config(state=tk.NORMAL if current_index < len(self.main_app.steps) - 1 else tk.DISABLED)
            else:
                self.prev_btn.config(state=tk.DISABLED)
                self.next_btn.config(state=tk.DISABLED)

        # Test controls frame (only if visible - hidden on real hardware)
        if hasattr(self, 'test_controls_frame') and self.test_controls_frame.winfo_ismapped():
            self._set_frame_state(self.test_controls_frame, state)

    def refresh_hardware_reference(self):
        """Update hardware reference after hot-swap"""
        self.hardware = self.main_app.hardware
        self.update_test_controls_state()
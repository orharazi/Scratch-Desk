import tkinter as tk
from tkinter import ttk
from step_generator import generate_complete_program_steps, get_step_count_summary
from mock_hardware import (
    trigger_x_left_sensor, trigger_x_right_sensor,
    trigger_y_top_sensor, trigger_y_bottom_sensor,
    toggle_limit_switch, get_limit_switch_state,
    line_marker_down, line_marker_up, line_cutter_down, line_cutter_up,
    row_marker_down, row_marker_up, row_cutter_down, row_cutter_up,
    lift_line_tools, lower_line_tools
)


class RightPanel:
    """Right panel for step navigation and execution controls"""
    
    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        
        # Responsive font sizing based on window width
        self.update_font_sizes()
        
        self.create_widgets()
        
        # Bind to window resize for dynamic font adjustment
        self.main_app.root.bind('<Configure>', self.on_window_resize)
    
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
            if hasattr(self, 'gen_steps_btn'):
                self.gen_steps_btn.config(font=self.button_font)
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
        self.title_label = tk.Label(self.scrollable_frame, text="CONTROLS & STATUS", font=self.title_font,
                bg='lightblue')
        self.title_label.pack(pady=3)

        # Generate Steps Button with responsive font and sizing
        self.gen_steps_btn = tk.Button(self.scrollable_frame, text="Generate Steps", command=self.generate_steps,
                 bg='yellow', fg='darkblue', font=self.button_font, height=1)
        self.gen_steps_btn.pack(fill=tk.X, padx=10, pady=3)
        
        # Step Navigation with responsive frame
        nav_frame = tk.Frame(self.scrollable_frame, bg='lightblue')
        nav_frame.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(nav_frame, text="Step Navigation:", font=('Arial', 9, 'bold'),
                bg='lightblue').pack()

        nav_buttons = tk.Frame(nav_frame, bg='lightblue')
        nav_buttons.pack(fill=tk.X, pady=2)

        self.prev_btn = tk.Button(nav_buttons, text="◄ Prev", command=self.prev_step,
                                 state=tk.DISABLED, width=8, font=('Arial', 8))
        self.prev_btn.pack(side=tk.LEFT)

        self.next_btn = tk.Button(nav_buttons, text="Next ►", command=self.next_step,
                                 state=tk.DISABLED, width=8, font=('Arial', 8))
        self.next_btn.pack(side=tk.RIGHT)

        self.step_info_label = tk.Label(nav_frame, text="No steps loaded",
                                       bg='lightblue', font=('Arial', 8), wraplength=250)
        self.step_info_label.pack(pady=2)
        
        # Step Details - Improved visibility and layout
        details_frame = tk.Frame(self.scrollable_frame, bg='lightblue')
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)

        tk.Label(details_frame, text="Steps Queue:", font=('Arial', 9, 'bold'),
                bg='lightblue', fg='darkblue').pack()

        # Create tabbed view for current step vs all steps
        notebook = ttk.Notebook(details_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # Current Step Tab
        current_tab = tk.Frame(notebook, bg='white')
        notebook.add(current_tab, text='Current')
        
        # Current step info with better formatting - more compact
        current_info_frame = tk.Frame(current_tab, bg='lightgray', relief=tk.RAISED, bd=2)
        current_info_frame.pack(fill=tk.X, padx=5, pady=3)

        self.current_step_label = tk.Label(current_info_frame, text="No step selected",
                                          font=('Arial', 8, 'bold'), bg='lightgray', fg='darkblue',
                                          wraplength=200)
        self.current_step_label.pack(pady=3)

        self.step_details = tk.Text(current_tab, height=3, width=25, font=('Arial', 7),
                                   wrap=tk.WORD, bg='white', fg='black', relief=tk.SUNKEN, bd=2)
        step_scroll = tk.Scrollbar(current_tab, orient=tk.VERTICAL)
        step_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.step_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=2)
        self.step_details.config(yscrollcommand=step_scroll.set)
        step_scroll.config(command=self.step_details.yview)

        # All Steps Tab
        all_steps_tab = tk.Frame(notebook, bg='white')
        notebook.add(all_steps_tab, text='All Steps')

        # Steps queue listbox with better visibility - more compact
        queue_frame = tk.Frame(all_steps_tab, bg='white')
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        self.steps_listbox = tk.Listbox(queue_frame, font=('Arial', 6), height=8,
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
        
        # Status Panel - Compact
        status_frame = tk.Frame(self.scrollable_frame, bg='lightblue')
        status_frame.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(status_frame, text="System Status:", font=('Arial', 9, 'bold'),
                bg='lightblue', fg='darkblue').pack()

        # Current Position with better visibility
        self.position_label = tk.Label(status_frame, text="Position: X=0.0, Y=0.0",
                                      bg='lightblue', fg='darkblue', font=('Arial', 8))
        self.position_label.pack(anchor=tk.W)

        # Sensor Status with better visibility
        self.sensor_label = tk.Label(status_frame, text="Sensor: Ready",
                                    bg='lightblue', fg='darkgreen', font=('Arial', 8))
        self.sensor_label.pack(anchor=tk.W)

        # System State with better visibility
        self.state_label = tk.Label(status_frame, text="State: Idle",
                                   bg='lightblue', fg='darkred', font=('Arial', 8))
        self.state_label.pack(anchor=tk.W)

        # Execution Controls (moved from bottom panel)
        exec_frame = tk.Frame(self.scrollable_frame, bg='lightblue')
        exec_frame.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(exec_frame, text="Execution:", font=('Arial', 9, 'bold'),
                bg='lightblue', fg='darkblue').pack()
        
        # Execution buttons in 2x2 grid - Compact
        button_grid = tk.Frame(exec_frame, bg='lightblue')
        button_grid.pack(pady=2)

        self.run_btn = tk.Button(button_grid, text="▶ RUN", command=self.run_execution,
                                bg='darkgreen', fg='white', font=('Arial', 8, 'bold'),
                                width=9, state=tk.DISABLED, relief=tk.RAISED, bd=2,
                                activebackground='green', activeforeground='white')
        self.run_btn.grid(row=0, column=0, padx=1, pady=1)

        self.pause_btn = tk.Button(button_grid, text="⏸ PAUSE", command=self.pause_execution,
                                  bg='darkorange', fg='black', font=('Arial', 8, 'bold'),
                                  width=9, state=tk.DISABLED, relief=tk.RAISED, bd=2,
                                  activebackground='orange', activeforeground='black')
        self.pause_btn.grid(row=0, column=1, padx=1, pady=1)

        self.stop_btn = tk.Button(button_grid, text="⏹ STOP", command=self.stop_execution,
                                 bg='darkred', fg='black', font=('Arial', 8, 'bold'),
                                 width=9, state=tk.DISABLED, relief=tk.RAISED, bd=2,
                                 activebackground='red', activeforeground='white')
        self.stop_btn.grid(row=1, column=0, padx=1, pady=1)

        self.reset_btn = tk.Button(button_grid, text="🔄 RESET", command=self.reset_execution,
                                  bg='royalblue', fg='black', font=('Arial', 8, 'bold'),
                                  width=9, relief=tk.RAISED, bd=2,
                                  activebackground='blue', activeforeground='white')
        self.reset_btn.grid(row=1, column=1, padx=1, pady=1)

        # Progress indicator (compact) with better visibility
        self.progress_label = tk.Label(exec_frame, text="Ready",
                                      bg='lightblue', fg='darkblue', font=('Arial', 7, 'bold'))
        self.progress_label.pack(pady=1)
        
        # TEST CONTROLS SECTION - Hardware testing controls
        test_controls_frame = tk.Frame(self.scrollable_frame, relief=tk.RIDGE, bd=2, bg='#F0F8FF')
        test_controls_frame.pack(fill=tk.X, padx=10, pady=5)

        # Title
        tk.Label(test_controls_frame, text="🧪 TEST CONTROLS", font=('Arial', 10, 'bold'),
                bg='#F0F8FF', fg='#003366').pack(pady=(5, 8))

        # EDGE SENSORS Section
        sensors_frame = tk.Frame(test_controls_frame, bg='#F0F8FF')
        sensors_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        tk.Label(sensors_frame, text="📡 Edge Sensors (Trigger)", font=('Arial', 9, 'bold'),
                bg='#F0F8FF', fg='#003366').pack(anchor='w', pady=(0, 4))

        # X Sensors (Rows) - Left and Right
        x_frame = tk.Frame(sensors_frame, bg='#F0F8FF')
        x_frame.pack(fill=tk.X, pady=2)
        tk.Label(x_frame, text="X-Axis (Rows):", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        tk.Button(x_frame, text="◄ Left", bg='#FF6600', fg='black',
                 command=self.trigger_x_left, width=8, font=('Arial', 8, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='#FF8833', activeforeground='black').pack(side=tk.LEFT, padx=2)
        tk.Button(x_frame, text="Right ►", bg='#FF6600', fg='black',
                 command=self.trigger_x_right, width=8, font=('Arial', 8, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='#FF8833', activeforeground='black').pack(side=tk.LEFT, padx=2)

        # Y Sensors (Lines) - Top and Bottom
        y_frame = tk.Frame(sensors_frame, bg='#F0F8FF')
        y_frame.pack(fill=tk.X, pady=2)
        tk.Label(y_frame, text="Y-Axis (Lines):", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        tk.Button(y_frame, text="▲ Top", bg='#8800FF', fg='black',
                 command=self.trigger_y_top, width=8, font=('Arial', 8, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='#9922FF', activeforeground='black').pack(side=tk.LEFT, padx=2)
        tk.Button(y_frame, text="Bottom ▼", bg='#8800FF', fg='black',
                 command=self.trigger_y_bottom, width=8, font=('Arial', 8, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='#9922FF', activeforeground='black').pack(side=tk.LEFT, padx=2)

        # Separator
        tk.Frame(test_controls_frame, bg='#7F8C8D', height=2).pack(fill=tk.X, padx=10, pady=8)

        # LIMIT SWITCHES Section
        limit_switches_frame = tk.Frame(test_controls_frame, bg='#F0F8FF')
        limit_switches_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        tk.Label(limit_switches_frame, text="🔌 Limit Switches (Toggle)", font=('Arial', 9, 'bold'),
                bg='#F0F8FF', fg='#003366').pack(anchor='w', pady=(0, 4))

        # Y-Axis Limit Switches
        y_ls_frame = tk.Frame(limit_switches_frame, bg='#F0F8FF')
        y_ls_frame.pack(fill=tk.X, pady=2)
        tk.Label(y_ls_frame, text="Y-Axis:", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        self.y_top_ls_var = tk.BooleanVar()
        tk.Checkbutton(y_ls_frame, text="Top", variable=self.y_top_ls_var,
                      command=lambda: self.toggle_ls('y_top'), bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)
        self.y_bottom_ls_var = tk.BooleanVar()
        tk.Checkbutton(y_ls_frame, text="Bottom", variable=self.y_bottom_ls_var,
                      command=lambda: self.toggle_ls('y_bottom'), bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)

        # X-Axis Limit Switches
        x_ls_frame = tk.Frame(limit_switches_frame, bg='#F0F8FF')
        x_ls_frame.pack(fill=tk.X, pady=2)
        tk.Label(x_ls_frame, text="X-Axis:", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        self.x_right_ls_var = tk.BooleanVar()
        tk.Checkbutton(x_ls_frame, text="Right", variable=self.x_right_ls_var,
                      command=lambda: self.toggle_ls('x_right'), bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)
        self.x_left_ls_var = tk.BooleanVar()
        tk.Checkbutton(x_ls_frame, text="Left", variable=self.x_left_ls_var,
                      command=lambda: self.toggle_ls('x_left'), bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)

        # Rows Limit Switch
        rows_ls_frame = tk.Frame(limit_switches_frame, bg='#F0F8FF')
        rows_ls_frame.pack(fill=tk.X, pady=2)
        tk.Label(rows_ls_frame, text="Rows Marker:", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        self.rows_ls_var = tk.BooleanVar()
        tk.Checkbutton(rows_ls_frame, text="Rows LS", variable=self.rows_ls_var,
                      command=lambda: self.toggle_ls('rows'), bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)

        # Separator
        tk.Frame(test_controls_frame, bg='#7F8C8D', height=2).pack(fill=tk.X, padx=10, pady=8)

        # PISTONS Section
        pistons_frame = tk.Frame(test_controls_frame, bg='#F0F8FF')
        pistons_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        tk.Label(pistons_frame, text="🔧 Pistons (Toggle)", font=('Arial', 9, 'bold'),
                bg='#F0F8FF', fg='#003366').pack(anchor='w', pady=(0, 4))

        # Lines Pistons (Marker, Cutter, Motor)
        lines_marker_frame = tk.Frame(pistons_frame, bg='#F0F8FF')
        lines_marker_frame.pack(fill=tk.X, pady=2)
        tk.Label(lines_marker_frame, text="Lines Marker:", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        self.lines_marker_var = tk.BooleanVar()
        tk.Checkbutton(lines_marker_frame, text="DOWN (Checked=DOWN)", variable=self.lines_marker_var,
                      command=self.toggle_line_marker, bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)

        lines_cutter_frame = tk.Frame(pistons_frame, bg='#F0F8FF')
        lines_cutter_frame.pack(fill=tk.X, pady=2)
        tk.Label(lines_cutter_frame, text="Lines Cutter:", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        self.lines_cutter_var = tk.BooleanVar()
        tk.Checkbutton(lines_cutter_frame, text="DOWN (Checked=DOWN)", variable=self.lines_cutter_var,
                      command=self.toggle_line_cutter, bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)

        lines_motor_frame = tk.Frame(pistons_frame, bg='#F0F8FF')
        lines_motor_frame.pack(fill=tk.X, pady=2)
        tk.Label(lines_motor_frame, text="Lines Motor:", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        self.lines_motor_var = tk.BooleanVar()
        tk.Checkbutton(lines_motor_frame, text="DOWN (Checked=DOWN)", variable=self.lines_motor_var,
                      command=self.toggle_line_motor, bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)

        # Rows Pistons (Marker and Cutter)
        rows_marker_frame = tk.Frame(pistons_frame, bg='#F0F8FF')
        rows_marker_frame.pack(fill=tk.X, pady=2)
        tk.Label(rows_marker_frame, text="Rows Marker:", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        self.rows_marker_var = tk.BooleanVar()
        tk.Checkbutton(rows_marker_frame, text="DOWN (Checked=DOWN)", variable=self.rows_marker_var,
                      command=self.toggle_row_marker, bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)

        rows_cutter_frame = tk.Frame(pistons_frame, bg='#F0F8FF')
        rows_cutter_frame.pack(fill=tk.X, pady=2)
        tk.Label(rows_cutter_frame, text="Rows Cutter:", bg='#F0F8FF', fg='#003366',
                font=('Arial', 8, 'bold'), width=15, anchor='w').pack(side=tk.LEFT)
        self.rows_cutter_var = tk.BooleanVar()
        tk.Checkbutton(rows_cutter_frame, text="DOWN (Checked=DOWN)", variable=self.rows_cutter_var,
                      command=self.toggle_row_cutter, bg='#F0F8FF', fg='black',
                      font=('Arial', 8), selectcolor='#27AE60').pack(side=tk.LEFT, padx=5)

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
    
    def generate_steps(self):
        """Generate steps for current program"""
        if not self.main_app.current_program:
            return
        
        try:
            # Generate complete steps for the program
            self.main_app.steps = generate_complete_program_steps(self.main_app.current_program)
            
            # No premature alert - let execution handle transitional safety checks
            
            # Reset execution engine with new steps
            self.main_app.execution_engine.load_steps(self.main_app.steps)
            
            # Update displays
            self.update_step_display()
            
            # Enable navigation if we have steps
            if self.main_app.steps:
                self.next_btn.config(state=tk.NORMAL)
                self.run_btn.config(state=tk.NORMAL)
                # Keep pointer at starting position (15, 15) - don't move to first line yet
            
            # Get step count summary
            summary = get_step_count_summary(self.main_app.current_program)
            self.step_info_label.config(
                text=f"Generated {len(self.main_app.steps)} steps ({summary['total_repetitions']} repetitions)"
            )
            
        except Exception as e:
            self.step_info_label.config(text=f"Error generating steps: {e}")
    
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
            
            step_summary = f"{status_icon} {i+1:3d}. {step['operation']}: {step['description'][:40]}..."
            self.steps_listbox.insert(tk.END, step_summary)
        
        # Scroll to current step
        current_index = self.main_app.execution_engine.current_step_index
        if 0 <= current_index < len(self.main_app.steps):
            self.steps_listbox.selection_clear(0, tk.END)
            self.steps_listbox.selection_set(current_index)
            self.steps_listbox.see(current_index)
        
        # Update navigation buttons
        self.prev_btn.config(state=tk.NORMAL if current_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if current_index < len(self.main_app.steps) - 1 else tk.DISABLED)
        
        # Update current step info
        if self.main_app.steps and 0 <= current_index < len(self.main_app.steps):
            current_step = self.main_app.steps[current_index]
            self.current_step_label.config(text=f"Step {current_index + 1}/{len(self.main_app.steps)}: {current_step['operation']}")
            
            # Update step details - fix newline parsing
            details_text = f"Operation: {current_step['operation']}\n"
            details_text += f"Description: {current_step['description']}\n"
            if current_step.get('parameters'):
                details_text += f"Parameters: {current_step['parameters']}"

            self.step_details.config(state=tk.NORMAL)
            self.step_details.delete(1.0, tk.END)
            self.step_details.insert(1.0, details_text)
            self.step_details.config(state=tk.DISABLED)
        else:
            self.current_step_label.config(text="No step selected")
            self.step_details.config(state=tk.NORMAL)
            self.step_details.delete(1.0, tk.END)
            self.step_details.config(state=tk.DISABLED)
    
    def on_step_select(self, event):
        """Handle step selection from listbox"""
        selection = self.steps_listbox.curselection()
        if selection and self.main_app.steps:
            step_index = selection[0]
            if 0 <= step_index < len(self.main_app.steps):
                step = self.main_app.steps[step_index]

                # Show step details in the text widget - fix newline parsing
                details_text = f"Step {step_index + 1}/{len(self.main_app.steps)}\n\n"
                details_text += f"Operation: {step['operation']}\n\n"
                details_text += f"Description: {step['description']}\n\n"

                if step.get('parameters'):
                    details_text += f"Parameters:\n"
                    for key, value in step['parameters'].items():
                        details_text += f"  {key}: {value}\n"

                self.step_details.config(state=tk.NORMAL)
                self.step_details.delete(1.0, tk.END)
                self.step_details.insert(1.0, details_text)
                self.step_details.config(state=tk.DISABLED)
    
    def prev_step(self):
        """Go to previous step"""
        if self.main_app.execution_engine.step_backward():
            result = self.main_app.execution_engine.execute_current_step()
            if (self.main_app.execution_engine.current_step_index < len(self.main_app.steps)):
                current_step = self.main_app.steps[self.main_app.execution_engine.current_step_index]
                step_desc = current_step.get('description', '')
                self.main_app.canvas_manager.detect_operation_mode_from_step(step_desc)
                self.main_app.canvas_manager.track_operation_from_step(step_desc)
            self.update_step_display()
    
    def next_step(self):
        """Go to next step"""
        if self.main_app.execution_engine.step_forward():
            result = self.main_app.execution_engine.execute_current_step()
            if (self.main_app.execution_engine.current_step_index < len(self.main_app.steps)):
                current_step = self.main_app.steps[self.main_app.execution_engine.current_step_index]
                step_desc = current_step.get('description', '')
                self.main_app.canvas_manager.detect_operation_mode_from_step(step_desc)
                self.main_app.canvas_manager.track_operation_from_step(step_desc)
            self.update_step_display()
    
    def run_execution(self):
        """Start execution"""
        if self.main_app.steps:
            self.main_app.execution_engine.start_execution()
            self.run_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            
            # Force immediate canvas position update when execution starts
            if hasattr(self.main_app, 'canvas_manager'):
                self.main_app.canvas_manager.update_position_display()
    
    def pause_execution(self):
        """Pause execution"""
        if self.main_app.execution_engine.pause_execution():
            self.run_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
    
    def stop_execution(self):
        """Stop execution"""
        if self.main_app.execution_engine.stop_execution():
            self.run_btn.config(state=tk.NORMAL if self.main_app.steps else tk.DISABLED)
            self.pause_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.main_app.operation_label.config(text="Execution Stopped", fg='red')
    
    def reset_execution(self):
        """Reset execution and UI state"""
        # Reset execution engine
        self.main_app.execution_engine.reset_execution()
        
        # Reset hardware state (position, tools, sensors)
        from mock_hardware import reset_hardware, move_x, move_y
        reset_hardware()
        
        # Move hardware to motor home positions (0, 0)
        move_x(0.0)  # Rows motor home position  
        move_y(0.0)  # Lines motor home position
        
        # Reset operation states to pending
        if hasattr(self.main_app, 'operation_states'):
            # Clear and reset line states
            self.main_app.operation_states['lines'].clear()
            if self.main_app.current_program:
                for line_num in range(1, self.main_app.current_program.number_of_lines + 1):
                    self.main_app.operation_states['lines'][line_num] = 'pending'
            
            # Clear and reset cut states  
            self.main_app.operation_states['cuts'].clear()
            for cut_name in ['top', 'bottom', 'left', 'right']:
                self.main_app.operation_states['cuts'][cut_name] = 'pending'
                
            # Clear and reset page states
            self.main_app.operation_states['pages'].clear()
            if self.main_app.current_program:
                for page_num in range(self.main_app.current_program.number_of_pages):
                    self.main_app.operation_states['pages'][page_num] = 'pending'
        
        # Reset progress bar
        if hasattr(self.main_app, 'progress') and hasattr(self.main_app, 'progress_text'):
            self.main_app.progress['value'] = 0
            self.main_app.progress_text.config(text="0% Complete")
        
        # Reset operation label
        self.main_app.operation_label.config(text="System Ready", fg='blue')
        
        # Reset progress label
        self.progress_label.config(text="Ready", fg='darkblue')
        
        # Reset sensor status label (cancel any pending updates)
        try:
            # Cancel any pending sensor label updates
            self.main_app.root.after_cancel()
        except:
            pass  # Ignore if no pending tasks
        self.sensor_label.config(text="Sensor: Ready", fg='darkgreen')
        
        # Reset state label
        self.state_label.config(text="State: Idle", fg='darkred')
        
        # Reset canvas and refresh colors to show all as pending
        if hasattr(self.main_app, 'canvas_manager'):
            # Reset motor operation mode to idle
            self.main_app.canvas_manager.set_motor_operation_mode("idle")
            
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
        
        print("🔄 Complete system reset - All components restored to initial state")
    
    def trigger_x_left(self):
        """Trigger X left sensor"""
        trigger_x_left_sensor()
        # Update old sensor_label only (status is shown in hardware panel)
        if hasattr(self, 'sensor_label'):
            self.sensor_label.config(text="Sensor: X-Left Triggered", fg='red')
            self.main_app.root.after(1000, lambda: self.sensor_label.config(text="Sensor: Ready", fg='darkgreen'))

        # Animate sensor trigger visualization
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.trigger_sensor_visualization('x_left')

    def trigger_x_right(self):
        """Trigger X right sensor"""
        trigger_x_right_sensor()
        # Update old sensor_label only (status is shown in hardware panel)
        if hasattr(self, 'sensor_label'):
            self.sensor_label.config(text="Sensor: X-Right Triggered", fg='red')
            self.main_app.root.after(1000, lambda: self.sensor_label.config(text="Sensor: Ready", fg='darkgreen'))

        # Animate sensor trigger visualization
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.trigger_sensor_visualization('x_right')

    def trigger_y_top(self):
        """Trigger Y top sensor"""
        trigger_y_top_sensor()
        # Update old sensor_label only (status is shown in hardware panel)
        if hasattr(self, 'sensor_label'):
            self.sensor_label.config(text="Sensor: Y-Top Triggered", fg='red')
            self.main_app.root.after(1000, lambda: self.sensor_label.config(text="Sensor: Ready", fg='darkgreen'))

        # Animate sensor trigger visualization
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.trigger_sensor_visualization('y_top')

    def trigger_y_bottom(self):
        """Trigger Y bottom sensor"""
        trigger_y_bottom_sensor()
        # Update old sensor_label only (status is shown in hardware panel)
        if hasattr(self, 'sensor_label'):
            self.sensor_label.config(text="Sensor: Y-Bottom Triggered", fg='red')
            self.main_app.root.after(1000, lambda: self.sensor_label.config(text="Sensor: Ready", fg='darkgreen'))

        # Animate sensor trigger visualization
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.trigger_sensor_visualization('y_bottom')
    
    def toggle_ls(self, switch_name):
        """Toggle a limit switch"""
        state = toggle_limit_switch(switch_name)
        print(f"Limit switch {switch_name} toggled: {'ON' if state else 'OFF'}")

        # Force canvas position update to refresh indicators
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_line_marker(self):
        """Toggle line marker piston"""
        if self.lines_marker_var.get():
            line_marker_down()
        else:
            line_marker_up()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_line_cutter(self):
        """Toggle line cutter piston"""
        if self.lines_cutter_var.get():
            line_cutter_down()
        else:
            line_cutter_up()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_line_motor(self):
        """Toggle line motor height"""
        if self.lines_motor_var.get():
            lower_line_tools()
        else:
            lift_line_tools()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_row_marker(self):
        """Toggle row marker piston"""
        if self.rows_marker_var.get():
            row_marker_down()
        else:
            row_marker_up()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()

    def toggle_row_cutter(self):
        """Toggle row cutter piston"""
        if self.rows_cutter_var.get():
            row_cutter_down()
        else:
            row_cutter_up()
        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.update_position_display()
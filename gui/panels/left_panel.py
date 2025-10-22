import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class LeftPanel:
    """Left panel for program control and parameter input"""
    
    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        self.program_fields = {}
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create all widgets for the left panel"""
        # Title - Compact
        tk.Label(self.parent_frame, text="PROGRAM CONTROL", font=('Arial', 11, 'bold'),
                bg='lightgray').pack(pady=3)

        # File Menu
        self.create_file_section()

        # Program Selection
        self.create_program_selection()

        # Input Fields
        self.create_input_fields()

        # Validation Status
        self.create_validation_section()
    
    def create_file_section(self):
        """Create file loading section"""
        file_frame = tk.Frame(self.parent_frame, bg='lightgray')
        file_frame.pack(fill=tk.X, padx=10, pady=3)

        tk.Button(file_frame, text="Load CSV", command=self.load_csv_file,
                 bg='darkgreen', fg='white', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='green', activeforeground='white').pack(fill=tk.X)

        self.current_file_label = tk.Label(file_frame, text="No file loaded",
                                          wraplength=200, bg='lightgray', font=('Arial', 8))
        self.current_file_label.pack(pady=(3,0))

    def create_program_selection(self):
        """Create program selection dropdown"""
        tk.Label(self.parent_frame, text="Program Selection:", font=('Arial', 9, 'bold'),
                bg='lightgray').pack(pady=(5,2))

        self.program_var = tk.StringVar()
        self.program_combo = ttk.Combobox(self.parent_frame, textvariable=self.program_var,
                                         state='readonly', width=25, font=('Arial', 9))
        self.program_combo.pack(padx=10, pady=3)
        self.program_combo.bind('<<ComboboxSelected>>', self.on_program_selected)
    
    def create_input_fields(self):
        """Create scrollable input fields section"""
        # Create scrollable frame for input fields
        canvas_frame = tk.Frame(self.parent_frame, bg='lightgray')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)
        
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
            ("Top Margin (cm):", "top_padding", 25),
            ("Bottom Margin (cm):", "bottom_padding", 25),
            # Row Pattern Settings  
            ("Width (cm):", "width", 25),
            ("Left Margin (cm):", "left_margin", 25),
            ("Right Margin (cm):", "right_margin", 25),
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
                 bg='darkorange', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='orange', activeforeground='black').pack(side=tk.LEFT, padx=(0,5))
        
        tk.Button(button_frame, text="Validate", command=self.validate_program,
                 bg='royalblue', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='blue', activeforeground='white').pack(side=tk.LEFT)
    
    def create_validation_section(self):
        """Create validation status section"""
        self.validation_frame = tk.Frame(self.parent_frame, bg='lightgray')
        self.validation_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.validation_indicator = tk.Label(self.validation_frame, text="●", 
                                           font=('Arial', 14), fg='gray', bg='lightgray')
        self.validation_indicator.pack(side=tk.LEFT)
        
        self.validation_text = tk.Label(self.validation_frame, text="No program selected", 
                                       bg='lightgray', font=('Arial', 9))
        self.validation_text.pack(side=tk.LEFT, padx=(5,0))
        
        # Add paper size display section
        self.create_paper_size_section()
    
    def create_paper_size_section(self):
        """Create paper size calculation display section"""
        # Paper size calculation frame
        paper_size_frame = tk.Frame(self.parent_frame, bg='lightsteelblue', relief=tk.RIDGE, bd=2)
        paper_size_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Title
        tk.Label(paper_size_frame, text="📐 ACTUAL PAPER SIZE (With Repeats)", 
                font=('Arial', 10, 'bold'), bg='lightsteelblue', fg='darkblue').pack(pady=5)
        
        # Pattern size section
        pattern_frame = tk.Frame(paper_size_frame, bg='lightsteelblue')
        pattern_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(pattern_frame, text="Single Pattern:", font=('Arial', 9, 'bold'),
                bg='lightsteelblue', fg='darkblue').grid(row=0, column=0, sticky="w")
        
        self.pattern_size_label = tk.Label(pattern_frame, text="0.0 × 0.0 cm", 
                                         font=('Arial', 9), bg='lightsteelblue', fg='darkblue')
        self.pattern_size_label.grid(row=0, column=1, sticky="w", padx=(5,0))
        
        # Repeats section
        tk.Label(pattern_frame, text="Repeats:", font=('Arial', 9, 'bold'),
                bg='lightsteelblue', fg='darkblue').grid(row=1, column=0, sticky="w")
        
        self.repeats_label = tk.Label(pattern_frame, text="1 rows × 1 lines", 
                                    font=('Arial', 9), bg='lightsteelblue', fg='darkblue')
        self.repeats_label.grid(row=1, column=1, sticky="w", padx=(5,0))
        
        # Actual size section (highlighted)
        actual_frame = tk.Frame(paper_size_frame, bg='lightcyan', relief=tk.SUNKEN, bd=2)
        actual_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(actual_frame, text="🎯 ACTUAL SIZE NEEDED:", font=('Arial', 10, 'bold'),
                bg='lightcyan', fg='darkred').pack()
        
        self.actual_size_label = tk.Label(actual_frame, text="0.0 × 0.0 cm", 
                                        font=('Arial', 12, 'bold'), bg='lightcyan', fg='darkred')
        self.actual_size_label.pack(pady=2)
        
        # Fit status
        self.fit_status_label = tk.Label(actual_frame, text="", 
                                       font=('Arial', 8), bg='lightcyan')
        self.fit_status_label.pack()
        
        pattern_frame.grid_columnconfigure(1, weight=1)
    
    def load_csv_file(self):
        """Load CSV file dialog"""
        file_path = filedialog.askopenfilename(
            title="Select CSV Program File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir="."
        )
        
        if file_path:
            self.main_app.load_csv_file_by_path(file_path)
            filename = file_path.split('/')[-1]
            self.current_file_label.config(text=f"File: {filename}")
    
    def update_program_list(self):
        """Update the program selection combo box"""
        program_names = [f"{p.program_number}. {p.program_name}" 
                        for p in self.main_app.programs]
        self.program_combo['values'] = program_names
        
        if program_names:
            self.program_combo.set(program_names[0])
            self.on_program_selected()  # Trigger canvas update
    
    def select_program(self, index):
        """Select program by index"""
        if 0 <= index < len(self.main_app.programs):
            program_names = self.program_combo['values']
            self.program_combo.set(program_names[index])
            self.on_program_selected()
    
    def on_program_selected(self, event=None):
        """Handle program selection"""
        if not self.program_combo.get():
            return
        
        try:
            selected_index = self.program_combo.current()
            if 0 <= selected_index < len(self.main_app.programs):
                self.main_app.current_program = self.main_app.programs[selected_index]
                self.update_program_details()
                self.main_app.canvas_manager.update_canvas_paper_area()
        except (ValueError, IndexError):
            pass
    
    def update_program_details(self):
        """Update input fields with current program details"""
        if not self.main_app.current_program:
            return
        
        p = self.main_app.current_program
        field_values = {
            'program_name': str(p.program_name),
            'program_number': str(p.program_number),
            'high': str(p.high),
            'number_of_lines': str(p.number_of_lines),
            'top_padding': str(p.top_padding),
            'bottom_padding': str(p.bottom_padding),
            'width': str(p.width),
            'left_margin': str(p.left_margin),
            'right_margin': str(p.right_margin),
            'page_width': str(p.page_width),
            'number_of_pages': str(p.number_of_pages),
            'buffer_between_pages': str(p.buffer_between_pages),
            'repeat_rows': str(p.repeat_rows),
            'repeat_lines': str(p.repeat_lines)
        }
        
        for field_name, value in field_values.items():
            if field_name in self.program_fields:
                self.program_fields[field_name].delete(0, tk.END)
                self.program_fields[field_name].insert(0, value)
        
        self.validate_program()
        self.update_paper_size_display()
    
    def validate_program(self):
        """Validate current program"""
        if not self.main_app.current_program:
            self.validation_indicator.config(fg='gray')
            self.validation_text.config(text="No program selected")
            return
        
        errors = self.main_app.current_program.validate()
        if not errors:
            self.validation_indicator.config(fg='green')
            self.validation_text.config(text="Program is valid")
        else:
            self.validation_indicator.config(fg='red')
            error_text = errors[0] if len(errors[0]) < 50 else errors[0][:50] + "..."
            self.validation_text.config(text=error_text)
    
    def on_field_change(self, event=None):
        """Handle field changes"""
        # Auto-validate after field change
        if self.main_app.current_program:
            self.validate_program()
            # Update paper size display if repeat fields changed
            widget = event.widget if event else None
            if widget in [self.program_fields.get('repeat_rows'), self.program_fields.get('repeat_lines'),
                         self.program_fields.get('width'), self.program_fields.get('high')]:
                self.update_paper_size_display_from_fields()
    
    def update_current_program(self):
        """Update current program with field values"""
        if not self.main_app.current_program:
            return
        
        try:
            p = self.main_app.current_program
            
            # Update program with field values
            p.program_name = self.program_fields['program_name'].get()
            p.program_number = int(self.program_fields['program_number'].get())
            p.high = float(self.program_fields['high'].get())
            p.number_of_lines = int(self.program_fields['number_of_lines'].get())
            p.top_padding = float(self.program_fields['top_padding'].get())
            p.bottom_padding = float(self.program_fields['bottom_padding'].get())
            p.width = float(self.program_fields['width'].get())
            p.left_margin = float(self.program_fields['left_margin'].get())
            p.right_margin = float(self.program_fields['right_margin'].get())
            p.page_width = float(self.program_fields['page_width'].get())
            p.number_of_pages = int(self.program_fields['number_of_pages'].get())
            p.buffer_between_pages = float(self.program_fields['buffer_between_pages'].get())
            p.repeat_rows = int(self.program_fields['repeat_rows'].get())
            p.repeat_lines = int(self.program_fields['repeat_lines'].get())
            
            # Update display
            self.update_program_list()
            self.main_app.canvas_manager.update_canvas_paper_area()
            self.validate_program()
            
            messagebox.showinfo("Success", "Program updated successfully!")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value entered: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update program: {e}")
    
    def update_paper_size_display(self):
        """Update paper size display with current program data"""
        if not self.main_app.current_program:
            self.pattern_size_label.config(text="No program selected")
            self.repeats_label.config(text="No program selected")
            self.actual_size_label.config(text="No program selected")
            self.fit_status_label.config(text="")
            return
        
        p = self.main_app.current_program
        
        # Single pattern size
        self.pattern_size_label.config(text=f"{p.width} × {p.high} cm")
        
        # Repeats
        self.repeats_label.config(text=f"{p.repeat_rows} rows × {p.repeat_lines} lines")
        
        # Calculate actual size
        actual_width = p.width * p.repeat_rows
        actual_height = p.high * p.repeat_lines
        
        self.actual_size_label.config(text=f"{actual_width} × {actual_height} cm")
        
        # Check if it fits on desk (from program model constants)
        from program_model import ScratchDeskProgram
        max_width = ScratchDeskProgram.MAX_WIDTH_OF_DESK
        max_height = ScratchDeskProgram.MAX_HEIGHT_OF_DESK
        
        fits_width = actual_width <= max_width
        fits_height = actual_height <= max_height
        fits_on_desk = fits_width and fits_height
        
        if fits_on_desk:
            self.fit_status_label.config(text="✅ Fits on desk", fg='darkgreen')
        else:
            warnings = []
            if not fits_width:
                warnings.append(f"Width exceeds desk ({actual_width} > {max_width})")
            if not fits_height:
                warnings.append(f"Height exceeds desk ({actual_height} > {max_height})")
            self.fit_status_label.config(text=f"⚠️ {'; '.join(warnings)}", fg='darkred')
    
    def update_paper_size_display_from_fields(self):
        """Update paper size display from current field values (for real-time updates)"""
        try:
            # Get values directly from fields
            width = float(self.program_fields['width'].get() or 0)
            high = float(self.program_fields['high'].get() or 0)
            repeat_rows = int(self.program_fields['repeat_rows'].get() or 1)
            repeat_lines = int(self.program_fields['repeat_lines'].get() or 1)
            
            # Single pattern size
            self.pattern_size_label.config(text=f"{width} × {high} cm")
            
            # Repeats
            self.repeats_label.config(text=f"{repeat_rows} rows × {repeat_lines} lines")
            
            # Calculate actual size
            actual_width = width * repeat_rows
            actual_height = high * repeat_lines
            
            self.actual_size_label.config(text=f"{actual_width} × {actual_height} cm")
            
            # Check if it fits on desk
            from program_model import ScratchDeskProgram
            max_width = ScratchDeskProgram.MAX_WIDTH_OF_DESK
            max_height = ScratchDeskProgram.MAX_HEIGHT_OF_DESK
            
            fits_width = actual_width <= max_width
            fits_height = actual_height <= max_height
            fits_on_desk = fits_width and fits_height
            
            if fits_on_desk:
                self.fit_status_label.config(text="✅ Fits on desk", fg='darkgreen')
            else:
                warnings = []
                if not fits_width:
                    warnings.append(f"Width exceeds desk ({actual_width} > {max_width})")
                if not fits_height:
                    warnings.append(f"Height exceeds desk ({actual_height} > {max_height})")
                self.fit_status_label.config(text=f"⚠️ {'; '.join(warnings)}", fg='darkred')
                
        except (ValueError, TypeError):
            # Handle invalid field values gracefully
            self.actual_size_label.config(text="Invalid values")
            self.fit_status_label.config(text="⚠️ Check your input values", fg='orange')
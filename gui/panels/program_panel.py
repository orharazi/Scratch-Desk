import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core.logger import get_logger
from core.translations import t, rtl
from core.program_model import translate_validation_error
from core.csv_parser import CSVParser


class ProgramPanel:
    """Program panel (right side in RTL layout) for program control and parameter input (collapsible)"""

    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        self.program_fields = {}
        self.logger = get_logger()
        self._collapsed = False
        self._creating_new_program = False
        self._pre_creation_program_index = None
        self._pre_creation_program = None

        self.create_widgets()

    def create_widgets(self):
        """Create all widgets for the left panel"""
        # Header bar with title and collapse toggle
        header_frame = tk.Frame(self.parent_frame, bg='#A0A0A0')
        header_frame.pack(fill=tk.X)

        self.toggle_btn = tk.Button(
            header_frame, text="◄", command=self.toggle_collapse,
            font=('Arial', 10, 'bold'), bg='#A0A0A0', fg='black',
            relief=tk.FLAT, width=2, cursor='hand2',
            activebackground='#888888'
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=2, pady=2)

        self.title_label = tk.Label(
            header_frame, text=t("PROGRAM CONTROL"),
            font=('Arial', 11, 'bold'), bg='#A0A0A0', fg='black'
        )
        self.title_label.pack(side=tk.RIGHT, pady=3, padx=5)

        # Content frame - holds everything that gets collapsed
        self.content_frame = tk.Frame(self.parent_frame, bg='lightgray')
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # File Menu
        self.create_file_section()

        # Program Selection
        self.create_program_selection()

        # Input Fields
        self.create_input_fields()

        # Validation Status
        self.create_validation_section()

    def toggle_collapse(self):
        """Toggle panel collapsed/expanded state"""
        if self._collapsed:
            # Expand
            self.content_frame.pack(fill=tk.BOTH, expand=True)
            self.toggle_btn.config(text="◄")
            title = t("NEW PROGRAM") if self._creating_new_program else t("PROGRAM CONTROL")
            self.title_label.config(text=title)
            self.main_app.program_frame.configure(width=280)
            self.main_app.root.grid_columnconfigure(2, minsize=220, weight=0)
        else:
            # Collapse
            self.content_frame.pack_forget()
            self.toggle_btn.config(text="►")
            self.title_label.config(text="")
            self.main_app.program_frame.configure(width=30)
            self.main_app.root.grid_columnconfigure(2, minsize=30, weight=0)
        self._collapsed = not self._collapsed

    def create_file_section(self):
        """Create file loading section"""
        file_frame = tk.Frame(self.content_frame, bg='lightgray')
        file_frame.pack(fill=tk.X, padx=10, pady=3)

        self.load_csv_btn = tk.Button(file_frame, text=t("Load CSV"), command=self.load_csv_file,
                 bg='darkgreen', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='green', activeforeground='black')
        self.load_csv_btn.pack(fill=tk.X)

        self.current_file_label = tk.Label(file_frame, text=t("No file loaded"),
                                          wraplength=200, bg='lightgray', fg='black', font=('Arial', 8), anchor='e', justify='right')
        self.current_file_label.pack(pady=(3,0), fill=tk.X)

    def create_program_selection(self):
        """Create program selection dropdown"""
        tk.Label(self.content_frame, text=t("Program Selection:"), font=('Arial', 9, 'bold'),
                bg='lightgray', fg='black', anchor='e').pack(pady=(5,2), fill=tk.X, padx=10)

        self.program_var = tk.StringVar()
        # Configure RTL style for combobox
        style = ttk.Style()
        style.configure('RTL.TCombobox', justify='right')
        self.program_combo = ttk.Combobox(self.content_frame, textvariable=self.program_var,
                                         state='readonly', width=22, font=('Arial', 9), style='RTL.TCombobox', justify='right')
        self.program_combo.pack(padx=10, pady=3, fill=tk.X)
        self.program_combo.bind('<<ComboboxSelected>>', self.on_program_selected)

    def create_input_fields(self):
        """Create scrollable input fields section"""
        # Create scrollable frame for input fields
        canvas_frame = tk.Frame(self.content_frame, bg='lightgray')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # Create canvas with scrollbar
        self.input_canvas = tk.Canvas(canvas_frame, bg='lightgray', highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.input_canvas.yview)
        self.input_frame = tk.Frame(self.input_canvas, bg='lightgray')

        self.input_frame.bind(
            "<Configure>",
            lambda e: self.input_canvas.configure(scrollregion=self.input_canvas.bbox("all"))
        )

        self._input_canvas_window = self.input_canvas.create_window((0, 0), window=self.input_frame, anchor="ne")
        self.input_canvas.configure(yscrollcommand=scrollbar.set)

        # Stretch input_frame to fill canvas width and keep anchored right
        def _on_input_canvas_configure(event):
            self.input_canvas.itemconfig(self._input_canvas_window, width=event.width)
            self.input_canvas.coords(self._input_canvas_window, event.width, 0)
        self.input_canvas.bind('<Configure>', _on_input_canvas_configure)

        self.input_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Program Details Header
        tk.Label(self.input_frame, text=t("Program Parameters:"), font=('Arial', 10, 'bold'),
                bg='lightgray', fg='black').grid(row=0, column=0, columnspan=2, pady=(0,10), sticky="e")

        # Create input fields with new CSV structure
        fields = [
            (t("Program Name:"), "program_name", 25),
            (t("Program Number:"), "program_number", 25),
            # Lines Pattern Settings
            (t("High (cm):"), "high", 25),
            (t("Number of Lines:"), "number_of_lines", 25),
            (t("Top Margin (cm):"), "top_padding", 25),
            (t("Bottom Margin (cm):"), "bottom_padding", 25),
            # Row Pattern Settings
            (t("Width (cm):"), "width", 25),
            (t("Left Margin (cm):"), "left_margin", 25),
            (t("Right Margin (cm):"), "right_margin", 25),
            (t("Page Width (cm):"), "page_width", 25),
            (t("Number of Pages:"), "number_of_pages", 25),
            (t("Buffer Between Pages (cm):"), "buffer_between_pages", 25),
            # Generate Settings
            (t("Repeat Rows:"), "repeat_rows", 25),
            (t("Repeat Lines:"), "repeat_lines", 25)
        ]

        row = 1
        for label_text, field_name, width in fields:
            # RTL layout: entry on left (col 0), label on right (col 1)
            # Program name needs wider field for Hebrew text
            entry_width = 18 if field_name == 'program_name' else 8
            entry = tk.Entry(self.input_frame, width=entry_width, font=('Arial', 9), justify='right')
            entry.grid(row=row, column=0, sticky="ew", pady=2, padx=(0,5))
            entry.bind('<KeyRelease>', self.on_field_change)

            tk.Label(self.input_frame, text=label_text, font=('Arial', 9),
                    bg='lightgray', fg='black', anchor='e').grid(row=row, column=1, sticky="e", pady=2)

            self.program_fields[field_name] = entry
            row += 1

        # Configure grid weights - labels column expands to push content right
        self.input_frame.grid_columnconfigure(0, weight=0)
        self.input_frame.grid_columnconfigure(1, weight=1)

        # Update and Add New buttons (normal mode)
        self._button_row = row
        self.button_frame = tk.Frame(self.input_frame, bg='lightgray')
        self.button_frame.grid(row=row, column=0, columnspan=2, pady=(10,5), sticky="ew")

        self.update_btn = tk.Button(self.button_frame, text=t("Update Program"), command=self.update_current_program,
                 bg='darkorange', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='orange', activeforeground='black')
        self.update_btn.pack(fill=tk.X, pady=(0,3))

        self.add_new_btn = tk.Button(self.button_frame, text=t("Add New Program"), command=self._start_new_program,
                 bg='#2980B9', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='#3498DB', activeforeground='black')
        self.add_new_btn.pack(fill=tk.X, pady=(0,3))

        self.delete_btn = tk.Button(self.button_frame, text=t("Delete Program"), command=self._delete_current_program,
                 bg='#C0392B', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='#E74C3C', activeforeground='black')
        self.delete_btn.pack(fill=tk.X)

        # Save and Cancel buttons (creation mode) - hidden by default
        self.creation_button_frame = tk.Frame(self.input_frame, bg='lightgray')

        self.save_new_btn = tk.Button(self.creation_button_frame, text=t("Save Program"), command=self._save_new_program,
                 bg='#27AE60', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='#2ECC71', activeforeground='black')
        self.save_new_btn.pack(fill=tk.X, pady=(0,3))

        self.cancel_new_btn = tk.Button(self.creation_button_frame, text=t("Cancel"), command=self._cancel_new_program,
                 bg='#C0392B', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, bd=2, activebackground='#E74C3C', activeforeground='black')
        self.cancel_new_btn.pack(fill=tk.X)

    def create_validation_section(self):
        """Create validation status section"""
        self.validation_frame = tk.Frame(self.content_frame, bg='lightgray')
        self.validation_frame.pack(fill=tk.X, padx=10, pady=5)

        self.validation_indicator = tk.Label(self.validation_frame, text="●",
                                           font=('Arial', 14), fg='gray', bg='lightgray')
        self.validation_indicator.pack(side=tk.RIGHT)

        self.validation_text = tk.Label(self.validation_frame, text=t("No program selected"),
                                       bg='lightgray', fg='black', font=('Arial', 9), anchor='e')
        self.validation_text.pack(side=tk.RIGHT, padx=(0,5))

        # Add paper size display section
        self.create_paper_size_section()

    def create_paper_size_section(self):
        """Create paper size calculation display section"""
        # Paper size calculation frame
        paper_size_frame = tk.Frame(self.content_frame, bg='lightsteelblue', relief=tk.RIDGE, bd=2)
        paper_size_frame.pack(fill=tk.X, padx=3, pady=5)

        # Title
        tk.Label(paper_size_frame, text=t("📐 ACTUAL PAPER SIZE (With Repeats)"),
                font=('Arial', 8, 'bold'), bg='lightsteelblue', fg='darkblue', wraplength=220).pack(pady=3)

        # Pattern size section
        pattern_frame = tk.Frame(paper_size_frame, bg='lightsteelblue')
        pattern_frame.pack(fill=tk.X, padx=10)

        # RTL layout: values on left (col 0), labels on right (col 1)
        self.pattern_size_label = tk.Label(pattern_frame, text=t("{width} × {height} cm", width="0.0", height="0.0"),
                                         font=('Arial', 9), bg='lightsteelblue', fg='darkblue')
        self.pattern_size_label.grid(row=0, column=0, sticky="e", padx=(0,5))

        tk.Label(pattern_frame, text=t("Single Pattern:"), font=('Arial', 9, 'bold'),
                bg='lightsteelblue', fg='darkblue').grid(row=0, column=1, sticky="e")

        # Repeats section
        self.repeats_label = tk.Label(pattern_frame, text=t("{rows} rows × {lines} lines", rows="1", lines="1"),
                                    font=('Arial', 9), bg='lightsteelblue', fg='darkblue')
        self.repeats_label.grid(row=1, column=0, sticky="e", padx=(0,5))

        tk.Label(pattern_frame, text=t("Repeats:"), font=('Arial', 9, 'bold'),
                bg='lightsteelblue', fg='darkblue').grid(row=1, column=1, sticky="e")

        # Line distance section
        self.line_distance_label = tk.Label(pattern_frame, text=t("N/A (single line)"),
                                           font=('Arial', 9), bg='lightsteelblue', fg='darkblue')
        self.line_distance_label.grid(row=2, column=0, sticky="e", padx=(0,5))

        tk.Label(pattern_frame, text=t("Line distance:"), font=('Arial', 9, 'bold'),
                bg='lightsteelblue', fg='darkblue').grid(row=2, column=1, sticky="e")

        # Actual size section (highlighted)
        actual_frame = tk.Frame(paper_size_frame, bg='lightcyan', relief=tk.SUNKEN, bd=2)
        actual_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(actual_frame, text=t("🎯 ACTUAL SIZE NEEDED:"), font=('Arial', 8, 'bold'),
                bg='lightcyan', fg='darkred').pack()

        self.actual_size_label = tk.Label(actual_frame, text=t("{width} × {height} cm", width="0.0", height="0.0"),
                                        font=('Arial', 10, 'bold'), bg='lightcyan', fg='darkred')
        self.actual_size_label.pack(pady=2)

        # Fit status
        self.fit_status_label = tk.Label(actual_frame, text="",
                                       font=('Arial', 8), bg='lightcyan', fg='black')
        self.fit_status_label.pack()

        pattern_frame.grid_columnconfigure(0, weight=1)

    def load_csv_file(self):
        """Load CSV file dialog"""
        file_path = filedialog.askopenfilename(
            title=t("Select CSV Program File"),
            filetypes=[(t("CSV files"), "*.csv"), (t("All files"), "*.*")],
            initialdir="."
        )

        if file_path:
            self.main_app.load_csv_file_by_path(file_path)
            filename = file_path.split('/')[-1]
            self.current_file_label.config(text=t("File: {filename}", filename=filename))

    def update_program_list(self):
        """Update the program selection combo box"""
        program_names = [rtl(f"{p.program_name} .{p.program_number}")
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
        """Handle program selection - resets execution state for new program"""
        if self._creating_new_program:
            return
        if not self.program_combo.get():
            return

        try:
            selected_index = self.program_combo.current()
            if 0 <= selected_index < len(self.main_app.programs):
                # Stop execution if running
                if hasattr(self.main_app, 'execution_engine') and self.main_app.execution_engine.is_running:
                    self.main_app.execution_engine.stop_execution()
                    self.logger.info("Stopped running execution for program switch", category="gui")

                # Clear old execution state (steps, step index, etc.)
                if hasattr(self.main_app, 'execution_engine'):
                    self.main_app.execution_engine.reset_execution(clear_steps=True)
                    self.main_app.steps = []

                # Prepare canvas for new program (clear sensor state, timers, etc.)
                if hasattr(self.main_app, 'canvas_manager'):
                    self.main_app.canvas_manager.prepare_for_new_program()

                # Set the new program
                self.main_app.current_program = self.main_app.programs[selected_index]
                self.update_program_details()

                # Initialize operation states for new program
                if hasattr(self.main_app, 'canvas_manager'):
                    self.main_app.canvas_manager.initialize_operation_states(self.main_app.current_program)
                    self.main_app.canvas_manager.update_canvas_paper_area()

                # Auto-generate steps for the new program
                if hasattr(self.main_app, 'controls_panel'):
                    self.main_app.controls_panel.generate_steps()

                self.logger.info(f"Switched to program: {self.main_app.current_program.program_name}", category="gui")
        except (ValueError, IndexError) as e:
            self.logger.error(f"Error selecting program: {e}", category="gui")

    def update_program_details(self):
        """Update input fields with current program details"""
        if not self.main_app.current_program:
            return

        p = self.main_app.current_program
        # Use RLI (Right-to-Left Isolate) for Hebrew program name in entry field
        # RLI/PDI are modern Unicode 6.3 isolate chars with better platform support than RLE/PDF
        # (cannot use rtl/get_display here as it reorders chars, breaking read-back)
        RLI = '\u2067'  # Right-to-Left Isolate
        PDI = '\u2069'  # Pop Directional Isolate
        field_values = {
            'program_name': f"{RLI}{p.program_name}{PDI}",
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
        """Validate current program object"""
        if not self.main_app.current_program:
            self.validation_indicator.config(fg='gray')
            self.validation_text.config(text=t("No program selected"))
            return

        errors = self.main_app.current_program.validate()
        self._show_validation_result(errors)

    def validate_from_fields(self):
        """Validate based on current field values (real-time as user types)"""
        temp_program = self._build_program_from_fields()
        if temp_program is None:
            self.validation_indicator.config(fg='red')
            self.validation_text.config(text=t("Invalid value entered"))
            return

        errors = temp_program.validate()
        self._show_validation_result(errors)

    def _show_validation_result(self, errors):
        """Display validation result in the indicator"""
        if not errors:
            self.validation_indicator.config(fg='green')
            self.validation_text.config(text=t("Program is valid"))
        else:
            self.validation_indicator.config(fg='red')
            translated_error = translate_validation_error(errors[0])
            error_text = translated_error if len(translated_error) < 50 else translated_error[:50] + "..."
            self.validation_text.config(text=error_text)

    def _strip_rtl_chars(self, text):
        """Strip RTL control characters from text for saving"""
        # Remove RLE, PDF, RLM, LRM, RLI, PDI control characters
        return (text.replace('\u202B', '').replace('\u202C', '')
                    .replace('\u200F', '').replace('\u200E', '')
                    .replace('\u2067', '').replace('\u2069', '').strip())

    def _build_program_from_fields(self):
        """Build a temporary ScratchDeskProgram from current field values for validation"""
        from core.program_model import ScratchDeskProgram
        try:
            return ScratchDeskProgram(
                program_number=int(self.program_fields['program_number'].get() or 0),
                program_name=self._strip_rtl_chars(self.program_fields['program_name'].get()),
                high=float(self.program_fields['high'].get() or 0),
                number_of_lines=int(self.program_fields['number_of_lines'].get() or 0),
                top_padding=float(self.program_fields['top_padding'].get() or 0),
                bottom_padding=float(self.program_fields['bottom_padding'].get() or 0),
                width=float(self.program_fields['width'].get() or 0),
                left_margin=float(self.program_fields['left_margin'].get() or 0),
                right_margin=float(self.program_fields['right_margin'].get() or 0),
                page_width=float(self.program_fields['page_width'].get() or 0),
                number_of_pages=int(self.program_fields['number_of_pages'].get() or 0),
                buffer_between_pages=float(self.program_fields['buffer_between_pages'].get() or 0),
                repeat_rows=int(self.program_fields['repeat_rows'].get() or 1),
                repeat_lines=int(self.program_fields['repeat_lines'].get() or 1),
            )
        except (ValueError, TypeError):
            return None

    def on_field_change(self, event=None):
        """Handle field changes - validate from current field values in real time"""
        if self.main_app.current_program or self._creating_new_program:
            self.validate_from_fields()
            self.update_paper_size_display_from_fields()

            # Live canvas preview during creation mode
            if self._creating_new_program:
                self._update_canvas_preview()

    def update_current_program(self):
        """Update current program with field values, refresh canvas and steps"""
        if not self.main_app.current_program:
            return

        try:
            p = self.main_app.current_program

            # Update program with field values (strip RTL chars for saving)
            p.program_name = self._strip_rtl_chars(self.program_fields['program_name'].get())
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

            # Update combo box label for the current program (without re-selecting)
            current_index = self.program_combo.current()
            program_names = [rtl(f"{prog.program_name} .{prog.program_number}")
                            for prog in self.main_app.programs]
            self.program_combo['values'] = program_names
            if 0 <= current_index < len(program_names):
                self.program_combo.set(program_names[current_index])

            # Reset execution state and canvas
            if hasattr(self.main_app, 'execution_engine'):
                self.main_app.execution_engine.reset_execution(clear_steps=True)
                self.main_app.steps = []

            # Reset canvas and operation states from scratch
            if hasattr(self.main_app, 'canvas_manager'):
                self.main_app.canvas_manager.prepare_for_new_program()
                self.main_app.operation_states = {}
                self.main_app.canvas_manager.initialize_operation_states(p)
                self.main_app.canvas_manager.update_canvas_paper_area()

            # Validate and regenerate steps
            self.validate_program()
            if hasattr(self.main_app, 'controls_panel'):
                self.main_app.controls_panel.generate_steps()

            self.update_paper_size_display()

            # Persist to CSV file
            self._persist_programs_to_csv()

            messagebox.showinfo(t("Success"), t("Program updated successfully!"))

        except ValueError as e:
            messagebox.showerror(t("Error"), t("Invalid value entered: {error}", error=str(e)))
        except Exception as e:
            messagebox.showerror(t("Error"), t("Failed to update program: {error}", error=str(e)))

    def _persist_programs_to_csv(self):
        """Save current programs list back to the CSV file"""
        csv_path = getattr(self.main_app, 'current_file', None)
        if not csv_path:
            self.logger.warning("No CSV file path set, cannot persist programs", category="gui")
            return False

        parser = CSVParser()
        success, errors = parser.save_programs_to_csv(self.main_app.programs, csv_path)
        if success:
            self.logger.info(f"Programs saved to {csv_path}", category="gui")
        else:
            self.logger.error(f"Failed to save programs: {errors}", category="gui")
        return success

    def _delete_current_program(self):
        """Delete the currently selected program with confirmation"""
        if not self.main_app.current_program:
            return

        if not self.main_app.programs or len(self.main_app.programs) <= 1:
            messagebox.showwarning(t("Warning"), t("Cannot delete the last program"))
            return

        # Block if execution is running
        if hasattr(self.main_app, 'execution_engine') and self.main_app.execution_engine.is_running:
            messagebox.showwarning(t("Warning"), t("Cannot delete program while execution is running"))
            return

        program_name = self.main_app.current_program.program_name
        program_number = self.main_app.current_program.program_number

        if not messagebox.askyesno(
            t("Delete Program"),
            t("Are you sure you want to delete program \"{name}\" (#{number})?",
              name=program_name, number=program_number)
        ):
            return

        selected_index = self.program_combo.current()
        self.main_app.programs.pop(selected_index)

        # Persist to CSV
        self._persist_programs_to_csv()

        # Select another program
        new_index = min(selected_index, len(self.main_app.programs) - 1)
        program_names = [rtl(f"{p.program_name} .{p.program_number}") for p in self.main_app.programs]
        self.program_combo['values'] = program_names
        self.program_combo.set(program_names[new_index])
        self.on_program_selected()

        self.logger.info(f"Deleted program: {program_name} (#{program_number})", category="gui")

    # =========================================================================
    # New Program Creation Mode
    # =========================================================================

    def _start_new_program(self):
        """Enter creation mode: clear fields, swap buttons, disable combo + Load CSV"""
        # Block if execution is running
        if hasattr(self.main_app, 'execution_engine') and self.main_app.execution_engine.is_running:
            messagebox.showwarning(t("Warning"), t("Cannot add program while execution is running"))
            return

        self._creating_new_program = True
        self._pre_creation_program_index = self.program_combo.current()
        self._pre_creation_program = self.main_app.current_program

        # Disable combo and Load CSV
        self.program_combo.config(state='disabled')
        self.load_csv_btn.config(state='disabled')

        # Swap button frames
        self.button_frame.grid_forget()
        self.creation_button_frame.grid(row=self._button_row, column=0, columnspan=2, pady=(10,5), sticky="ew")

        # Update title
        self.title_label.config(text=t("NEW PROGRAM"))

        # Fill fields with valid defaults
        defaults = {
            'program_number': str(self._get_next_program_number()),
            'program_name': '',
            'high': '10.0',
            'number_of_lines': '1',
            'top_padding': '0.0',
            'bottom_padding': '0.0',
            'width': '10.0',
            'left_margin': '1.0',
            'right_margin': '1.0',
            'page_width': '8.0',
            'number_of_pages': '1',
            'buffer_between_pages': '0.0',
            'repeat_rows': '1',
            'repeat_lines': '1',
        }
        for field_name, value in defaults.items():
            if field_name in self.program_fields:
                self.program_fields[field_name].delete(0, tk.END)
                self.program_fields[field_name].insert(0, value)

        # Trigger validation and paper size update
        self.validate_from_fields()
        self.update_paper_size_display_from_fields()

        # Render canvas preview with default values
        self._update_canvas_preview()

        self.logger.info("Entered new program creation mode", category="gui")

    def _get_next_program_number(self):
        """Returns max(existing program numbers) + 1, or 1 if no programs"""
        if not self.main_app.programs:
            return 1
        return max(p.program_number for p in self.main_app.programs) + 1

    def _save_new_program(self):
        """Build program from fields, validate, add to programs list"""
        # Check program name (strip RTL chars)
        name = self._strip_rtl_chars(self.program_fields['program_name'].get())
        if not name:
            messagebox.showerror(t("Error"), t("Program name cannot be empty"))
            return

        # Build program from fields
        new_program = self._build_program_from_fields()
        if new_program is None:
            messagebox.showerror(t("Error"), t("Invalid value entered"))
            return

        # Check duplicate program number
        for p in self.main_app.programs:
            if p.program_number == new_program.program_number:
                messagebox.showerror(t("Error"), t("Program number {number} already exists", number=new_program.program_number))
                return

        # Validate the program
        errors = new_program.validate()
        if errors:
            self._show_validation_result(errors)
            messagebox.showerror(t("Error"), t("Program has validation errors"))
            return

        # Add to programs list
        self.main_app.programs.append(new_program)
        new_index = len(self.main_app.programs) - 1

        # Persist to CSV file
        self._persist_programs_to_csv()

        # Exit creation mode
        self._exit_creation_mode()

        # Update combo and select the new program
        program_names = [rtl(f"{p.program_name} .{p.program_number}")
                        for p in self.main_app.programs]
        self.program_combo['values'] = program_names
        self.program_combo.set(program_names[new_index])
        self.on_program_selected()

        messagebox.showinfo(t("Success"), t("Program added successfully!"))
        self.logger.info(f"New program created: {new_program.program_name} (#{new_program.program_number})", category="gui")

    def _cancel_new_program(self):
        """Cancel creation mode, confirm if data was entered, restore previous selection"""
        # Check if user entered a name (non-default data, strip RTL chars)
        name = self._strip_rtl_chars(self.program_fields['program_name'].get())
        if name:
            if not messagebox.askyesno(t("Warning"), t("Discard new program?")):
                return

        self._exit_creation_mode()

        # Restore previous selection
        if self._pre_creation_program_index is not None and self._pre_creation_program_index >= 0:
            program_names = self.program_combo['values']
            if self._pre_creation_program_index < len(program_names):
                self.program_combo.set(program_names[self._pre_creation_program_index])
                self.on_program_selected()
            else:
                self._clear_fields_for_no_selection()
        else:
            self._clear_fields_for_no_selection()

        self.logger.info("Cancelled new program creation", category="gui")

    def _exit_creation_mode(self):
        """Shared cleanup: reset flag, swap buttons back, re-enable combo + Load CSV, restore title"""
        self._creating_new_program = False

        # Swap button frames back
        self.creation_button_frame.grid_forget()
        self.button_frame.grid(row=self._button_row, column=0, columnspan=2, pady=(10,5), sticky="ew")

        # Re-enable combo and Load CSV
        self.program_combo.config(state='readonly')
        self.load_csv_btn.config(state='normal')

        # Restore title
        self.title_label.config(text=t("PROGRAM CONTROL"))

    def _update_canvas_preview(self):
        """Build a temp program from fields and render it on the canvas"""
        temp_program = self._build_program_from_fields()
        if temp_program is None:
            return

        # Set as current_program so canvas rendering works
        self.main_app.current_program = temp_program

        if hasattr(self.main_app, 'canvas_manager'):
            self.main_app.canvas_manager.initialize_operation_states(temp_program)
            self.main_app.canvas_manager.update_canvas_paper_area()

    def _clear_fields_for_no_selection(self):
        """Clear all fields when no program is selected after cancel"""
        self.main_app.current_program = self._pre_creation_program if hasattr(self, '_pre_creation_program') else None
        for field_name in self.program_fields:
            self.program_fields[field_name].delete(0, tk.END)
        self.validation_indicator.config(fg='gray')
        self.validation_text.config(text=t("No program selected"))
        # Clear canvas preview
        if hasattr(self.main_app, 'canvas') and not self.main_app.current_program:
            self.main_app.canvas.delete("work_lines")
            if hasattr(self.main_app, 'canvas_manager') and 'paper' in self.main_app.canvas_manager.canvas_objects:
                self.main_app.canvas.delete(self.main_app.canvas_manager.canvas_objects['paper'])
                del self.main_app.canvas_manager.canvas_objects['paper']

    def update_paper_size_display(self):
        """Update paper size display with current program data"""
        if not self.main_app.current_program:
            self.pattern_size_label.config(text=t("No program selected"))
            self.repeats_label.config(text=t("No program selected"))
            self.line_distance_label.config(text="")
            self.actual_size_label.config(text=t("No program selected"))
            self.fit_status_label.config(text="")
            return

        p = self.main_app.current_program

        # Single pattern size
        self.pattern_size_label.config(text=t("{width} × {height} cm", width=p.width, height=p.high))

        # Repeats
        self.repeats_label.config(text=t("{rows} rows × {lines} lines", rows=p.repeat_rows, lines=p.repeat_lines))

        # Distance between lines
        if p.number_of_lines > 1:
            available_space = p.high - p.top_padding - p.bottom_padding
            line_distance = available_space / (p.number_of_lines - 1)
            self.line_distance_label.config(text=t("{distance:.2f} cm", distance=line_distance))
        else:
            self.line_distance_label.config(text=t("{distance:.2f} cm", distance=0.0))

        # Calculate actual size
        actual_width = p.width * p.repeat_rows
        actual_height = p.high * p.repeat_lines

        self.actual_size_label.config(text=t("{width} × {height} cm", width=actual_width, height=actual_height))

        # Check if it fits on desk (from program model constants)
        from core.program_model import ScratchDeskProgram
        max_width = ScratchDeskProgram.MAX_WIDTH_OF_DESK
        max_height = ScratchDeskProgram.MAX_HEIGHT_OF_DESK

        fits_width = actual_width <= max_width
        fits_height = actual_height <= max_height
        fits_on_desk = fits_width and fits_height

        if fits_on_desk:
            self.fit_status_label.config(text=t("✅ Fits on desk"), fg='darkgreen')
        else:
            warnings = []
            if not fits_width:
                warnings.append(t("Width exceeds desk ({actual} > {max})", actual=actual_width, max=max_width))
            if not fits_height:
                warnings.append(t("Height exceeds desk ({actual} > {max})", actual=actual_height, max=max_height))
            self.fit_status_label.config(text=t("⚠️ {warnings}", warnings="; ".join(warnings)), fg='darkred')

    def update_paper_size_display_from_fields(self):
        """Update paper size display from current field values (for real-time updates)"""
        try:
            # Get values directly from fields
            width = float(self.program_fields['width'].get() or 0)
            high = float(self.program_fields['high'].get() or 0)
            repeat_rows = int(self.program_fields['repeat_rows'].get() or 1)
            repeat_lines = int(self.program_fields['repeat_lines'].get() or 1)
            number_of_lines = int(self.program_fields['number_of_lines'].get() or 0)
            top_padding = float(self.program_fields['top_padding'].get() or 0)
            bottom_padding = float(self.program_fields['bottom_padding'].get() or 0)

            # Single pattern size
            self.pattern_size_label.config(text=t("{width} × {height} cm", width=width, height=high))

            # Repeats
            self.repeats_label.config(text=t("{rows} rows × {lines} lines", rows=repeat_rows, lines=repeat_lines))

            # Distance between lines
            if number_of_lines > 1:
                available_space = high - top_padding - bottom_padding
                line_distance = available_space / (number_of_lines - 1)
                self.line_distance_label.config(text=t("{distance:.2f} cm", distance=line_distance))
            else:
                self.line_distance_label.config(text=t("{distance:.2f} cm", distance=0.0))

            # Calculate actual size
            actual_width = width * repeat_rows
            actual_height = high * repeat_lines

            self.actual_size_label.config(text=t("{width} × {height} cm", width=actual_width, height=actual_height))

            # Check if it fits on desk
            from core.program_model import ScratchDeskProgram
            max_width = ScratchDeskProgram.MAX_WIDTH_OF_DESK
            max_height = ScratchDeskProgram.MAX_HEIGHT_OF_DESK

            fits_width = actual_width <= max_width
            fits_height = actual_height <= max_height
            fits_on_desk = fits_width and fits_height

            if fits_on_desk:
                self.fit_status_label.config(text=t("✅ Fits on desk"), fg='darkgreen')
            else:
                warnings = []
                if not fits_width:
                    warnings.append(t("Width exceeds desk ({actual} > {max})", actual=actual_width, max=max_width))
                if not fits_height:
                    warnings.append(t("Height exceeds desk ({actual} > {max})", actual=actual_height, max=max_height))
                self.fit_status_label.config(text=t("⚠️ {warnings}", warnings="; ".join(warnings)), fg='darkred')

        except (ValueError, TypeError):
            # Handle invalid field values gracefully
            self.actual_size_label.config(text=t("Invalid values"))
            self.fit_status_label.config(text=t("⚠️ Check your input values"), fg='orange')

    def create_work_operations_status(self):
        """Create work operations status box (moved from center panel for more canvas space)"""
        # Work operations frame
        ops_frame = tk.Frame(self.content_frame, relief=tk.RIDGE, bd=2, bg='lightblue')
        ops_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        # Title
        tk.Label(ops_frame, text=t("📋 WORK OPERATIONS STATUS"),
                font=('Arial', 9, 'bold'), bg='lightblue', fg='darkblue').pack(pady=2)

        # Operations displayed vertically for narrow panel
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
        mark_frame.pack(fill=tk.X, padx=5, pady=2)

        tk.Label(mark_frame, text=t("✏️ MARK"), font=('Arial', 8, 'bold'),
                bg='lightblue', fg='darkblue').pack()

        self.mark_status_frame = tk.Frame(mark_frame, bg='lightblue')
        self.mark_status_frame.pack(pady=1)

        self.create_status_indicators(self.mark_status_frame, [
            (t("Ready"), mark_colors['pending']), (t("Working"), mark_colors['in_progress']), (t("Done"), mark_colors['completed'])
        ])

        # CUT Operations
        cut_frame = tk.Frame(ops_frame, bg='lightblue')
        cut_frame.pack(fill=tk.X, padx=5, pady=2)

        tk.Label(cut_frame, text=t("✂️ CUT"), font=('Arial', 8, 'bold'),
                bg='lightblue', fg='darkblue').pack()

        self.cut_status_frame = tk.Frame(cut_frame, bg='lightblue')
        self.cut_status_frame.pack(pady=1)

        self.create_status_indicators(self.cut_status_frame, [
            (t("Ready"), cut_colors['pending']), (t("Working"), cut_colors['in_progress']), (t("Done"), cut_colors['completed'])
        ])

    def set_locked(self, locked: bool):
        """Lock or unlock the program panel during execution.

        When locked, the user cannot change the program selection, edit fields,
        load CSV files, or modify programs.
        """
        state = tk.DISABLED if locked else tk.NORMAL

        # Lock/unlock CSV load button
        if hasattr(self, 'load_csv_btn'):
            self.load_csv_btn.config(state=state)

        # Lock/unlock program combo (readonly when unlocked, disabled when locked)
        if hasattr(self, 'program_combo'):
            self.program_combo.config(state='disabled' if locked else 'readonly')

        # Lock/unlock all input fields
        for entry in self.program_fields.values():
            entry.config(state=state)

        # Lock/unlock action buttons
        if hasattr(self, 'update_btn'):
            self.update_btn.config(state=state)
        if hasattr(self, 'add_new_btn'):
            self.add_new_btn.config(state=state)
        if hasattr(self, 'delete_btn'):
            self.delete_btn.config(state=state)

    def create_status_indicators(self, parent, status_list):
        """Create colored line indicators for operation statuses"""
        for status_text, color in status_list:
            indicator_frame = tk.Frame(parent, bg='lightblue')
            indicator_frame.pack(side=tk.RIGHT, padx=2)

            # Colored line indicator
            canvas = tk.Canvas(indicator_frame, width=12, height=6, bg='lightblue', highlightthickness=0)
            canvas.pack()
            canvas.create_line(2, 3, 10, 3, fill=color, width=2)

            # Status text
            tk.Label(indicator_frame, text=status_text, font=('Arial', 6),
                    bg='lightblue', fg=color).pack()
import tkinter as tk
import re
from mock_hardware import get_current_x, get_current_y, move_x, move_y, get_hardware_status


class CanvasOperations:
    """Handles canvas operations for paper area and work lines visualization"""
    
    def __init__(self, main_app, canvas_manager):
        self.main_app = main_app
        self.canvas_manager = canvas_manager
        self.canvas_objects = main_app.canvas_objects
    
    def update_canvas_paper_area(self):
        """Update canvas to show current program's paper area and work lines with original logic"""
        if not self.main_app.current_program:
            return
        
        # Add debug keybindings when we have a program loaded
        self.add_debug_keybindings()
        
        # Clear all tagged objects for clean redraw
        self.main_app.canvas.delete("work_lines")
        
        p = self.main_app.current_program
        
        # Paper coordinates from settings (bottom-left corner at paper_start_x)
        hardware_limits = self.main_app.settings.get("hardware_limits", {})
        PAPER_OFFSET_X = hardware_limits.get("paper_start_x", 15.0)
        PAPER_OFFSET_Y = PAPER_OFFSET_X  # Use same value for Y start
        paper_bottom_left_x = PAPER_OFFSET_X
        paper_bottom_left_y = PAPER_OFFSET_Y
        
        # ACTUAL paper size (with repeats) - showing original behavior
        paper_width = p.width * p.repeat_rows
        paper_height = p.high * p.repeat_lines
        
        print(f"🖼️ CANVAS UPDATE: Showing ACTUAL paper size {paper_width}×{paper_height}cm (repeats: {p.repeat_rows}×{p.repeat_lines})")
        
        # Convert to canvas coordinates using settings
        sim_settings = self.main_app.settings.get("simulation", {})
        max_y_cm = sim_settings.get("max_display_y", 80)
        canvas_x1 = self.main_app.offset_x + paper_bottom_left_x * self.main_app.scale_x
        canvas_y1 = self.main_app.offset_y + (max_y_cm - paper_bottom_left_y - paper_height) * self.main_app.scale_y
        canvas_x2 = self.main_app.offset_x + (paper_bottom_left_x + paper_width) * self.main_app.scale_x
        canvas_y2 = self.main_app.offset_y + (max_y_cm - paper_bottom_left_y) * self.main_app.scale_y
        
        # Update or create paper rectangle
        if 'paper' in self.canvas_objects:
            self.main_app.canvas.coords(self.canvas_objects['paper'], canvas_x1, canvas_y1, canvas_x2, canvas_y2)
        else:
            self.canvas_objects['paper'] = self.main_app.canvas.create_rectangle(
                canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                outline='blue', width=3, fill='lightblue', stipple='gray50'
            )
        
        # Add program label with repeat information
        single_size = f"{p.width}×{p.high}cm"
        repeats_info = f"{p.repeat_rows}×{p.repeat_lines}" if (p.repeat_rows > 1 or p.repeat_lines > 1) else ""
        
        if repeats_info:
            label_text = f"{p.program_name}\nActual: {paper_width}×{paper_height}cm (Pattern: {single_size}, Repeats: {repeats_info})"
        else:
            label_text = f"{p.program_name}\n{paper_width}×{paper_height}cm"
        
        self.main_app.canvas.create_text(
            canvas_x1 + (canvas_x2 - canvas_x1) / 2, canvas_y1 - 25,
            text=label_text, 
            font=('Arial', 9, 'bold'), fill='darkblue', tags="work_lines", justify='center'
        )
        
        # Add line marking and cutting visualizations
        self.draw_work_lines(p, paper_bottom_left_x, paper_bottom_left_y, max_y_cm)
        
        # Legend is now drawn in center panel UI instead of on canvas
    
    def draw_work_lines(self, program, paper_x, paper_y, max_y_cm):
        """Draw visualization of lines that will be marked and cut with REPEAT SUPPORT"""

        # Initialize operation states when program changes
        self.initialize_operation_states(program)

        # Clear previous work line objects
        self.main_app.work_line_objects = {}

        # Calculate ACTUAL paper dimensions with repeats
        actual_paper_width = program.width * program.repeat_rows
        actual_paper_height = program.high * program.repeat_lines

        # Load colors from settings (fallback colors match WORK OPERATIONS STATUS)
        operation_colors = self.main_app.settings.get("operation_colors", {})
        lines_colors = operation_colors.get("lines", {
            "pending": "#FF6600",
            "in_progress": "#FF8800",
            "completed": "#00AA00"
        })
        rows_colors = operation_colors.get("rows", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })
        cuts_colors = operation_colors.get("cuts", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })

        print(f"📏 DRAWING WORK LINES: ACTUAL size {actual_paper_width}×{actual_paper_height}cm")
        
        # CORRECTED REPEAT VISUALIZATION: Process each repeated section individually
        # Each section has its own margins - match step generator logic exactly
        print(f"🖼️ CANVAS REPEAT: {program.repeat_lines} sections of {program.high}cm each")
        
        # Process each repeated section from top to bottom
        overall_line_num = 0
        for section_num in range(program.repeat_lines):
            section_start_y = paper_y + (program.repeat_lines - section_num) * program.high  # Top of this section
            section_end_y = paper_y + (program.repeat_lines - section_num - 1) * program.high  # Bottom of this section
            
            # Calculate line positions within THIS section (with section-specific margins)
            first_line_y_section = section_start_y - program.top_padding
            last_line_y_section = section_end_y + program.bottom_padding
            available_space_section = first_line_y_section - last_line_y_section
            
            if program.number_of_lines > 1:
                line_spacing_section = available_space_section / (program.number_of_lines - 1)
            else:
                line_spacing_section = 0
            
            print(f"   Canvas Section {section_num + 1}: lines from {first_line_y_section:.1f} to {last_line_y_section:.1f}cm")
            
            # Draw all lines in this section
            for line_in_section in range(program.number_of_lines):
                overall_line_num += 1
                line_y_real = first_line_y_section - (line_in_section * line_spacing_section)
                
                # Convert to canvas coordinates - lines span ENTIRE repeated paper width
                line_y_canvas = self.main_app.offset_y + (max_y_cm - line_y_real) * self.main_app.scale_y
                line_x1_canvas = self.main_app.offset_x + paper_x * self.main_app.scale_x
                line_x2_canvas = self.main_app.offset_x + (paper_x + actual_paper_width) * self.main_app.scale_x
                
                # SOLID lines - only color changes based on state (using settings)
                state = self.main_app.operation_states['lines'].get(overall_line_num, 'pending')
                if state == 'completed':
                    line_color = lines_colors['completed']
                elif state == 'in_progress':
                    line_color = lines_colors['in_progress']
                else:  # pending
                    line_color = lines_colors['pending']

                # Draw line - SOLID LINE
                line_id = self.main_app.canvas.create_line(
                    line_x1_canvas, line_y_canvas, line_x2_canvas, line_y_canvas,
                    fill=line_color, width=3, tags="work_lines"
                )
                
                # Store line object for dynamic updates (using settings colors)
                self.main_app.work_line_objects[f'line_{overall_line_num}'] = {
                    'id': line_id,
                    'type': 'line',
                    'color_pending': lines_colors['pending'],
                    'color_in_progress': lines_colors['in_progress'],
                    'color_completed': lines_colors['completed']
                }
                
                # Add line number label with matching color
                label_id = self.main_app.canvas.create_text(
                    line_x1_canvas - 25, line_y_canvas,
                    text=f"L{overall_line_num}", font=('Arial', 9, 'bold'), fill=line_color, tags="work_lines"
                )
                self.main_app.work_line_objects[f'line_{overall_line_num}']['label_id'] = label_id
        
        # Draw vertical lines (Row Pattern) WITH REPEAT SUPPORT - Show ALL page marks across repeated sections
        first_page_start = paper_x + program.left_margin
        
        # Calculate TOTAL pages across all repeated sections
        total_pages = program.number_of_pages * program.repeat_rows
        
        print(f"📄 DRAWING PAGES: {total_pages} total pages ({program.number_of_pages} per section × {program.repeat_rows} sections)")
        
        # Draw each page's start and end marks (across entire repeated area)
        page_mark_id = 1  # For tracking state
        
        for page_num in range(total_pages):
            # Calculate page start position across ENTIRE repeated paper
            page_start_x = first_page_start + page_num * (program.page_width + program.buffer_between_pages)
            
            # Calculate page end position  
            page_end_x = page_start_x + program.page_width
            
            # Draw page START mark - spans ACTUAL paper height
            page_start_canvas = self.main_app.offset_x + page_start_x * self.main_app.scale_x
            page_y1_canvas = self.main_app.offset_y + (max_y_cm - (paper_y + actual_paper_height)) * self.main_app.scale_y
            page_y2_canvas = self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y
            
            # Individual row state tracking - each edge is independent
            # Convert LEFT-TO-RIGHT drawing to RIGHT-TO-LEFT numbering
            # Drawing: page_num 0,1,2,3 (left to right)
            # RTL: page_num 3,2,1,0 (right to left) → R1,R2,R3... (right to left)
            rtl_drawing_row_num = (page_num * 2) + 1  # Drawing row number (left to right)
            individual_row_num = program.number_of_pages * 2 - rtl_drawing_row_num + 1  # Convert to RTL numbering
            row_state = self.main_app.operation_states['rows'].get(f'row_{rtl_drawing_row_num}', 'pending')

            # SOLID lines - only color changes based on state
            if row_state == 'completed':
                start_color = rows_colors['completed']
            elif row_state == 'in_progress':
                start_color = rows_colors['in_progress']
            else:  # pending
                start_color = rows_colors['pending']

            # Create individual row line (right edge) - SOLID LINE
            row_start_id = self.main_app.canvas.create_line(
                page_start_canvas, page_y1_canvas,
                page_start_canvas, page_y2_canvas,
                fill=start_color, width=3, tags="work_lines"
            )
            
            # Row label (R1, R3, R5, etc.)
            self.main_app.canvas.create_text(
                page_start_canvas, page_y2_canvas + 15,
                text=f"R{individual_row_num}", font=('Arial', 8, 'bold'), 
                fill=start_color, tags="work_lines"
            )
            
            # Draw page END mark
            page_end_canvas = self.main_app.offset_x + page_end_x * self.main_app.scale_x
            
            # Individual row state tracking - left edge is independent
            # Convert LEFT-TO-RIGHT drawing to RIGHT-TO-LEFT numbering for left edges
            rtl_drawing_row_num_left = (page_num * 2) + 2  # Drawing row number for left edges
            individual_row_num_left = program.number_of_pages * 2 - rtl_drawing_row_num_left + 1  # Convert to RTL numbering
            end_row_state = self.main_app.operation_states['rows'].get(f'row_{rtl_drawing_row_num_left}', 'pending')

            # SOLID lines - only color changes based on state
            if end_row_state == 'completed':
                end_color = rows_colors['completed']
            elif end_row_state == 'in_progress':
                end_color = rows_colors['in_progress']
            else:  # pending
                end_color = rows_colors['pending']

            # Create individual row line (left edge) - SOLID LINE
            row_end_id = self.main_app.canvas.create_line(
                page_end_canvas, page_y1_canvas,
                page_end_canvas, page_y2_canvas,
                fill=end_color, width=3, tags="work_lines"
            )
            
            # Row label (R2, R4, R6, etc.)
            self.main_app.canvas.create_text(
                page_end_canvas, page_y2_canvas + 15,
                text=f"R{individual_row_num_left}", font=('Arial', 8, 'bold'), 
                fill=end_color, tags="work_lines"
            )
            
            # Store individual row objects for dynamic updates (using settings colors)
            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num}'] = {
                'id': row_start_id,
                'type': 'row',
                'color_pending': rows_colors['pending'],
                'color_in_progress': rows_colors['in_progress'],
                'color_completed': rows_colors['completed']
            }

            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num_left}'] = {
                'id': row_end_id,
                'type': 'row',
                'color_pending': rows_colors['pending'],
                'color_in_progress': rows_colors['in_progress'],
                'color_completed': rows_colors['completed']
            }
        
        # Draw cut edges - horizontal cuts (top and bottom)
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
            state = self.main_app.operation_states['cuts'].get(cut_name, 'pending')

            # SOLID lines - only color changes based on state
            if state == 'completed':
                cut_color = cuts_colors['completed']
            elif state == 'in_progress':
                cut_color = cuts_colors['in_progress']
            else:  # pending
                cut_color = cuts_colors['pending']

            if orientation == 'horizontal':
                # Horizontal cuts span the paper width - SOLID LINE
                cut_y_canvas = self.main_app.offset_y + (max_y_cm - cut_pos) * self.main_app.scale_y
                cut_x1_canvas = self.main_app.offset_x + paper_x * self.main_app.scale_x
                cut_x2_canvas = self.main_app.offset_x + (paper_x + actual_paper_width) * self.main_app.scale_x

                cut_id = self.main_app.canvas.create_line(
                    cut_x1_canvas, cut_y_canvas, cut_x2_canvas, cut_y_canvas,
                    fill=cut_color, width=4, tags="work_lines"
                )

                # Add cut label
                self.main_app.canvas.create_text(
                    cut_x2_canvas + 10, cut_y_canvas,
                    text=cut_labels[i], font=('Arial', 8, 'bold'), fill=cut_color, tags="work_lines"
                )

            else:  # vertical
                # Vertical cuts span the paper height - SOLID LINE
                cut_x_canvas = self.main_app.offset_x + cut_pos * self.main_app.scale_x
                cut_y1_canvas = self.main_app.offset_y + (max_y_cm - (paper_y + actual_paper_height)) * self.main_app.scale_y
                cut_y2_canvas = self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y

                cut_id = self.main_app.canvas.create_line(
                    cut_x_canvas, cut_y1_canvas, cut_x_canvas, cut_y2_canvas,
                    fill=cut_color, width=4, tags="work_lines"
                )
                
                # Add cut label
                self.main_app.canvas.create_text(
                    cut_x_canvas, cut_y1_canvas - 10,
                    text=cut_labels[i], font=('Arial', 8, 'bold'), fill=cut_color, tags="work_lines"
                )
            
            # Store cut objects for dynamic updates (using settings colors)
            self.main_app.work_line_objects[f'cut_{cut_name}'] = {
                'id': cut_id,
                'type': 'cut',
                'color_pending': cuts_colors['pending'],
                'color_in_progress': cuts_colors['in_progress'],
                'color_completed': cuts_colors['completed']
            }
    
    def initialize_operation_states(self, program):
        """Initialize operation states for tracking completion status"""
        if not hasattr(self.main_app, 'operation_states'):
            self.main_app.operation_states = {}
        
        # Ensure all sub-dictionaries exist
        if 'lines' not in self.main_app.operation_states:
            self.main_app.operation_states['lines'] = {}
        if 'rows' not in self.main_app.operation_states:
            self.main_app.operation_states['rows'] = {}
        if 'cuts' not in self.main_app.operation_states:
            self.main_app.operation_states['cuts'] = {}
        
        # Initialize line states (total lines across all repeats)
        total_lines = program.number_of_lines * program.repeat_lines
        for line_num in range(1, total_lines + 1):
            if line_num not in self.main_app.operation_states['lines']:
                self.main_app.operation_states['lines'][line_num] = 'pending'
        
        # Initialize row states (total rows across all repeats)  
        total_rows = program.number_of_pages * 2 * program.repeat_rows  # 2 edges per page
        for row_num in range(1, total_rows + 1):
            row_key = f'row_{row_num}'
            if row_key not in self.main_app.operation_states['rows']:
                self.main_app.operation_states['rows'][row_key] = 'pending'
        
        # Initialize cut states
        cut_names = ['top', 'bottom', 'left', 'right']
        for cut_name in cut_names:
            if cut_name not in self.main_app.operation_states['cuts']:
                self.main_app.operation_states['cuts'][cut_name] = 'pending'
    
    def update_operation_state(self, operation_type, operation_id, new_state):
        """Update the state of a specific operation and refresh display"""
        if not hasattr(self.main_app, 'operation_states'):
            return
        
        # Ensure the operation_type sub-dictionary exists
        if operation_type not in self.main_app.operation_states:
            self.main_app.operation_states[operation_type] = {}
        
        self.main_app.operation_states[operation_type][operation_id] = new_state
        print(f"🔄 STATE UPDATE: {operation_type}.{operation_id} = {new_state}")
        
        # Update canvas colors immediately
        self.refresh_work_lines_colors()
    
    def track_operation_from_step(self, step_description):
        """Track operation progress from step descriptions"""
        if not step_description:
            return

        step_desc = step_description.lower()

        # Track line operations - match "Line X", "line X", "L X"
        line_match = re.search(r'(?:line|l)\s*(\d+)', step_desc, re.IGNORECASE)
        if line_match:
            line_num = int(line_match.group(1))
            # Detect state from keywords
            if any(keyword in step_desc for keyword in ['complete', 'marked', 'close line marker', 'finished']):
                self.update_operation_state('lines', line_num, 'completed')
                print(f"✅ Line {line_num} marked as COMPLETED")
            elif any(keyword in step_desc for keyword in ['marking', 'in progress', 'open line marker', 'mark line']):
                self.update_operation_state('lines', line_num, 'in_progress')
                print(f"🔄 Line {line_num} marked as IN PROGRESS")

        # Track row operations - match "RTL Page X" with edge detection
        # Rows are numbered by drawing order: (page-1)*2+1 for RIGHT, (page-1)*2+2 for LEFT
        rtl_page_match = re.search(r'rtl page\s*(\d+)', step_desc, re.IGNORECASE)
        if rtl_page_match:
            rtl_page_num = int(rtl_page_match.group(1))

            # Detect which edge (RIGHT or LEFT)
            row_num = None
            if 'right edge' in step_desc:
                row_num = (rtl_page_num - 1) * 2 + 1
            elif 'left edge' in step_desc:
                row_num = (rtl_page_num - 1) * 2 + 2

            if row_num is not None:
                row_key = f'row_{row_num}'

                # Detect state from keywords - mark in_progress on "Open", completed on "Close"
                if any(keyword in step_desc for keyword in ['close row marker', 'close row cutter', 'finished']):
                    self.update_operation_state('rows', row_key, 'completed')
                    print(f"✅ Row {row_num} (RTL Page {rtl_page_num}) marked as COMPLETED")
                elif any(keyword in step_desc for keyword in ['open row marker', 'open row cutter', 'wait top y sensor']):
                    self.update_operation_state('rows', row_key, 'in_progress')
                    print(f"🔄 Row {row_num} (RTL Page {rtl_page_num}) marked as IN PROGRESS")

        # Track cut edge operations
        for cut_name in ['top', 'bottom', 'left', 'right']:
            if cut_name in step_desc and 'edge' in step_desc:
                if any(keyword in step_desc for keyword in ['complete', 'close', 'finished']):
                    self.update_operation_state('cuts', cut_name, 'completed')
                    print(f"✅ {cut_name.title()} cut marked as COMPLETED")
                elif any(keyword in step_desc for keyword in ['cutting', 'open']):
                    self.update_operation_state('cuts', cut_name, 'in_progress')
                    print(f"🔄 {cut_name.title()} cut marked as IN PROGRESS")
    
    def refresh_work_lines_colors(self):
        """Refresh colors of work lines based on current operation states"""
        if not hasattr(self.main_app, 'work_line_objects') or not hasattr(self.main_app, 'operation_states'):
            return
        
        for obj_key, obj_data in self.main_app.work_line_objects.items():
            obj_type = obj_data['type']
            obj_id = obj_data['id']
            
            # Determine current state with safe access
            if obj_type == 'line':
                line_num = int(obj_key.split('_')[1])
                state = self.main_app.operation_states.get('lines', {}).get(line_num, 'pending')
            elif obj_type == 'row':
                row_key = obj_key  # Already in format 'row_N'
                state = self.main_app.operation_states.get('rows', {}).get(row_key, 'pending')
            elif obj_type == 'cut':
                cut_name = obj_key.split('_')[1]
                state = self.main_app.operation_states.get('cuts', {}).get(cut_name, 'pending')
            else:
                continue
            
            # Get color for current state (handle both 'in_progress' and 'progress' for backwards compatibility)
            if state == 'in_progress':
                color_key = 'color_in_progress'
            else:
                color_key = f'color_{state}'

            if color_key in obj_data:
                new_color = obj_data[color_key]
                
                # Update canvas object color
                self.main_app.canvas.itemconfig(obj_id, fill=new_color)
                
                # Update label color if it exists
                if 'label_id' in obj_data:
                    self.main_app.canvas.itemconfig(obj_data['label_id'], fill=new_color)
    
    def draw_enhanced_legend(self):
        """Draw enhanced legend on canvas (original functionality)"""
        legend_x = self.main_app.canvas_width - 200
        legend_y = 100
        
        # Legend title
        self.main_app.canvas.create_text(
            legend_x, legend_y - 20,
            text="Operations Legend", font=('Arial', 12, 'bold'), fill='black'
        )
        
        # Line operations
        self.main_app.canvas.create_text(
            legend_x, legend_y + 10,
            text="Lines:", font=('Arial', 10, 'bold'), fill='black', anchor='w'
        )
        
        # Line colors
        colors = [('#FF4444', 'Pending'), ('#FF8800', 'In Progress'), ('#00AA00', 'Completed')]
        for i, (color, label) in enumerate(colors):
            y_pos = legend_y + 30 + i * 20
            self.main_app.canvas.create_line(
                legend_x + 10, y_pos, legend_x + 30, y_pos,
                fill=color, width=3
            )
            self.main_app.canvas.create_text(
                legend_x + 35, y_pos,
                text=label, font=('Arial', 9), fill='black', anchor='w'
            )
    
    def test_color_changes(self):
        """Test color changes for debugging"""
        if hasattr(self.main_app, 'operation_states'):
            # Change a few states for testing
            if 1 in self.main_app.operation_states['lines']:
                self.update_operation_state('lines', 1, 'completed')
            if 'row_1' in self.main_app.operation_states['rows']:
                self.update_operation_state('rows', 'row_1', 'in_progress')
            if 'top' in self.main_app.operation_states['cuts']:
                self.update_operation_state('cuts', 'top', 'completed')
    
    def add_debug_keybindings(self):
        """Add debug keybindings for testing (original functionality)"""
        if hasattr(self.main_app, 'debug_bindings_added'):
            return  # Already added
        
        self.main_app.debug_bindings_added = True
        
        # Add keybinding for testing color changes
        self.main_app.root.bind('<Control-t>', lambda e: self.test_color_changes())
        print("🔧 DEBUG: Added Ctrl+T to test color changes")
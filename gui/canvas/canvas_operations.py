import tkinter as tk
import re


class CanvasOperations:
    """Handles work lines visualization, operation tracking, and color management"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.canvas_objects = main_app.canvas_objects
    
    def update_canvas_paper_area(self):
        """Update canvas to show current program's paper area and work lines"""
        if not self.main_app.current_program:
            return
        
        # Add debug keybindings when we have a program loaded
        self.add_debug_keybindings()
        
        # Clear all tagged objects for clean redraw
        self.main_app.canvas.delete("work_lines")
        
        p = self.main_app.current_program
        
        # Paper coordinates (bottom-left corner at 15, 15)
        paper_x = 15.0
        paper_y = 15.0
        
        # CALCULATE ACTUAL PAPER DIMENSIONS WITH REPEATS
        actual_paper_width = p.width * p.repeat_rows
        actual_paper_height = p.high * p.repeat_lines
        
        print(f"📄 PAPER VISUALIZATION: {actual_paper_width}×{actual_paper_height}cm (with repeats)")
        
        # Canvas coordinates
        max_y_cm = self.main_app.settings.get("simulation", {}).get("max_display_y", 80)
        canvas_x1 = self.main_app.offset_x + paper_x * self.main_app.scale_x
        canvas_y1 = self.main_app.offset_y + (max_y_cm - (paper_y + actual_paper_height)) * self.main_app.scale_y
        canvas_x2 = self.main_app.offset_x + (paper_x + actual_paper_width) * self.main_app.scale_x
        canvas_y2 = self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y
        
        # Draw paper rectangle
        self.main_app.canvas.create_rectangle(
            canvas_x1, canvas_y1, canvas_x2, canvas_y2,
            outline='darkgreen', fill='lightgreen', width=3, stipple='gray12', tags="work_lines"
        )
        
        # Paper info label
        info_text = f"Program {p.program_number}: {p.program_name}\\nActual Size: {actual_paper_width}×{actual_paper_height}cm"
        self.main_app.canvas.create_text(
            (canvas_x1 + canvas_x2) / 2, canvas_y1 - 20,
            text=info_text, font=('Arial', 10, 'bold'), fill='darkgreen', tags="work_lines"
        )
        
        # Draw work lines and cuts
        self.draw_work_lines(p, paper_x, paper_y, max_y_cm)
        
        # Draw enhanced legend
        self.draw_enhanced_legend()
    
    def draw_work_lines(self, program, paper_x, paper_y, max_y_cm):
        """Draw visualization of lines that will be marked and cut with REPEAT SUPPORT"""
        
        # Initialize operation states when program changes
        self.initialize_operation_states(program)
        
        # Clear previous work line objects
        self.main_app.work_line_objects = {}
        
        # Calculate ACTUAL paper dimensions with repeats
        actual_paper_width = program.width * program.repeat_rows
        actual_paper_height = program.high * program.repeat_lines
        
        print(f"📏 DRAWING WORK LINES: ACTUAL size {actual_paper_width}×{actual_paper_height}cm")
        
        # CORRECTED REPEAT LOGIC: Process each repeated section individually
        # Each section has its own margins and line spacing
        print(f"📄 REPEAT PROCESSING: {program.repeat_lines} sections of {program.high}cm each")
        print(f"   Each section: {program.number_of_lines} lines with {program.top_padding}cm top, {program.bottom_padding}cm bottom margins")
        
        # Draw all lines across all repeated sections
        overall_line_num = 0
        for section_num in range(program.repeat_lines):
            section_start_y = paper_y + (program.repeat_lines - section_num) * program.high  # Top of this section
            section_end_y = paper_y + (program.repeat_lines - section_num - 1) * program.high  # Bottom of this section
            
            # Calculate line positions within THIS section
            first_line_y_section = section_start_y - program.top_padding
            last_line_y_section = section_end_y + program.bottom_padding
            available_space_section = first_line_y_section - last_line_y_section
            
            if program.number_of_lines > 1:
                line_spacing_section = available_space_section / (program.number_of_lines - 1)
            else:
                line_spacing_section = 0
            
            # Draw lines for this section
            for line_in_section in range(program.number_of_lines):
                overall_line_num += 1
                line_y_real = first_line_y_section - (line_in_section * line_spacing_section)
                line_y_canvas = self.main_app.offset_y + (max_y_cm - line_y_real) * self.main_app.scale_y
                line_x1_canvas = self.main_app.offset_x + paper_x * self.main_app.scale_x
                line_x2_canvas = self.main_app.offset_x + (paper_x + actual_paper_width) * self.main_app.scale_x
                
                # Dynamic color based on state
                state = self.main_app.operation_states['lines'].get(overall_line_num, 'pending')
                if state == 'completed':
                    line_color = '#00AA00'  # Bright green for completed
                    dash_pattern = (10, 2)  # Solid-like for completed
                    width = 3
                elif state == 'in_progress':
                    line_color = '#FF8800'  # Orange for in progress
                    dash_pattern = (8, 4)
                    width = 3
                else:  # pending
                    line_color = '#FF4444'  # Red for pending
                    dash_pattern = (4, 4)
                    width = 2
                
                # Draw line
                line_id = self.main_app.canvas.create_line(
                    line_x1_canvas, line_y_canvas, line_x2_canvas, line_y_canvas,
                    fill=line_color, width=width, dash=dash_pattern, tags="work_lines"
                )
                
                # Store line object for dynamic updates
                self.main_app.work_line_objects[f'line_{overall_line_num}'] = {
                    'id': line_id,
                    'type': 'line',
                    'line_number': overall_line_num,
                    'section': section_num + 1,
                    'color_pending': '#FF4444',
                    'color_progress': '#FF8800',
                    'color_completed': '#00AA00'
                }
                
                # Add line number label with matching color
                label_id = self.main_app.canvas.create_text(
                    line_x2_canvas + 15, line_y_canvas,
                    text=f"L{overall_line_num}", font=('Arial', 9, 'bold'), fill=line_color, tags="work_lines"
                )
                
                self.main_app.work_line_objects[f'line_{overall_line_num}']['label_id'] = label_id
        
        # Draw row markings (pages)
        for page_num in range(program.number_of_pages):
            # Calculate page positions (LEFT-TO-RIGHT for drawing, but RTL numbering)
            page_left_edge = paper_x + program.left_margin + (page_num * (program.page_width + program.buffer_between_pages))
            page_right_edge = page_left_edge + program.page_width
            
            # Convert to canvas coordinates
            page_left_canvas = self.main_app.offset_x + page_left_edge * self.main_app.scale_x
            page_right_canvas = self.main_app.offset_x + page_right_edge * self.main_app.scale_x
            page_top_canvas = self.main_app.offset_y + (max_y_cm - (paper_y + actual_paper_height)) * self.main_app.scale_y
            page_bottom_canvas = self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y
            
            # Convert LEFT-TO-RIGHT drawing to RIGHT-TO-LEFT numbering
            # Drawing: page_num 0,1,2,3 (left to right)
            # RTL: page_num 3,2,1,0 (right to left) → R1,R2,R3... (right to left)
            rtl_drawing_row_num = (page_num * 2) + 1  # Drawing row number (left to right)
            individual_row_num = program.number_of_pages * 2 - rtl_drawing_row_num + 1  # Convert to RTL numbering
            row_state = self.main_app.operation_states['rows'].get(f'row_{rtl_drawing_row_num}', 'pending')
            
            if row_state == 'completed':
                start_color = '#0088AA'  # Cyan for completed
                start_dash = (8, 2)
                start_width = 3
            elif row_state == 'in_progress':
                start_color = '#8800FF'  # Purple for in progress
                start_dash = (6, 3)
                start_width = 3
            else:  # pending
                start_color = '#4444FF'  # Blue for pending
                start_dash = (4, 4)
                start_width = 2
            
            # Draw RIGHT edge of page (start of RTL page marking)
            start_id = self.main_app.canvas.create_line(
                page_right_canvas, page_top_canvas, page_right_canvas, page_bottom_canvas,
                fill=start_color, width=start_width, dash=start_dash, tags="work_lines"
            )
            
            # Store right edge object for updates
            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num}'] = {
                'id': start_id,
                'type': 'row',
                'page_number': page_num + 1,
                'edge': 'right',
                'color_pending': '#4444FF',
                'color_progress': '#8800FF',
                'color_completed': '#0088AA'
            }
            
            # Add RIGHT edge label
            start_label_id = self.main_app.canvas.create_text(
                page_right_canvas + 10, page_top_canvas - 10,
                text=f"R{individual_row_num}", font=('Arial', 8, 'bold'), fill=start_color, tags="work_lines"
            )
            
            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num}']['label_id'] = start_label_id
            
            # Individual row state tracking - left edge is independent
            # Convert LEFT-TO-RIGHT drawing to RIGHT-TO-LEFT numbering for left edges
            rtl_drawing_row_num_left = (page_num * 2) + 2  # Drawing row number for left edges
            individual_row_num_left = program.number_of_pages * 2 - rtl_drawing_row_num_left + 1  # Convert to RTL numbering
            end_row_state = self.main_app.operation_states['rows'].get(f'row_{rtl_drawing_row_num_left}', 'pending')
            
            if end_row_state == 'completed':
                end_color = '#0088AA'  # Cyan for completed
                end_dash = (8, 2)
                end_width = 3
            elif end_row_state == 'in_progress':
                end_color = '#8800FF'  # Purple for in progress
                end_dash = (6, 3)
                end_width = 3
            else:  # pending
                end_color = '#4444FF'  # Blue for pending
                end_dash = (4, 4)
                end_width = 2
            
            # Draw LEFT edge of page (end of RTL page marking)  
            end_id = self.main_app.canvas.create_line(
                page_left_canvas, page_top_canvas, page_left_canvas, page_bottom_canvas,
                fill=end_color, width=end_width, dash=end_dash, tags="work_lines"
            )
            
            # Store left edge object for updates
            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num_left}'] = {
                'id': end_id,
                'type': 'row',
                'page_number': page_num + 1,
                'edge': 'left',
                'color_pending': '#4444FF',
                'color_progress': '#8800FF',
                'color_completed': '#0088AA'
            }
            
            # Add LEFT edge label
            end_label_id = self.main_app.canvas.create_text(
                page_left_canvas - 10, page_top_canvas - 10,
                text=f"R{individual_row_num_left}", font=('Arial', 8, 'bold'), fill=end_color, tags="work_lines"
            )
            
            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num_left}']['label_id'] = end_label_id
        
        # Draw cutting lines
        cuts = ['top', 'bottom', 'left', 'right']
        cut_positions = [
            (paper_y + actual_paper_height, 'horizontal'),  # Top edge
            (paper_y, 'horizontal'),  # Bottom edge
            (paper_x, 'vertical'),    # Left edge
            (paper_x + actual_paper_width, 'vertical')  # Right edge
        ]
        cut_labels = ['TOP CUT', 'BOTTOM CUT', 'LEFT CUT', 'RIGHT CUT']
        
        for i, (cut_pos, orientation) in enumerate(cut_positions):
            cut_name = cuts[i]
            state = self.main_app.operation_states['cuts'].get(cut_name, 'pending')
            
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
                # Horizontal cutting line
                cut_y_canvas = self.main_app.offset_y + (max_y_cm - cut_pos) * self.main_app.scale_y
                cut_id = self.main_app.canvas.create_line(
                    self.main_app.offset_x + paper_x * self.main_app.scale_x,
                    cut_y_canvas,
                    self.main_app.offset_x + (paper_x + actual_paper_width) * self.main_app.scale_x,
                    cut_y_canvas,
                    fill=cut_color, width=width, tags="work_lines"
                )
                
                # Add cut label
                label_id = self.main_app.canvas.create_text(
                    self.main_app.offset_x + (paper_x + actual_paper_width + 5) * self.main_app.scale_x,
                    cut_y_canvas,
                    text=cut_labels[i], font=('Arial', 8, 'bold'), fill=cut_color, tags="work_lines"
                )
                
                # Store cut object for dynamic updates
                self.main_app.work_line_objects[f'cut_{cut_name}'] = {
                    'id': cut_id,
                    'label_id': label_id,
                    'type': 'cut',
                    'orientation': orientation,
                    'color_pending': '#8800FF',
                    'color_progress': '#FF0088',
                    'color_completed': '#AA00AA'
                }
            
            else:  # vertical
                # Vertical cutting line
                cut_x_canvas = self.main_app.offset_x + cut_pos * self.main_app.scale_x
                cut_id = self.main_app.canvas.create_line(
                    cut_x_canvas,
                    self.main_app.offset_y + (max_y_cm - (paper_y + actual_paper_height)) * self.main_app.scale_y,
                    cut_x_canvas,
                    self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y,
                    fill=cut_color, width=width, tags="work_lines"
                )
                
                # Store cut object for dynamic updates
                self.main_app.work_line_objects[f'cut_{cut_name}'] = {
                    'id': cut_id,
                    'type': 'cut',
                    'orientation': orientation,
                    'color_pending': '#8800FF',
                    'color_progress': '#FF0088',
                    'color_completed': '#AA00AA'
                }
    
    def initialize_operation_states(self, program):
        """Initialize operation states for the current program WITH REPEAT SUPPORT"""
        # Calculate TOTAL elements across all repeated sections
        total_lines = program.number_of_lines * program.repeat_lines
        total_pages = program.number_of_pages * program.repeat_rows
        total_rows = total_pages * 2  # 2 rows per page (right edge + left edge)
        
        print(f"🔄 INITIALIZING STATES: {total_lines} lines, {total_pages} pages, {total_rows} rows (with repeats)")
        
        self.main_app.operation_states = {
            'lines': {},      # Track line marking states: {1: 'pending', 2: 'completed', ...}
            'cuts': {},       # Track cutting states: {'top'/'bottom'/'left'/'right': 'pending'/'completed'}
            'pages': {},      # Track page states: {0: 'pending', 1: 'completed', ...}
            'rows': {}        # Track individual row states: {'row_1': 'pending', 'row_2': 'completed', ...}
        }
        
        # Initialize ALL lines across repeated sections as pending
        for line_num in range(1, total_lines + 1):
            self.main_app.operation_states['lines'][line_num] = 'pending'
        
        # Initialize all cuts as pending
        for cut_name in ['top', 'bottom', 'left', 'right']:
            self.main_app.operation_states['cuts'][cut_name] = 'pending'
            
        # Initialize cuts between repeated sections (if more than 1 line repeat)
        if program.repeat_lines > 1:
            for section_num in range(1, program.repeat_lines):
                cut_key = f'between_{section_num}_{section_num + 1}'
                self.main_app.operation_states['cuts'][cut_key] = 'pending'
                print(f"📐 Initialized cut between sections {section_num} and {section_num + 1}: {cut_key}")
        
        # Initialize ALL pages across repeated sections as pending (both start and end for each page)
        for page_num in range(1, total_pages + 1):
            self.main_app.operation_states['pages'][f'{page_num}_start'] = 'pending'
            self.main_app.operation_states['pages'][f'{page_num}_end'] = 'pending'
        
        # Initialize ALL individual rows across repeated sections as pending
        for row_num in range(1, total_rows + 1):
            self.main_app.operation_states['rows'][f'row_{row_num}'] = 'pending'
    
    def update_operation_state(self, operation_type, operation_id, new_state):
        """Update the state of a specific operation and refresh visualization"""
        print(f"🎨 COLOR UPDATE: {operation_type} {operation_id} → {new_state}")
        if operation_type in self.main_app.operation_states:
            self.main_app.operation_states[operation_type][operation_id] = new_state
            print(f"✅ State updated in operation_states: {operation_type}[{operation_id}] = {new_state}")
            # Refresh only the work lines without redrawing everything
            if self.main_app.current_program:
                print("🖌️ Calling refresh_work_lines_colors()...")
                self.refresh_work_lines_colors()
            else:
                print("❌ No current_program - skipping color refresh")
    
    def track_operation_from_step(self, step_description):
        """Track operations from step descriptions for real-time updates"""
        print(f"🔍 TRACKING STEP: {step_description}")
        if not self.main_app.current_program:
            print("❌ No current program - cannot track operation")
            return
            
        desc = step_description.lower()
        print(f"📝 Processing description: {desc}")
        
        # Track line marking operations - pattern: "Mark line X/Y: Open/Close line marker"
        if 'lines' in desc and 'line marker' in desc:
            line_match = re.search(r'mark line (\d+)/(\d+)', desc)
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
            # Track cuts between sections - NEW PATTERN: "Cut between sections X and Y: Open/Close line cutter"
            elif 'cut between sections' in desc:
                section_match = re.search(r'cut between sections (\d+) and (\d+)', desc)
                if section_match:
                    section1 = int(section_match.group(1))
                    section2 = int(section_match.group(2))
                    cut_key = f'between_{section1}_{section2}'
                    
                    if 'open line cutter' in desc:
                        self.update_operation_state('cuts', cut_key, 'in_progress')
                        print(f"🟠 Cut between sections {section1}-{section2} started (IN PROGRESS)")
                    elif 'close line cutter' in desc:
                        self.update_operation_state('cuts', cut_key, 'completed')
                        print(f"🟣 Cut between sections {section1}-{section2} completed (COMPLETED)")
        
        # Track row marking operations - INDIVIDUAL ROW TRACKING (not page-based)
        elif 'row marker' in desc and 'rtl page' in desc:
            page_match = re.search(r'rtl page (\d+)/(\d+)', desc)
            if page_match:
                rtl_page_num = int(page_match.group(1))  # RTL page numbering: 1=rightmost, ascending
                total_pages = int(page_match.group(2))
                
                # Calculate individual row number for RIGHT-TO-LEFT operation
                # RTL Page 1 (rightmost) RIGHT edge = Row 1 (rightmost drawn row)
                # RTL Page 1 (rightmost) LEFT edge = Row 2
                # RTL Page 2 RIGHT edge = Row 3, etc.
                # But we need to map to the drawing system which numbers LEFT-TO-RIGHT
                
                # Calculate RTL row number
                if '(right edge)' in desc:
                    rtl_row_num = (rtl_page_num - 1) * 2 + 1  # 1, 3, 5, 7...
                    edge_type = 'RIGHT'
                elif '(left edge)' in desc:
                    rtl_row_num = (rtl_page_num - 1) * 2 + 2  # 2, 4, 6, 8...
                    edge_type = 'LEFT'
                
                # Convert RTL row number to drawing system row number (flip the mapping)
                # RTL Row 1 (rightmost) → Drawing Row 8 (rightmost in 8-row system)
                # RTL Row 2 → Drawing Row 7, RTL Row 3 → Drawing Row 6, etc.
                total_rows = total_pages * 2
                individual_row_num = total_rows - rtl_row_num + 1
                
                # Use individual row tracking instead of page-based
                row_key = f'row_{individual_row_num}'
                
                if 'open row marker' in desc:
                    self.update_operation_state('rows', row_key, 'in_progress')
                    print(f"🟠 RTL Page {rtl_page_num} {edge_type} edge → RTL Row {rtl_row_num} → Drawing Row {individual_row_num} marking started (IN PROGRESS)")
                elif 'close row marker' in desc:
                    self.update_operation_state('rows', row_key, 'completed')
                    print(f"🔵 RTL Page {rtl_page_num} {edge_type} edge → RTL Row {rtl_row_num} → Drawing Row {individual_row_num} marking completed (COMPLETED)")
        
        # Track row cutting operations - NEW PATTERN: "Cut RIGHT/LEFT paper edge: Open/Close row cutter"
        elif 'row cutter' in desc:
            if 'cut right paper edge' in desc:
                if 'open row cutter' in desc:
                    self.update_operation_state('cuts', 'right', 'in_progress')
                    print("🟠 RIGHT paper edge cut started (IN PROGRESS)")
                elif 'close row cutter' in desc:
                    self.update_operation_state('cuts', 'right', 'completed')
                    print("🟣 RIGHT paper edge cut completed (COMPLETED)")
            elif 'cut left paper edge' in desc:
                if 'open row cutter' in desc:
                    self.update_operation_state('cuts', 'left', 'in_progress')
                    print("🟠 LEFT paper edge cut started (IN PROGRESS)")
                elif 'close row cutter' in desc:
                    self.update_operation_state('cuts', 'left', 'completed')
                    print("🟣 LEFT paper edge cut completed (COMPLETED)")
    
    def refresh_work_lines_colors(self):
        """Refresh work line colors based on current operation states without redrawing"""
        print("🖌️ refresh_work_lines_colors() called")
        if not hasattr(self.main_app, 'work_line_objects'):
            print("❌ No work_line_objects attribute")
            return
        if not self.main_app.current_program:
            print("❌ No current_program")
            return
            
        print(f"📊 work_line_objects keys: {list(self.main_app.work_line_objects.keys())}")
        print(f"📊 operation_states: {self.main_app.operation_states}")
            
        # Update line colors - CORRECTED: Use TOTAL lines across ALL repeated sections
        total_lines = self.main_app.current_program.number_of_lines * self.main_app.current_program.repeat_lines
        print(f"🔢 Updating colors for {total_lines} total lines")
        
        for line_num in range(1, total_lines + 1):
            obj_key = f'line_{line_num}'
            print(f"🔍 Checking line {line_num} (key: {obj_key})")
            
            if obj_key in self.main_app.work_line_objects:
                obj = self.main_app.work_line_objects[obj_key]
                state = self.main_app.operation_states['lines'].get(line_num, 'pending')
                print(f"  📍 Line {line_num} state: {state}")
                
                if state == 'completed':
                    color = obj['color_completed']
                    width = 3
                elif state == 'in_progress':
                    color = obj['color_progress']
                    width = 3
                else:
                    color = obj['color_pending']
                    width = 2
                
                print(f"  🎨 Setting line {line_num} color to {color}")
                
                # Update line color
                self.main_app.canvas.itemconfig(obj['id'], fill=color, width=width)
                if 'label_id' in obj:
                    self.main_app.canvas.itemconfig(obj['label_id'], fill=color)
            else:
                print(f"  ❌ Line {line_num} object not found in work_line_objects")
        
        print(f"🔄 Color refresh completed. Updated {len([k for k in self.main_app.work_line_objects.keys() if k.startswith('line_')])} line objects")
        
        # Update cut colors
        for cut_name in ['top', 'bottom', 'left', 'right']:
            obj_key = f'cut_{cut_name}'
            if obj_key in self.main_app.work_line_objects:
                obj = self.main_app.work_line_objects[obj_key]
                state = self.main_app.operation_states['cuts'].get(cut_name, 'pending')
                
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
                self.main_app.canvas.itemconfig(obj['id'], fill=color, width=width)
                if 'label_id' in obj:
                    self.main_app.canvas.itemconfig(obj['label_id'], fill=color)
        
        # Update individual row colors (each row edge is completely independent)
        if hasattr(self.main_app, 'operation_states') and 'rows' in self.main_app.operation_states:
            total_rows = self.main_app.current_program.number_of_pages * 2 * self.main_app.current_program.repeat_rows
            for row_num in range(1, total_rows + 1):
                row_obj_key = f'row_{row_num}'
                row_state = self.main_app.operation_states['rows'].get(f'row_{row_num}', 'pending')
                
                if row_obj_key in self.main_app.work_line_objects:
                    obj = self.main_app.work_line_objects[row_obj_key]
                    
                    if row_state == 'completed':
                        color = obj['color_completed']
                        dash = (8, 2)
                        width = 3
                    elif row_state == 'in_progress':
                        color = obj['color_progress']
                        dash = (6, 3)
                        width = 3
                    else:
                        color = obj['color_pending']
                        dash = (4, 4)
                        width = 2
                    
                    # Update individual row color and style
                    self.main_app.canvas.itemconfig(obj['id'], fill=color, width=width, dash=dash)
                    if 'label_id' in obj:
                        self.main_app.canvas.itemconfig(obj['label_id'], fill=color)
    
    def draw_enhanced_legend(self):
        """Draw an enhanced color-coded legend showing operation states"""
        # Position legend at bottom of canvas for maximum simulation space
        legend_x = 20  # Start from left side
        legend_y = self.main_app.canvas_height - 180  # Near bottom
        box_width = self.main_app.canvas_width - 40  # Full width minus margins
        box_height = 120  # Reduced height for compactness
        
        # Legend background
        self.main_app.canvas.create_rectangle(
            legend_x, legend_y, legend_x + box_width, legend_y + box_height,
            fill='white', outline='darkblue', width=2, tags="legend"
        )
        
        # Title
        self.main_app.canvas.create_text(
            legend_x + box_width/2, legend_y + 15,
            text="📊 OPERATION STATUS LEGEND", 
            font=('Arial', 11, 'bold'), fill='darkblue', tags="legend"
        )
        
        # Color indicators and descriptions
        y_offset = 35
        col_width = box_width / 3
        
        # Lines column
        self.draw_operation_column(legend_x + 10, legend_y + y_offset, 
                                   "📏 LINES", [
                                       ('#FF4444', 'Pending'),
                                       ('#FF8800', 'Marking'),  
                                       ('#00AA00', 'Complete')
                                   ])
        
        # Cuts column  
        self.draw_operation_column(legend_x + col_width + 10, legend_y + y_offset,
                                   "✂️ CUTS", [
                                       ('#8800FF', 'Pending'),
                                       ('#FF0088', 'Cutting'),
                                       ('#AA00AA', 'Complete')
                                   ])
        
        # Rows column
        self.draw_operation_column(legend_x + col_width*2 + 10, legend_y + y_offset,
                                   "📄 ROWS", [
                                       ('#4444FF', 'Pending'),
                                       ('#8800FF', 'Marking'),
                                       ('#0088AA', 'Complete')
                                   ])
        
        # Progress summary
        self.draw_progress_summary(legend_x + 10, legend_y + box_height - 25, box_width - 20)
    
    def draw_operation_column(self, x, y, title, states):
        """Draw a column of operation states with colors"""
        # Column title
        self.main_app.canvas.create_text(x, y, text=title, font=('Arial', 9, 'bold'), 
                                        fill='darkblue', tags="legend", anchor="w")
        
        # State indicators
        for i, (color, description) in enumerate(states):
            state_y = y + 15 + (i * 15)
            
            # Show colored indicator or description
            if description.startswith('#'):  # It's a color code
                # Color indicator (small rectangle)
                self.main_app.canvas.create_rectangle(x, state_y, x + 12, state_y + 8,
                                                     fill=color, outline='black', tags="legend")
                self.main_app.canvas.create_text(x + 20, state_y + 4, text=description,
                                               font=('Arial', 8), fill='black', tags="legend", anchor="w")
            else:
                # Color indicator + text description
                self.main_app.canvas.create_rectangle(x, state_y, x + 12, state_y + 8,
                                                     fill=color, outline='black', tags="legend")
                self.main_app.canvas.create_text(x + 20, state_y + 4, text=description,
                                               font=('Arial', 8), fill='black', tags="legend", anchor="w")
    
    def draw_progress_summary(self, x, y, width):
        """Draw overall progress summary"""
        if not hasattr(self.main_app, 'operation_states'):
            return
        
        total_operations = 0
        completed_operations = 0
        
        # Count line states
        for state in self.main_app.operation_states['lines'].values():
            total_operations += 1
            if state == 'completed':
                completed_operations += 1
        
        # Count cut states
        for state in self.main_app.operation_states['cuts'].values():
            total_operations += 1
            if state == 'completed':
                completed_operations += 1
        
        # Calculate progress percentage
        if total_operations > 0:
            progress_percent = (completed_operations / total_operations) * 100
        else:
            progress_percent = 0
        
        summary_text = f"📊 Overall Progress: {completed_operations}/{total_operations} ({progress_percent:.0f}%)"
        self.main_app.canvas.create_text(x + 10, y, text=summary_text, 
                               font=('Arial', 9, 'bold'), fill='darkgreen', tags="legend")
    
    def test_color_changes(self):
        """TEST METHOD: Force color changes to debug the issue"""
        print("🧪 TESTING COLOR CHANGES...")
        if not hasattr(self.main_app, 'work_line_objects') or not self.main_app.current_program:
            print("❌ Cannot test - missing work_line_objects or current_program")
            return
            
        # Test: Change first line to in_progress
        if 'line_1' in self.main_app.work_line_objects:
            print("🧪 Testing: Setting line 1 to in_progress")
            self.update_operation_state('lines', 1, 'in_progress')
            
        # Test: Change first cut to in_progress  
        if 'cut_top' in self.main_app.work_line_objects:
            print("🧪 Testing: Setting top cut to in_progress")
            self.update_operation_state('cuts', 'top', 'in_progress')
    
    def add_debug_keybindings(self):
        """Add keyboard shortcuts for testing color changes"""
        if hasattr(self.main_app, 'root'):
            # Bind 't' key to test color changes
            self.main_app.root.bind('<Key-t>', lambda e: self.test_color_changes())
            print("🔧 DEBUG: Press 't' key to test color changes")
import tkinter as tk
import re
import json
from core.logger import get_logger
from core.translations import t

# Load settings
def load_settings():
    try:
        with open('config/settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

settings = load_settings()
visualization_settings = settings.get("visualization", {})
ui_fonts = settings.get("ui_fonts", {})


class CanvasOperations:
    """Handles canvas operations for paper area and work lines visualization"""

    def __init__(self, main_app, canvas_manager):
        self.main_app = main_app
        self.canvas_manager = canvas_manager
        self.logger = get_logger()
        # Access hardware through canvas_manager
        self.hardware = canvas_manager.hardware
        self.canvas_objects = main_app.canvas_objects
    
    def update_canvas_paper_area(self):
        """Update canvas to show current program's paper area and work lines with original logic"""
        if not self.main_app.current_program:
            return

        # Check if canvas is ready (center_panel has initialized it)
        if hasattr(self.main_app, 'center_panel') and hasattr(self.main_app.center_panel, '_canvas_initialized'):
            if not self.main_app.center_panel._canvas_initialized:
                self.logger.debug(" update_canvas_paper_area() called before canvas initialization - will retry after init", category="gui")
                # Schedule retry after canvas is initialized
                self.main_app.root.after(100, self.update_canvas_paper_area)
                return

        # Add debug keybindings when we have a program loaded
        self.add_debug_keybindings()
        
        # Clear all tagged objects for clean redraw
        self.main_app.canvas.delete("work_lines")
        
        p = self.main_app.current_program
        
        # Paper coordinates from settings (bottom-left corner at paper_start_x)
        hardware_limits = self.main_app.settings.get("hardware_limits", {})
        PAPER_OFFSET_X = hardware_limits.get("paper_start_x", 15.0)
        PAPER_OFFSET_Y = hardware_limits.get("paper_start_y", 15.0)
        paper_bottom_left_x = PAPER_OFFSET_X
        paper_bottom_left_y = PAPER_OFFSET_Y
        
        # ACTUAL paper size (with repeats) - showing original behavior
        paper_width = p.width * p.repeat_rows
        paper_height = p.high * p.repeat_lines
        
        self.logger.debug(f"🖼 CANVAS UPDATE: Showing ACTUAL paper size {paper_width}×{paper_height}cm (repeats: {p.repeat_rows}×{p.repeat_lines})", category="gui")
        
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
                outline='blue', width=visualization_settings.get("line_width_marks", 3), fill='lightblue', stipple='gray50'
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
            font=tuple(ui_fonts.get("normal", ["Arial", 9, "bold"])), fill='darkblue', tags="work_lines", justify='center'
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
        # mark_colors = operation_colors.get("lines", {
        #     "pending": "#FF6600",
        #     "in_progress": "#FF8800",
        #     "completed": "#00AA00"
        # })
        # rows_colors = operation_colors.get("rows", {
        #     "pending": "#8800FF",
        #     "in_progress": "#FF0088",
        #     "completed": "#AA00AA"
        # })
        mark_colors = operation_colors.get("mark", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })
        cuts_colors = operation_colors.get("cuts", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })

        self.logger.debug(f" DRAWING WORK LINES: ACTUAL size {actual_paper_width}×{actual_paper_height}cm", category="gui")
        self.logger.debug(f"🎨 Mark colors: {mark_colors}", category="gui")
        self.logger.debug(f"🎨 Cuts colors: {cuts_colors}", category="gui")
        
        # CORRECTED REPEAT VISUALIZATION: Process each repeated section individually
        # Each section has its own margins - match step generator logic exactly
        self.logger.debug(f"🖼 CANVAS REPEAT: {program.repeat_lines} sections of {program.high}cm each", category="gui")
        
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
            
            self.logger.debug(f" Canvas Section {section_num + 1}: lines from {first_line_y_section:.1f} to {last_line_y_section:.1f}cm", category="gui")
            
            # Draw all lines in this section
            for line_in_section in range(program.number_of_lines):
                overall_line_num += 1
                line_y_real = first_line_y_section - (line_in_section * line_spacing_section)
                
                # Convert to canvas coordinates - lines span ENTIRE repeated paper width
                line_y_canvas = self.main_app.offset_y + (max_y_cm - line_y_real) * self.main_app.scale_y
                line_x1_canvas = self.main_app.offset_x + paper_x * self.main_app.scale_x
                line_x2_canvas = self.main_app.offset_x + (paper_x + actual_paper_width) * self.main_app.scale_x
                
                # DASHED lines - color changes based on state (using settings)
                state = self.main_app.operation_states['lines'].get(overall_line_num, 'pending')
                if state == 'completed':
                    line_color = mark_colors['completed']
                    dash_pattern = (10, 2)  # Almost solid
                elif state == 'in_progress':
                    line_color = mark_colors['in_progress']
                    dash_pattern = (8, 4)  # Medium dash
                else:  # pending
                    line_color = mark_colors['pending']
                    dash_pattern = (5, 5)  # Dashed

                # Draw line - DASHED LINE
                line_id = self.main_app.canvas.create_line(
                    line_x1_canvas, line_y_canvas, line_x2_canvas, line_y_canvas,
                    fill=line_color, width=visualization_settings.get("line_width_marks", 3), dash=dash_pattern, tags="work_lines"
                )
                
                # Store line object for dynamic updates (using settings colors)
                self.main_app.work_line_objects[f'line_{overall_line_num}'] = {
                    'id': line_id,
                    'type': 'line',
                    'color_pending': mark_colors['pending'],
                    'color_in_progress': mark_colors['in_progress'],
                    'color_completed': mark_colors['completed']
                }
                
                # Add line number label with matching color
                label_id = self.main_app.canvas.create_text(
                    line_x1_canvas - 25, line_y_canvas,
                    text=f"L{overall_line_num}", font=tuple(ui_fonts.get("normal", ["Arial", 9, "bold"])), fill=line_color, tags="work_lines"
                )
                self.main_app.work_line_objects[f'line_{overall_line_num}']['label_id'] = label_id
        
        # Draw vertical lines (Row Pattern) WITH REPEAT SUPPORT - Each section is a duplicate with same layout
        # Calculate TOTAL pages across all repeated sections
        total_pages = program.number_of_pages * program.repeat_rows

        self.logger.debug(f"📄 DRAWING PAGES: {total_pages} total pages ({program.number_of_pages} per section × {program.repeat_rows} sections)", category="gui")

        # Draw each page's start and end marks (across entire repeated area)
        page_mark_id = 1  # For tracking state

        for page_num in range(total_pages):
            # Calculate which section and page within section
            section_index = page_num // program.number_of_pages
            page_in_section = page_num % program.number_of_pages

            # Each section starts at paper_x + (section_index * section_width)
            section_start_x = paper_x + (section_index * program.width)

            # Within each section, pages follow the same layout as a single section
            # First page starts at section_start + left_margin
            page_start_x = section_start_x + program.left_margin + page_in_section * (program.page_width + program.buffer_between_pages)

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
            individual_row_num = total_pages * 2 - rtl_drawing_row_num + 1  # Convert to RTL numbering (use total_pages for repeats)
            row_state = self.main_app.operation_states['rows'].get(f'row_{rtl_drawing_row_num}', 'pending')

            # Rows with color AND dash pattern changes based on state
            if row_state == 'completed':
                start_color = mark_colors['completed']
                start_dash = (10, 2)  # Almost solid
            elif row_state == 'in_progress':
                start_color = mark_colors['in_progress']
                start_dash = (8, 4)  # Medium dash
            else:  # pending
                start_color = mark_colors['pending']
                start_dash = (5, 5)  # Dashed

            # Create individual row line (right edge) with dash pattern
            row_start_id = self.main_app.canvas.create_line(
                page_start_canvas, page_y1_canvas,
                page_start_canvas, page_y2_canvas,
                fill=start_color, width=visualization_settings.get("line_width_marks", 3), dash=start_dash, tags="work_lines"
            )
            
            # Row label (R1, R3, R5, etc.)
            self.main_app.canvas.create_text(
                page_start_canvas, page_y2_canvas + 15,
                text=f"R{individual_row_num}", font=tuple(ui_fonts.get("label", ["Arial", 8, "bold"])), 
                fill=start_color, tags="work_lines"
            )
            
            # Draw page END mark
            page_end_canvas = self.main_app.offset_x + page_end_x * self.main_app.scale_x
            
            # Individual row state tracking - left edge is independent
            # Convert LEFT-TO-RIGHT drawing to RIGHT-TO-LEFT numbering for left edges
            rtl_drawing_row_num_left = (page_num * 2) + 2  # Drawing row number for left edges
            individual_row_num_left = total_pages * 2 - rtl_drawing_row_num_left + 1  # Convert to RTL numbering (use total_pages for repeats)
            end_row_state = self.main_app.operation_states['rows'].get(f'row_{rtl_drawing_row_num_left}', 'pending')

            # Rows with color AND dash pattern changes based on state
            if end_row_state == 'completed':
                end_color = mark_colors['completed']
                end_dash = (10, 2)  # Almost solid
            elif end_row_state == 'in_progress':
                end_color = mark_colors['in_progress']
                end_dash = (8, 4)  # Medium dash
            else:  # pending
                end_color = mark_colors['pending']
                end_dash = (5, 5)  # Dashed

            # Create individual row line (left edge) with dash pattern
            row_end_id = self.main_app.canvas.create_line(
                page_end_canvas, page_y1_canvas,
                page_end_canvas, page_y2_canvas,
                fill=end_color, width=visualization_settings.get("line_width_marks", 3), dash=end_dash, tags="work_lines"
            )
            
            # Row label (R2, R4, R6, etc.)
            self.main_app.canvas.create_text(
                page_end_canvas, page_y2_canvas + 15,
                text=f"R{individual_row_num_left}", font=tuple(ui_fonts.get("label", ["Arial", 8, "bold"])), 
                fill=end_color, tags="work_lines"
            )
            
            # Store individual row objects for dynamic updates (using settings colors)
            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num}'] = {
                'id': row_start_id,
                'type': 'row',
                'color_pending': mark_colors['pending'],
                'color_in_progress': mark_colors['in_progress'],
                'color_completed': mark_colors['completed']
            }

            self.main_app.work_line_objects[f'row_{rtl_drawing_row_num_left}'] = {
                'id': row_end_id,
                'type': 'row',
                'color_pending': mark_colors['pending'],
                'color_in_progress': mark_colors['in_progress'],
                'color_completed': mark_colors['completed']
            }
        
        # Draw cut edges - horizontal cuts (top and bottom) using ACTUAL dimensions with repeats
        cuts = ['top', 'bottom', 'left', 'right']
        cut_positions = [
            (paper_y + actual_paper_height, 'horizontal'),  # top edge of ACTUAL paper (with repeats)
            (paper_y, 'horizontal'),                        # bottom edge of paper
            (paper_x, 'vertical'),                          # left edge of paper
            (paper_x + actual_paper_width, 'vertical')      # right edge of ACTUAL paper (with repeats)
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
                    fill=cut_color, width=visualization_settings.get("line_width_cuts", 4), tags="work_lines"
                )

                # Add cut label
                self.main_app.canvas.create_text(
                    cut_x2_canvas + 10, cut_y_canvas,
                    text=cut_labels[i], font=tuple(ui_fonts.get("label", ["Arial", 8, "bold"])), fill=cut_color, tags="work_lines"
                )

            else:  # vertical
                # Vertical cuts span the paper height - SOLID LINE
                cut_x_canvas = self.main_app.offset_x + cut_pos * self.main_app.scale_x
                cut_y1_canvas = self.main_app.offset_y + (max_y_cm - (paper_y + actual_paper_height)) * self.main_app.scale_y
                cut_y2_canvas = self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y

                cut_id = self.main_app.canvas.create_line(
                    cut_x_canvas, cut_y1_canvas, cut_x_canvas, cut_y2_canvas,
                    fill=cut_color, width=visualization_settings.get("line_width_cuts", 4), tags="work_lines"
                )
                
                # Add cut label
                self.main_app.canvas.create_text(
                    cut_x_canvas, cut_y1_canvas - 10,
                    text=cut_labels[i], font=tuple(ui_fonts.get("label", ["Arial", 8, "bold"])), fill=cut_color, tags="work_lines"
                )
            
            # Store cut objects for dynamic updates (using settings colors)
            self.main_app.work_line_objects[f'cut_{cut_name}'] = {
                'id': cut_id,
                'type': 'cut',
                'color_pending': cuts_colors['pending'],
                'color_in_progress': cuts_colors['in_progress'],
                'color_completed': cuts_colors['completed']
            }

        # Draw intermediate cuts between repeated sections (if repeat_lines > 1 or repeat_rows > 1)
        # Horizontal cuts between line sections (when repeat_lines > 1)
        if program.repeat_lines > 1:
            for section_num in range(program.repeat_lines - 1):
                # Cut position at the boundary between sections
                # section_end_y = bottom of section = top of next section
                section_end_y = paper_y + (program.repeat_lines - section_num - 1) * program.high

                # Draw horizontal cut line spanning full actual width
                cut_y_canvas = self.main_app.offset_y + (max_y_cm - section_end_y) * self.main_app.scale_y
                cut_x1_canvas = self.main_app.offset_x + paper_x * self.main_app.scale_x
                cut_x2_canvas = self.main_app.offset_x + (paper_x + actual_paper_width) * self.main_app.scale_x

                # Intermediate cuts use same color as outer cuts (pending initially) - SOLID line like edge cuts
                intermediate_cut_id = self.main_app.canvas.create_line(
                    cut_x1_canvas, cut_y_canvas, cut_x2_canvas, cut_y_canvas,
                    fill=cuts_colors['pending'], width=visualization_settings.get("line_width_cuts", 4),
                    tags="work_lines"  # Solid line like edge cuts - color changes only
                )

                # Add label for intermediate cut
                self.main_app.canvas.create_text(
                    cut_x2_canvas + 10, cut_y_canvas,
                    text=f"SEC {section_num + 1}-{section_num + 2}",
                    font=tuple(ui_fonts.get("small", ["Arial", 7])),
                    fill=cuts_colors['pending'], tags="work_lines"
                )

                # Store intermediate cut for dynamic updates
                cut_name = f"section_{section_num + 1}_{section_num + 2}"
                self.main_app.work_line_objects[f'cut_{cut_name}'] = {
                    'id': intermediate_cut_id,
                    'type': 'cut',
                    'color_pending': cuts_colors['pending'],
                    'color_in_progress': cuts_colors['in_progress'],
                    'color_completed': cuts_colors['completed']
                }

        # Vertical cuts between row sections (when repeat_rows > 1)
        if program.repeat_rows > 1:
            for section_num in range(program.repeat_rows - 1):
                # Cut position at the boundary between row sections
                # section_end_x = right edge of section = left edge of next section
                section_end_x = paper_x + (section_num + 1) * program.width

                # Draw vertical cut line spanning full actual height
                cut_x_canvas = self.main_app.offset_x + section_end_x * self.main_app.scale_x
                cut_y1_canvas = self.main_app.offset_y + (max_y_cm - (paper_y + actual_paper_height)) * self.main_app.scale_y
                cut_y2_canvas = self.main_app.offset_y + (max_y_cm - paper_y) * self.main_app.scale_y

                # Intermediate cuts use same color as outer cuts (pending initially) - SOLID line like edge cuts
                intermediate_cut_id = self.main_app.canvas.create_line(
                    cut_x_canvas, cut_y1_canvas, cut_x_canvas, cut_y2_canvas,
                    fill=cuts_colors['pending'], width=visualization_settings.get("line_width_cuts", 4),
                    tags="work_lines"  # Solid line like edge cuts - color changes only
                )

                # Add label for intermediate cut
                self.main_app.canvas.create_text(
                    cut_x_canvas, cut_y1_canvas - 10,
                    text=f"SEC {section_num + 1}-{section_num + 2}",
                    font=tuple(ui_fonts.get("small", ["Arial", 7])),
                    fill=cuts_colors['pending'], tags="work_lines"
                )

                # Store intermediate cut for dynamic updates (rows don't have intermediate cuts in execution, but keep for consistency)
                cut_name = f"row_section_{section_num + 1}_{section_num + 2}"
                self.main_app.work_line_objects[f'cut_{cut_name}'] = {
                    'id': intermediate_cut_id,
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

        # Initialize intermediate section cut states
        if program.repeat_lines > 1:
            for section_num in range(program.repeat_lines - 1):
                cut_name = f"section_{section_num + 1}_{section_num + 2}"
                if cut_name not in self.main_app.operation_states['cuts']:
                    self.main_app.operation_states['cuts'][cut_name] = 'pending'

        if program.repeat_rows > 1:
            for section_num in range(program.repeat_rows - 1):
                cut_name = f"row_section_{section_num + 1}_{section_num + 2}"
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
        self.logger.debug(f" STATE UPDATE: {operation_type}.{operation_id} = {new_state}", category="gui")
        
        # Update canvas colors immediately
        self.refresh_work_lines_colors()
    
    def track_operation_from_step(self, step_description):
        """Track operation progress from step descriptions

        Note: Checks both English and Hebrew keywords to work with translated descriptions
        """
        if not step_description:
            return

        step_desc = step_description.lower()

        # Track line operations - match "Mark line X" or "סמן קו X" pattern in step descriptions
        # ONLY change color on sensor/tool actions, NOT on move operations
        line_match = re.search(r'(?:mark line|סמן קו)\s*(\d+)', step_desc, re.IGNORECASE)
        if line_match:
            line_num = int(line_match.group(1))

            # Change to in_progress ONLY when waiting for LEFT sensor (user needs to trigger)
            # Check both English and Hebrew keywords
            if any(keyword in step_desc for keyword in [
                'wait for left rows sensor', 'wait left rows sensor',  # English
                'המתן לחיישן עמודות שמאלי'  # Hebrew: wait for left rows sensor
            ]):
                self.update_operation_state('lines', line_num, 'in_progress')
                self.logger.debug(f" Line {line_num} → IN PROGRESS (waiting for LEFT sensor)", category="gui")
            # Change to completed ONLY when closing the marker
            elif any(keyword in step_desc for keyword in [
                'close line marker',  # English
                'סגור סמן שורות'  # Hebrew: close line marker
            ]):
                self.update_operation_state('lines', line_num, 'completed')
                self.logger.info(f" Line {line_num} → COMPLETED (marker closed)", category="gui")

        # Track row operations - match "Page X/Y (Section Z, Page W/N)" or "עמוד X/Y (חלק Z, עמוד W/N)" with edge detection
        # Pages are processed with sections and pages within sections
        # Need to convert page number to canvas page position
        # ONLY change color on sensor/tool actions, NOT on move operations
        # ONLY track row MARKING operations, not cutting operations
        rtl_page_match = re.search(r'(?:page|עמוד)\s*(\d+)', step_desc, re.IGNORECASE)
        if rtl_page_match and any(keyword in step_desc for keyword in ['row marker', 'סמן עמודות']):  # Only for row marking, not cutting
            rtl_page_num = int(rtl_page_match.group(1))

            # Calculate total pages to convert RTL numbering to canvas position
            if hasattr(self.main_app, 'current_program') and self.main_app.current_program:
                program = self.main_app.current_program
                pages_per_section = program.number_of_pages
                num_sections = program.repeat_rows
                total_pages = pages_per_section * num_sections

                # RTL page number is 1-indexed, convert to 0-indexed
                rtl_page_index = rtl_page_num - 1

                # Step generator calculates: rtl_page_number = rtl_section_index * pages_per_section + rtl_page_in_section + 1
                # This means rtl_page_index (0-indexed) DIRECTLY represents execution order:
                # - rtl_page_index 0 = first page executed (rightmost section, rightmost page)
                # - rtl_page_index 1 = second page executed (rightmost section, second from right page)
                # - etc.

                # Decode execution order to section and page within section
                execution_section = rtl_page_index // pages_per_section  # Which section in execution order (0 = first = rightmost)
                page_in_section = rtl_page_index % pages_per_section  # Which page within that section (0 = first = rightmost)

                # Convert execution section to physical section
                physical_section_index = num_sections - 1 - execution_section

                # Pages within section are in canvas LTR order in the loop, but execution is RTL
                # So page_in_section 0 (first in execution) = rightmost = physical page (pages_per_section - 1)
                physical_page_in_section = pages_per_section - 1 - page_in_section

                # Canvas page number (LTR): section * pages_per_section + page
                canvas_page_num = physical_section_index * pages_per_section + physical_page_in_section

                self.logger.debug(f" RTL→Canvas conversion: RTL Page {rtl_page_num} → exec_section={execution_section}, page_in_section={page_in_section} → physical_section={physical_section_index}, physical_page={physical_page_in_section} → canvas_page={canvas_page_num}", category="gui")

                # Calculate row number based on canvas page position
                # Canvas draws pages LTR: page 0, page 1, page 2, ...
                # Each page has 2 edges: left edge (odd row) and right edge (even row)
                row_num = None
                if any(keyword in step_desc for keyword in ['right edge', 'קצה ימני']):
                    # RIGHT edge = even row number
                    row_num = canvas_page_num * 2 + 2
                elif any(keyword in step_desc for keyword in ['left edge', 'קצה שמאלי']):
                    # LEFT edge = odd row number
                    row_num = canvas_page_num * 2 + 1

                if row_num is not None:
                    row_key = f'row_{row_num}'

                    # Change to in_progress when OPENING the row marker (marking starts)
                    if any(keyword in step_desc for keyword in [
                        'open row marker',  # English
                        'פתח סמן עמודות'  # Hebrew: open row marker
                    ]):
                        self.update_operation_state('rows', row_key, 'in_progress')
                        self.logger.debug(f" Row {row_num} (RTL Page {rtl_page_num}, canvas page {canvas_page_num}) → IN PROGRESS", category="gui")
                    # Change to completed when closing the row marker (marking finishes)
                    elif any(keyword in step_desc for keyword in [
                        'close row marker',  # English
                        'סגור סמן עמודות'  # Hebrew: close row marker
                    ]):
                        self.update_operation_state('rows', row_key, 'completed')
                        self.logger.info(f" Row {row_num} (RTL Page {rtl_page_num}, canvas page {canvas_page_num}) → COMPLETED", category="gui")

        # Track cut edge operations - ONLY for actual cutting operations
        # Pattern "cut X" (e.g. "cut top", "cut right") ensures we only match cutting steps
        # This excludes "row marker (RIGHT edge)" because it doesn't have "cut right"
        if not any(keyword in step_desc for keyword in ['row marker', 'סמן עמודות']):  # Extra safety: exclude row marking steps
            # Track intermediate LINE section cuts (e.g., "Cut between sections 1 and 2" or "חיתוך בין חלקים")
            section_cut_match = re.search(r'(?:cut between sections|חיתוך בין חלקים)\s+(\d+)\s+(?:and|ו-)\s*(\d+)', step_desc, re.IGNORECASE)
            if section_cut_match:
                section_1 = section_cut_match.group(1)
                section_2 = section_cut_match.group(2)
                cut_name = f"section_{section_1}_{section_2}"

                if any(keyword in step_desc for keyword in ['close', 'finished', 'סגור', 'הושלם']):
                    self.update_operation_state('cuts', cut_name, 'completed')
                    self.logger.info(f" Line section cut {section_1}-{section_2} → COMPLETED", category="gui")
                elif any(keyword in step_desc for keyword in ['open', 'פתח']):
                    self.update_operation_state('cuts', cut_name, 'in_progress')
                    self.logger.debug(f" Line section cut {section_1}-{section_2} → IN PROGRESS", category="gui")

            # Track intermediate ROW section cuts (e.g., "Cut between row sections 1 and 2" or "חיתוך בין חלקי עמודות")
            row_section_cut_match = re.search(r'(?:cut between row sections|חיתוך בין חלקי עמודות)\s+(\d+)\s+(?:and|ו-)\s*(\d+)', step_desc, re.IGNORECASE)
            if row_section_cut_match:
                section_1 = int(row_section_cut_match.group(1))
                section_2 = int(row_section_cut_match.group(2))
                # Normalize to ascending order (canvas stores as lower_higher)
                lower_section = min(section_1, section_2)
                higher_section = max(section_1, section_2)
                cut_name = f"row_section_{lower_section}_{higher_section}"

                if any(keyword in step_desc for keyword in ['close', 'finished', 'סגור', 'הושלם']):
                    self.update_operation_state('cuts', cut_name, 'completed')
                    self.logger.info(f" Row section cut {lower_section}-{higher_section} → COMPLETED", category="gui")
                elif any(keyword in step_desc for keyword in ['open', 'פתח']):
                    self.update_operation_state('cuts', cut_name, 'in_progress')
                    self.logger.debug(f" Row section cut {lower_section}-{higher_section} → IN PROGRESS", category="gui")

            # Track outer edge cuts (top/bottom/left/right and Hebrew equivalents)
            # Note: Hebrew includes "נייר" (paper) in the middle: "חיתוך קצה נייר ימני" = "cut paper edge right"
            cut_patterns = [
                ('top', ['cut top', 'חיתוך קצה', 'עליון']),  # top edge cut
                ('bottom', ['cut bottom', 'חיתוך קצה', 'תחתון']),  # bottom edge cut
                ('left', ['חיתוך קצה', 'שמאלי']),  # left edge cut (Hebrew: "חיתוך קצה נייר שמאלי")
                ('right', ['חיתוך קצה', 'ימני'])  # right edge cut (Hebrew: "חיתוך קצה נייר ימני")
            ]

            for cut_name, patterns in cut_patterns:
                # For left/right cuts: must have "חיתוך קצה" AND "שמאלי"/"ימני" OR "cut left"/"cut right"
                # For top/bottom: must have "חיתוך קצה" AND "עליון"/"תחתון" OR "cut top"/"cut bottom"
                matches = False
                if cut_name in ['left', 'right']:
                    # Hebrew: check for both "חיתוך קצה" and the direction word
                    if all(p in step_desc for p in patterns):
                        matches = True
                    # English: check for "cut left" or "cut right"
                    elif f'cut {cut_name}' in step_desc and 'edge' in step_desc:
                        matches = True
                else:  # top or bottom
                    # Hebrew: check for both "חיתוך קצה" and the direction word
                    if all(p in step_desc for p in patterns[:2]) and patterns[2] in step_desc:
                        matches = True
                    # English: check for "cut top" or "cut bottom"
                    elif f'cut {cut_name}' in step_desc and 'edge' in step_desc:
                        matches = True

                if matches:
                    if any(keyword in step_desc for keyword in ['complete', 'close', 'finished', 'סגור', 'הושלם']):
                        self.update_operation_state('cuts', cut_name, 'completed')
                        self.logger.info(f" {cut_name.title()} cut edge → COMPLETED", category="gui")
                    elif any(keyword in step_desc for keyword in ['cutting', 'open', 'פתח']):
                        self.update_operation_state('cuts', cut_name, 'in_progress')
                        self.logger.debug(f" {cut_name.title()} cut edge → IN PROGRESS", category="gui")
    
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
                # Extract cut name - handle both simple cuts (cut_top) and section cuts (cut_section_1_2, cut_row_section_1_2)
                cut_name = obj_key.replace('cut_', '', 1)  # Remove first 'cut_' prefix only
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
        """Draw enhanced legend on canvas using colors from settings"""
        legend_x = self.main_app.canvas_width - 200
        legend_y = 100

        # Load colors from settings
        operation_colors = self.main_app.settings.get("operation_colors", {})
        mark_colors = operation_colors.get("mark", {
            "pending": "#8800FF",
            "in_progress": "#FF0088",
            "completed": "#AA00AA"
        })

        # Legend title
        self.main_app.canvas.create_text(
            legend_x, legend_y - 20,
            text="Operations Legend", font=tuple(ui_fonts.get("title", ["Arial", 12, "bold"])), fill='black'
        )

        # Line operations (MARK)
        self.main_app.canvas.create_text(
            legend_x, legend_y + 10,
            text="Lines (MARK):", font=tuple(ui_fonts.get("heading", ["Arial", 10, "bold"])), fill='black', anchor='e'
        )

        # Line colors from settings
        line_color_list = [
            (mark_colors['pending'], 'Ready'),
            (mark_colors['in_progress'], 'Working'),
            (mark_colors['completed'], 'Done')
        ]
        for i, (color, label) in enumerate(line_color_list):
            y_pos = legend_y + 30 + i * 20
            self.main_app.canvas.create_line(
                legend_x + 10, y_pos, legend_x + 30, y_pos,
                fill=color, width=visualization_settings.get("line_width_marks", 3), dash=tuple(visualization_settings.get("dash_pattern_pending", [5, 5])) if label == 'Ready' else (tuple(visualization_settings.get("dash_pattern_in_progress", [8, 4])) if label == 'Working' else tuple(visualization_settings.get("dash_pattern_completed", [10, 2])))
            )
            self.main_app.canvas.create_text(
                legend_x + 35, y_pos,
                text=label, font=tuple(ui_fonts.get("normal", ["Arial", 9])), fill='black', anchor='e'
            )

        # Row operations (CUT)
        self.main_app.canvas.create_text(
            legend_x, legend_y + 100,
            text="Rows (CUT):", font=tuple(ui_fonts.get("heading", ["Arial", 10, "bold"])), fill='black', anchor='e'
        )

        # Row colors from settings
        row_color_list = [
            (mark_colors['pending'], 'Ready'),
            (mark_colors['in_progress'], 'Working'),
            (mark_colors['completed'], 'Done')
        ]
        for i, (color, label) in enumerate(row_color_list):
            y_pos = legend_y + 120 + i * 20
            self.main_app.canvas.create_line(
                legend_x + 10, y_pos, legend_x + 30, y_pos,
                fill=color, width=visualization_settings.get("line_width_marks", 3), dash=tuple(visualization_settings.get("dash_pattern_pending", [5, 5])) if label == 'Ready' else (tuple(visualization_settings.get("dash_pattern_in_progress", [8, 4])) if label == 'Working' else tuple(visualization_settings.get("dash_pattern_completed", [10, 2])))
            )
            self.main_app.canvas.create_text(
                legend_x + 35, y_pos,
                text=label, font=tuple(ui_fonts.get("normal", ["Arial", 9])), fill='black', anchor='e'
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
        self.logger.debug(" DEBUG: Added Ctrl+T to test color changes", category="gui")

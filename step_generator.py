#!/usr/bin/env python3

# Updated step generation system for new CSV structure
# Uses new field names: high, top_padding, bottom_padding, width, left_margin, etc.

def create_step(operation, parameters=None, description=""):
    """Create a simple step dictionary - optimized for minimal memory usage"""
    return {
        'operation': operation,
        'parameters': parameters or {},
        'description': description
    }

def generate_lines_marking_steps(program):
    """
    Generate steps for lines marking workflow with REPEAT SUPPORT.
    
    REPEAT FUNCTIONALITY:
    - If repeat_lines > 1: Actual paper height = high * repeat_lines
    - Lines are marked across the ENTIRE repeated paper height
    - Cuts span the full width (width * repeat_rows) 
    
    MOTOR BEHAVIOR:
    - Lines motor (Y-axis) operates independently for line marking
    - Rows motor (X-axis) stays at X=0 during lines operations
    - Lines motor moves to Y=0 after line marking completion
    
    New fields used:
    - high, repeat_lines -> ACTUAL HEIGHT = high * repeat_lines
    - width, repeat_rows -> ACTUAL WIDTH = width * repeat_rows  
    - top_padding, bottom_padding, number_of_lines (unchanged)
    
    Coordinates: Program coordinates are relative to paper position (15, 15)
    """
    steps = []
    
    # Paper offset - program coordinates start at (15, 15) on desk
    PAPER_OFFSET_X = 15.0
    PAPER_OFFSET_Y = 15.0
    
    # CALCULATE ACTUAL PAPER DIMENSIONS WITH REPEATS
    actual_paper_width = program.width * program.repeat_rows
    actual_paper_height = program.high * program.repeat_lines
    
    print(f"🔄 REPEAT CALCULATION:")
    print(f"   Single pattern: {program.width}cm W × {program.high}cm H")
    print(f"   Repeats: {program.repeat_rows} rows × {program.repeat_lines} lines") 
    print(f"   ACTUAL PAPER SIZE: {actual_paper_width}cm W × {actual_paper_height}cm H")
    
    # INDEPENDENT MOTOR OPERATION: Ensure rows motor is at home position (X=0)
    steps.append(create_step(
        'move_x',
        {'position': 0.0},
        "Lines operation: Move rows motor to home position (X=0)"
    ))
    
    # Init: Move Y motor to ACTUAL high position (paper_offset + actual_paper_height)
    desk_y_position = PAPER_OFFSET_Y + actual_paper_height
    steps.append(create_step(
        'move_y',
        {'position': desk_y_position},
        f"Init: Move Y motor to {desk_y_position}cm (paper + {actual_paper_height}cm ACTUAL high)"
    ))
    
    # Cut top edge workflow - LEFT sensor first, then RIGHT sensor
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_left', 'description': 'Wait for LEFT X sensor to start top cut'},
        "Cut top edge: Wait for LEFT X sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'down'},
        "Cut top edge: Open line cutter"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_right', 'description': 'Wait for RIGHT X sensor to complete top cut'},
        "Cut top edge: Wait for RIGHT X sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'up'},
        "Cut top edge: Close line cutter"
    ))
    
    # Move to first line position (paper_offset + ACTUAL_height - top_padding) 
    first_line_position = PAPER_OFFSET_Y + actual_paper_height - program.top_padding
    steps.append(create_step(
        'move_y',
        {'position': first_line_position},
        f"Move to first line position: {first_line_position}cm (paper + {actual_paper_height - program.top_padding}cm ACTUAL)"
    ))
    
    # Calculate line spacing across the ENTIRE repeated paper height
    # Lines span the full actual height from top_padding to bottom_padding
    last_line_position = PAPER_OFFSET_Y + program.bottom_padding
    available_space = first_line_position - last_line_position  # Distance from first to last line
    
    # Calculate total lines to mark across ALL repeated sections
    total_lines_to_mark = program.number_of_lines * program.repeat_lines
    if total_lines_to_mark > 1:
        line_spacing = available_space / (total_lines_to_mark - 1)
    else:
        line_spacing = 0
    
    print(f"📏 LINE SPACING CALCULATION:")
    print(f"   Lines per section: {program.number_of_lines}")
    print(f"   Repeated sections: {program.repeat_lines}")
    print(f"   TOTAL LINES TO MARK: {total_lines_to_mark}")
    print(f"   Line spacing: {line_spacing:.2f}cm")
    
    for line_num in range(total_lines_to_mark):
        # Calculate which repeat section and line within section this is
        section_num = line_num // program.number_of_lines + 1
        line_in_section = line_num % program.number_of_lines + 1
        line_description = f"Mark line {line_num + 1}/{total_lines_to_mark} (Section {section_num}, Line {line_in_section})"
        
        steps.append(create_step(
            'wait_sensor',
            {'sensor': 'x_left', 'description': f'Wait for LEFT X sensor for line {line_num + 1}'},
            f"{line_description}: Wait for LEFT X sensor"
        ))
        
        steps.append(create_step(
            'tool_action',
            {'tool': 'line_marker', 'action': 'down'},
            f"{line_description}: Open line marker"
        ))
        
        steps.append(create_step(
            'wait_sensor',
            {'sensor': 'x_right', 'description': f'Wait for RIGHT X sensor for line {line_num + 1}'},
            f"{line_description}: Wait for RIGHT X sensor"
        ))
        
        steps.append(create_step(
            'tool_action',
            {'tool': 'line_marker', 'action': 'up'},
            f"{line_description}: Close line marker"
        ))
        
        # Move to next line position (except for last line)
        if line_num < total_lines_to_mark - 1:
            next_position = first_line_position - ((line_num + 1) * line_spacing)
            steps.append(create_step(
                'move_y',
                {'position': next_position},
                f"Move to next line position: {next_position:.1f}cm"
            ))
    
    # Cut bottom edge: Move to bottom position (paper starting position)
    bottom_position = PAPER_OFFSET_Y
    steps.append(create_step(
        'move_y',
        {'position': bottom_position},
        f"Move to bottom cut position: {bottom_position}cm (paper starting position)"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_left', 'description': 'Wait for LEFT X sensor to start bottom cut'},
        "Cut bottom edge: Wait for LEFT X sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'down'},
        "Cut bottom edge: Open line cutter"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_right', 'description': 'Wait for RIGHT X sensor to complete bottom cut'},
        "Cut bottom edge: Wait for RIGHT X sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'up'},
        "Cut bottom edge: Close line cutter"
    ))
    
    # LINES OPERATION COMPLETE: Move lines motor to home position (Y=0)
    steps.append(create_step(
        'move_y',
        {'position': 0.0},
        "Lines complete: Move lines motor to home position (Y=0)"
    ))
    
    return steps

def generate_row_marking_steps(program):
    """
    Generate steps for row marking workflow with REPEAT SUPPORT.
    
    REPEAT FUNCTIONALITY:
    - If repeat_rows > 1: Actual paper width = width * repeat_rows
    - Pages are marked across ALL repeated sections
    - Cuts span the full height (high * repeat_lines)
    
    MOTOR BEHAVIOR:
    - Rows motor (X-axis) operates independently for row marking  
    - Lines motor (Y-axis) stays at Y=0 during row operations
    - This function should only be called AFTER lines marking is complete
    
    SAFETY REQUIREMENT:
    - Row marker MUST be in DOWN state before rows operations can begin
    - Default state is UP, user must manually set it DOWN
    
    New fields used:
    - width, repeat_rows -> ACTUAL WIDTH = width * repeat_rows
    - high, repeat_lines -> ACTUAL HEIGHT = high * repeat_lines
    - left_margin, right_margin, page_width, number_of_pages, buffer_between_pages
    
    Coordinates: Program coordinates are relative to paper position (15, 15)
    """
    steps = []
    
    # Note: Safety checks for rows operations happen during execution, not step generation
    
    # Paper offset - program coordinates start at (15, 15) on desk
    PAPER_OFFSET_X = 15.0
    PAPER_OFFSET_Y = 15.0
    
    # CALCULATE ACTUAL PAPER DIMENSIONS WITH REPEATS
    actual_paper_width = program.width * program.repeat_rows
    actual_paper_height = program.high * program.repeat_lines
    
    print(f"🔄 ROW REPEAT CALCULATION:")
    print(f"   Single pattern: {program.width}cm W × {program.high}cm H")
    print(f"   Repeats: {program.repeat_rows} rows × {program.repeat_lines} lines") 
    print(f"   ACTUAL PAPER SIZE: {actual_paper_width}cm W × {actual_paper_height}cm H")
    
    # INDEPENDENT MOTOR OPERATION: Ensure lines motor is at home position (Y=0)
    steps.append(create_step(
        'move_y',
        {'position': 0.0},
        "Rows operation: Ensure lines motor is at home position (Y=0)"
    ))
    
    # STEP 1: Cut RIGHT edge of ACTUAL paper first (spans all repeated sections)
    right_paper_cut_position = PAPER_OFFSET_X + actual_paper_width  # Right boundary of ACTUAL paper
    steps.append(create_step(
        'move_x',
        {'position': right_paper_cut_position},
        f"Cut RIGHT paper edge: Move to {right_paper_cut_position}cm (ACTUAL width)"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_top', 'description': 'Wait for TOP Y sensor for right paper cut'},
        "Cut RIGHT paper edge: Wait for TOP Y sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'down'},
        "Cut RIGHT paper edge: Open row cutter"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_bottom', 'description': 'Wait for BOTTOM Y sensor for right paper cut'},
        "Cut RIGHT paper edge: Wait for BOTTOM Y sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'up'},
        "Cut RIGHT paper edge: Close row cutter"
    ))
    
    # STEP 2: Mark pages across ALL repeated sections (RIGHT-TO-LEFT)
    # Calculate total pages across all repeated sections
    total_pages = program.number_of_pages * program.repeat_rows
    
    print(f"📄 PAGE MARKING CALCULATION:")
    print(f"   Pages per section: {program.number_of_pages}")
    print(f"   Repeated sections: {program.repeat_rows}")
    print(f"   TOTAL PAGES TO MARK: {total_pages}")
    
    for page_index in range(total_pages):
        # Calculate which repeat section and page within section this is
        section_num = page_index // program.number_of_pages + 1
        page_in_section = page_index % program.number_of_pages + 1
        
        # RIGHT-TO-LEFT page numbering: rightmost = Page 1, ascending order
        rtl_page_number = page_index + 1
        
        # Physical page position (rightmost page first) across ACTUAL paper width
        physical_page_index = total_pages - 1 - page_index  
        page_left_edge = PAPER_OFFSET_X + program.left_margin + (physical_page_index * (program.page_width + program.buffer_between_pages))
        page_right_edge = page_left_edge + program.page_width
        
        page_description = f"RTL Page {rtl_page_number}/{total_pages} (Section {section_num}, Page {page_in_section})"
        
        # Move to this page's RIGHT edge first (starting point for each page)
        steps.append(create_step(
            'move_x',
            {'position': page_right_edge},
            f"Move to {page_description} RIGHT edge: {page_right_edge}cm"
        ))
        
        # Mark RIGHT edge of page
        steps.append(create_step(
            'wait_sensor',
            {'sensor': 'y_top', 'description': f'TOP Y sensor for {page_description} right edge'},
            f"{page_description}: Wait TOP Y sensor (RIGHT edge)"
        ))
        
        steps.append(create_step(
            'tool_action',
            {'tool': 'row_marker', 'action': 'down'},
            f"{page_description}: Open row marker (RIGHT edge)"
        ))
        
        steps.append(create_step(
            'wait_sensor',
            {'sensor': 'y_bottom', 'description': f'BOTTOM Y sensor for {page_description} right edge'},
            f"{page_description}: Wait BOTTOM Y sensor (RIGHT edge)"
        ))
        
        steps.append(create_step(
            'tool_action',
            {'tool': 'row_marker', 'action': 'up'},
            f"{page_description}: Close row marker (RIGHT edge)"
        ))
        
        # Move RIGHT-TO-LEFT to this page's LEFT edge  
        steps.append(create_step(
            'move_x',
            {'position': page_left_edge},
            f"RTL: Move to {page_description} LEFT edge: {page_left_edge}cm"
        ))
        
        # Mark LEFT edge of page
        steps.append(create_step(
            'wait_sensor',
            {'sensor': 'y_top', 'description': f'TOP Y sensor for {page_description} left edge'},
            f"{page_description}: Wait TOP Y sensor (LEFT edge)"
        ))
        
        steps.append(create_step(
            'tool_action',
            {'tool': 'row_marker', 'action': 'down'},
            f"{page_description}: Open row marker (LEFT edge)"
        ))
        
        steps.append(create_step(
            'wait_sensor',
            {'sensor': 'y_bottom', 'description': f'BOTTOM Y sensor for {page_description} left edge'},
            f"{page_description}: Wait BOTTOM Y sensor (LEFT edge)"
        ))
        
        steps.append(create_step(
            'tool_action',
            {'tool': 'row_marker', 'action': 'up'},
            f"{page_description}: Close row marker (LEFT edge)"
        ))
    
    # STEP 3: Cut LEFT edge of ACTUAL paper last
    left_paper_cut_position = PAPER_OFFSET_X  # Left boundary of ACTUAL paper
    steps.append(create_step(
        'move_x',
        {'position': left_paper_cut_position},
        f"Cut LEFT paper edge: Move to {left_paper_cut_position}cm (ACTUAL paper boundary)"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_top', 'description': 'Wait for TOP Y sensor for left paper cut'},
        "Cut LEFT paper edge: Wait for TOP Y sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'down'},
        "Cut LEFT paper edge: Open row cutter"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_bottom', 'description': 'Wait for BOTTOM Y sensor for left paper cut'},
        "Cut LEFT paper edge: Wait for BOTTOM Y sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'up'},
        "Cut LEFT paper edge: Close row cutter"
    ))
    
    # ROWS OPERATION COMPLETE: Move rows motor to home position (X=0)
    steps.append(create_step(
        'move_x',
        {'position': 0.0},
        "Rows complete: Move rows motor to home position (X=0)"
    ))
    
    return steps

def generate_complete_program_steps(program):
    """
    Generate complete step sequence for a program with PROPER repeat support.
    
    FIXED REPEAT FUNCTIONALITY:
    - repeat_rows, repeat_lines now affect the ACTUAL PAPER SIZE
    - No more nested loops - repeats are handled within the marking functions
    - Actual paper size = (width * repeat_rows) × (height * repeat_lines)
    - Single workflow that processes the entire repeated paper
    """
    all_steps = []
    
    # Calculate actual paper dimensions
    actual_paper_width = program.width * program.repeat_rows
    actual_paper_height = program.high * program.repeat_lines
    total_repeats = program.repeat_rows * program.repeat_lines
    
    # Add starting step with actual dimensions
    all_steps.append(create_step(
        'program_start',
        {'program_number': program.program_number, 
         'actual_width': actual_paper_width,
         'actual_height': actual_paper_height,
         'repeat_rows': program.repeat_rows,
         'repeat_lines': program.repeat_lines},
        f"=== Starting Program {program.program_number}: {program.program_name} (ACTUAL SIZE: {actual_paper_width}×{actual_paper_height}cm) ==="
    ))
    
    # Generate lines marking steps (handles all repeated sections internally)
    print(f"\n🎯 GENERATING LINES STEPS with repeats...")
    lines_steps = generate_lines_marking_steps(program)
    all_steps.extend(lines_steps)
    
    # Generate row marking steps (handles all repeated sections internally)  
    print(f"\n🎯 GENERATING ROWS STEPS with repeats...")
    row_steps = generate_row_marking_steps(program)
    all_steps.extend(row_steps)
    
    # Add completion step
    all_steps.append(create_step(
        'program_complete',
        {'program_number': program.program_number, 
         'total_repeats': total_repeats,
         'actual_width': actual_paper_width,
         'actual_height': actual_paper_height},
        f"=== Program {program.program_number} completed: {actual_paper_width}×{actual_paper_height}cm paper processed ==="
    ))
    
    return all_steps

def get_step_count_summary(program):
    """Get summary of step counts for a program with FIXED repeat structure"""
    # With the new approach, the functions handle repeats internally
    lines_steps = generate_lines_marking_steps(program)
    row_steps = generate_row_marking_steps(program)
    
    # Calculate actual dimensions and repeat info
    actual_paper_width = program.width * program.repeat_rows
    actual_paper_height = program.high * program.repeat_lines
    total_repeats = program.repeat_rows * program.repeat_lines
    
    # Total steps = lines + rows + 2 (start/complete)
    total_steps = len(lines_steps) + len(row_steps) + 2
    
    # Calculate actual counts with repeats
    total_lines_marked = program.number_of_lines * program.repeat_lines
    total_pages_marked = program.number_of_pages * program.repeat_rows
    
    return {
        'lines_steps': len(lines_steps),
        'row_steps': len(row_steps), 
        'total_steps': total_steps,
        'total_repeats': total_repeats,
        'actual_paper_width': actual_paper_width,
        'actual_paper_height': actual_paper_height,
        'total_lines_marked': total_lines_marked,
        'total_pages_marked': total_pages_marked
    }
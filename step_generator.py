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
    Generate steps for lines marking workflow using new CSV structure.
    
    MOTOR BEHAVIOR:
    - Lines motor (Y-axis) operates independently for line marking
    - Rows motor (X-axis) stays at X=0 during lines operations
    - Lines motor moves to Y=0 after line marking completion
    
    New fields used:
    - high (replaces general_high)
    - top_padding (replaces top_buffer) 
    - bottom_padding (replaces bottom_buffer)
    - number_of_lines (unchanged)
    
    Coordinates: Program coordinates are relative to paper position (15, 15)
    """
    steps = []
    
    # Paper offset - program coordinates start at (15, 15) on desk
    PAPER_OFFSET_X = 15.0
    PAPER_OFFSET_Y = 15.0
    
    # INDEPENDENT MOTOR OPERATION: Ensure rows motor is at home position (X=0)
    steps.append(create_step(
        'move_x',
        {'position': 0.0},
        "Lines operation: Move rows motor to home position (X=0)"
    ))
    
    # Init: Move Y motor to high position (paper_offset + program.high)
    desk_y_position = PAPER_OFFSET_Y + program.high
    steps.append(create_step(
        'move_y',
        {'position': desk_y_position},
        f"Init: Move Y motor to {desk_y_position}cm (paper + {program.high}cm high)"
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
    
    # Move to first line position (paper_offset + high - top_padding)
    first_line_position = PAPER_OFFSET_Y + program.high - program.top_padding
    steps.append(create_step(
        'move_y',
        {'position': first_line_position},
        f"Move to first line position: {first_line_position}cm (paper + {program.high - program.top_padding}cm)"
    ))
    
    # Calculate line spacing - ensure lines span from top_padding to bottom_padding
    # Last line should be slightly above bottom edge (not ON the edge where cut happens)
    last_line_position = PAPER_OFFSET_Y + program.bottom_padding
    available_space = first_line_position - last_line_position  # Distance from first to last line
    
    # Calculate spacing for actual lines to mark (N lines = N internal markings + 2 edge cuts)
    actual_lines_to_mark = program.number_of_lines  
    if actual_lines_to_mark > 1:
        line_spacing = available_space / (actual_lines_to_mark - 1)
    else:
        line_spacing = 0
    
    for line_num in range(actual_lines_to_mark):
        line_description = f"Mark line {line_num + 1}/{actual_lines_to_mark}"
        
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
        if line_num < actual_lines_to_mark - 1:
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
    Generate steps for row marking workflow using new CSV structure.
    
    MOTOR BEHAVIOR:
    - Rows motor (X-axis) operates independently for row marking  
    - Lines motor (Y-axis) stays at Y=0 during row operations
    - This function should only be called AFTER lines marking is complete
    
    SAFETY REQUIREMENT:
    - Row marker MUST be in DOWN state before rows operations can begin
    - Default state is UP, user must manually set it DOWN
    
    New fields used:
    - width (replaces general_width)
    - left_margin, right_margin
    - page_width, number_of_pages, buffer_between_pages
    
    Coordinates: Program coordinates are relative to paper position (15, 15)
    """
    steps = []
    
    # Note: Safety checks for rows operations happen during execution, not step generation
    
    # Paper offset - program coordinates start at (15, 15) on desk
    PAPER_OFFSET_X = 15.0
    PAPER_OFFSET_Y = 15.0
    
    # INDEPENDENT MOTOR OPERATION: Ensure lines motor is at home position (Y=0)
    steps.append(create_step(
        'move_y',
        {'position': 0.0},
        "Rows operation: Ensure lines motor is at home position (Y=0)"
    ))
    
    # STEP 1: Cut RIGHT edge of paper first (as requested)
    right_paper_cut_position = PAPER_OFFSET_X + program.width  # Right paper boundary
    steps.append(create_step(
        'move_x',
        {'position': right_paper_cut_position},
        f"Cut RIGHT paper edge: Move to {right_paper_cut_position}cm"
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
    
    # STEP 2: Start marking pages RIGHT-TO-LEFT (rightmost page = Page 1)
    # Calculate positions for RIGHT-TO-LEFT operation
    for page_index in range(program.number_of_pages):
        # RIGHT-TO-LEFT page numbering: rightmost = Page 1, ascending order
        rtl_page_number = page_index + 1
        
        # Physical page position (rightmost page first)
        physical_page_index = program.number_of_pages - 1 - page_index  # 3,2,1,0 for 4 pages
        page_left_edge = PAPER_OFFSET_X + program.left_margin + (physical_page_index * (program.page_width + program.buffer_between_pages))
        page_right_edge = page_left_edge + program.page_width
        
        page_description = f"RTL Page {rtl_page_number}/{program.number_of_pages}"
        
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
    
    # STEP 3: Cut LEFT edge of paper last
    left_paper_cut_position = PAPER_OFFSET_X  # Left paper boundary
    steps.append(create_step(
        'move_x',
        {'position': left_paper_cut_position},
        f"Cut LEFT paper edge: Move to {left_paper_cut_position}cm"
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
    Generate complete step sequence for a program with repeat support.
    
    New fields used:
    - repeat_rows, repeat_lines (new repeat functionality)
    """
    all_steps = []
    
    # Add starting step
    all_steps.append(create_step(
        'program_start',
        {'program_number': program.program_number},
        f"=== Starting Program {program.program_number}: {program.program_name} ==="
    ))
    
    # Generate steps for each repetition
    for repeat_row in range(program.repeat_rows):
        for repeat_line in range(program.repeat_lines):
            
            # Add position setup for repeated patterns
            if repeat_row > 0 or repeat_line > 0:
                x_offset = repeat_row * program.width
                y_offset = repeat_line * program.high
                
                all_steps.append(create_step(
                    'move_position',
                    {'x_offset': x_offset, 'y_offset': y_offset},
                    f"Position for repeat ({repeat_row  }, {repeat_line  }): offset +{x_offset:.1f}x, +{y_offset:.1f}y"
                ))
            
            # Generate lines marking steps
            lines_steps = generate_lines_marking_steps(program)
            for step in lines_steps:
                step['description'] = f"Lines [{repeat_row  },{repeat_line  }] {step['description']}"
                all_steps.append(step)
            
            # Generate row marking steps
            row_steps = generate_row_marking_steps(program) 
            for step in row_steps:
                step['description'] = f"Rows [{repeat_row  },{repeat_line  }] {step['description']}"
                all_steps.append(step)
    
    # Add completion step
    all_steps.append(create_step(
        'program_complete',
        {'program_number': program.program_number, 'total_repeats': program.repeat_rows * program.repeat_lines},
        f"=== Program {program.program_number} completed with {program.repeat_rows * program.repeat_lines} repetitions ==="
    ))
    
    return all_steps

def get_step_count_summary(program):
    """Get summary of step counts for a program with new structure"""
    lines_steps = generate_lines_marking_steps(program)
    row_steps = generate_row_marking_steps(program)
    
    # Calculate steps per repetition
    steps_per_repetition = len(lines_steps) + len(row_steps)
    
    # Calculate total steps including repetitions
    total_repetitions = program.repeat_rows * program.repeat_lines
    total_steps = 2 + (steps_per_repetition * total_repetitions)  # +2 for start/complete steps
    
    return {
        'lines_steps': len(lines_steps),
        'row_steps': len(row_steps),
        'steps_per_repetition': steps_per_repetition,
        'total_repetitions': total_repetitions,
        'total_steps': total_steps
    }
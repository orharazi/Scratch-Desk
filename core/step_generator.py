#!/usr/bin/env python3

# Updated step generation system for new CSV structure
# Uses new field names: high, top_padding, bottom_padding, width, left_margin, etc.

from core.logger import get_logger
from core.translations import t

# Module-level logger for functions
logger = get_logger()

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

    logger.debug(f"REPEAT CALCULATION:", category="execution")
    logger.debug(f"   Single pattern: {program.width}cm W × {program.high}cm H", category="execution")
    logger.debug(f"   Repeats: {program.repeat_rows} rows × {program.repeat_lines} lines", category="execution")
    logger.debug(f"   ACTUAL PAPER SIZE: {actual_paper_width}cm W × {actual_paper_height}cm H", category="execution")

    # INDEPENDENT MOTOR OPERATION: Ensure both motors start at home position
    steps.append(create_step(
        'move_x',
        {'position': 0.0},
        t("Init: Move rows motor to home position (X=0)")
    ))

    steps.append(create_step(
        'move_y',
        {'position': 0.0},
        t("Init: Move lines motor to home position (Y=0)")
    ))

    # Init: Move Y motor to ACTUAL high position (paper_offset + actual_paper_height)
    # When moving UP, piston automatically lifts, but we show it explicitly in steps
    desk_y_position = PAPER_OFFSET_Y + actual_paper_height

    steps.append(create_step(
        'tool_action',
        {'tool': 'line_motor_piston', 'action': 'up'},
        t("⚠️ Lifting line motor piston UP (preparing for upward movement to {pos}cm)", pos=desk_y_position)
    ))

    steps.append(create_step(
        'move_y',
        {'position': desk_y_position},
        t("Init: Move Y motor to {pos}cm (paper + {height}cm ACTUAL high)", pos=desk_y_position, height=actual_paper_height)
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'line_motor_piston', 'action': 'down'},
        t("Line motor piston DOWN (Y motor assembly lowered to default position)")
    ))

    # Cut top edge workflow - LEFT sensor first, then RIGHT sensor
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_left', 'description': 'Wait for LEFT X sensor to start top cut'},
        t("Cut top edge: Wait for LEFT X sensor")
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'down'},
        t("Cut top edge: Open line cutter")
    ))

    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_right', 'description': 'Wait for RIGHT X sensor to complete top cut'},
        t("Cut top edge: Wait for RIGHT X sensor")
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'up'},
        t("Cut top edge: Close line cutter")
    ))

    # CORRECTED REPEAT LOGIC: Process each repeated section individually
    # Each section has its own margins and line spacing
    logger.debug(f"REPEAT PROCESSING: {program.repeat_lines} sections of {program.high}cm each", category="execution")
    logger.debug(f"   Each section: {program.number_of_lines} lines with {program.top_padding}cm top, {program.bottom_padding}cm bottom margins", category="execution")

    # Process each repeated section from top to bottom
    for section_num in range(program.repeat_lines):
        section_start_y = PAPER_OFFSET_Y + (program.repeat_lines - section_num) * program.high  # Top of this section
        section_end_y = PAPER_OFFSET_Y + (program.repeat_lines - section_num - 1) * program.high  # Bottom of this section

        logger.debug(f"SECTION {section_num + 1}: Y range {section_end_y:.1f} to {section_start_y:.1f}cm", category="execution")

        # Calculate line positions within THIS section
        first_line_y_section = section_start_y - program.top_padding
        last_line_y_section = section_end_y + program.bottom_padding
        available_space_section = first_line_y_section - last_line_y_section

        if program.number_of_lines > 1:
            line_spacing_section = available_space_section / (program.number_of_lines - 1)
        else:
            line_spacing_section = 0

        logger.debug(f"   Lines in section: {first_line_y_section:.1f} to {last_line_y_section:.1f}cm (spacing: {line_spacing_section:.2f}cm)", category="execution")

        # Move to first line of this section
        if section_num == 0:  # Only move for first section (already positioned at top)
            steps.append(create_step(
                'move_y',
                {'position': first_line_y_section},
                t("Move to first line of section {section}: {pos}cm", section=section_num + 1, pos=first_line_y_section)
            ))

        # Mark all lines in this section
        for line_in_section in range(program.number_of_lines):
            overall_line_num = section_num * program.number_of_lines + line_in_section + 1
            line_y_position = first_line_y_section - (line_in_section * line_spacing_section)

            line_description = t("Mark line {num}/{total} (Section {section}, Line {line})",
                                num=overall_line_num,
                                total=program.number_of_lines * program.repeat_lines,
                                section=section_num + 1,
                                line=line_in_section + 1)

            # Move to this line position (unless it's the first line of first section)
            if not (section_num == 0 and line_in_section == 0):
                steps.append(create_step(
                    'move_y',
                    {'position': line_y_position},
                    t("Move to line position: {pos:.1f}cm", pos=line_y_position)
                ))

            # Mark this line
            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'x_left', 'description': f'Wait for LEFT X sensor for line {overall_line_num}'},
                t("{desc}: Wait for LEFT X sensor", desc=line_description)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'line_marker', 'action': 'down'},
                t("{desc}: Open line marker", desc=line_description)
            ))

            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'x_right', 'description': f'Wait for RIGHT X sensor for line {overall_line_num}'},
                t("{desc}: Wait for RIGHT X sensor", desc=line_description)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'line_marker', 'action': 'up'},
                t("{desc}: Close line marker", desc=line_description)
            ))

        # ADD CUT BETWEEN SECTIONS (except after the last section)
        if section_num < program.repeat_lines - 1:  # Not the last section
            cut_position = section_end_y  # Cut at the bottom of current section (= top of next section)

            # Move to cut position between sections
            steps.append(create_step(
                'move_y',
                {'position': cut_position},
                t("Move to cut between sections {sec1} and {sec2}: {pos}cm",
                  sec1=section_num + 1, sec2=section_num + 2, pos=cut_position)
            ))

            # Perform cut between sections
            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'x_left', 'description': f'Wait for LEFT X sensor for cut between sections {section_num + 1}-{section_num + 2}'},
                t("Cut between sections {sec1} and {sec2}: Wait for LEFT X sensor",
                  sec1=section_num + 1, sec2=section_num + 2)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'line_cutter', 'action': 'down'},
                t("Cut between sections {sec1} and {sec2}: Open line cutter",
                  sec1=section_num + 1, sec2=section_num + 2)
            ))

            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'x_right', 'description': f'Wait for RIGHT X sensor for cut between sections {section_num + 1}-{section_num + 2}'},
                t("Cut between sections {sec1} and {sec2}: Wait for RIGHT X sensor",
                  sec1=section_num + 1, sec2=section_num + 2)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'line_cutter', 'action': 'up'},
                t("Cut between sections {sec1} and {sec2}: Close line cutter",
                  sec1=section_num + 1, sec2=section_num + 2)
            ))

    # Cut bottom edge: Move to bottom position (paper starting position)
    bottom_position = PAPER_OFFSET_Y
    steps.append(create_step(
        'move_y',
        {'position': bottom_position},
        t("Move to bottom cut position: {pos}cm (paper starting position)", pos=bottom_position)
    ))

    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_left', 'description': 'Wait for LEFT X sensor to start bottom cut'},
        t("Cut bottom edge: Wait for LEFT X sensor")
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'down'},
        t("Cut bottom edge: Open line cutter")
    ))

    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_right', 'description': 'Wait for RIGHT X sensor to complete bottom cut'},
        t("Cut bottom edge: Wait for RIGHT X sensor")
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'up'},
        t("Cut bottom edge: Close line cutter")
    ))

    # LINES OPERATION COMPLETE: Move lines motor to home position (Y=0)
    steps.append(create_step(
        'move_y',
        {'position': 0.0},
        t("Lines complete: Move lines motor to home position (Y=0)")
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

    logger.debug(f"ROW REPEAT CALCULATION:", category="execution")
    logger.debug(f"   Single pattern: {program.width}cm W × {program.high}cm H", category="execution")
    logger.debug(f"   Repeats: {program.repeat_rows} rows × {program.repeat_lines} lines", category="execution")
    logger.debug(f"   ACTUAL PAPER SIZE: {actual_paper_width}cm W × {actual_paper_height}cm H", category="execution")

    # INDEPENDENT MOTOR OPERATION: Ensure lines motor is at home position (Y=0)
    steps.append(create_step(
        'move_y',
        {'position': 0.0},
        t("Rows operation: Ensure lines motor is at home position (Y=0)")
    ))

    # STEP 1: Cut RIGHT edge of ACTUAL paper first (spans all repeated sections)
    right_paper_cut_position = PAPER_OFFSET_X + actual_paper_width  # Right boundary of ACTUAL paper
    steps.append(create_step(
        'move_x',
        {'position': right_paper_cut_position},
        t("Cut RIGHT paper edge: Move to {pos}cm (ACTUAL width)", pos=right_paper_cut_position)
    ))

    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_top', 'description': 'Wait for TOP Y sensor for right paper cut'},
        t("Cut RIGHT paper edge: Wait for TOP Y sensor")
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'down'},
        t("Cut RIGHT paper edge: Open row cutter")
    ))

    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_bottom', 'description': 'Wait for BOTTOM Y sensor for right paper cut'},
        t("Cut RIGHT paper edge: Wait for BOTTOM Y sensor")
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'up'},
        t("Cut RIGHT paper edge: Close row cutter")
    ))

    # STEP 2: Mark pages BY SECTION (RIGHT-TO-LEFT), cutting between sections as we go
    # Process sections from RIGHTMOST to LEFTMOST (RTL order)
    logger.debug(f"PAGE MARKING BY SECTION (RTL):", category="execution")
    logger.debug(f"   Pages per section: {program.number_of_pages}", category="execution")
    logger.debug(f"   Repeated sections: {program.repeat_rows}", category="execution")

    # Process sections RIGHT-TO-LEFT: rightmost section first
    for rtl_section_index in range(program.repeat_rows):
        # RTL: section 0 is rightmost, section N-1 is leftmost
        # Convert to physical LTR index: rightmost = highest index
        section_index = program.repeat_rows - 1 - rtl_section_index
        section_num = section_index + 1

        logger.debug(f"   Processing section {section_num}/{program.repeat_rows} (RTL order: {rtl_section_index + 1})", category="execution")

        # Mark all pages in this section (RIGHT-TO-LEFT execution order)
        # Process pages from rightmost to leftmost (RTL)
        for rtl_page_in_section in range(program.number_of_pages):
            # RTL execution: page 0 is rightmost, page N-1 is leftmost
            # But physical position uses LTR layout: page 0 is leftmost, page N-1 is rightmost

            # Calculate which physical page position (LTR) we're at
            # RTL page 0 (rightmost) = LTR page N-1 (rightmost position)
            physical_page_in_section = program.number_of_pages - 1 - rtl_page_in_section

            # Calculate TRUE RTL page number based on EXECUTION order (not physical position)
            # This represents: which page in the execution sequence (1 = first executed, N = last executed)
            rtl_page_number = rtl_section_index * program.number_of_pages + rtl_page_in_section + 1

            # Calculate total pages for RTL numbering
            total_pages = program.number_of_pages * program.repeat_rows

            # Each section has the same layout - calculate position within this section
            # Section starts at PAPER_OFFSET_X + (section_index * section_width)
            section_start_x = PAPER_OFFSET_X + (section_index * program.width)

            # Calculate page edges using LTR physical position (to match canvas)
            # Physical page 0 (leftmost) at section_start + left_margin
            # Physical page N-1 (rightmost) at section_start + left_margin + (N-1) * (width + buffer)
            page_left_edge = section_start_x + program.left_margin + (physical_page_in_section * (program.page_width + program.buffer_between_pages))
            page_right_edge = page_left_edge + program.page_width

            page_description = t("RTL Page {num}/{total} (Section {section}, RTL Page {page}/{pages})",
                               num=rtl_page_number, total=total_pages, section=section_num,
                               page=rtl_page_in_section + 1, pages=program.number_of_pages)

            logger.debug(f"      RTL Page {rtl_page_number}: section_index={section_index}, rtl_page_in_section={rtl_page_in_section}, physical_page={physical_page_in_section}, position={page_left_edge:.1f}-{page_right_edge:.1f}cm", category="execution")

            # Move to this page's RIGHT edge first (starting point for each page)
            steps.append(create_step(
                'move_x',
                {'position': page_right_edge},
                t("Move to {desc} RIGHT edge: {pos}cm", desc=page_description, pos=page_right_edge)
            ))

            # Mark RIGHT edge of page
            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'y_top', 'description': f'TOP Y sensor for {page_description} right edge'},
                t("{desc}: Wait TOP Y sensor (RIGHT edge)", desc=page_description)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'row_marker', 'action': 'down'},
                t("{desc}: Open row marker (RIGHT edge)", desc=page_description)
            ))

            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'y_bottom', 'description': f'BOTTOM Y sensor for {page_description} right edge'},
                t("{desc}: Wait BOTTOM Y sensor (RIGHT edge)", desc=page_description)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'row_marker', 'action': 'up'},
                t("{desc}: Close row marker (RIGHT edge)", desc=page_description)
            ))

            # Move RIGHT-TO-LEFT to this page's LEFT edge
            steps.append(create_step(
                'move_x',
                {'position': page_left_edge},
                t("RTL: Move to {desc} LEFT edge: {pos}cm", desc=page_description, pos=page_left_edge)
            ))

            # Mark LEFT edge of page
            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'y_top', 'description': f'TOP Y sensor for {page_description} left edge'},
                t("{desc}: Wait TOP Y sensor (LEFT edge)", desc=page_description)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'row_marker', 'action': 'down'},
                t("{desc}: Open row marker (LEFT edge)", desc=page_description)
            ))

            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'y_bottom', 'description': f'BOTTOM Y sensor for {page_description} left edge'},
                t("{desc}: Wait BOTTOM Y sensor (LEFT edge)", desc=page_description)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'row_marker', 'action': 'up'},
                t("{desc}: Close row marker (LEFT edge)", desc=page_description)
            ))

        # AFTER finishing all pages in this section, cut between this section and the next (if not the last section)
        if rtl_section_index < program.repeat_rows - 1:
            # Calculate the cut position: LEFT boundary of current section (which is to the LEFT of where we just marked)
            # In RTL: we just finished section_index, next we'll do section_index-1
            # The cut is at the LEFT edge of the section we just finished = section_start_x
            section_start_x = PAPER_OFFSET_X + section_index * program.width

            logger.debug(f"   Adding cut AFTER section {section_num} at X={section_start_x}cm", category="execution")

            # Move to cut position between sections
            steps.append(create_step(
                'move_x',
                {'position': section_start_x},
                t("Move to cut between row sections {sec1} and {sec2}: {pos}cm",
                  sec1=section_num, sec2=section_num - 1, pos=section_start_x)
            ))

            # Perform cut between sections (vertical cut spanning full height)
            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'y_top', 'description': f'Wait for TOP Y sensor for cut between row sections {section_num}-{section_num - 1}'},
                t("Cut between row sections {sec1} and {sec2}: Wait for TOP Y sensor",
                  sec1=section_num, sec2=section_num - 1)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'row_cutter', 'action': 'down'},
                t("Cut between row sections {sec1} and {sec2}: Open row cutter",
                  sec1=section_num, sec2=section_num - 1)
            ))

            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'y_bottom', 'description': f'Wait for BOTTOM Y sensor for cut between row sections {section_num}-{section_num - 1}'},
                t("Cut between row sections {sec1} and {sec2}: Wait for BOTTOM Y sensor",
                  sec1=section_num, sec2=section_num - 1)
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'row_cutter', 'action': 'up'},
                t("Cut between row sections {sec1} and {sec2}: Close row cutter",
                  sec1=section_num, sec2=section_num - 1)
            ))

    # STEP 3: Cut LEFT edge of ACTUAL paper last
    left_paper_cut_position = PAPER_OFFSET_X  # Left boundary of ACTUAL paper
    steps.append(create_step(
        'move_x',
        {'position': left_paper_cut_position},
        t("Cut LEFT paper edge: Move to {pos}cm (ACTUAL paper boundary)", pos=left_paper_cut_position)
    ))

    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_top', 'description': 'Wait for TOP Y sensor for left paper cut'},
        t("Cut LEFT paper edge: Wait for TOP Y sensor")
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'down'},
        t("Cut LEFT paper edge: Open row cutter")
    ))

    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_bottom', 'description': 'Wait for BOTTOM Y sensor for left paper cut'},
        t("Cut LEFT paper edge: Wait for BOTTOM Y sensor")
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'up'},
        t("Cut LEFT paper edge: Close row cutter")
    ))

    # ROWS OPERATION COMPLETE: Move rows motor to home position (X=0)
    steps.append(create_step(
        'move_x',
        {'position': 0.0},
        t("Rows complete: Move rows motor to home position (X=0)")
    ))

    return steps

def generate_complete_program_steps(program):
    """
    Generate complete step sequence for a program with PROPER repeat support.

    FIXED REPEAT FUNCTIONALITY:
    - repeat_rows, repeat_lines now affect the ACTUAL PAPER SIZE
    - No more nested loops - repeats are handled within the marking functions
    - Actual paper size = (width * repeat_rows) × (height * repeat_lines)
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
        t("=== Starting Program {num}: {name} (ACTUAL SIZE: {width}×{height}cm) ===",
          num=program.program_number, name=program.program_name,
          width=actual_paper_width, height=actual_paper_height)
    ))

    # Generate lines marking steps (handles all repeated sections internally)
    logger.debug(f"GENERATING LINES STEPS with repeats...", category="execution")
    lines_steps = generate_lines_marking_steps(program)
    all_steps.extend(lines_steps)

    # Generate row marking steps (handles all repeated sections internally)
    logger.debug(f"GENERATING ROWS STEPS with repeats...", category="execution")
    row_steps = generate_row_marking_steps(program)
    all_steps.extend(row_steps)

    # Add completion step
    all_steps.append(create_step(
        'program_complete',
        {'program_number': program.program_number,
         'total_repeats': total_repeats,
         'actual_width': actual_paper_width,
         'actual_height': actual_paper_height},
        t("=== Program {num} completed: {width}×{height}cm paper processed ===",
          num=program.program_number, width=actual_paper_width, height=actual_paper_height)
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
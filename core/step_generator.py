#!/usr/bin/env python3

# Updated step generation system for new CSV structure
# Uses new field names: high, top_padding, bottom_padding, width, left_margin, etc.

import json
import os

from core.logger import get_logger

# Module-level logger for functions
logger = get_logger()


def _load_paper_offsets():
    """Load paper offsets from settings.json"""
    try:
        settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        limits = settings.get('hardware_limits', {})
        return limits.get('paper_start_x', 15.0), limits.get('paper_start_y', 15.0)
    except Exception:
        return 15.0, 15.0  # Defaults


# Load paper offsets from config
PAPER_OFFSET_X, PAPER_OFFSET_Y = _load_paper_offsets()

# Hebrew translations for step UI display
HEBREW_TRANSLATIONS = {
    # Operations
    'move_x': 'הזזת מנוע עמודות',
    'move_y': 'הזזת מנוע שורות',
    'program_start': 'התחלת תוכנית',
    'program_complete': 'סיום תוכנית',

    # Tools
    'line_motor_piston': 'בוכנת מנוע שורות',
    'line_cutter': 'חותך שורות',
    'line_marker': 'סמן שורות',
    'row_cutter': 'חותך עמודות',
    'row_marker': 'סמן עמודות',

    # Actions
    'up': 'למעלה',
    'down': 'למטה',
    'open': 'פתיחה',
    'close': 'סגירה',

    # Sensors (X sensors serve lines/שורות operations, Y sensors serve rows/עמודות operations)
    'x_left': 'חיישן שורות שמאלי',
    'x_right': 'חיישן שורות ימני',
    'y_top': 'חיישן עמודות עליון',
    'y_bottom': 'חיישן עמודות תחתון',

    # Common terms
    'wait': 'המתנה',
    'to position': 'למיקום',
    'cm': 'ס״מ',
}

def _generate_heb_operation_title(operation, parameters):
    """Generate user-friendly Hebrew title for operation"""
    if operation == 'move_x':
        pos = parameters.get('position', 0)
        return f"הזזת מנוע עמודות למיקום {pos:.1f}ס״מ"

    elif operation == 'move_y':
        pos = parameters.get('position', 0)
        return f"הזזת מנוע שורות למיקום {pos:.1f}ס״מ"

    elif operation == 'tool_action':
        tool = parameters.get('tool', '')
        action = parameters.get('action', '')

        # Map tool names to Hebrew
        tool_heb = HEBREW_TRANSLATIONS.get(tool, tool)

        # Map action to operation verb
        if action == 'down':
            if 'cutter' in tool:
                action_verb = 'פתיחת'  # Opening (for cutters)
            elif 'marker' in tool:
                action_verb = 'פתיחת'  # Opening (for markers)
            elif 'piston' in tool:
                action_verb = 'הורדת'  # Lowering (for pistons)
            else:
                action_verb = 'הפעלת'  # Activating
        elif action == 'up':
            if 'cutter' in tool:
                action_verb = 'סגירת'  # Closing (for cutters)
            elif 'marker' in tool:
                action_verb = 'סגירת'  # Closing (for markers)
            elif 'piston' in tool:
                action_verb = 'הרמת'  # Raising (for pistons)
            else:
                action_verb = 'כיבוי'  # Deactivating
        else:
            action_verb = 'הפעלת'

        return f"{action_verb} {tool_heb}"

    elif operation == 'wait_sensor':
        sensor = parameters.get('sensor', '')
        sensor_heb = HEBREW_TRANSLATIONS.get(sensor, sensor)
        return f"המתנה ל{sensor_heb}"

    elif operation == 'program_start':
        prog_num = parameters.get('program_number', '')
        return f"התחלת תוכנית {prog_num}"

    elif operation == 'program_complete':
        prog_num = parameters.get('program_number', '')
        return f"סיום תוכנית {prog_num}"

    else:
        return operation

def _translate_description_to_hebrew(description):
    """Translate English description to Hebrew"""
    # Simple translation mappings for common patterns
    translations = {
        'Init: Move rows motor to home position (X=0)': 'אתחול: הזז מנוע עמודות למיקום בית (X=0)',
        'Init: Move lines motor to home position (Y=0)': 'אתחול: הזז מנוע שורות למיקום בית (Y=0)',
        'Line motor piston DOWN (Y motor assembly lowered to default position)': 'בוכנת מנוע שורות למטה (מכלול מנוע שורות הונמך למצב ברירת מחדל)',

        'Cut top edge: Wait for left lines sensor': 'חיתוך קצה עליון: המתן לחיישן שורות שמאלי',
        'Cut top edge: Open line cutter': 'חיתוך קצה עליון: פתח חותך שורות',
        'Cut top edge: Wait for right lines sensor': 'חיתוך קצה עליון: המתן לחיישן שורות ימני',
        'Cut top edge: Close line cutter': 'חיתוך קצה עליון: סגור חותך שורות',

        'Cut bottom edge: Wait for left lines sensor': 'חיתוך קצה תחתון: המתן לחיישן שורות שמאלי',
        'Cut bottom edge: Open line cutter': 'חיתוך קצה תחתון: פתח חותך שורות',
        'Cut bottom edge: Wait for right lines sensor': 'חיתוך קצה תחתון: המתן לחיישן שורות ימני',
        'Cut bottom edge: Close line cutter': 'חיתוך קצה תחתון: סגור חותך שורות',

        'Cut RIGHT paper edge: Wait for top rows sensor': 'חיתוך קצה ימני: המתן לחיישן עמודות עליון',
        'Cut RIGHT paper edge: Open row cutter': 'חיתוך קצה ימני: פתח חותך עמודות',
        'Cut RIGHT paper edge: Wait for bottom rows sensor': 'חיתוך קצה ימני: המתן לחיישן עמודות תחתון',
        'Cut RIGHT paper edge: Close row cutter': 'חיתוך קצה ימני: סגור חותך עמודות',

        'Cut LEFT paper edge: Wait for top rows sensor': 'חיתוך קצה שמאלי: המתן לחיישן עמודות עליון',
        'Cut LEFT paper edge: Open row cutter': 'חיתוך קצה שמאלי: פתח חותך עמודות',
        'Cut LEFT paper edge: Wait for bottom rows sensor': 'חיתוך קצה שמאלי: המתן לחיישן עמודות תחתון',
        'Cut LEFT paper edge: Close row cutter': 'חיתוך קצה שמאלי: סגור חותך עמודות',

        'Lines complete: Move lines motor to home position (Y=0)': 'שורות הושלמו: הזז מנוע שורות למיקום בית (Y=0)',
        'Rows operation: Ensure lines motor is at home position (Y=0)': 'פעולת עמודות: ודא שמנוע שורות במיקום בית (Y=0)',
        'Rows complete: Move rows motor to home position (X=0)': 'עמודות הושלמו: הזז מנוע עמודות למיקום בית (X=0)',
    }

    # Check for exact match first
    if description in translations:
        return translations[description]

    # Handle dynamic descriptions with pattern matching
    desc_lower = description.lower()

    # Pattern: "Move to first line of section X: Y cm"
    if 'move to first line of section' in desc_lower:
        import re
        match = re.search(r'section (\d+): ([\d.]+)cm', description)
        if match:
            section, pos = match.groups()
            return f"עבור לקו ראשון של חלק {section}: {pos}ס״מ"

    # Pattern: "Move to line position: X cm"
    if 'move to line position:' in desc_lower:
        import re
        match = re.search(r': ([\d.]+)cm', description)
        if match:
            pos = match.group(1)
            return f"עבור למיקום קו: {pos}ס״מ"

    # Pattern: "Mark line X/Y (Section Z, Line W): ..."
    if 'mark line' in desc_lower:
        import re
        match = re.search(r'mark line (\d+)/(\d+) \(section (\d+), line (\d+)\)', desc_lower)
        if match:
            line, total, section, line_in_sec = match.groups()
            if 'wait for left lines sensor' in desc_lower:
                return f"סמן קו {line}/{total} (חלק {section}, קו {line_in_sec}): המתן לחיישן שורות שמאלי"
            elif 'open line marker' in desc_lower:
                return f"סמן קו {line}/{total} (חלק {section}, קו {line_in_sec}): פתח סמן שורות"
            elif 'wait for right lines sensor' in desc_lower:
                return f"סמן קו {line}/{total} (חלק {section}, קו {line_in_sec}): המתן לחיישן שורות ימני"
            elif 'close line marker' in desc_lower:
                return f"סמן קו {line}/{total} (חלק {section}, קו {line_in_sec}): סגור סמן שורות"

    # Pattern: "Move to cut between sections X and Y: Z cm"
    if 'move to cut between sections' in desc_lower:
        import re
        match = re.search(r'sections (\d+) and (\d+): ([\d.]+)cm', description)
        if match:
            s1, s2, pos = match.groups()
            return f"עבור לחיתוך בין חלקים {s1} ו-{s2}: {pos}ס״מ"

    # Pattern: "Cut between sections X and Y: ..."
    if 'cut between sections' in desc_lower:
        import re
        match = re.search(r'sections (\d+) and (\d+)', description)
        if match:
            s1, s2 = match.groups()
            if 'wait for left lines sensor' in desc_lower:
                return f"חיתוך בין חלקים {s1} ו-{s2}: המתן לחיישן שורות שמאלי"
            elif 'open line cutter' in desc_lower:
                return f"חיתוך בין חלקים {s1} ו-{s2}: פתח חותך שורות"
            elif 'wait for right lines sensor' in desc_lower:
                return f"חיתוך בין חלקים {s1} ו-{s2}: המתן לחיישן שורות ימני"
            elif 'close line cutter' in desc_lower:
                return f"חיתוך בין חלקים {s1} ו-{s2}: סגור חותך שורות"
            elif ': move to' in desc_lower:
                match2 = re.search(r'to ([\d.]+)cm', description)
                if match2:
                    pos = match2.group(1)
                    return f"עבור לחיתוך בין חלקים {s1} ו-{s2}: {pos}ס״מ"

    # Pattern: "Move to bottom cut position: X cm"
    if 'move to bottom cut position' in desc_lower:
        import re
        match = re.search(r': ([\d.]+)cm', description)
        if match:
            pos = match.group(1)
            return f"עבור למיקום חיתוך תחתון: {pos}ס״מ (מיקום התחלת נייר)"

    # Pattern: "Cut RIGHT paper edge: Move to X cm"
    if 'cut right paper edge: move to' in desc_lower:
        import re
        match = re.search(r'to ([\d.]+)cm', description)
        if match:
            pos = match.group(1)
            return f"חיתוך קצה ימני: עבור ל-{pos}ס״מ (רוחב בפועל)"

    # Pattern: "Cut LEFT paper edge: Move to X cm"
    if 'cut left paper edge: move to' in desc_lower:
        import re
        match = re.search(r'to ([\d.]+)cm', description)
        if match:
            pos = match.group(1)
            return f"חיתוך קצה שמאלי: עבור ל-{pos}ס״מ (גבול נייר בפועל)"

    # Pattern: "Page X/Y (Section Z, Page W/N): ..."
    if 'page' in desc_lower and 'section' in desc_lower:
        import re
        match = re.search(r'page (\d+)/(\d+) \(section (\d+), page (\d+)/(\d+)\)', desc_lower)
        if match:
            page, total, section, page_in_sec, pages_per_sec = match.groups()
            if 'right edge:' in desc_lower and 'move to' in desc_lower:
                match2 = re.search(r': ([\d.]+)cm', description)
                if match2:
                    pos = match2.group(1)
                    return f"עבור לעמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}) קצה ימני: {pos}ס״מ"
            elif 'wait top rows sensor (right edge)' in desc_lower:
                return f"עמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}): המתן לחיישן עמודות עליון (קצה ימני)"
            elif 'open row marker (right edge)' in desc_lower:
                return f"עמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}): פתח סמן עמודות (קצה ימני)"
            elif 'wait bottom rows sensor (right edge)' in desc_lower:
                return f"עמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}): המתן לחיישן עמודות תחתון (קצה ימני)"
            elif 'close row marker (right edge)' in desc_lower:
                return f"עמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}): סגור סמן עמודות (קצה ימני)"
            elif 'left edge:' in desc_lower and 'move to' in desc_lower:
                match2 = re.search(r': ([\d.]+)cm', description)
                if match2:
                    pos = match2.group(1)
                    return f"עבור לעמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}) קצה שמאלי: {pos}ס״מ"
            elif 'wait top rows sensor (left edge)' in desc_lower:
                return f"עמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}): המתן לחיישן עמודות עליון (קצה שמאלי)"
            elif 'open row marker (left edge)' in desc_lower:
                return f"עמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}): פתח סמן עמודות (קצה שמאלי)"
            elif 'wait bottom rows sensor (left edge)' in desc_lower:
                return f"עמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}): המתן לחיישן עמודות תחתון (קצה שמאלי)"
            elif 'close row marker (left edge)' in desc_lower:
                return f"עמוד {page}/{total} (חלק {section}, עמוד {page_in_sec}/{pages_per_sec}): סגור סמן עמודות (קצה שמאלי)"

    # Pattern: "Move to cut between row sections X and Y: Z cm"
    if 'move to cut between row sections' in desc_lower:
        import re
        match = re.search(r'sections (\d+) and (\d+): ([\d.]+)cm', description)
        if match:
            s1, s2, pos = match.groups()
            return f"עבור לחיתוך בין חלקי עמודות {s1} ו-{s2}: {pos}ס״מ"

    # Pattern: "Cut between row sections X and Y: ..."
    if 'cut between row sections' in desc_lower:
        import re
        match = re.search(r'sections (\d+) and (\d+)', description)
        if match:
            s1, s2 = match.groups()
            if 'wait for top rows sensor' in desc_lower:
                return f"חיתוך בין חלקי עמודות {s1} ו-{s2}: המתן לחיישן עמודות עליון"
            elif 'open row cutter' in desc_lower:
                return f"חיתוך בין חלקי עמודות {s1} ו-{s2}: פתח חותך עמודות"
            elif 'wait for bottom rows sensor' in desc_lower:
                return f"חיתוך בין חלקי עמודות {s1} ו-{s2}: המתן לחיישן עמודות תחתון"
            elif 'close row cutter' in desc_lower:
                return f"חיתוך בין חלקי עמודות {s1} ו-{s2}: סגור חותך עמודות"
            elif ': move to' in desc_lower:
                match2 = re.search(r': ([\d.]+)cm', description)
                if match2:
                    pos = match2.group(1)
                    return f"עבור לחיתוך בין חלקי עמודות {s1} ו-{s2}: {pos}ס״מ"

    # Pattern: "⚠️ Lifting line motor piston UP..."
    if 'lifting line motor piston up' in desc_lower:
        import re
        match = re.search(r'to ([\d.]+)cm', description)
        if match:
            pos = match.group(1)
            return f"⚠️ הרמת בוכנת מנוע שורות למעלה (הכנה לתנועה עליונה ל-{pos}ס״מ)"

    # Pattern: "Init: Move Y motor to X cm..."
    if 'init: move y motor to' in desc_lower:
        import re
        match = re.search(r'to ([\d.]+)cm.*\+ ([\d.]+)cm', description)
        if match:
            pos, height = match.groups()
            return f"אתחול: הזז מנוע שורות ל-{pos}ס״מ (נייר + {height}ס״מ גובה בפועל)"

    # Pattern: "=== Starting Program X: Y (ACTUAL SIZE: ...)"
    if '=== starting program' in desc_lower:
        import re
        match = re.search(r'program (\d+): ([^(]+) \(actual size: ([\d.]+)×([\d.]+)cm\)', description, re.IGNORECASE)
        if match:
            prog, name, width, height = match.groups()
            return f"=== מתחיל תוכנית {prog}: {name.strip()} (גודל בפועל: {width}×{height}ס״מ) ==="

    # Pattern: "=== Program X completed: ...)"
    if '=== program' in desc_lower and 'completed' in desc_lower:
        import re
        match = re.search(r'program (\d+) completed: ([\d.]+)×([\d.]+)cm', description, re.IGNORECASE)
        if match:
            prog, width, height = match.groups()
            return f"=== תוכנית {prog} הושלמה: נייר {width}×{height}ס״מ עובד ==="

    # If no translation found, return original
    return description

def create_step(operation, parameters=None, description=""):
    """Create a simple step dictionary with Hebrew UI fields"""
    params = parameters or {}

    # Generate Hebrew fields for UI display
    heb_operation_title = _generate_heb_operation_title(operation, params)
    heb_description = _translate_description_to_hebrew(description)

    return {
        'operation': operation,
        'parameters': params,
        'description': description,
        'hebOperationTitle': heb_operation_title,
        'hebDescription': heb_description
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
    
    Coordinates: Program coordinates are relative to paper position (loaded from settings)
    """
    steps = []

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
        "Init: Move rows motor to home position (X=0)"
    ))

    steps.append(create_step(
        'move_y',
        {'position': 0.0},
        "Init: Move lines motor to home position (Y=0)"
    ))

    # Init: Move Y motor to ACTUAL high position (paper_offset + actual_paper_height)
    # When moving UP, piston automatically lifts, but we show it explicitly in steps
    desk_y_position = PAPER_OFFSET_Y + actual_paper_height

    steps.append(create_step(
        'tool_action',
        {'tool': 'line_motor_piston', 'action': 'up'},
        f"⚠️ Lifting line motor piston UP (preparing for upward movement to {desk_y_position}cm)"
    ))

    steps.append(create_step(
        'move_y',
        {'position': desk_y_position},
        f"Init: Move Y motor to {desk_y_position}cm (paper + {actual_paper_height}cm ACTUAL high)"
    ))

    steps.append(create_step(
        'tool_action',
        {'tool': 'line_motor_piston', 'action': 'down'},
        "Line motor piston DOWN (Y motor assembly lowered to default position)"
    ))
    
    # Cut top edge workflow - LEFT sensor first, then RIGHT sensor
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_left', 'description': 'Wait for left lines sensor to start top cut'},
        "Cut top edge: Wait for left lines sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'down'},
        "Cut top edge: Open line cutter"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_right', 'description': 'Wait for right lines sensor to complete top cut'},
        "Cut top edge: Wait for right lines sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'up'},
        "Cut top edge: Close line cutter"
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
        
        # Move to first line of this section (skip if margin is 0 - coincides with edge cut)
        if section_num == 0 and program.top_padding != 0:
            steps.append(create_step(
                'move_y',
                {'position': first_line_y_section},
                f"Move to first line of section {section_num + 1}: {first_line_y_section}cm"
            ))

        # Mark all lines in this section
        for line_in_section in range(program.number_of_lines):
            overall_line_num = section_num * program.number_of_lines + line_in_section + 1
            line_y_position = first_line_y_section - (line_in_section * line_spacing_section)

            # Skip marking if line position coincides with a section edge cut (margin is 0)
            is_first_line = (line_in_section == 0)
            is_last_line = (line_in_section == program.number_of_lines - 1)
            skip_mark = (is_first_line and program.top_padding == 0) or \
                        (is_last_line and program.bottom_padding == 0 and program.number_of_lines > 1)
            if skip_mark:
                logger.debug(f"   Skipping line {overall_line_num} mark at {line_y_position:.1f}cm (coincides with section edge cut)", category="execution")
                continue

            line_description = f"Mark line {overall_line_num}/{program.number_of_lines * program.repeat_lines} (Section {section_num + 1}, Line {line_in_section + 1})"

            # Move to this line position (unless it's the first line of first section)
            if not (section_num == 0 and line_in_section == 0):
                steps.append(create_step(
                    'move_y',
                    {'position': line_y_position},
                    f"Move to line position: {line_y_position:.1f}cm"
                ))

            # Mark this line
            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'x_left', 'description': f'Wait for left lines sensor for line {overall_line_num}'},
                f"{line_description}: Wait for left lines sensor"
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'line_marker', 'action': 'down'},
                f"{line_description}: Open line marker"
            ))

            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'x_right', 'description': f'Wait for right lines sensor for line {overall_line_num}'},
                f"{line_description}: Wait for right lines sensor"
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'line_marker', 'action': 'up'},
                f"{line_description}: Close line marker"
            ))
        
        # ADD CUT BETWEEN SECTIONS (except after the last section)
        if section_num < program.repeat_lines - 1:  # Not the last section
            cut_position = section_end_y  # Cut at the bottom of current section (= top of next section)
            
            # Move to cut position between sections
            steps.append(create_step(
                'move_y',
                {'position': cut_position},
                f"Move to cut between sections {section_num + 1} and {section_num + 2}: {cut_position}cm"
            ))
            
            # Perform cut between sections
            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'x_left', 'description': f'Wait for left lines sensor for cut between sections {section_num + 1}-{section_num + 2}'},
                f"Cut between sections {section_num + 1} and {section_num + 2}: Wait for left lines sensor"
            ))
            
            steps.append(create_step(
                'tool_action',
                {'tool': 'line_cutter', 'action': 'down'},
                f"Cut between sections {section_num + 1} and {section_num + 2}: Open line cutter"
            ))
            
            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'x_right', 'description': f'Wait for right lines sensor for cut between sections {section_num + 1}-{section_num + 2}'},
                f"Cut between sections {section_num + 1} and {section_num + 2}: Wait for right lines sensor"
            ))
            
            steps.append(create_step(
                'tool_action',
                {'tool': 'line_cutter', 'action': 'up'},
                f"Cut between sections {section_num + 1} and {section_num + 2}: Close line cutter"
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
        {'sensor': 'x_left', 'description': 'Wait for left lines sensor to start bottom cut'},
        "Cut bottom edge: Wait for left lines sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'line_cutter', 'action': 'down'},
        "Cut bottom edge: Open line cutter"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'x_right', 'description': 'Wait for right lines sensor to complete bottom cut'},
        "Cut bottom edge: Wait for right lines sensor"
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
    
    Coordinates: Program coordinates are relative to paper position (loaded from settings)
    """
    steps = []

    # Note: Safety checks for rows operations happen during execution, not step generation

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
        {'sensor': 'y_top', 'description': 'Wait for top rows sensor for right paper cut'},
        "Cut RIGHT paper edge: Wait for top rows sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'down'},
        "Cut RIGHT paper edge: Open row cutter"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_bottom', 'description': 'Wait for bottom rows sensor for right paper cut'},
        "Cut RIGHT paper edge: Wait for bottom rows sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'up'},
        "Cut RIGHT paper edge: Close row cutter"
    ))
    
    # STEP 2: Mark pages BY SECTION (RIGHT-TO-LEFT), cutting between sections as we go
    # Process sections from RIGHTMOST to LEFTMOST (RTL order)
    logger.debug(f"PAGE MARKING BY SECTION (RTL):", category="execution")
    logger.debug(f"   Pages per section: {program.number_of_pages}", category="execution")
    logger.debug(f"   Repeated sections: {program.repeat_rows}", category="execution")

    # Process sections RIGHT-TO-LEFT: rightmost section first
    rows_start_move_done = False  # Track first positioning move for safety system
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

            page_description = f"Page {rtl_page_number}/{total_pages} (Section {section_num}, Page {rtl_page_in_section + 1}/{program.number_of_pages})"

            logger.debug(f"      RTL Page {rtl_page_number}: section_index={section_index}, rtl_page_in_section={rtl_page_in_section}, physical_page={physical_page_in_section}, position={page_left_edge:.1f}-{page_right_edge:.1f}cm", category="execution")

            # Check if page edges coincide with section boundary cuts (margin is 0 - no need to mark)
            is_rightmost_page = (physical_page_in_section == program.number_of_pages - 1)
            is_leftmost_page = (physical_page_in_section == 0)
            skip_right_mark = is_rightmost_page and program.right_margin == 0
            skip_left_mark = is_leftmost_page and program.left_margin == 0

            if skip_right_mark and skip_left_mark:
                logger.debug(f"      Skipping {page_description}: both edges coincide with cuts", category="execution")
                continue

            if not skip_right_mark:
                # Move to this page's RIGHT edge and mark it
                description_prefix = "Rows start: " if not rows_start_move_done else ""
                rows_start_move_done = True
                steps.append(create_step(
                    'move_x',
                    {'position': page_right_edge},
                    f"{description_prefix}Move to {page_description} RIGHT edge: {page_right_edge}cm"
                ))

                # Mark RIGHT edge of page
                steps.append(create_step(
                    'wait_sensor',
                    {'sensor': 'y_top', 'description': f'top rows sensor for {page_description} right edge'},
                    f"{page_description}: Wait top rows sensor (RIGHT edge)"
                ))

                steps.append(create_step(
                    'tool_action',
                    {'tool': 'row_marker', 'action': 'down'},
                    f"{page_description}: Open row marker (RIGHT edge)"
                ))

                steps.append(create_step(
                    'wait_sensor',
                    {'sensor': 'y_bottom', 'description': f'bottom rows sensor for {page_description} right edge'},
                    f"{page_description}: Wait bottom rows sensor (RIGHT edge)"
                ))

                steps.append(create_step(
                    'tool_action',
                    {'tool': 'row_marker', 'action': 'up'},
                    f"{page_description}: Close row marker (RIGHT edge)"
                ))

            if not skip_left_mark:
                # Move to this page's LEFT edge and mark it
                description_prefix = "Rows start: " if not rows_start_move_done else ""
                rows_start_move_done = True
                steps.append(create_step(
                    'move_x',
                    {'position': page_left_edge},
                    f"{description_prefix}Move to {page_description} LEFT edge: {page_left_edge}cm"
                ))

                # Mark LEFT edge of page
                steps.append(create_step(
                    'wait_sensor',
                    {'sensor': 'y_top', 'description': f'top rows sensor for {page_description} left edge'},
                    f"{page_description}: Wait top rows sensor (LEFT edge)"
                ))

                steps.append(create_step(
                    'tool_action',
                    {'tool': 'row_marker', 'action': 'down'},
                    f"{page_description}: Open row marker (LEFT edge)"
                ))

                steps.append(create_step(
                    'wait_sensor',
                    {'sensor': 'y_bottom', 'description': f'bottom rows sensor for {page_description} left edge'},
                    f"{page_description}: Wait bottom rows sensor (LEFT edge)"
                ))

                steps.append(create_step(
                    'tool_action',
                    {'tool': 'row_marker', 'action': 'up'},
                    f"{page_description}: Close row marker (LEFT edge)"
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
                f"Move to cut between row sections {section_num} and {section_num - 1}: {section_start_x}cm"
            ))

            # Perform cut between sections (vertical cut spanning full height)
            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'y_top', 'description': f'Wait for top rows sensor for cut between row sections {section_num}-{section_num - 1}'},
                f"Cut between row sections {section_num} and {section_num - 1}: Wait for top rows sensor"
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'row_cutter', 'action': 'down'},
                f"Cut between row sections {section_num} and {section_num - 1}: Open row cutter"
            ))

            steps.append(create_step(
                'wait_sensor',
                {'sensor': 'y_bottom', 'description': f'Wait for bottom rows sensor for cut between row sections {section_num}-{section_num - 1}'},
                f"Cut between row sections {section_num} and {section_num - 1}: Wait for bottom rows sensor"
            ))

            steps.append(create_step(
                'tool_action',
                {'tool': 'row_cutter', 'action': 'up'},
                f"Cut between row sections {section_num} and {section_num - 1}: Close row cutter"
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
        {'sensor': 'y_top', 'description': 'Wait for top rows sensor for left paper cut'},
        "Cut LEFT paper edge: Wait for top rows sensor"
    ))
    
    steps.append(create_step(
        'tool_action',
        {'tool': 'row_cutter', 'action': 'down'},
        "Cut LEFT paper edge: Open row cutter"
    ))
    
    steps.append(create_step(
        'wait_sensor',
        {'sensor': 'y_bottom', 'description': 'Wait for bottom rows sensor for left paper cut'},
        "Cut LEFT paper edge: Wait for bottom rows sensor"
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
#!/usr/bin/env python3

"""
Comprehensive tests for core/step_generator.py

Tests the step generation logic for lines marking, row marking, and complete program execution.
"""

import unittest
from core.program_model import ScratchDeskProgram
from core.step_generator import (
    create_step,
    generate_lines_marking_steps,
    generate_row_marking_steps,
    generate_complete_program_steps,
    get_step_count_summary,
    PAPER_OFFSET_X,
    PAPER_OFFSET_Y
)


class TestCreateStep(unittest.TestCase):
    """Tests for create_step function"""

    def test_step_has_required_keys(self):
        """All 5 keys present in step"""
        step = create_step('move_x', {'position': 10.0}, "Test description")
        required_keys = ['operation', 'parameters', 'description', 'hebOperationTitle', 'hebDescription']
        for key in required_keys:
            self.assertIn(key, step)

    def test_step_defaults(self):
        """Empty parameters dict, empty description"""
        step = create_step('move_x')
        self.assertEqual(step['parameters'], {})
        self.assertEqual(step['description'], "")

    def test_hebrew_title_generated(self):
        """Hebrew title populated for known operations like move_x"""
        step = create_step('move_x', {'position': 10.0})
        self.assertIsNotNone(step['hebOperationTitle'])
        self.assertNotEqual(step['hebOperationTitle'], "")
        self.assertIn('10.0', step['hebOperationTitle'])


class TestGenerateLinesMarkingSteps(unittest.TestCase):
    """Tests for generate_lines_marking_steps function"""

    def setUp(self):
        """Create valid test program"""
        self.program = ScratchDeskProgram(
            program_number=1,
            program_name="Test",
            high=10.0,
            number_of_lines=5,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=1
        )

    def test_basic_lines_generation(self):
        """Generates steps with init, edge cuts, line marks, return home"""
        steps = generate_lines_marking_steps(self.program)

        # Should have steps
        self.assertGreater(len(steps), 0)

        # Check for init moves
        self.assertEqual(steps[0]['operation'], 'move_x')
        self.assertEqual(steps[1]['operation'], 'move_y')

        # Check for edge cuts (top and bottom)
        wait_sensors = [s for s in steps if s['operation'] == 'wait_sensor']
        self.assertGreater(len(wait_sensors), 0)

        # Check for line marks
        tool_actions = [s for s in steps if s['operation'] == 'tool_action' and s['parameters'].get('tool') == 'line_marker']
        self.assertGreater(len(tool_actions), 0)

        # Check returns to home (lines ends with move_y back to 0)
        self.assertEqual(steps[-1]['operation'], 'move_y')
        self.assertEqual(steps[-1]['parameters']['position'], 0.0)

    def test_single_line_program(self):
        """1 line: produces correct steps"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Single Line",
            high=10.0,
            number_of_lines=1,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=1
        )

        steps = generate_lines_marking_steps(program)

        # Should have line marker actions
        line_markers = [s for s in steps if s['operation'] == 'tool_action' and
                       s['parameters'].get('tool') == 'line_marker']
        self.assertGreater(len(line_markers), 0)

        # Should have edge cuts
        line_cutters = [s for s in steps if s['operation'] == 'tool_action' and
                       s['parameters'].get('tool') == 'line_cutter']
        self.assertGreater(len(line_cutters), 0)

    def test_repeat_lines_creates_sections(self):
        """repeat_lines=2 creates 2 sections with inter-section cut"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Repeat Lines",
            high=10.0,
            number_of_lines=3,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=2
        )

        steps = generate_lines_marking_steps(program)

        # Check for section mentions in descriptions
        section_descriptions = [s['description'] for s in steps if 'section' in s['description'].lower()]
        self.assertGreater(len(section_descriptions), 0)

        # Should have cuts between sections
        cut_between = [s for s in steps if 'cut between sections' in s['description'].lower()]
        self.assertGreater(len(cut_between), 0)

    def test_repeat_lines_section_cuts(self):
        """N-1 cuts between N sections (check repeat_lines=3 has 2 cuts)"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Three Sections",
            high=10.0,
            number_of_lines=2,
            top_padding=1.0,
            bottom_padding=1.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=3
        )

        steps = generate_lines_marking_steps(program)

        # Count "cut between sections" occurrences
        cut_between_count = len([s for s in steps if 'cut between sections' in s['description'].lower() and
                                'open line cutter' in s['description'].lower()])

        # Should have 2 cuts between 3 sections
        self.assertEqual(cut_between_count, 2)

    def test_zero_top_padding_skips_first_mark(self):
        """top_padding=0 -> first line mark skipped"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Zero Top Padding",
            high=10.0,
            number_of_lines=3,
            top_padding=0.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=1
        )

        steps = generate_lines_marking_steps(program)

        # Count line marker actions
        line_marker_downs = [s for s in steps if s['operation'] == 'tool_action' and
                           s['parameters'].get('tool') == 'line_marker' and
                           s['parameters'].get('action') == 'down']

        # Should have 2 line marks (not 3) because first is skipped
        self.assertEqual(len(line_marker_downs), 2)

    def test_zero_bottom_padding_skips_last_mark(self):
        """bottom_padding=0 -> last line mark skipped (multi-line)"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Zero Bottom Padding",
            high=10.0,
            number_of_lines=3,
            top_padding=2.0,
            bottom_padding=0.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=1
        )

        steps = generate_lines_marking_steps(program)

        # Count line marker actions
        line_marker_downs = [s for s in steps if s['operation'] == 'tool_action' and
                           s['parameters'].get('tool') == 'line_marker' and
                           s['parameters'].get('action') == 'down']

        # Should have 2 line marks (not 3) because last is skipped
        self.assertEqual(len(line_marker_downs), 2)

    def test_paper_offset_applied(self):
        """Positions include PAPER_OFFSET_Y (15cm)"""
        steps = generate_lines_marking_steps(self.program)

        # Find Y movement steps
        y_moves = [s for s in steps if s['operation'] == 'move_y' and s['parameters']['position'] > 0]

        # At least one position should include paper offset
        self.assertTrue(any(s['parameters']['position'] >= PAPER_OFFSET_Y for s in y_moves))

    def test_init_steps_present(self):
        """First steps are move_x(0), move_y(0)"""
        steps = generate_lines_marking_steps(self.program)

        self.assertEqual(steps[0]['operation'], 'move_x')
        self.assertEqual(steps[0]['parameters']['position'], 0.0)
        self.assertEqual(steps[1]['operation'], 'move_y')
        self.assertEqual(steps[1]['parameters']['position'], 0.0)

    def test_returns_to_home(self):
        """Last step is move_y(0) — lines ends by returning Y motor to position 0"""
        steps = generate_lines_marking_steps(self.program)

        self.assertEqual(steps[-1]['operation'], 'move_y')
        self.assertEqual(steps[-1]['parameters']['position'], 0.0)

    def test_actual_height_calculation(self):
        """desk_y = PAPER_OFFSET_Y + (high * repeat_lines)"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Height Test",
            high=10.0,
            number_of_lines=2,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=2
        )

        steps = generate_lines_marking_steps(program)

        expected_desk_y = PAPER_OFFSET_Y + (program.high * program.repeat_lines)

        # Find the move to desk_y position
        desk_y_moves = [s for s in steps if s['operation'] == 'move_y' and
                       s['parameters']['position'] == expected_desk_y]

        self.assertGreater(len(desk_y_moves), 0)


class TestGenerateRowMarkingSteps(unittest.TestCase):
    """Tests for generate_row_marking_steps function"""

    def setUp(self):
        """Create valid test program"""
        self.program = ScratchDeskProgram(
            program_number=1,
            program_name="Test",
            high=10.0,
            number_of_lines=5,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=1
        )

    def test_basic_rows_generation(self):
        """Generates ensure_home, right cut, pages, left cut, return"""
        steps = generate_row_marking_steps(self.program)

        # Should have steps
        self.assertGreater(len(steps), 0)

        # First step should ensure Y at home
        self.assertEqual(steps[0]['operation'], 'move_y')
        self.assertEqual(steps[0]['parameters']['position'], 0.0)

        # Should have right paper edge cut
        right_cuts = [s for s in steps if 'right paper edge' in s['description'].lower()]
        self.assertGreater(len(right_cuts), 0)

        # Should have left paper edge cut
        left_cuts = [s for s in steps if 'left paper edge' in s['description'].lower()]
        self.assertGreater(len(left_cuts), 0)

        # Last step should return to home
        self.assertEqual(steps[-1]['operation'], 'move_x')
        self.assertEqual(steps[-1]['parameters']['position'], 0.0)

    def test_rtl_execution_order(self):
        """Rightmost page processed first"""
        steps = generate_row_marking_steps(self.program)

        # Find page descriptions
        page_steps = [s for s in steps if 'page 1/' in s['description'].lower()]

        # First page should have highest position (rightmost)
        if page_steps:
            first_page_moves = [s for s in page_steps if s['operation'] == 'move_x']
            if first_page_moves:
                first_page_x = first_page_moves[0]['parameters']['position']
                # Should be near the right side (greater than paper offset)
                self.assertGreater(first_page_x, PAPER_OFFSET_X)

    def test_single_page_single_section(self):
        """1 page: right cut, page marks, left cut"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Single Page",
            high=10.0,
            number_of_lines=3,
            top_padding=2.0,
            bottom_padding=2.0,
            width=18.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=1,
            buffer_between_pages=0.0,
            repeat_rows=1,
            repeat_lines=1
        )

        steps = generate_row_marking_steps(program)

        # Should have right paper edge cut
        right_cuts = [s for s in steps if 'right paper edge' in s['description'].lower() and
                     'open row cutter' in s['description'].lower()]
        self.assertEqual(len(right_cuts), 1)

        # Should have left paper edge cut
        left_cuts = [s for s in steps if 'left paper edge' in s['description'].lower() and
                    'open row cutter' in s['description'].lower()]
        self.assertEqual(len(left_cuts), 1)

    def test_repeat_rows_creates_sections(self):
        """repeat_rows=2 creates 2 sections with inter-section cut"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Repeat Rows",
            high=10.0,
            number_of_lines=3,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=2,
            repeat_lines=1
        )

        steps = generate_row_marking_steps(program)

        # Check for section mentions
        section_descriptions = [s['description'] for s in steps if 'section' in s['description'].lower()]
        self.assertGreater(len(section_descriptions), 0)

        # Should have cuts between sections
        cut_between = [s for s in steps if 'cut between row sections' in s['description'].lower()]
        self.assertGreater(len(cut_between), 0)

    def test_zero_margins_skip_marks(self):
        """left_margin=0, right_margin=0 -> skip edge marks"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Zero Margins",
            high=10.0,
            number_of_lines=3,
            top_padding=2.0,
            bottom_padding=2.0,
            width=8.0,
            left_margin=0.0,
            right_margin=0.0,
            page_width=8.0,
            number_of_pages=1,
            buffer_between_pages=0.0,
            repeat_rows=1,
            repeat_lines=1
        )

        steps = generate_row_marking_steps(program)

        # Count row marker actions
        row_marker_actions = [s for s in steps if s['operation'] == 'tool_action' and
                            s['parameters'].get('tool') == 'row_marker']

        # Should have no row marker actions because margins are 0
        self.assertEqual(len(row_marker_actions), 0)

    def test_paper_offset_x_applied(self):
        """Positions include PAPER_OFFSET_X (15cm)"""
        steps = generate_row_marking_steps(self.program)

        # Find X movement steps
        x_moves = [s for s in steps if s['operation'] == 'move_x' and s['parameters']['position'] > 0]

        # At least one position should include paper offset
        self.assertTrue(any(s['parameters']['position'] >= PAPER_OFFSET_X for s in x_moves))

    def test_rows_start_prefix(self):
        """First move_x has "Rows start:" prefix"""
        steps = generate_row_marking_steps(self.program)

        # Find first move_x with positive position
        move_x_steps = [s for s in steps if s['operation'] == 'move_x' and s['parameters']['position'] > 0]

        if move_x_steps:
            # One of the early move_x steps should have "Rows start:" prefix
            has_prefix = any('rows start:' in s['description'].lower() for s in move_x_steps[:5])
            self.assertTrue(has_prefix)

    def test_returns_to_home(self):
        """Last step is move_x(0)"""
        steps = generate_row_marking_steps(self.program)

        self.assertEqual(steps[-1]['operation'], 'move_x')
        self.assertEqual(steps[-1]['parameters']['position'], 0.0)

    def test_ensures_y_at_home(self):
        """First step ensures Y=0"""
        steps = generate_row_marking_steps(self.program)

        self.assertEqual(steps[0]['operation'], 'move_y')
        self.assertEqual(steps[0]['parameters']['position'], 0.0)


class TestGenerateCompleteProgramSteps(unittest.TestCase):
    """Tests for generate_complete_program_steps function"""

    def setUp(self):
        """Create valid test program"""
        self.program = ScratchDeskProgram(
            program_number=1,
            program_name="Test",
            high=10.0,
            number_of_lines=5,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=1
        )

    def test_complete_program_structure(self):
        """Has program_start, lines steps, rows steps, program_complete"""
        steps = generate_complete_program_steps(self.program)

        # Should have at least 4 steps (start, some lines, some rows, complete)
        self.assertGreater(len(steps), 4)

        # First step should be program_start
        self.assertEqual(steps[0]['operation'], 'program_start')

        # Last step should be program_complete
        self.assertEqual(steps[-1]['operation'], 'program_complete')

        # Should have lines operations
        has_lines = any(s['operation'] == 'tool_action' and
                       s['parameters'].get('tool') == 'line_marker' for s in steps)
        self.assertTrue(has_lines)

        # Should have rows operations
        has_rows = any(s['operation'] == 'tool_action' and
                      s['parameters'].get('tool') == 'row_marker' for s in steps)
        self.assertTrue(has_rows)

    def test_program_start_has_metadata(self):
        """Contains program_number, actual dimensions"""
        steps = generate_complete_program_steps(self.program)

        start_step = steps[0]
        self.assertEqual(start_step['operation'], 'program_start')
        self.assertIn('program_number', start_step['parameters'])
        self.assertIn('actual_width', start_step['parameters'])
        self.assertIn('actual_height', start_step['parameters'])
        self.assertIn('repeat_rows', start_step['parameters'])
        self.assertIn('repeat_lines', start_step['parameters'])

    def test_program_complete_has_metadata(self):
        """Contains total_repeats, actual dimensions"""
        steps = generate_complete_program_steps(self.program)

        complete_step = steps[-1]
        self.assertEqual(complete_step['operation'], 'program_complete')
        self.assertIn('program_number', complete_step['parameters'])
        self.assertIn('total_repeats', complete_step['parameters'])
        self.assertIn('actual_width', complete_step['parameters'])
        self.assertIn('actual_height', complete_step['parameters'])


class TestGetStepCountSummary(unittest.TestCase):
    """Tests for get_step_count_summary function"""

    def setUp(self):
        """Create valid test program"""
        self.program = ScratchDeskProgram(
            program_number=1,
            program_name="Test",
            high=10.0,
            number_of_lines=5,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=1
        )

    def test_summary_fields(self):
        """Returns all expected keys"""
        summary = get_step_count_summary(self.program)

        expected_keys = [
            'lines_steps',
            'row_steps',
            'total_steps',
            'total_repeats',
            'actual_paper_width',
            'actual_paper_height',
            'total_lines_marked',
            'total_pages_marked'
        ]

        for key in expected_keys:
            self.assertIn(key, summary)

    def test_total_lines_with_repeats(self):
        """number_of_lines * repeat_lines"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Lines Repeat Test",
            high=10.0,
            number_of_lines=3,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=1,
            repeat_lines=2
        )

        summary = get_step_count_summary(program)

        expected_total_lines = program.number_of_lines * program.repeat_lines
        self.assertEqual(summary['total_lines_marked'], expected_total_lines)

    def test_total_pages_with_repeats(self):
        """number_of_pages * repeat_rows"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Pages Repeat Test",
            high=10.0,
            number_of_lines=3,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=2,
            repeat_lines=1
        )

        summary = get_step_count_summary(program)

        expected_total_pages = program.number_of_pages * program.repeat_rows
        self.assertEqual(summary['total_pages_marked'], expected_total_pages)

    def test_actual_dimensions(self):
        """width * repeat_rows, high * repeat_lines"""
        program = ScratchDeskProgram(
            program_number=1,
            program_name="Dimensions Test",
            high=10.0,
            number_of_lines=3,
            top_padding=2.0,
            bottom_padding=2.0,
            width=48.0,
            left_margin=5.0,
            right_margin=5.0,
            page_width=8.0,
            number_of_pages=4,
            buffer_between_pages=2.0,
            repeat_rows=2,
            repeat_lines=3
        )

        summary = get_step_count_summary(program)

        expected_width = program.width * program.repeat_rows
        expected_height = program.high * program.repeat_lines

        self.assertEqual(summary['actual_paper_width'], expected_width)
        self.assertEqual(summary['actual_paper_height'], expected_height)


if __name__ == '__main__':
    unittest.main()

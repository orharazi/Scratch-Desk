#!/usr/bin/env python3

"""
Comprehensive margin validation tests for step_generator.py

Validates that ALL programs from sample_programs.csv produce step positions
that exactly match the expected margins from the program definition.

Tests both:
- Row operations (X-axis): left_margin, right_margin, page_width, buffer_between_pages
- Line operations (Y-axis): top_padding, bottom_padding, line spacing
"""

import os
import unittest
from core.program_model import ScratchDeskProgram
from core.csv_parser import CSVParser
from core.step_generator import (
    generate_row_marking_steps,
    generate_lines_marking_steps,
    generate_complete_program_steps,
    PAPER_OFFSET_X,
    PAPER_OFFSET_Y,
)

TOLERANCE = 0.001  # floating point tolerance in cm


def _load_all_csv_programs():
    """Load all valid programs from sample_programs.csv"""
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sample_programs.csv')
    parser = CSVParser()
    programs, errors = parser.load_programs_from_csv(csv_path)
    return programs


def _extract_move_x_steps(steps):
    """Return list of (position, description) for all move_x steps"""
    return [
        (s['parameters']['position'], s['description'])
        for s in steps if s['operation'] == 'move_x'
    ]


def _extract_move_y_steps(steps):
    """Return list of (position, description) for all move_y steps"""
    return [
        (s['parameters']['position'], s['description'])
        for s in steps if s['operation'] == 'move_y'
    ]


def _extract_page_edge_marks(steps):
    """
    Extract all page edge mark positions from row marking steps.
    Returns list of dicts with: position, edge ('left'/'right'), description
    """
    marks = []
    for s in steps:
        if s['operation'] != 'move_x':
            continue
        desc = s['description'].lower()
        pos = s['parameters']['position']
        if 'right edge' in desc:
            marks.append({'position': pos, 'edge': 'right', 'description': s['description']})
        elif 'left edge' in desc:
            marks.append({'position': pos, 'edge': 'left', 'description': s['description']})
    return marks


def _extract_cut_positions(steps):
    """
    Extract paper cut positions (not section boundary cuts).
    Returns dict with 'right_paper_cut' and 'left_paper_cut'.
    """
    cuts = {}
    for s in steps:
        if s['operation'] != 'move_x':
            continue
        desc = s['description'].lower()
        pos = s['parameters']['position']
        if 'cut right paper edge' in desc:
            cuts['right_paper_cut'] = pos
        elif 'cut left paper edge' in desc:
            cuts['left_paper_cut'] = pos
    return cuts


def _extract_section_cuts(steps):
    """Extract between-section cut positions."""
    cuts = []
    for s in steps:
        if s['operation'] != 'move_x':
            continue
        desc = s['description'].lower()
        pos = s['parameters']['position']
        if 'cut between row sections' in desc:
            cuts.append(pos)
    return cuts


def _extract_line_positions(steps):
    """
    Extract all line mark Y positions from lines marking steps.
    Returns list of floats (Y positions).
    """
    positions = []
    for s in steps:
        if s['operation'] != 'move_y':
            continue
        desc = s['description'].lower()
        pos = s['parameters']['position']
        if 'move to line position' in desc or 'move to first line' in desc:
            positions.append(pos)
    return positions


def _extract_line_cut_positions(steps):
    """
    Extract all line cut Y positions (top, bottom, between-section).
    Returns dict with 'top_cut', 'bottom_cut', and 'section_cuts' list.
    """
    result = {'section_cuts': []}
    for s in steps:
        if s['operation'] != 'move_y':
            continue
        desc = s['description'].lower()
        pos = s['parameters']['position']
        if 'cut between sections' in desc:
            result['section_cuts'].append(pos)
    # Top cut is at the initial Y position (paper_offset + actual_height)
    # Bottom cut is at PAPER_OFFSET_Y
    return result


class TestRowMarginsAllCSVPrograms(unittest.TestCase):
    """
    For EVERY program in sample_programs.csv, verify that the generated
    row marking steps produce positions that match the program's margin values.
    """

    @classmethod
    def setUpClass(cls):
        cls.programs = _load_all_csv_programs()
        assert len(cls.programs) > 0, "No programs loaded from CSV"

    def test_all_programs_loaded(self):
        """Sanity: CSV loads without errors"""
        self.assertGreater(len(self.programs), 0)

    def test_paper_cut_positions_all_programs(self):
        """Paper boundary cuts are at PAPER_OFFSET_X and PAPER_OFFSET_X + actual_width"""
        for p in self.programs:
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_row_marking_steps(p)
                cuts = _extract_cut_positions(steps)
                actual_width = p.width * p.repeat_rows

                self.assertAlmostEqual(
                    cuts['left_paper_cut'], PAPER_OFFSET_X, places=3,
                    msg=f"Left paper cut should be at PAPER_OFFSET_X={PAPER_OFFSET_X}"
                )
                self.assertAlmostEqual(
                    cuts['right_paper_cut'], PAPER_OFFSET_X + actual_width, places=3,
                    msg=f"Right paper cut should be at {PAPER_OFFSET_X + actual_width}"
                )

    def test_section_cut_positions_all_programs(self):
        """Between-section cuts are at correct section boundaries"""
        for p in self.programs:
            if p.repeat_rows <= 1:
                continue
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_row_marking_steps(p)
                section_cuts = _extract_section_cuts(steps)

                expected_cuts = []
                # Sections are processed RTL; cuts happen at left boundary of each non-leftmost section
                for rtl_idx in range(p.repeat_rows - 1):
                    section_index = p.repeat_rows - 1 - rtl_idx
                    cut_pos = PAPER_OFFSET_X + section_index * p.width
                    expected_cuts.append(cut_pos)

                self.assertEqual(
                    len(section_cuts), len(expected_cuts),
                    msg=f"Expected {len(expected_cuts)} section cuts, got {len(section_cuts)}"
                )
                for actual, expected in zip(sorted(section_cuts), sorted(expected_cuts)):
                    self.assertAlmostEqual(actual, expected, places=3)

    def test_left_margin_all_programs(self):
        """
        Left margin: the leftmost page's left edge in each section must be
        exactly left_margin away from the section's left boundary.
        """
        for p in self.programs:
            if p.left_margin == 0:
                continue  # skip_left_mark applies, no mark generated
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_row_marking_steps(p)
                marks = _extract_page_edge_marks(steps)

                # Group marks by section
                for section_index in range(p.repeat_rows):
                    section_start = PAPER_OFFSET_X + section_index * p.width

                    # The leftmost page's left edge in this section
                    expected_left_edge = section_start + p.left_margin

                    # Find left-edge marks in this section (within section boundaries)
                    section_end = section_start + p.width
                    section_left_marks = [
                        m for m in marks
                        if m['edge'] == 'left'
                        and section_start - TOLERANCE <= m['position'] <= section_end + TOLERANCE
                    ]

                    # The smallest left-edge position in this section = leftmost page left edge
                    if section_left_marks:
                        leftmost_mark = min(m['position'] for m in section_left_marks)
                        actual_left_margin = leftmost_mark - section_start
                        self.assertAlmostEqual(
                            actual_left_margin, p.left_margin, places=3,
                            msg=(f"Program {p.program_number} '{p.program_name}' section {section_index}: "
                                 f"LEFT margin = {actual_left_margin:.4f}, expected {p.left_margin}")
                        )

    def test_right_margin_all_programs(self):
        """
        Right margin: the rightmost page's right edge in each section must be
        exactly right_margin away from the section's right boundary.
        """
        for p in self.programs:
            if p.right_margin == 0:
                continue  # skip_right_mark applies, no mark generated
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_row_marking_steps(p)
                marks = _extract_page_edge_marks(steps)

                for section_index in range(p.repeat_rows):
                    section_start = PAPER_OFFSET_X + section_index * p.width
                    section_end = section_start + p.width

                    expected_right_edge = section_end - p.right_margin

                    # Find right-edge marks in this section
                    section_right_marks = [
                        m for m in marks
                        if m['edge'] == 'right'
                        and section_start - TOLERANCE <= m['position'] <= section_end + TOLERANCE
                    ]

                    if section_right_marks:
                        rightmost_mark = max(m['position'] for m in section_right_marks)
                        actual_right_margin = section_end - rightmost_mark
                        self.assertAlmostEqual(
                            actual_right_margin, p.right_margin, places=3,
                            msg=(f"Program {p.program_number} '{p.program_name}' section {section_index}: "
                                 f"RIGHT margin = {actual_right_margin:.4f}, expected {p.right_margin}")
                        )

    def test_page_width_all_programs(self):
        """
        For every page, right_edge - left_edge must equal page_width.
        """
        for p in self.programs:
            if p.left_margin == 0 and p.right_margin == 0:
                continue  # no marks generated
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_row_marking_steps(p)
                marks = _extract_page_edge_marks(steps)

                # Group marks: consecutive right-edge then left-edge form a page
                # Step generator emits: right edge, left edge for each page (RTL order)
                i = 0
                while i < len(marks) - 1:
                    if marks[i]['edge'] == 'right' and marks[i + 1]['edge'] == 'left':
                        right_pos = marks[i]['position']
                        left_pos = marks[i + 1]['position']
                        actual_page_width = right_pos - left_pos
                        self.assertAlmostEqual(
                            actual_page_width, p.page_width, places=3,
                            msg=(f"Program {p.program_number}: page width from marks "
                                 f"({right_pos} - {left_pos} = {actual_page_width}) != {p.page_width}")
                        )
                        i += 2
                    else:
                        i += 1

    def test_buffer_between_pages_all_programs(self):
        """
        For multi-page sections, the gap between adjacent pages must equal buffer_between_pages.
        """
        for p in self.programs:
            if p.number_of_pages <= 1:
                continue
            if p.left_margin == 0 and p.right_margin == 0:
                continue
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_row_marking_steps(p)
                marks = _extract_page_edge_marks(steps)

                for section_index in range(p.repeat_rows):
                    section_start = PAPER_OFFSET_X + section_index * p.width
                    section_end = section_start + p.width

                    # Collect all page edges in this section, sorted by position
                    section_marks = sorted(
                        [m for m in marks
                         if section_start - TOLERANCE <= m['position'] <= section_end + TOLERANCE],
                        key=lambda m: m['position']
                    )

                    # Extract page boundaries: pairs of (left_edge, right_edge) sorted by position
                    pages = []
                    left_edges = sorted(m['position'] for m in section_marks if m['edge'] == 'left')
                    right_edges = sorted(m['position'] for m in section_marks if m['edge'] == 'right')

                    # Match left and right edges into pages
                    for le in left_edges:
                        # Find the right edge that is page_width away
                        for re in right_edges:
                            if abs((re - le) - p.page_width) < TOLERANCE:
                                pages.append((le, re))
                                break

                    pages.sort(key=lambda x: x[0])

                    # Check buffer between consecutive pages
                    for j in range(len(pages) - 1):
                        gap = pages[j + 1][0] - pages[j][1]
                        self.assertAlmostEqual(
                            gap, p.buffer_between_pages, places=3,
                            msg=(f"Program {p.program_number} section {section_index}: "
                                 f"buffer between pages {j} and {j+1} = {gap}, "
                                 f"expected {p.buffer_between_pages}")
                        )

    def test_total_mark_count_all_programs(self):
        """
        Each section with non-zero margins should have exactly
        2 * number_of_pages edge marks (one left + one right per page),
        minus any skipped edges where margin is 0.
        """
        for p in self.programs:
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_row_marking_steps(p)
                marks = _extract_page_edge_marks(steps)

                # Calculate expected marks per section
                expected_per_section = p.number_of_pages * 2
                if p.right_margin == 0:
                    expected_per_section -= 1  # rightmost page right edge skipped
                if p.left_margin == 0:
                    expected_per_section -= 1  # leftmost page left edge skipped

                # If both are 0 for a single-page section, both marks are skipped
                if p.number_of_pages == 1 and p.left_margin == 0 and p.right_margin == 0:
                    expected_per_section = 0

                expected_total = expected_per_section * p.repeat_rows
                self.assertEqual(
                    len(marks), expected_total,
                    msg=(f"Program {p.program_number} '{p.program_name}': "
                         f"expected {expected_total} marks ({expected_per_section}/section x {p.repeat_rows} sections), "
                         f"got {len(marks)}")
                )


class TestLineMarginsAllCSVPrograms(unittest.TestCase):
    """
    For EVERY program in sample_programs.csv, verify that the generated
    line marking steps produce Y positions matching top_padding and bottom_padding.
    """

    @classmethod
    def setUpClass(cls):
        cls.programs = _load_all_csv_programs()

    def test_top_padding_all_programs(self):
        """
        First line in each section must be top_padding below the section top boundary.
        """
        for p in self.programs:
            if p.top_padding == 0:
                continue
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_lines_marking_steps(p)
                line_positions = _extract_line_positions(steps)

                if not line_positions:
                    continue

                for section_num in range(p.repeat_lines):
                    section_top = PAPER_OFFSET_Y + (p.repeat_lines - section_num) * p.high

                    expected_first_line = section_top - p.top_padding

                    # Find the highest Y position in this section range
                    section_bottom = PAPER_OFFSET_Y + (p.repeat_lines - section_num - 1) * p.high
                    section_lines = [
                        y for y in line_positions
                        if section_bottom - TOLERANCE <= y <= section_top + TOLERANCE
                    ]

                    if section_lines:
                        actual_first_line = max(section_lines)  # highest Y = topmost line
                        actual_top_padding = section_top - actual_first_line
                        self.assertAlmostEqual(
                            actual_top_padding, p.top_padding, places=3,
                            msg=(f"Program {p.program_number} section {section_num}: "
                                 f"top_padding = {actual_top_padding:.4f}, expected {p.top_padding}")
                        )

    def test_bottom_padding_all_programs(self):
        """
        Last line in each section must be bottom_padding above the section bottom boundary.
        """
        for p in self.programs:
            if p.bottom_padding == 0 or p.number_of_lines <= 1:
                continue
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_lines_marking_steps(p)
                line_positions = _extract_line_positions(steps)

                if not line_positions:
                    continue

                for section_num in range(p.repeat_lines):
                    section_top = PAPER_OFFSET_Y + (p.repeat_lines - section_num) * p.high
                    section_bottom = PAPER_OFFSET_Y + (p.repeat_lines - section_num - 1) * p.high

                    section_lines = [
                        y for y in line_positions
                        if section_bottom - TOLERANCE <= y <= section_top + TOLERANCE
                    ]

                    if section_lines:
                        actual_last_line = min(section_lines)  # lowest Y = bottommost line
                        actual_bottom_padding = actual_last_line - section_bottom
                        self.assertAlmostEqual(
                            actual_bottom_padding, p.bottom_padding, places=3,
                            msg=(f"Program {p.program_number} section {section_num}: "
                                 f"bottom_padding = {actual_bottom_padding:.4f}, expected {p.bottom_padding}")
                        )

    def test_line_count_per_section_all_programs(self):
        """Each section must have exactly number_of_lines line positions."""
        for p in self.programs:
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_lines_marking_steps(p)
                line_positions = _extract_line_positions(steps)

                # Adjust for skipped lines (top_padding=0 or bottom_padding=0)
                expected_per_section = p.number_of_lines
                if p.top_padding == 0:
                    expected_per_section -= 1
                if p.bottom_padding == 0 and p.number_of_lines > 1:
                    expected_per_section -= 1

                expected_total = expected_per_section * p.repeat_lines
                self.assertEqual(
                    len(line_positions), expected_total,
                    msg=(f"Program {p.program_number}: expected {expected_total} lines "
                         f"({expected_per_section}/section x {p.repeat_lines} sections), "
                         f"got {len(line_positions)}")
                )

    def test_line_spacing_uniform_all_programs(self):
        """Lines within each section must be uniformly spaced."""
        for p in self.programs:
            if p.number_of_lines <= 2:
                continue
            with self.subTest(program=f"{p.program_number} {p.program_name}"):
                steps = generate_lines_marking_steps(p)
                line_positions = _extract_line_positions(steps)

                for section_num in range(p.repeat_lines):
                    section_top = PAPER_OFFSET_Y + (p.repeat_lines - section_num) * p.high
                    section_bottom = PAPER_OFFSET_Y + (p.repeat_lines - section_num - 1) * p.high

                    section_lines = sorted([
                        y for y in line_positions
                        if section_bottom - TOLERANCE <= y <= section_top + TOLERANCE
                    ], reverse=True)  # descending: top to bottom

                    if len(section_lines) < 3:
                        continue

                    # All spacings should be equal
                    spacings = [section_lines[i] - section_lines[i + 1]
                                for i in range(len(section_lines) - 1)]
                    for i, spacing in enumerate(spacings):
                        self.assertAlmostEqual(
                            spacing, spacings[0], places=3,
                            msg=(f"Program {p.program_number} section {section_num}: "
                                 f"spacing[{i}]={spacing:.4f} != spacing[0]={spacings[0]:.4f}")
                        )


class TestMezuza12Detailed(unittest.TestCase):
    """
    Detailed test for מזוזה 12 (program 9) - the specific program the user reported issues with.

    This program has:
    - Different left/right margins: left_margin=0.4, right_margin=0.7
    - repeat_rows=2 (two sections side by side)
    - repeat_lines=2 (two sections stacked)
    """

    def setUp(self):
        self.program = ScratchDeskProgram(
            program_number=9,
            program_name="מזוזה 12",
            high=11.8,
            number_of_lines=22,
            top_padding=0.8,
            bottom_padding=0.5,
            width=12.5,
            left_margin=0.4,
            right_margin=0.7,
            page_width=11.4,
            number_of_pages=1,
            buffer_between_pages=0.0,
            repeat_rows=2,
            repeat_lines=2
        )

    def test_program_validates(self):
        """מזוזה 12 must pass validation"""
        errors = self.program.validate()
        self.assertEqual(errors, [], msg=f"Validation errors: {errors}")

    def test_width_formula(self):
        """width == left_margin + right_margin + page_width * pages + buffer * (pages-1)"""
        p = self.program
        expected = p.left_margin + p.right_margin + (p.page_width * p.number_of_pages) + (p.buffer_between_pages * (p.number_of_pages - 1))
        self.assertAlmostEqual(p.width, expected, places=3)

    def test_section_0_left_margin(self):
        """Section 0 (leftmost): left margin = 0.4cm"""
        p = self.program
        steps = generate_row_marking_steps(p)
        marks = _extract_page_edge_marks(steps)

        section_start = PAPER_OFFSET_X
        section_end = PAPER_OFFSET_X + p.width

        left_marks_in_section = [
            m for m in marks
            if m['edge'] == 'left'
            and section_start - TOLERANCE <= m['position'] <= section_end + TOLERANCE
        ]
        self.assertEqual(len(left_marks_in_section), 1, "Should have exactly 1 left-edge mark in section 0")

        actual_margin = left_marks_in_section[0]['position'] - section_start
        self.assertAlmostEqual(actual_margin, 0.4, places=3,
                               msg=f"Section 0 LEFT margin: {actual_margin} != 0.4")

    def test_section_0_right_margin(self):
        """Section 0 (leftmost): right margin = 0.7cm"""
        p = self.program
        steps = generate_row_marking_steps(p)
        marks = _extract_page_edge_marks(steps)

        section_start = PAPER_OFFSET_X
        section_end = PAPER_OFFSET_X + p.width

        right_marks_in_section = [
            m for m in marks
            if m['edge'] == 'right'
            and section_start - TOLERANCE <= m['position'] <= section_end + TOLERANCE
        ]
        self.assertEqual(len(right_marks_in_section), 1, "Should have exactly 1 right-edge mark in section 0")

        actual_margin = section_end - right_marks_in_section[0]['position']
        self.assertAlmostEqual(actual_margin, 0.7, places=3,
                               msg=f"Section 0 RIGHT margin: {actual_margin} != 0.7")

    def test_section_1_left_margin(self):
        """Section 1 (rightmost): left margin = 0.4cm"""
        p = self.program
        steps = generate_row_marking_steps(p)
        marks = _extract_page_edge_marks(steps)

        section_start = PAPER_OFFSET_X + p.width
        section_end = PAPER_OFFSET_X + 2 * p.width

        left_marks_in_section = [
            m for m in marks
            if m['edge'] == 'left'
            and section_start - TOLERANCE <= m['position'] <= section_end + TOLERANCE
        ]
        self.assertEqual(len(left_marks_in_section), 1, "Should have exactly 1 left-edge mark in section 1")

        actual_margin = left_marks_in_section[0]['position'] - section_start
        self.assertAlmostEqual(actual_margin, 0.4, places=3,
                               msg=f"Section 1 LEFT margin: {actual_margin} != 0.4")

    def test_section_1_right_margin(self):
        """Section 1 (rightmost): right margin = 0.7cm"""
        p = self.program
        steps = generate_row_marking_steps(p)
        marks = _extract_page_edge_marks(steps)

        section_start = PAPER_OFFSET_X + p.width
        section_end = PAPER_OFFSET_X + 2 * p.width

        right_marks_in_section = [
            m for m in marks
            if m['edge'] == 'right'
            and section_start - TOLERANCE <= m['position'] <= section_end + TOLERANCE
        ]
        self.assertEqual(len(right_marks_in_section), 1, "Should have exactly 1 right-edge mark in section 1")

        actual_margin = section_end - right_marks_in_section[0]['position']
        self.assertAlmostEqual(actual_margin, 0.7, places=3,
                               msg=f"Section 1 RIGHT margin: {actual_margin} != 0.7")

    def test_margins_differ(self):
        """Left and right margins must NOT be equal"""
        self.assertNotAlmostEqual(self.program.left_margin, self.program.right_margin,
                                  msg="Test only makes sense if margins are different")

    def test_right_margin_not_equal_to_left(self):
        """
        THE CORE USER BUG: Verify the right margin gap is NOT equal to left margin gap.
        This tests the specific issue reported by the user.
        """
        p = self.program
        steps = generate_row_marking_steps(p)
        marks = _extract_page_edge_marks(steps)

        for section_index in range(p.repeat_rows):
            section_start = PAPER_OFFSET_X + section_index * p.width
            section_end = section_start + p.width

            left_marks = [m for m in marks if m['edge'] == 'left'
                          and section_start - TOLERANCE <= m['position'] <= section_end + TOLERANCE]
            right_marks = [m for m in marks if m['edge'] == 'right'
                           and section_start - TOLERANCE <= m['position'] <= section_end + TOLERANCE]

            if left_marks and right_marks:
                left_margin_actual = min(m['position'] for m in left_marks) - section_start
                right_margin_actual = section_end - max(m['position'] for m in right_marks)

                # The actual left margin must equal program.left_margin
                self.assertAlmostEqual(left_margin_actual, p.left_margin, places=3,
                                       msg=f"Section {section_index}: left margin wrong")
                # The actual right margin must equal program.right_margin
                self.assertAlmostEqual(right_margin_actual, p.right_margin, places=3,
                                       msg=f"Section {section_index}: right margin wrong")
                # They must NOT be equal (the reported bug)
                self.assertNotAlmostEqual(
                    left_margin_actual, right_margin_actual, places=3,
                    msg=f"Section {section_index}: right margin ({right_margin_actual}) "
                        f"equals left margin ({left_margin_actual}) - THIS IS THE BUG"
                )

    def test_section_boundary_cut_position(self):
        """Between-section cut must be at PAPER_OFFSET_X + width (boundary of section 0 and 1)"""
        p = self.program
        steps = generate_row_marking_steps(p)
        section_cuts = _extract_section_cuts(steps)

        self.assertEqual(len(section_cuts), 1, "Should have exactly 1 between-section cut")
        expected_cut = PAPER_OFFSET_X + p.width
        self.assertAlmostEqual(section_cuts[0], expected_cut, places=3)

    def test_full_position_trace(self):
        """
        Print complete position trace for debugging - also verify all positions.
        """
        p = self.program
        steps = generate_row_marking_steps(p)

        all_x_moves = _extract_move_x_steps(steps)

        # Build expected positions
        actual_width = p.width * p.repeat_rows
        expected_positions = {
            'right_paper_cut': PAPER_OFFSET_X + actual_width,
            'left_paper_cut': PAPER_OFFSET_X,
            'home': 0.0,
        }

        # Section 1 (rightmost, processed first in RTL)
        s1_start = PAPER_OFFSET_X + p.width
        expected_positions['s1_page_right'] = s1_start + p.left_margin + p.page_width
        expected_positions['s1_page_left'] = s1_start + p.left_margin

        # Section boundary cut
        expected_positions['section_cut'] = PAPER_OFFSET_X + p.width

        # Section 0 (leftmost, processed second in RTL)
        s0_start = PAPER_OFFSET_X
        expected_positions['s0_page_right'] = s0_start + p.left_margin + p.page_width
        expected_positions['s0_page_left'] = s0_start + p.left_margin

        # Verify expected execution order
        expected_order = [
            ('right_paper_cut', PAPER_OFFSET_X + actual_width),
            ('s1_page_right', s1_start + p.left_margin + p.page_width),
            ('s1_page_left', s1_start + p.left_margin),
            ('section_cut', PAPER_OFFSET_X + p.width),
            ('s0_page_right', s0_start + p.left_margin + p.page_width),
            ('s0_page_left', s0_start + p.left_margin),
            ('left_paper_cut', PAPER_OFFSET_X),
            ('home', 0.0),
        ]

        # Verify we have the right number of move_x steps
        # move_y(0) + right_cut + s1_right + s1_left + section_cut + s0_right + s0_left + left_cut + home
        # But move_y is not move_x, so: right_cut + s1_right + s1_left + section_cut + s0_right + s0_left + left_cut + home = 8
        self.assertEqual(len(all_x_moves), len(expected_order),
                         msg=f"Expected {len(expected_order)} move_x steps, got {len(all_x_moves)}")

        for i, (name, expected_pos) in enumerate(expected_order):
            actual_pos = all_x_moves[i][0]
            self.assertAlmostEqual(
                actual_pos, expected_pos, places=3,
                msg=f"Step {i} ({name}): position {actual_pos} != expected {expected_pos}"
            )

    def test_lines_top_padding_both_sections(self):
        """Top padding in both line sections must be 0.8cm"""
        p = self.program
        steps = generate_lines_marking_steps(p)
        line_positions = _extract_line_positions(steps)

        for section_num in range(p.repeat_lines):
            section_top = PAPER_OFFSET_Y + (p.repeat_lines - section_num) * p.high
            section_bottom = PAPER_OFFSET_Y + (p.repeat_lines - section_num - 1) * p.high

            section_lines = [y for y in line_positions
                             if section_bottom - TOLERANCE <= y <= section_top + TOLERANCE]
            if section_lines:
                topmost = max(section_lines)
                actual_top_padding = section_top - topmost
                self.assertAlmostEqual(
                    actual_top_padding, p.top_padding, places=3,
                    msg=f"Lines section {section_num}: top_padding={actual_top_padding}, expected {p.top_padding}"
                )

    def test_lines_bottom_padding_both_sections(self):
        """Bottom padding in both line sections must be 0.5cm"""
        p = self.program
        steps = generate_lines_marking_steps(p)
        line_positions = _extract_line_positions(steps)

        for section_num in range(p.repeat_lines):
            section_top = PAPER_OFFSET_Y + (p.repeat_lines - section_num) * p.high
            section_bottom = PAPER_OFFSET_Y + (p.repeat_lines - section_num - 1) * p.high

            section_lines = [y for y in line_positions
                             if section_bottom - TOLERANCE <= y <= section_top + TOLERANCE]
            if section_lines:
                bottommost = min(section_lines)
                actual_bottom_padding = bottommost - section_bottom
                self.assertAlmostEqual(
                    actual_bottom_padding, p.bottom_padding, places=3,
                    msg=f"Lines section {section_num}: bottom_padding={actual_bottom_padding}, expected {p.bottom_padding}"
                )


if __name__ == '__main__':
    unittest.main(verbosity=2)

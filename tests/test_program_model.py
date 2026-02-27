"""
Comprehensive tests for the ScratchDeskProgram class.

Tests cover:
- Construction (defaults, all params, type conversions)
- Validation (width formula, desk size, values, padding, line spacing)
- is_valid()
- get_total_desk_dimensions()
- __str__ and __repr__
- translate_validation_error()
"""

import pytest
from core.program_model import ScratchDeskProgram, translate_validation_error


# ============================================================================
# Construction Tests
# ============================================================================

def test_construction_defaults():
    """Test construction with default values."""
    prog = ScratchDeskProgram()
    assert prog.program_number == 0
    assert prog.program_name == ""
    assert prog.high == 0.0
    assert prog.number_of_lines == 0
    assert prog.top_padding == 0.0
    assert prog.bottom_padding == 0.0
    assert prog.width == 0.0
    assert prog.left_margin == 0.0
    assert prog.right_margin == 0.0
    assert prog.page_width == 0.0
    assert prog.number_of_pages == 1
    assert prog.buffer_between_pages == 0.0
    assert prog.repeat_rows == 1
    assert prog.repeat_lines == 1


def test_construction_all_params():
    """Test construction with all parameters specified."""
    prog = ScratchDeskProgram(
        program_number=5,
        program_name="Test Program",
        high=10.0,
        number_of_lines=5,
        top_padding=1.0,
        bottom_padding=1.5,
        width=20.0,
        left_margin=2.0,
        right_margin=3.0,
        page_width=15.0,
        number_of_pages=3,
        buffer_between_pages=0.5,
        repeat_rows=2,
        repeat_lines=3
    )
    assert prog.program_number == 5
    assert prog.program_name == "Test Program"
    assert prog.high == 10.0
    assert prog.number_of_lines == 5
    assert prog.top_padding == 1.0
    assert prog.bottom_padding == 1.5
    assert prog.width == 20.0
    assert prog.left_margin == 2.0
    assert prog.right_margin == 3.0
    assert prog.page_width == 15.0
    assert prog.number_of_pages == 3
    assert prog.buffer_between_pages == 0.5
    assert prog.repeat_rows == 2
    assert prog.repeat_lines == 3


def test_construction_type_conversion_string_to_int():
    """Test that string integers are converted to int for integer fields."""
    prog = ScratchDeskProgram(
        program_number="5",
        number_of_lines="10",
        number_of_pages="3",
        repeat_rows="2",
        repeat_lines="4"
    )
    assert prog.program_number == 5
    assert prog.number_of_lines == 10
    assert prog.number_of_pages == 3
    assert prog.repeat_rows == 2
    assert prog.repeat_lines == 4


def test_construction_type_conversion_string_to_float():
    """Test that string values are converted to floats for float fields."""
    prog = ScratchDeskProgram(
        high="10.5",
        top_padding="1.2",
        bottom_padding="1.8",
        width="20.5",
        left_margin="2.3",
        right_margin="3.4",
        page_width="15.6",
        buffer_between_pages="0.7"
    )
    assert prog.high == 10.5
    assert prog.top_padding == 1.2
    assert prog.bottom_padding == 1.8
    assert prog.width == 20.5
    assert prog.left_margin == 2.3
    assert prog.right_margin == 3.4
    assert prog.page_width == 15.6
    assert prog.buffer_between_pages == 0.7


def test_construction_negative_values_stored():
    """Test that negative values are stored (validation catches them later)."""
    prog = ScratchDeskProgram(
        high=-5.0,
        top_padding=-1.0,
        left_margin=-2.0,
        buffer_between_pages=-0.5
    )
    assert prog.high == -5.0
    assert prog.top_padding == -1.0
    assert prog.left_margin == -2.0
    assert prog.buffer_between_pages == -0.5


# ============================================================================
# Validation Tests - Width Formula
# ============================================================================

def test_validation_width_formula_exact_match():
    """Test that validation passes when width formula exactly matches."""
    # width = left_margin + right_margin + (page_width * number_of_pages) + (buffer_between_pages * (number_of_pages - 1))
    # width = 2.0 + 3.0 + (10.0 * 2) + (0.5 * (2 - 1)) = 2.0 + 3.0 + 20.0 + 0.5 = 25.5
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=25.5,
        left_margin=2.0,
        right_margin=3.0,
        page_width=10.0,
        number_of_pages=2,
        buffer_between_pages=0.5
    )
    errors = prog.validate()
    width_errors = [e for e in errors if "Row pattern validation failed" in e]
    assert len(width_errors) == 0


def test_validation_width_formula_mismatch():
    """Test that validation fails when width formula doesn't match."""
    # Expected: 2.0 + 3.0 + (10.0 * 2) + (0.5 * 1) = 25.5
    # Provided: 30.0
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=30.0,  # Wrong!
        left_margin=2.0,
        right_margin=3.0,
        page_width=10.0,
        number_of_pages=2,
        buffer_between_pages=0.5
    )
    errors = prog.validate()
    width_errors = [e for e in errors if "Row pattern validation failed" in e]
    assert len(width_errors) == 1
    assert "30.0" in width_errors[0]
    assert "25.5" in width_errors[0]


def test_validation_width_formula_tolerance():
    """Test that validation allows small floating point differences (tolerance 0.001)."""
    # Expected: 25.5
    # Provided: 25.5001 (within tolerance)
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=25.5001,
        left_margin=2.0,
        right_margin=3.0,
        page_width=10.0,
        number_of_pages=2,
        buffer_between_pages=0.5
    )
    errors = prog.validate()
    width_errors = [e for e in errors if "Row pattern validation failed" in e]
    assert len(width_errors) == 0


def test_validation_width_formula_one_page_no_buffer():
    """Test width formula with one page (buffer should not be added)."""
    # width = 2.0 + 3.0 + (10.0 * 1) + (0.5 * (1 - 1)) = 2.0 + 3.0 + 10.0 + 0.0 = 15.0
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=15.0,
        left_margin=2.0,
        right_margin=3.0,
        page_width=10.0,
        number_of_pages=1,
        buffer_between_pages=0.5  # Should not be used
    )
    errors = prog.validate()
    width_errors = [e for e in errors if "Row pattern validation failed" in e]
    assert len(width_errors) == 0


# ============================================================================
# Validation Tests - Desk Size
# ============================================================================

def test_validation_desk_size_fits():
    """Test that validation passes when dimensions fit on desk."""
    prog = ScratchDeskProgram(
        high=20.0,
        number_of_lines=5,
        width=30.0,
        left_margin=10.0,
        right_margin=10.0,
        page_width=10.0,
        number_of_pages=1,
        repeat_rows=2,  # total width: 30 * 2 = 60 <= 120
        repeat_lines=2  # total height: 20 * 2 = 40 <= 80
    )
    errors = prog.validate()
    desk_errors = [e for e in errors if "Desk" in e and "exceeded" in e]
    assert len(desk_errors) == 0


def test_validation_desk_width_exceeded():
    """Test that validation fails when total width exceeds MAX_WIDTH_OF_DESK."""
    prog = ScratchDeskProgram(
        high=20.0,
        number_of_lines=5,
        width=50.0,
        left_margin=20.0,
        right_margin=20.0,
        page_width=10.0,
        number_of_pages=1,
        repeat_rows=3  # total width: 50 * 3 = 150 > 120
    )
    errors = prog.validate()
    width_errors = [e for e in errors if "Desk width exceeded" in e]
    assert len(width_errors) == 1
    assert "150" in width_errors[0]
    assert "120" in width_errors[0]


def test_validation_desk_height_exceeded():
    """Test that validation fails when total height exceeds MAX_HEIGHT_OF_DESK."""
    prog = ScratchDeskProgram(
        high=30.0,
        number_of_lines=5,
        width=20.0,
        left_margin=10.0,
        right_margin=10.0,
        page_width=0.0,  # Will fail width formula but testing height
        number_of_pages=1,
        repeat_lines=3  # total height: 30 * 3 = 90 > 80
    )
    errors = prog.validate()
    height_errors = [e for e in errors if "Desk height exceeded" in e]
    assert len(height_errors) == 1
    assert "90" in height_errors[0]
    assert "80" in height_errors[0]


def test_validation_desk_size_boundary():
    """Test boundary case where dimensions exactly match desk limits."""
    prog = ScratchDeskProgram(
        high=80.0,
        number_of_lines=5,
        width=120.0,
        left_margin=60.0,
        right_margin=60.0,
        page_width=0.0,
        number_of_pages=1,
        repeat_rows=1,  # total width: 120 * 1 = 120 = MAX
        repeat_lines=1  # total height: 80 * 1 = 80 = MAX
    )
    errors = prog.validate()
    desk_errors = [e for e in errors if "Desk" in e and "exceeded" in e]
    assert len(desk_errors) == 0


# ============================================================================
# Validation Tests - Zero and Negative Values
# ============================================================================

def test_validation_zero_number_of_lines():
    """Test that validation fails when number_of_lines is zero."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=0,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    assert "Number of lines must be greater than 0" in errors


def test_validation_zero_number_of_pages():
    """Test that validation fails when number_of_pages is zero."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=0
    )
    errors = prog.validate()
    assert "Number of pages must be greater than 0" in errors


def test_validation_zero_repeat_rows():
    """Test that validation fails when repeat_rows is zero."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1,
        repeat_rows=0
    )
    errors = prog.validate()
    assert "Repeat rows must be greater than 0" in errors


def test_validation_zero_repeat_lines():
    """Test that validation fails when repeat_lines is zero."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1,
        repeat_lines=0
    )
    errors = prog.validate()
    assert "Repeat lines must be greater than 0" in errors


def test_validation_zero_high():
    """Test that validation fails when high is zero."""
    prog = ScratchDeskProgram(
        high=0.0,
        number_of_lines=3,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    assert "High must be greater than 0" in errors


def test_validation_zero_width():
    """Test that validation fails when width is zero."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=0.0,
        left_margin=0.0,
        right_margin=0.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    assert "Width must be greater than 0" in errors


def test_validation_zero_page_width():
    """Test that validation fails when page_width is zero."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    assert "Page width must be greater than 0" in errors


def test_validation_negative_padding():
    """Test that validation fails when padding values are negative."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        top_padding=-1.0,
        bottom_padding=-0.5,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    assert "Padding values cannot be negative" in errors


def test_validation_negative_margins():
    """Test that validation fails when margin values are negative."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=10.0,
        left_margin=-2.0,
        right_margin=-3.0,
        page_width=15.0,
        number_of_pages=1
    )
    errors = prog.validate()
    assert "Margin values cannot be negative" in errors


def test_validation_negative_buffer():
    """Test that validation fails when buffer_between_pages is negative."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1,
        buffer_between_pages=-0.5
    )
    errors = prog.validate()
    assert "Buffer between pages cannot be negative" in errors


def test_validation_zero_padding_valid():
    """Test that zero padding is valid (not negative)."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        top_padding=0.0,
        bottom_padding=0.0,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    padding_errors = [e for e in errors if "Padding values cannot be negative" in e]
    assert len(padding_errors) == 0


def test_validation_zero_margins_valid():
    """Test that zero margins are valid (not negative)."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        width=10.0,
        left_margin=0.0,
        right_margin=0.0,
        page_width=10.0,
        number_of_pages=1
    )
    errors = prog.validate()
    margin_errors = [e for e in errors if "Margin values cannot be negative" in e]
    assert len(margin_errors) == 0


# ============================================================================
# Validation Tests - Padding and Line Spacing
# ============================================================================

def test_validation_padding_exceeds_height():
    """Test that validation fails when padding exceeds height."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        top_padding=6.0,
        bottom_padding=5.0,  # total 11.0 > 10.0
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    assert "Padding exceeds height: no room for lines" in errors


def test_validation_padding_equals_height():
    """Test that validation fails when padding equals height."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        top_padding=5.0,
        bottom_padding=5.0,  # total 10.0 = 10.0
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    assert "Padding exceeds height: no room for lines" in errors


def test_validation_line_spacing_too_small():
    """Test that validation fails when line spacing is below minimum."""
    # high = 10.0, padding = 1.0 + 1.0 = 2.0
    # available = 10.0 - 2.0 = 8.0
    # lines = 50, spacing = 8.0 / (50 - 1) = 8.0 / 49 = 0.163 < 0.3
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=50,
        top_padding=1.0,
        bottom_padding=1.0,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    spacing_errors = [e for e in errors if "Line spacing too small" in e]
    assert len(spacing_errors) == 1
    assert "0.16 cm" in spacing_errors[0]  # 0.163 formatted as 0.16
    assert "0.3 cm" in spacing_errors[0]


def test_validation_line_spacing_at_minimum():
    """Test that validation passes when line spacing is exactly at minimum."""
    # high = 10.0, padding = 1.0 + 1.0 = 2.0
    # available = 8.0
    # lines = 27, spacing = 8.0 / 26 = 0.307 >= 0.3 (passes)
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=27,
        top_padding=1.0,
        bottom_padding=1.0,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    spacing_errors = [e for e in errors if "Line spacing too small" in e]
    assert len(spacing_errors) == 0


def test_validation_single_line_skips_spacing_check():
    """Test that line spacing check is skipped for single line."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=1,
        top_padding=1.0,
        bottom_padding=1.0,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    errors = prog.validate()
    spacing_errors = [e for e in errors if "Line spacing too small" in e]
    assert len(spacing_errors) == 0


# ============================================================================
# Validation Tests - Multiple Errors
# ============================================================================

def test_validation_multiple_errors():
    """Test that validation can return multiple errors at once."""
    prog = ScratchDeskProgram(
        high=0.0,  # Error: must be > 0
        number_of_lines=0,  # Error: must be > 0
        top_padding=-1.0,  # Error: cannot be negative
        width=100.0,
        left_margin=-2.0,  # Error: cannot be negative
        right_margin=10.0,
        page_width=50.0,
        number_of_pages=1,
        repeat_rows=2  # total width: 100 * 2 = 200 > 120 (Error)
    )
    errors = prog.validate()
    assert len(errors) >= 5  # At least 5 distinct errors


# ============================================================================
# is_valid() Tests
# ============================================================================

def test_is_valid_true():
    """Test that is_valid returns True for a valid program."""
    prog = ScratchDeskProgram(
        high=10.0,
        number_of_lines=3,
        top_padding=1.0,
        bottom_padding=1.0,
        width=15.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=5.0,
        number_of_pages=1
    )
    assert prog.is_valid() is True


def test_is_valid_false():
    """Test that is_valid returns False for an invalid program."""
    prog = ScratchDeskProgram(
        high=0.0,  # Invalid
        number_of_lines=3,
        width=10.0,
        left_margin=5.0,
        right_margin=5.0,
        page_width=0.0,
        number_of_pages=1
    )
    assert prog.is_valid() is False


# ============================================================================
# get_total_desk_dimensions() Tests
# ============================================================================

def test_get_total_desk_dimensions_with_repeats():
    """Test get_total_desk_dimensions with repeat factors."""
    prog = ScratchDeskProgram(
        high=20.0,
        number_of_lines=5,
        width=30.0,
        left_margin=10.0,
        right_margin=10.0,
        page_width=10.0,
        number_of_pages=1,
        repeat_rows=3,
        repeat_lines=2
    )
    dims = prog.get_total_desk_dimensions()
    assert dims['total_width'] == 90.0  # 30 * 3
    assert dims['total_height'] == 40.0  # 20 * 2
    assert dims['fits_on_desk'] is True


def test_get_total_desk_dimensions_fits():
    """Test that fits_on_desk is True when dimensions fit."""
    prog = ScratchDeskProgram(
        high=40.0,
        number_of_lines=5,
        width=60.0,
        left_margin=30.0,
        right_margin=30.0,
        page_width=0.0,
        number_of_pages=1,
        repeat_rows=1,
        repeat_lines=1
    )
    dims = prog.get_total_desk_dimensions()
    assert dims['fits_on_desk'] is True


def test_get_total_desk_dimensions_doesnt_fit():
    """Test that fits_on_desk is False when dimensions don't fit."""
    prog = ScratchDeskProgram(
        high=50.0,
        number_of_lines=5,
        width=70.0,
        left_margin=35.0,
        right_margin=35.0,
        page_width=0.0,
        number_of_pages=1,
        repeat_rows=2,  # 70 * 2 = 140 > 120
        repeat_lines=2  # 50 * 2 = 100 > 80
    )
    dims = prog.get_total_desk_dimensions()
    assert dims['fits_on_desk'] is False


def test_get_total_desk_dimensions_single_repeat():
    """Test get_total_desk_dimensions with no repeats (factors of 1)."""
    prog = ScratchDeskProgram(
        high=25.0,
        number_of_lines=5,
        width=35.0,
        left_margin=10.0,
        right_margin=10.0,
        page_width=15.0,
        number_of_pages=1
    )
    dims = prog.get_total_desk_dimensions()
    assert dims['total_width'] == 35.0
    assert dims['total_height'] == 25.0
    assert dims['fits_on_desk'] is True


# ============================================================================
# __str__ and __repr__ Tests
# ============================================================================

def test_str_representation():
    """Test __str__ returns readable format."""
    prog = ScratchDeskProgram(program_number=42, program_name="Test ABC")
    result = str(prog)
    assert result == "Program 42: Test ABC"


def test_repr_representation():
    """Test __repr__ returns evaluable format."""
    prog = ScratchDeskProgram(program_number=15, program_name="Sample")
    result = repr(prog)
    assert result == "ScratchDeskProgram(program_number=15, program_name='Sample')"


def test_str_with_empty_name():
    """Test __str__ with empty program name."""
    prog = ScratchDeskProgram(program_number=10, program_name="")
    result = str(prog)
    assert result == "Program 10: "


def test_repr_with_special_characters():
    """Test __repr__ with special characters in name."""
    prog = ScratchDeskProgram(program_number=7, program_name="Test's \"Program\"")
    result = repr(prog)
    assert "program_number=7" in result
    assert "Test's \"Program\"" in result


# ============================================================================
# translate_validation_error() Tests
# ============================================================================

def test_translate_validation_error_line_spacing_dynamic():
    """Test translate_validation_error handles line spacing with dynamic values."""
    error = "Line spacing too small (0.16 cm, minimum 0.3 cm)"
    # Should extract values and call t() with them
    result = translate_validation_error(error)
    # The function should handle this and return translated version
    assert "0.16" in result or "spacing" in result.lower()


def test_translate_validation_error_static_error():
    """Test translate_validation_error handles static error strings."""
    error = "Number of lines must be greater than 0"
    result = translate_validation_error(error)
    # Should call t(error_text) for static errors
    # Since we're testing the function, not translations, just verify it doesn't crash
    assert result is not None


def test_translate_validation_error_unknown_passthrough():
    """Test translate_validation_error passes through unknown errors."""
    error = "Some completely unknown error message"
    result = translate_validation_error(error)
    # Should still process it (via t() fallback)
    assert result is not None

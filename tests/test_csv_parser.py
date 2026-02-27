"""
Comprehensive tests for CSV parser (core/csv_parser.py)
Tests loading, saving, validation, and error handling of CSV files.
"""

import pytest
import csv
import os
from core.csv_parser import CSVParser
from core.program_model import ScratchDeskProgram


class TestLoadPrograms:
    """Test load_programs_from_csv method"""

    def test_load_valid_csv(self, tmp_path):
        """Returns programs list, empty errors"""
        csv_file = tmp_path / "valid.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,Test Program,10.0,5,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(programs) == 1
        assert len(errors) == 0
        assert programs[0].program_number == 1
        assert programs[0].program_name == "Test Program"
        assert programs[0].high == 10.0
        assert programs[0].number_of_lines == 5

    def test_load_file_not_found(self, tmp_path):
        """Returns empty programs, error message"""
        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(tmp_path / "nonexistent.csv"))

        assert len(programs) == 0
        assert len(errors) == 1
        assert "File not found" in errors[0]

    def test_load_missing_headers(self, tmp_path):
        """Returns error about missing headers"""
        csv_file = tmp_path / "missing_headers.csv"
        csv_file.write_text(
            "program_number,program_name,high\n"
            "1,Test,10.0\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(programs) == 0
        assert len(errors) == 1
        assert "Missing required headers" in errors[0]
        assert "number_of_lines" in errors[0]

    def test_load_extra_headers_ignored(self, tmp_path):
        """Extra headers logged, programs loaded"""
        csv_file = tmp_path / "extra_headers.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines,extra_column,another_extra\n"
            "1,Test Program,10.0,5,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1,ignored,also_ignored\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        # Programs should load successfully despite extra headers
        assert len(programs) == 1
        assert len(errors) == 0

    def test_load_empty_csv(self, tmp_path):
        """Only headers, no data rows -> empty programs, no errors"""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(programs) == 0
        assert len(errors) == 0

    def test_load_invalid_row_data(self, tmp_path):
        """Non-numeric values -> error with row number"""
        csv_file = tmp_path / "invalid_data.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,Test Program,invalid_number,5,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(programs) == 0
        assert len(errors) == 1
        assert "Row 2" in errors[0]
        assert "Error parsing data" in errors[0]

    def test_load_mixed_valid_invalid(self, tmp_path):
        """Valid programs returned, errors for invalid"""
        csv_file = tmp_path / "mixed.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,Valid Program,10.0,5,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n"
            "2,Invalid Program,10.0,invalid,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n"
            "3,Another Valid,10.0,5,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(programs) == 2
        assert len(errors) == 1
        assert programs[0].program_number == 1
        assert programs[1].program_number == 3
        assert "Row 3" in errors[0]

    def test_load_empty_values_default_to_zero(self, tmp_path):
        """Empty cells -> 0 or 0.0"""
        csv_file = tmp_path / "empty_values.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,Test Program,10.0,5,,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        # Program will be created but may fail validation
        # The key is that empty top_padding defaults to 0.0
        assert programs[0].top_padding == 0.0

    def test_load_float_as_integer(self, tmp_path):
        """5.0 in integer field -> 5"""
        csv_file = tmp_path / "float_as_int.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1.0,Test Program,10.0,5.0,2.0,2.0,48.0,5.0,5.0,8.0,4.0,2.0,1.0,1.0\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        # Should convert 1.0 to 1, 5.0 to 5, 4.0 to 4
        assert programs[0].program_number == 1
        assert programs[0].number_of_lines == 5
        assert programs[0].number_of_pages == 4
        assert programs[0].repeat_rows == 1
        assert programs[0].repeat_lines == 1

    def test_load_whitespace_stripped(self, tmp_path):
        """ 5.0  -> 5.0"""
        csv_file = tmp_path / "whitespace.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "  1  ,  Test Program  ,  10.0  ,  5  ,  2.0  ,  2.0  ,  48.0  ,  5.0  ,  5.0  ,  8.0  ,  4  ,  2.0  ,  1  ,  1  \n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(programs) == 1
        assert programs[0].program_number == 1
        assert programs[0].program_name == "Test Program"
        assert programs[0].high == 10.0
        assert programs[0].number_of_lines == 5

    def test_load_csv_encoding_utf8(self, tmp_path):
        """UTF-8 encoded file with Hebrew names"""
        csv_file = tmp_path / "hebrew.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,תוכנית בדיקה,10.0,5,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(programs) == 1
        assert programs[0].program_name == "תוכנית בדיקה"

    def test_load_validation_errors_include_row_number(self, tmp_path):
        """Errors contain Row N:"""
        csv_file = tmp_path / "validation_errors.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,Invalid Width,10.0,5,2.0,2.0,99.0,5.0,5.0,8.0,4,2.0,1,1\n"
            "2,Invalid Lines,10.0,0,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(errors) >= 2
        assert any("Row 2" in error for error in errors)
        assert any("Row 3" in error for error in errors)


class TestCreateProgramFromRow:
    """Test _create_program_from_row method"""

    def test_all_fields_mapped_correctly(self):
        """All fields map correctly from row dict to program"""
        parser = CSVParser()
        row = {
            'program_number': '1',
            'program_name': 'Test Program',
            'high': '10.0',
            'number_of_lines': '5',
            'top_padding': '2.0',
            'bottom_padding': '2.0',
            'width': '48.0',
            'left_margin': '5.0',
            'right_margin': '5.0',
            'page_width': '8.0',
            'number_of_pages': '4',
            'buffer_between_pages': '2.0',
            'repeat_rows': '1',
            'repeat_lines': '1'
        }

        program = parser._create_program_from_row(row)

        assert program.program_number == 1
        assert program.program_name == "Test Program"
        assert program.high == 10.0
        assert program.number_of_lines == 5
        assert program.top_padding == 2.0
        assert program.bottom_padding == 2.0
        assert program.width == 48.0
        assert program.left_margin == 5.0
        assert program.right_margin == 5.0
        assert program.page_width == 8.0
        assert program.number_of_pages == 4
        assert program.buffer_between_pages == 2.0
        assert program.repeat_rows == 1
        assert program.repeat_lines == 1

    def test_integer_fields_converted(self):
        """Integer fields properly converted"""
        parser = CSVParser()
        row = {
            'program_number': '42',
            'program_name': 'Test',
            'high': '10.0',
            'number_of_lines': '7',
            'top_padding': '0.0',
            'bottom_padding': '0.0',
            'width': '48.0',
            'left_margin': '0.0',
            'right_margin': '0.0',
            'page_width': '8.0',
            'number_of_pages': '3',
            'buffer_between_pages': '0.0',
            'repeat_rows': '2',
            'repeat_lines': '4'
        }

        program = parser._create_program_from_row(row)

        assert isinstance(program.program_number, int)
        assert isinstance(program.number_of_lines, int)
        assert isinstance(program.number_of_pages, int)
        assert isinstance(program.repeat_rows, int)
        assert isinstance(program.repeat_lines, int)
        assert program.program_number == 42
        assert program.number_of_lines == 7
        assert program.number_of_pages == 3
        assert program.repeat_rows == 2
        assert program.repeat_lines == 4

    def test_float_fields_converted(self):
        """Float fields properly converted"""
        parser = CSVParser()
        row = {
            'program_number': '1',
            'program_name': 'Test',
            'high': '12.5',
            'number_of_lines': '5',
            'top_padding': '1.5',
            'bottom_padding': '2.3',
            'width': '50.7',
            'left_margin': '3.2',
            'right_margin': '4.8',
            'page_width': '9.1',
            'number_of_pages': '4',
            'buffer_between_pages': '1.7',
            'repeat_rows': '1',
            'repeat_lines': '1'
        }

        program = parser._create_program_from_row(row)

        assert isinstance(program.high, float)
        assert isinstance(program.top_padding, float)
        assert isinstance(program.bottom_padding, float)
        assert isinstance(program.width, float)
        assert isinstance(program.left_margin, float)
        assert isinstance(program.right_margin, float)
        assert isinstance(program.page_width, float)
        assert isinstance(program.buffer_between_pages, float)
        assert program.high == 12.5
        assert program.top_padding == 1.5
        assert program.bottom_padding == 2.3
        assert program.width == 50.7

    def test_program_name_string(self):
        """Program name is properly converted to string"""
        parser = CSVParser()
        row = {
            'program_number': '1',
            'program_name': 'My Test Program 123',
            'high': '10.0',
            'number_of_lines': '5',
            'top_padding': '0.0',
            'bottom_padding': '0.0',
            'width': '48.0',
            'left_margin': '5.0',
            'right_margin': '5.0',
            'page_width': '8.0',
            'number_of_pages': '4',
            'buffer_between_pages': '2.0',
            'repeat_rows': '1',
            'repeat_lines': '1'
        }

        program = parser._create_program_from_row(row)

        assert isinstance(program.program_name, str)
        assert program.program_name == "My Test Program 123"

    def test_missing_field_defaults_to_zero(self):
        """Missing fields default to 0 or 0.0"""
        parser = CSVParser()
        row = {
            'program_number': '1',
            'program_name': 'Test',
            'high': '10.0',
            'number_of_lines': '5',
            # top_padding missing
            'bottom_padding': '0.0',
            'width': '48.0',
            'left_margin': '5.0',
            'right_margin': '5.0',
            'page_width': '8.0',
            'number_of_pages': '4',
            'buffer_between_pages': '2.0',
            'repeat_rows': '1',
            'repeat_lines': '1'
        }

        program = parser._create_program_from_row(row)

        assert program.top_padding == 0.0


class TestSavePrograms:
    """Test save_programs_to_csv method"""

    def test_save_valid_programs(self, tmp_path):
        """Save valid programs to CSV"""
        csv_file = tmp_path / "output.csv"

        programs = [
            ScratchDeskProgram(
                program_number=1, program_name="Test Program 1",
                high=10.0, number_of_lines=5, top_padding=2.0, bottom_padding=2.0,
                width=48.0, left_margin=5.0, right_margin=5.0,
                page_width=8.0, number_of_pages=4, buffer_between_pages=2.0,
                repeat_rows=1, repeat_lines=1
            ),
            ScratchDeskProgram(
                program_number=2, program_name="Test Program 2",
                high=15.0, number_of_lines=3, top_padding=1.0, bottom_padding=1.0,
                width=30.0, left_margin=5.0, right_margin=5.0,
                page_width=10.0, number_of_pages=2, buffer_between_pages=0.0,
                repeat_rows=2, repeat_lines=2
            )
        ]

        parser = CSVParser()
        success, errors = parser.save_programs_to_csv(programs, str(csv_file))

        assert success is True
        assert len(errors) == 0
        assert csv_file.exists()

        # Verify file contents
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]['program_number'] == '1'
            assert rows[0]['program_name'] == 'Test Program 1'
            assert rows[1]['program_number'] == '2'

    def test_save_empty_list(self, tmp_path):
        """Saves CSV with only headers"""
        csv_file = tmp_path / "empty_output.csv"

        parser = CSVParser()
        success, errors = parser.save_programs_to_csv([], str(csv_file))

        assert success is True
        assert len(errors) == 0
        assert csv_file.exists()

        # Verify file has headers but no data
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 0
            assert 'program_number' in reader.fieldnames
            assert 'program_name' in reader.fieldnames

    def test_save_and_reload_roundtrip(self, tmp_path):
        """Save then load produces identical programs"""
        csv_file = tmp_path / "roundtrip.csv"

        original_programs = [
            ScratchDeskProgram(
                program_number=1, program_name="Roundtrip Test",
                high=10.0, number_of_lines=5, top_padding=2.0, bottom_padding=2.0,
                width=48.0, left_margin=5.0, right_margin=5.0,
                page_width=8.0, number_of_pages=4, buffer_between_pages=2.0,
                repeat_rows=1, repeat_lines=1
            )
        ]

        parser = CSVParser()

        # Save
        success, errors = parser.save_programs_to_csv(original_programs, str(csv_file))
        assert success is True

        # Load
        loaded_programs, errors = parser.load_programs_from_csv(str(csv_file))
        assert len(loaded_programs) == 1
        assert len(errors) == 0

        # Compare
        orig = original_programs[0]
        loaded = loaded_programs[0]
        assert loaded.program_number == orig.program_number
        assert loaded.program_name == orig.program_name
        assert loaded.high == orig.high
        assert loaded.number_of_lines == orig.number_of_lines
        assert loaded.top_padding == orig.top_padding
        assert loaded.bottom_padding == orig.bottom_padding
        assert loaded.width == orig.width
        assert loaded.left_margin == orig.left_margin
        assert loaded.right_margin == orig.right_margin
        assert loaded.page_width == orig.page_width
        assert loaded.number_of_pages == orig.number_of_pages
        assert loaded.buffer_between_pages == orig.buffer_between_pages
        assert loaded.repeat_rows == orig.repeat_rows
        assert loaded.repeat_lines == orig.repeat_lines

    def test_save_to_invalid_path(self, tmp_path):
        """Save to invalid path returns error"""
        invalid_path = tmp_path / "nonexistent_dir" / "output.csv"

        programs = [
            ScratchDeskProgram(
                program_number=1, program_name="Test",
                high=10.0, number_of_lines=5, top_padding=2.0, bottom_padding=2.0,
                width=48.0, left_margin=5.0, right_margin=5.0,
                page_width=8.0, number_of_pages=4, buffer_between_pages=2.0,
                repeat_rows=1, repeat_lines=1
            )
        ]

        parser = CSVParser()
        success, errors = parser.save_programs_to_csv(programs, str(invalid_path))

        assert success is False
        assert len(errors) == 1
        assert "Error saving CSV file" in errors[0]

    def test_save_preserves_all_fields(self, tmp_path):
        """Save preserves all field values exactly"""
        csv_file = tmp_path / "all_fields.csv"

        program = ScratchDeskProgram(
            program_number=42, program_name="Field Test Program",
            high=12.5, number_of_lines=7, top_padding=1.5, bottom_padding=2.3,
            width=60.0, left_margin=7.5, right_margin=8.5,
            page_width=10.0, number_of_pages=3, buffer_between_pages=1.5,
            repeat_rows=3, repeat_lines=2
        )

        parser = CSVParser()
        success, errors = parser.save_programs_to_csv([program], str(csv_file))
        assert success is True

        # Read back and verify
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert row['program_number'] == '42'
            assert row['program_name'] == 'Field Test Program'
            assert row['high'] == '12.5'
            assert row['number_of_lines'] == '7'
            assert row['top_padding'] == '1.5'
            assert row['bottom_padding'] == '2.3'
            assert row['width'] == '60.0'
            assert row['left_margin'] == '7.5'
            assert row['right_margin'] == '8.5'
            assert row['page_width'] == '10.0'
            assert row['number_of_pages'] == '3'
            assert row['buffer_between_pages'] == '1.5'
            assert row['repeat_rows'] == '3'
            assert row['repeat_lines'] == '2'


class TestValidateCsvFile:
    """Test validate_csv_file method"""

    def test_validate_valid_file(self, tmp_path):
        """Returns True for valid file"""
        csv_file = tmp_path / "valid.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,Test Program,10.0,5,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        result = parser.validate_csv_file(str(csv_file))

        assert result is True

    def test_validate_invalid_file(self, tmp_path):
        """Returns False for invalid file"""
        csv_file = tmp_path / "invalid.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,Invalid Program,10.0,0,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        result = parser.validate_csv_file(str(csv_file))

        assert result is False


class TestWidthFormula:
    """Test width formula validation: width = left_margin + right_margin + (page_width * number_of_pages) + (buffer_between_pages * (number_of_pages - 1))"""

    def test_valid_width_calculation(self, tmp_path):
        """width=48, left=5, right=5, page_width=8, pages=4, buffer=2 -> 5+5+(8*4)+(2*3) = 48"""
        csv_file = tmp_path / "valid_width.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,Valid Width Test,10.0,5,2.0,2.0,48.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(programs) == 1
        assert len(errors) == 0

        # Verify calculation: 5 + 5 + (8 * 4) + (2 * 3) = 5 + 5 + 32 + 6 = 48
        program = programs[0]
        expected_width = (program.left_margin + program.right_margin +
                         (program.page_width * program.number_of_pages) +
                         (program.buffer_between_pages * (program.number_of_pages - 1)))
        assert program.width == expected_width == 48.0

    def test_invalid_width_calculation(self, tmp_path):
        """width=50 but formula gives 48 -> validation error"""
        csv_file = tmp_path / "invalid_width.csv"
        csv_file.write_text(
            "program_number,program_name,high,number_of_lines,top_padding,bottom_padding,"
            "width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,"
            "repeat_rows,repeat_lines\n"
            "1,Invalid Width Test,10.0,5,2.0,2.0,50.0,5.0,5.0,8.0,4,2.0,1,1\n",
            encoding='utf-8'
        )

        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(str(csv_file))

        assert len(programs) == 0
        assert len(errors) == 1
        assert "Row 2" in errors[0]
        assert "Row pattern validation failed" in errors[0]

import csv
from core.program_model import ScratchDeskProgram
from core.logger import get_logger

class CSVParser:
    """
    Updated CSV Parser for new CSV structure and validation formulas.
    
    New CSV Headers:
    - program_number, program_name
    - high, number_of_lines, top_padding, bottom_padding
    - width, left_margin, right_margin, page_width, number_of_pages, buffer_between_pages
    - repeat_rows, repeat_lines
    """
    
    def __init__(self):
        self.logger = get_logger()
        self.required_headers = [
            # General Program Information
            'program_number', 'program_name',
            # Lines Pattern Settings
            'high', 'number_of_lines', 'top_padding', 'bottom_padding',
            # Row Pattern Settings
            'width', 'left_margin', 'right_margin',
            'page_width', 'number_of_pages', 'buffer_between_pages',
            # Generate Settings
            'repeat_rows', 'repeat_lines'
        ]
    
    def load_programs_from_csv(self, file_path):
        """Load programs from CSV file with new structure and validate using new formulas"""
        programs = []
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                # Check if all required headers are present
                missing_headers = set(self.required_headers) - set(csv_reader.fieldnames or [])
                if missing_headers:
                    errors.append(f"Missing required headers: {', '.join(missing_headers)}")
                    return programs, errors
                
                # Check for extra headers (informational)
                extra_headers = set(csv_reader.fieldnames or []) - set(self.required_headers)
                if extra_headers:
                    self.logger.info(f"Extra headers found (will be ignored): {', '.join(extra_headers)}", category="parser")
                
                for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because header is row 1
                    try:
                        program = self._create_program_from_row(row)
                        validation_errors = program.validate()
                        
                        if validation_errors:
                            for error in validation_errors:
                                errors.append(f"Row {row_num}: {error}")
                        else:
                            programs.append(program)
                    
                    except (ValueError, TypeError) as e:
                        errors.append(f"Row {row_num}: Error parsing data - {str(e)}")
                    
                    except Exception as e:
                        errors.append(f"Row {row_num}: Unexpected error - {str(e)}")
        
        except FileNotFoundError:
            errors.append(f"File not found: {file_path}")
        
        except Exception as e:
            errors.append(f"Error reading CSV file: {str(e)}")
        
        return programs, errors
    
    def _create_program_from_row(self, row):
        """Create ScratchDeskProgram instance from CSV row with new field names"""
        # Convert string values to appropriate types
        program_data = {}
        
        # Integer fields
        integer_fields = [
            'program_number', 'number_of_lines', 'number_of_pages', 'repeat_rows', 'repeat_lines'
        ]
        
        # Float fields
        float_fields = [
            'high', 'top_padding', 'bottom_padding', 'width', 
            'left_margin', 'right_margin',
            'page_width', 'buffer_between_pages'
        ]
        
        # Handle integer conversions
        for field in integer_fields:
            value = row.get(field, '0').strip()
            if not value:
                value = '0'
            program_data[field] = int(float(value))  # Handle cases like "5.0"
        
        # Handle float conversions
        for field in float_fields:
            value = row.get(field, '0.0').strip()
            if not value:
                value = '0.0'
            program_data[field] = float(value)
        
        # Handle string field
        program_data['program_name'] = row.get('program_name', '').strip()
        
        return ScratchDeskProgram(**program_data)
    
    def save_programs_to_csv(self, programs, file_path):
        """Save programs to CSV file with new structure"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=self.required_headers)
                writer.writeheader()
                
                for program in programs:
                    writer.writerow({
                        # General Program Information
                        'program_number': program.program_number,
                        'program_name': program.program_name,
                        # Lines Pattern Settings
                        'high': program.high,
                        'number_of_lines': program.number_of_lines,
                        'top_padding': program.top_padding,
                        'bottom_padding': program.bottom_padding,
                        # Row Pattern Settings
                        'width': program.width,
                        'left_margin': program.left_margin,
                        'right_margin': program.right_margin,
                        'page_width': program.page_width,
                        'number_of_pages': program.number_of_pages,
                        'buffer_between_pages': program.buffer_between_pages,
                        # Generate Settings
                        'repeat_rows': program.repeat_rows,
                        'repeat_lines': program.repeat_lines
                    })
            return True, []
        
        except Exception as e:
            return False, [f"Error saving CSV file: {str(e)}"]
    
    def validate_csv_file(self, file_path):
        """Validate CSV file and show detailed results"""
        programs, errors = self.load_programs_from_csv(file_path)
        
        if errors:
            self.logger.error("Validation Errors Found:", category="parser")
            for error in errors:
                self.logger.error(f"  - {error}", category="parser")
            self.logger.warning(f"Loaded {len(programs)} valid programs out of total rows.", category="parser")
            return False

        self.logger.info(f"CSV validation successful! Loaded {len(programs)} valid programs.", category="parser")
        
        # Show validation details for each program
        for program in programs:
            dims = program.get_total_desk_dimensions()
            status = "VALID" if program.is_valid() else "INVALID"
            self.logger.debug(f"  {status} - {program.program_name}: "
                  f"{dims['total_width']:.1f}x{dims['total_height']:.1f}cm "
                  f"({'fits' if dims['fits_on_desk'] else 'too large'})", category="parser")
        
        return True
    
    def test_validation_examples(self):
        """Test the validation formulas with example data"""
        self.logger.info("Testing validation formulas...", category="parser")
        
        # Test Program 1 - Should fail row pattern validation
        test1 = ScratchDeskProgram(
            program_number=1, program_name="Test Program 1",
            high=10, number_of_lines=5, top_padding=2, bottom_padding=2,
            width=50, left_margin=5, right_margin=5,
            page_width=8, number_of_pages=4, buffer_between_pages=2,
            repeat_rows=1, repeat_lines=1
        )
        
        self.logger.debug(f"Test 1: {test1.program_name}", category="parser")
        errors = test1.validate()
        if errors:
            self.logger.error("  VALIDATION FAILED:", category="parser")
            for error in errors:
                self.logger.error(f"    - {error}", category="parser")
        else:
            self.logger.info("  VALIDATION PASSED", category="parser")
        
        # Test Program 2 - Should fail row pattern validation  
        test2 = ScratchDeskProgram(
            program_number=2, program_name="Test Program 2", 
            high=15, number_of_lines=3, top_padding=1, bottom_padding=1,
            width=80, left_margin=10, right_margin=10,
            page_width=12, number_of_pages=3, buffer_between_pages=3,
            repeat_rows=1, repeat_lines=2
        )
        
        self.logger.debug(f"Test 2: {test2.program_name}", category="parser")
        errors = test2.validate()
        if errors:
            self.logger.error("  VALIDATION FAILED:", category="parser")
            for error in errors:
                self.logger.error(f"    - {error}", category="parser")
        else:
            self.logger.info("  VALIDATION PASSED", category="parser")
        
        # Test Program 3 - Should pass all validations
        test3 = ScratchDeskProgram(
            program_number=3, program_name="Valid Test Program",
            high=10, number_of_lines=5, top_padding=2, bottom_padding=2,
            width=48, left_margin=5, right_margin=5,
            page_width=8, number_of_pages=4, buffer_between_pages=2,
            repeat_rows=1, repeat_lines=1
        )
        
        self.logger.debug(f"Test 3: {test3.program_name}", category="parser")
        errors = test3.validate()
        if errors:
            self.logger.error("  VALIDATION FAILED:", category="parser")
            for error in errors:
                self.logger.error(f"    - {error}", category="parser")
        else:
            self.logger.info("  VALIDATION PASSED", category="parser")
            dims = test3.get_total_desk_dimensions()
            self.logger.debug(f"    Total desk usage: {dims['total_width']}x{dims['total_height']}cm", category="parser")
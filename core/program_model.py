class ScratchDeskProgram:
    """
    Updated ScratchDeskProgram class with new CSV structure and validation formulas.
    
    New Structure:
    - Lines Pattern: high, number_of_lines, top_padding, bottom_padding
    - Row Pattern: width, left_margin, right_margin, page_width, number_of_pages, buffer_between_pages
    - Generate Settings: repeat_rows, repeat_lines
    """
    
    # System constants for desk size constraints (updated to real values)
    MAX_WIDTH_OF_DESK = 120.0  # cm (real desk width)
    MAX_HEIGHT_OF_DESK = 80.0   # cm (real desk height)
    
    def __init__(self, program_number=0, program_name="", 
                 # Lines Pattern Settings
                 high=0.0, number_of_lines=0, top_padding=0.0, bottom_padding=0.0,
                 # Row Pattern Settings  
                 width=0.0, left_margin=0.0, right_margin=0.0,
                 page_width=0.0, number_of_pages=1, buffer_between_pages=0.0,
                 # Generate Settings
                 repeat_rows=1, repeat_lines=1):
        
        # General Program Information
        self.program_number = int(program_number)
        self.program_name = str(program_name)
        
        # Lines Pattern Settings
        self.high = float(high)
        self.number_of_lines = int(number_of_lines)
        self.top_padding = float(top_padding)
        self.bottom_padding = float(bottom_padding)
        
        # Row Pattern Settings
        self.width = float(width)
        self.left_margin = float(left_margin)
        self.right_margin = float(right_margin)
        self.page_width = float(page_width)
        self.number_of_pages = int(number_of_pages)
        self.buffer_between_pages = float(buffer_between_pages)
        
        # Generate Settings
        self.repeat_rows = int(repeat_rows)
        self.repeat_lines = int(repeat_lines)
    
    def validate(self):
        """
        Validate program using new validation formulas:
        1. Row Pattern Validation: width = left_margin + right_margin + (page_width * number_of_pages) + (buffer_between_pages * (number_of_pages - 1))
        2. Desk Size Validation: width * repeat_rows <= MAX_WIDTH_OF_DESK AND high * repeat_lines <= MAX_HEIGHT_OF_DESK
        """
        errors = []
        
        # Row Pattern Validation Formula
        expected_width = (self.left_margin + self.right_margin + 
                         (self.page_width * self.number_of_pages) + 
                         (self.buffer_between_pages * (self.number_of_pages - 1)))
        
        if abs(self.width - expected_width) > 0.001:  # Allow small floating point differences
            errors.append(f"Row pattern validation failed: width ({self.width}) != "
                         f"left_margin + right_margin + "
                         f"(page_width * number_of_pages) + (buffer_between_pages * (number_of_pages - 1)) "
                         f"({expected_width:.3f})")
        
        # Desk Size Validation - Width
        total_desk_width = self.width * self.repeat_rows
        if total_desk_width > self.MAX_WIDTH_OF_DESK:
            errors.append(f"Desk width validation failed: width * repeat_rows ({total_desk_width:.1f}cm) > "
                         f"MAX_WIDTH_OF_DESK ({self.MAX_WIDTH_OF_DESK}cm)")
        
        # Desk Size Validation - Height
        total_desk_height = self.high * self.repeat_lines
        if total_desk_height > self.MAX_HEIGHT_OF_DESK:
            errors.append(f"Desk height validation failed: high * repeat_lines ({total_desk_height:.1f}cm) > "
                         f"MAX_HEIGHT_OF_DESK ({self.MAX_HEIGHT_OF_DESK}cm)")
        
        # Basic value validations
        if self.number_of_lines <= 0:
            errors.append("Number of lines must be greater than 0")
        
        if self.number_of_pages <= 0:
            errors.append("Number of pages must be greater than 0")
        
        if self.repeat_rows <= 0:
            errors.append("Repeat rows must be greater than 0")
            
        if self.repeat_lines <= 0:
            errors.append("Repeat lines must be greater than 0")
        
        if self.high <= 0:
            errors.append("High must be greater than 0")
        
        if self.width <= 0:
            errors.append("Width must be greater than 0")
        
        if self.page_width <= 0:
            errors.append("Page width must be greater than 0")
        
        # Logical validations
        if self.top_padding < 0 or self.bottom_padding < 0:
            errors.append("Padding values cannot be negative")
            
        if any([self.left_margin < 0, self.right_margin < 0]):
            errors.append("Margin values cannot be negative")
            
        if self.buffer_between_pages < 0:
            errors.append("Buffer between pages cannot be negative")
        
        return errors
    
    def is_valid(self):
        """Check if program passes all validations"""
        return len(self.validate()) == 0
    
    def get_total_desk_dimensions(self):
        """Get total dimensions when repeated on desk"""
        return {
            'total_width': self.width * self.repeat_rows,
            'total_height': self.high * self.repeat_lines,
            'fits_on_desk': (self.width * self.repeat_rows <= self.MAX_WIDTH_OF_DESK and 
                           self.high * self.repeat_lines <= self.MAX_HEIGHT_OF_DESK)
        }
    
    def __str__(self):
        return f"Program {self.program_number}: {self.program_name}"
    
    def __repr__(self):
        return f"ScratchDeskProgram(program_number={self.program_number}, program_name='{self.program_name}')"
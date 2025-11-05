#!/usr/bin/env python3

import time
from core.csv_parser import CSVParser
from core.program_model import ScratchDeskProgram

def main():
    print("Scratch Desk Program Manager for Raspberry Pi")
    print("=" * 50)
    
    parser = CSVParser()
    
    while True:
        print("\nOptions:")
        print("1. Load and validate CSV file")
        print("2. Create new program")
        print("3. List all programs")
        print("4. Save programs to CSV")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            load_csv(parser)
        elif choice == "2":
            create_program()
        elif choice == "3":
            list_programs(parser)
        elif choice == "4":
            save_csv(parser)
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

def load_csv(parser):
    file_path = input("Enter CSV file path (or press Enter for 'sample_programs.csv'): ").strip()
    if not file_path:
        file_path = "sample_programs.csv"
    
    print(f"\nLoading programs from {file_path}...")
    programs, errors = parser.load_programs_from_csv(file_path)
    
    if errors:
        print("\nErrors found:")
        for error in errors:
            print(f"  - {error}")
    
    if programs:
        print(f"\nSuccessfully loaded {len(programs)} valid programs:")
        for program in programs:
            print(f"  - {program}")
    
    return programs

def create_program():
    print("\nCreate New Program")
    print("-" * 20)
    
    try:
        program_number = int(input("Program number: "))
        program_name = input("Program name: ")
        
        print("\nLines marking parameters:")
        general_high = float(input("General height: "))
        top_buffer = float(input("Top buffer: "))
        bottom_buffer = float(input("Bottom buffer: "))
        number_of_lines = int(input("Number of lines: "))
        line_width = float(input("Line width: "))
        
        print("\nRow making parameters:")
        general_width = float(input("General width: "))
        page_margin = float(input("Page margin: "))
        number_of_pages = int(input("Number of pages: "))
        page_width = float(input("Page width: "))
        
        program = ScratchDeskProgram(
            program_number, program_name, general_high, top_buffer,
            bottom_buffer, number_of_lines, line_width, general_width,
            page_margin, number_of_pages, page_width
        )
        
        validation_errors = program.validate()
        if validation_errors:
            print("\nValidation errors:")
            for error in validation_errors:
                print(f"  - {error}")
        else:
            print(f"\nProgram created successfully: {program}")
            
        return program
    
    except ValueError as e:
        print(f"Error: Invalid input - {e}")
        return None

def list_programs(parser):
    file_path = input("Enter CSV file path (or press Enter for 'sample_programs.csv'): ").strip()
    if not file_path:
        file_path = "sample_programs.csv"
    
    programs, errors = parser.load_programs_from_csv(file_path)
    
    if errors:
        print("\nErrors found:")
        for error in errors:
            print(f"  - {error}")
        return
    
    if not programs:
        print("No programs found.")
        return
    
    print(f"\nFound {len(programs)} programs:")
    print("-" * 60)
    
    for program in programs:
        print(f"Program {program.program_number}: {program.program_name}")
        print(f"  Size: {program.general_width} x {program.general_height}")
        print(f"  Lines: {program.number_of_lines} (width: {program.line_width})")
        print(f"  Pages: {program.number_of_pages} (width: {program.page_width})")
        print(f"  Margins: {program.page_margin}")
        print(f"  Buffers: top={program.top_buffer}, bottom={program.bottom_buffer}")
        print()

def save_csv(parser):
    print("Save functionality requires programs in memory.")
    print("This is a placeholder for future implementation.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Program will exit.")
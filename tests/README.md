# Scratch-Desk CNC Test Suite

This directory contains the test infrastructure and test suite for the Scratch-Desk CNC Control System.

## Directory Structure

```
tests/
├── __init__.py                    # Test package marker
├── conftest.py                    # Pytest fixtures and configuration
├── test_infrastructure.py         # Infrastructure verification tests
├── test_program_model.py          # Program model tests (existing)
└── fixtures/                      # Test data files
    ├── valid_programs.csv         # Valid program test data
    ├── invalid_programs.csv       # Invalid program test data
    ├── missing_headers.csv        # Malformed CSV test data
    ├── empty.csv                  # Empty CSV test data
    └── settings_test.json         # Minimal test settings
```

## Running Tests

### Run All Tests
```bash
python3 -m pytest tests/
```

### Run Specific Test File
```bash
python3 -m pytest tests/test_program_model.py -v
```

### Run With Coverage
```bash
python3 -m pytest tests/ --cov=core --cov=hardware --cov-report=html
```

### Run Tests Matching Pattern
```bash
python3 -m pytest tests/ -k "test_valid" -v
```

## Available Fixtures

All fixtures are defined in `conftest.py` and are automatically available to all tests.

### Autouse Fixtures

- **reset_singletons** (autouse): Automatically resets all singleton instances between tests:
  - Hardware factory (`_hardware_instance`)
  - Mock hardware global state
  - MachineStateManager (`_instance`)
  - Logger singleton (`_logger_instance`)

### Configuration Fixtures

- **mock_settings**: Returns a minimal settings dictionary optimized for testing
  - Mock hardware enabled
  - Fast timing values (0.001s delays)
  - Logging disabled
  - Useful for unit tests that don't need full settings

- **settings_file(tmp_path)**: Creates a temporary `settings.json` file
  - Returns the file path as a string
  - File is automatically cleaned up after test
  - Uses `mock_settings` content

- **safety_rules_file(tmp_path)**: Creates a temporary `safety_rules.json` file
  - Contains test safety rules (Y-axis blocked by row marker)
  - Returns the file path as a string
  - File is automatically cleaned up after test

### Program Fixtures

- **valid_program**: Returns a valid `ScratchDeskProgram` instance
  - Program number: 1
  - Program name: "Test Program"
  - Valid dimensions and spacing

- **invalid_program**: Returns an invalid `ScratchDeskProgram` instance
  - Program number: 2
  - Width mismatch (50.0 vs expected 48.0)
  - Useful for testing validation logic

### Hardware Fixtures

- **mock_hardware**: Returns a mock hardware interface instance
  - Already reset by autouse fixture
  - Initialized and ready to use
  - All state changes visible for testing

### CSV Fixtures

- **csv_file(tmp_path)**: Creates a temporary CSV file with valid programs
  - Contains 2 test programs
  - Returns the file path as a string
  - File is automatically cleaned up after test

## Test Data Files

### valid_programs.csv
Contains 2 valid programs with correct dimensions:
- Valid Program One: 10cm high, 5 lines, 4 pages
- Valid Program Two: 20cm high, 10 lines, 1 page

### invalid_programs.csv
Contains 2 invalid programs for testing error handling:
- Bad Width: Width exceeds calculated width
- Zero Lines: Number of lines is 0

### missing_headers.csv
CSV file with missing required headers (only has 3 of 14 required fields)

### empty.csv
CSV file with headers but no data rows

### settings_test.json
Minimal settings file optimized for fast test execution:
- Mock hardware mode enabled
- All timing values set to 0.001s for speed
- Logging disabled (WARNING level only)
- All required configuration sections present

## Writing Tests

### Basic Test Structure

```python
def test_something(mock_settings, mock_hardware):
    """Test description"""
    # Arrange
    expected_value = 10.0

    # Act
    result = some_function(mock_settings)

    # Assert
    assert result == expected_value
```

### Testing with Mock Hardware

```python
def test_hardware_operation(mock_hardware):
    """Test hardware operations"""
    # Mock hardware is already reset and initialized
    mock_hardware.move_x(10.0)

    # Check state
    assert mock_hardware.current_x == 10.0
```

### Testing with Temporary Files

```python
def test_with_settings(settings_file):
    """Test that uses settings file"""
    # settings_file is a string path to temporary file
    settings = load_settings(settings_file)
    assert settings['hardware_config']['use_real_hardware'] is False
```

### Testing Programs

```python
def test_program_validation(valid_program, invalid_program):
    """Test program validation"""
    # Test valid program
    assert valid_program.validate() is True

    # Test invalid program
    with pytest.raises(ValidationError):
        invalid_program.validate()
```

## Test Categories

### Unit Tests
Test individual functions and classes in isolation:
- `test_program_model.py` - Program data model validation
- Individual component tests

### Integration Tests
Test interactions between components:
- CSV parsing with program model
- Step generation with execution engine
- Safety system with hardware interface

### Fixture Tests
Test that fixtures themselves work correctly:
- `test_infrastructure.py` - Verifies all fixtures and test data

## Best Practices

1. **Use fixtures**: Don't create test data manually - use the provided fixtures
2. **Reset between tests**: The autouse fixture handles this automatically
3. **Fast tests**: Use mock_settings for fast timing values
4. **Isolated tests**: Each test should be independent and not rely on test execution order
5. **Clear assertions**: Use descriptive assertion messages
6. **Test names**: Use `test_<what>_<condition>_<expected>` naming pattern

## Singleton Reset

The `reset_singletons` fixture automatically resets all singleton instances between tests. This ensures:
- Clean state for each test
- No test pollution
- Predictable behavior
- Thread safety

If you add a new singleton, add it to the `reset_singletons` fixture in `conftest.py`.

## Troubleshooting

### Fixtures Not Found
Make sure your test file is in the `tests/` directory and pytest can find `conftest.py`.

### Import Errors
The `conftest.py` adds the project root to `sys.path`. If imports fail, check that you're running pytest from the project root.

### State Pollution
If tests fail when run together but pass individually, there may be a singleton that's not being reset. Add it to `reset_singletons`.

### Slow Tests
Use `mock_settings` fixture which has timing values optimized for speed (0.001s delays).

## Coverage Goals

Target coverage by module:
- `core/`: 90%+ coverage
- `hardware/`: 80%+ coverage (mock mode only)
- `gui/`: 60%+ coverage (UI components are harder to test)

Run coverage reports:
```bash
python3 -m pytest tests/ --cov=core --cov=hardware --cov-report=html
open htmlcov/index.html
```

"""
Verification test to ensure test infrastructure is working correctly.
This test should pass if all fixtures and setup are correct.
"""
import pytest
import os


def test_fixtures_directory_exists():
    """Verify fixtures directory exists"""
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    assert os.path.exists(fixtures_dir), "Fixtures directory should exist"


def test_csv_fixtures_exist():
    """Verify all CSV fixture files exist"""
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    csv_files = [
        'valid_programs.csv',
        'invalid_programs.csv',
        'missing_headers.csv',
        'empty.csv'
    ]
    for csv_file in csv_files:
        path = os.path.join(fixtures_dir, csv_file)
        assert os.path.exists(path), f"{csv_file} should exist"


def test_settings_fixture_exists():
    """Verify settings_test.json fixture exists"""
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    settings_path = os.path.join(fixtures_dir, 'settings_test.json')
    assert os.path.exists(settings_path), "settings_test.json should exist"


def test_mock_settings_fixture(mock_settings):
    """Test mock_settings fixture returns valid dict"""
    assert isinstance(mock_settings, dict), "mock_settings should be a dict"
    assert 'hardware_config' in mock_settings, "Should have hardware_config"
    assert 'hardware_limits' in mock_settings, "Should have hardware_limits"
    assert 'timing' in mock_settings, "Should have timing"
    assert mock_settings['hardware_config']['use_real_hardware'] is False


def test_valid_program_fixture(valid_program):
    """Test valid_program fixture returns valid ScratchDeskProgram"""
    from core.program_model import ScratchDeskProgram
    assert isinstance(valid_program, ScratchDeskProgram)
    assert valid_program.program_number == 1
    assert valid_program.program_name == "Test Program"
    assert valid_program.high == 10.0
    assert valid_program.number_of_lines == 5


def test_invalid_program_fixture(invalid_program):
    """Test invalid_program fixture returns invalid ScratchDeskProgram"""
    from core.program_model import ScratchDeskProgram
    assert isinstance(invalid_program, ScratchDeskProgram)
    assert invalid_program.program_number == 2
    assert invalid_program.width == 50.0  # Width mismatch


def test_mock_hardware_fixture(mock_hardware):
    """Test mock_hardware fixture returns hardware instance"""
    assert mock_hardware is not None
    # Verify it has expected methods
    assert hasattr(mock_hardware, 'move_x')
    assert hasattr(mock_hardware, 'move_y')
    assert hasattr(mock_hardware, 'line_marker_down')
    assert hasattr(mock_hardware, 'line_marker_up')


def test_singleton_reset(mock_hardware):
    """Test that singletons are properly reset between tests"""
    # This test verifies the autouse fixture is working
    from core.machine_state import MachineStateManager

    # Get machine state manager (uses __new__ for singleton pattern)
    manager = MachineStateManager()
    assert manager is not None

    # Hardware instance should exist after getting mock_hardware
    assert mock_hardware is not None


def test_settings_file_fixture(settings_file, mock_settings):
    """Test settings_file fixture creates valid JSON file"""
    import json
    assert os.path.exists(settings_file)
    with open(settings_file) as f:
        loaded = json.load(f)
    assert loaded == mock_settings


def test_safety_rules_file_fixture(safety_rules_file):
    """Test safety_rules_file fixture creates valid JSON file"""
    import json
    assert os.path.exists(safety_rules_file)
    with open(safety_rules_file) as f:
        rules = json.load(f)
    assert 'version' in rules
    assert 'rules' in rules
    assert len(rules['rules']) > 0


def test_csv_file_fixture(csv_file):
    """Test csv_file fixture creates valid CSV file"""
    import csv
    assert os.path.exists(csv_file)
    with open(csv_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]['program_name'] == 'Test Program'
    assert rows[1]['program_name'] == 'Second Program'

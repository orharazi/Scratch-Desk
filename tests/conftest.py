import pytest
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress logger console output at import time (before any test runs)
import core.logger as _logger_mod
_suppress_logger = _logger_mod.get_logger()
_suppress_logger.console_output = False


@pytest.fixture(autouse=True)
def reset_singletons(monkeypatch):
    """Reset all singletons between tests and ensure mock hardware mode"""
    # Keep logger suppressed (never reset the singleton)
    _suppress_logger.console_output = False

    # Reset hardware factory
    import hardware.interfaces.hardware_factory as hf
    hf._hardware_instance = None

    # Force mock hardware mode by patching the config loader
    def mock_load_config(config_path="config/settings.json"):
        """Return mock hardware config for all tests"""
        with open(config_path, 'r') as f:
            config = json.load(f)
        if 'hardware_config' not in config:
            config['hardware_config'] = {}
        config['hardware_config']['use_real_hardware'] = False
        return config

    monkeypatch.setattr(hf, 'load_config', mock_load_config)

    # Reset MachineStateManager
    from core.machine_state import MachineStateManager, MachineState
    MachineStateManager._instance = None

    # Reset mock hardware global state
    from hardware.implementations.mock import mock_hardware
    mock_hardware.reset_hardware()

    yield

    # Cleanup after test
    hf._hardware_instance = None
    MachineStateManager._instance = None

@pytest.fixture
def mock_settings():
    """Minimal settings dict for testing"""
    return {
        "hardware_config": {"use_real_hardware": False},
        "hardware_limits": {
            "max_x_position": 120.0,
            "max_y_position": 80.0,
            "min_x_position": 0.0,
            "min_y_position": 0.0,
            "paper_start_x": 15.0,
            "paper_start_y": 15.0,
            "min_line_spacing": 0.3
        },
        "timing": {
            "motor_movement_delay_per_cm": 0.001,
            "max_motor_movement_delay": 0.01,
            "tool_action_delay": 0.001,
            "sensor_wait_timeout": 2.0,
            "sensor_poll_timeout": 0.01,
            "row_marker_stable_delay": 0.01,
            "execution_loop_delay": 0.001,
            "thread_join_timeout_execution": 1.0,
            "thread_join_timeout_safety": 0.5,
            "safety_check_interval": 0.01,
            "transition_monitor_interval": 0.01
        },
        "safety": {
            "setup_movement_keywords": ["home position", "ensure", "init:"],
            "rows_start_position_keywords": ["rows start:"]
        },
        "logging": {
            "level": "WARNING",
            "console_output": False,
            "file_output": False,
            "use_colors": False,
            "use_icons": False,
            "categories": {}
        }
    }

@pytest.fixture
def settings_file(tmp_path, mock_settings):
    """Create temporary settings.json"""
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(mock_settings))
    return str(path)

@pytest.fixture
def safety_rules_file(tmp_path):
    """Create temporary safety_rules.json with test rules"""
    rules = {
        "version": "1.0.0",
        "global_enabled": True,
        "available_directions": {
            "move_x": {"positive": "positive", "negative": "negative"},
            "move_y": {"positive": "positive", "negative": "negative"}
        },
        "rules": [
            {
                "id": "Y_AXIS_BLOCKED",
                "name": "Y-Axis Blocked by Row Marker",
                "enabled": True,
                "priority": 10,
                "conditions": {
                    "operator": "OR",
                    "items": [
                        {"type": "piston", "source": "row_marker", "operator": "equals", "value": "down"}
                    ]
                },
                "blocked_operations": [
                    {"operation": "move_y", "exclude_setup": True, "exclude_rows_start": False}
                ],
                "message": "Cannot move Y-axis! Row marker is DOWN."
            }
        ]
    }
    path = tmp_path / "safety_rules.json"
    path.write_text(json.dumps(rules))
    return str(path)

@pytest.fixture
def valid_program():
    """Return a valid ScratchDeskProgram"""
    from core.program_model import ScratchDeskProgram
    return ScratchDeskProgram(
        program_number=1, program_name="Test Program",
        high=10.0, number_of_lines=5, top_padding=2.0, bottom_padding=2.0,
        width=48.0, left_margin=5.0, right_margin=5.0,
        page_width=8.0, number_of_pages=4, buffer_between_pages=2.0,
        repeat_rows=1, repeat_lines=1
    )

@pytest.fixture
def invalid_program():
    """Return an invalid program (width mismatch)"""
    from core.program_model import ScratchDeskProgram
    return ScratchDeskProgram(
        program_number=2, program_name="Bad Program",
        high=10.0, number_of_lines=5, top_padding=2.0, bottom_padding=2.0,
        width=50.0, left_margin=5.0, right_margin=5.0,
        page_width=8.0, number_of_pages=4, buffer_between_pages=2.0,
        repeat_rows=1, repeat_lines=1
    )

@pytest.fixture
def mock_hardware():
    """Get mock hardware instance (already reset by autouse fixture)"""
    from hardware.interfaces.hardware_factory import get_hardware_interface
    hw = get_hardware_interface()
    if hasattr(hw, 'initialize'):
        hw.initialize()
    return hw

@pytest.fixture
def csv_file(tmp_path):
    """Create temporary CSV with valid programs"""
    csv_content = '''program_number,program_name,high,number_of_lines,top_padding,bottom_padding,width,left_margin,right_margin,page_width,number_of_pages,buffer_between_pages,repeat_rows,repeat_lines
1,Test Program,10,5,2,2,48,5,5,8,4,2,1,1
2,Second Program,20,10,3,3,24,2,2,20,1,0,2,1'''
    path = tmp_path / "programs.csv"
    path.write_text(csv_content)
    return str(path)

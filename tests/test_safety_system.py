#!/usr/bin/env python3

"""
Comprehensive tests for the safety system (core/safety_system.py)

Tests cover:
- SafetyViolation exception
- SafetyRulesManager (rule loading, condition evaluation, operation blocking)
- SafetySystem (enable/disable, step checking, violations log)
"""

import pytest
import json
import os
import time
from unittest.mock import patch, MagicMock

# Import the modules under test
from core.safety_system import (
    SafetyViolation,
    SafetyRulesManager,
    SafetySystem,
    load_settings
)
from hardware.interfaces.hardware_factory import get_hardware_interface


# ==================== TestSafetyViolation ====================

class TestSafetyViolation:
    """Tests for SafetyViolation exception class"""

    def test_exception_attributes(self):
        """Test that message and safety_code are set correctly"""
        msg = "Test violation message"
        code = "TEST_CODE"
        violation = SafetyViolation(msg, code)

        assert violation.message == msg
        assert violation.safety_code == code
        assert str(violation) == msg

    def test_exception_without_code(self):
        """Test that safety_code defaults to None when not provided"""
        msg = "Test violation without code"
        violation = SafetyViolation(msg)

        assert violation.message == msg
        assert violation.safety_code is None


# ==================== TestSafetyRulesManager ====================

class TestSafetyRulesManager:
    """Tests for SafetyRulesManager class"""

    def test_load_rules_from_file(self):
        """Test rules are loaded from the real safety_rules.json file"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        # Should have loaded rules from the actual file
        assert isinstance(manager.rules_data, dict)
        assert isinstance(manager.rules, list)
        # The real file has rules
        if os.path.exists(manager.RULES_FILE):
            assert len(manager.rules) > 0

    def test_load_rules_missing_file(self, tmp_path, monkeypatch):
        """Test fallback to empty rules when file is missing"""
        hw = get_hardware_interface()

        # Point to non-existent file
        missing_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr(SafetyRulesManager, 'RULES_FILE', str(missing_file))

        manager = SafetyRulesManager(hw)

        assert manager.rules_data == {"global_enabled": True, "rules": []}
        assert manager.rules == []
        assert manager._rules_file_mtime == 0

    def test_load_rules_invalid_json(self, tmp_path, monkeypatch):
        """Test fallback to empty rules when JSON is invalid"""
        hw = get_hardware_interface()

        # Create file with invalid JSON
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{invalid json content")
        monkeypatch.setattr(SafetyRulesManager, 'RULES_FILE', str(invalid_file))

        manager = SafetyRulesManager(hw)

        assert manager.rules_data == {"global_enabled": True, "rules": []}
        assert manager.rules == []
        assert manager._rules_file_mtime == 0

    def test_rules_cached_by_mtime(self, tmp_path, monkeypatch):
        """Test that rules with same mtime are not reloaded"""
        hw = get_hardware_interface()

        # Create a valid rules file
        rules_file = tmp_path / "test_rules.json"
        rules_data = {
            "global_enabled": True,
            "rules": [
                {
                    "id": "TEST_RULE",
                    "name": "Test Rule",
                    "enabled": True,
                    "conditions": {"operator": "AND", "items": []},
                    "blocked_operations": []
                }
            ]
        }
        rules_file.write_text(json.dumps(rules_data))
        monkeypatch.setattr(SafetyRulesManager, 'RULES_FILE', str(rules_file))

        manager = SafetyRulesManager(hw)
        initial_mtime = manager._rules_file_mtime
        initial_rules = manager.rules.copy()

        # Load again without changing file - mtime should prevent reload
        manager.load_rules()

        assert manager._rules_file_mtime == initial_mtime
        assert manager.rules == initial_rules

    def test_globally_enabled_default(self, tmp_path, monkeypatch):
        """Test that global_enabled defaults to True"""
        hw = get_hardware_interface()

        # Create rules file without global_enabled
        rules_file = tmp_path / "test_rules.json"
        rules_data = {"rules": []}
        rules_file.write_text(json.dumps(rules_data))
        monkeypatch.setattr(SafetyRulesManager, 'RULES_FILE', str(rules_file))

        manager = SafetyRulesManager(hw)

        assert manager.is_globally_enabled() is True


# ==================== TestEvaluateCondition ====================

class TestEvaluateCondition:
    """Tests for SafetyRulesManager.evaluate_condition"""

    def test_piston_equals_match(self):
        """Test piston condition with equals operator matching"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {"row_marker": "down"},
            "sensors": {},
            "positions": {}
        }
        condition = {
            "type": "piston",
            "source": "row_marker",
            "operator": "equals",
            "value": "down"
        }

        result = manager.evaluate_condition(condition, state)
        assert result is True

    def test_piston_equals_no_match(self):
        """Test piston condition with equals operator not matching"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {"row_marker": "up"},
            "sensors": {},
            "positions": {}
        }
        condition = {
            "type": "piston",
            "source": "row_marker",
            "operator": "equals",
            "value": "down"
        }

        result = manager.evaluate_condition(condition, state)
        assert result is False

    def test_sensor_equals_match(self):
        """Test sensor condition with equals operator"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {},
            "sensors": {"row_motor_limit_switch": "up"},
            "positions": {}
        }
        condition = {
            "type": "sensor",
            "source": "row_motor_limit_switch",
            "operator": "equals",
            "value": "up"
        }

        result = manager.evaluate_condition(condition, state)
        assert result is True

    def test_position_equals(self):
        """Test position condition with equals operator"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {},
            "sensors": {},
            "positions": {"x_position": 50.0}
        }
        condition = {
            "type": "position",
            "source": "x_position",
            "operator": "equals",
            "value": 50.0
        }

        result = manager.evaluate_condition(condition, state)
        assert result is True

    def test_not_equals_operator(self):
        """Test not_equals operator"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {"row_marker": "up"},
            "sensors": {},
            "positions": {}
        }
        condition = {
            "type": "piston",
            "source": "row_marker",
            "operator": "not_equals",
            "value": "down"
        }

        result = manager.evaluate_condition(condition, state)
        assert result is True

    def test_greater_than_operator(self):
        """Test greater_than operator"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {},
            "sensors": {},
            "positions": {"y_position": 25.0}
        }
        condition = {
            "type": "position",
            "source": "y_position",
            "operator": "greater_than",
            "value": 10.0
        }

        result = manager.evaluate_condition(condition, state)
        assert result is True

    def test_less_than_operator(self):
        """Test less_than operator"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {},
            "sensors": {},
            "positions": {"x_position": 5.0}
        }
        condition = {
            "type": "position",
            "source": "x_position",
            "operator": "less_than",
            "value": 10.0
        }

        result = manager.evaluate_condition(condition, state)
        assert result is True

    def test_unknown_source_returns_false(self):
        """Test that unknown source returns False"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {},
            "sensors": {},
            "positions": {}
        }
        condition = {
            "type": "piston",
            "source": "nonexistent_piston",
            "operator": "equals",
            "value": "down"
        }

        result = manager.evaluate_condition(condition, state)
        assert result is False

    def test_string_case_insensitive(self):
        """Test that string comparison is case-insensitive"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {"row_marker": "DOWN"},
            "sensors": {},
            "positions": {}
        }
        condition = {
            "type": "piston",
            "source": "row_marker",
            "operator": "equals",
            "value": "down"
        }

        result = manager.evaluate_condition(condition, state)
        assert result is True


# ==================== TestEvaluateConditions ====================

class TestEvaluateConditions:
    """Tests for SafetyRulesManager.evaluate_conditions"""

    def test_and_all_true(self):
        """Test AND operator when all conditions are true"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {"row_marker": "down", "line_marker": "up"},
            "sensors": {},
            "positions": {}
        }
        conditions = {
            "operator": "AND",
            "items": [
                {"type": "piston", "source": "row_marker", "operator": "equals", "value": "down"},
                {"type": "piston", "source": "line_marker", "operator": "equals", "value": "up"}
            ]
        }

        result = manager.evaluate_conditions(conditions, state)
        assert result is True

    def test_and_one_false(self):
        """Test AND operator when one condition is false"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {"row_marker": "down", "line_marker": "down"},
            "sensors": {},
            "positions": {}
        }
        conditions = {
            "operator": "AND",
            "items": [
                {"type": "piston", "source": "row_marker", "operator": "equals", "value": "down"},
                {"type": "piston", "source": "line_marker", "operator": "equals", "value": "up"}
            ]
        }

        result = manager.evaluate_conditions(conditions, state)
        assert result is False

    def test_or_one_true(self):
        """Test OR operator when one condition is true"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {"row_marker": "down", "line_marker": "down"},
            "sensors": {},
            "positions": {}
        }
        conditions = {
            "operator": "OR",
            "items": [
                {"type": "piston", "source": "row_marker", "operator": "equals", "value": "down"},
                {"type": "piston", "source": "line_marker", "operator": "equals", "value": "up"}
            ]
        }

        result = manager.evaluate_conditions(conditions, state)
        assert result is True

    def test_or_all_false(self):
        """Test OR operator when all conditions are false"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {"row_marker": "up", "line_marker": "up"},
            "sensors": {},
            "positions": {}
        }
        conditions = {
            "operator": "OR",
            "items": [
                {"type": "piston", "source": "row_marker", "operator": "equals", "value": "down"},
                {"type": "piston", "source": "line_marker", "operator": "equals", "value": "down"}
            ]
        }

        result = manager.evaluate_conditions(conditions, state)
        assert result is False

    def test_empty_conditions_returns_false(self):
        """Test that empty conditions dict returns False"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {},
            "sensors": {},
            "positions": {}
        }

        result = manager.evaluate_conditions({}, state)
        assert result is False

    def test_empty_items_returns_false(self):
        """Test that empty items list returns False"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)

        state = {
            "pistons": {},
            "sensors": {},
            "positions": {}
        }
        conditions = {
            "operator": "AND",
            "items": []
        }

        result = manager.evaluate_conditions(conditions, state)
        assert result is False


# ==================== TestCheckOperationBlocked ====================

class TestCheckOperationBlocked:
    """Tests for SafetyRulesManager.check_operation_blocked"""

    def test_operation_blocked(self):
        """Test that matching operation is blocked"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)
        manager.rules_data = {"available_directions": {}}

        rule = {
            "blocked_operations": [
                {"operation": "move_y"}
            ]
        }

        result = manager.check_operation_blocked(rule, "move_y")
        assert result is True

    def test_operation_not_blocked(self):
        """Test that non-matching operation is not blocked"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)
        manager.rules_data = {"available_directions": {}}

        rule = {
            "blocked_operations": [
                {"operation": "move_y"}
            ]
        }

        result = manager.check_operation_blocked(rule, "move_x")
        assert result is False

    def test_setup_excluded(self):
        """Test that setup movements are excluded when exclude_setup is True"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)
        manager.rules_data = {"available_directions": {}}

        rule = {
            "blocked_operations": [
                {"operation": "move_y", "exclude_setup": True}
            ]
        }

        # With is_setup=True, operation should not be blocked
        result = manager.check_operation_blocked(rule, "move_y", is_setup=True)
        assert result is False

        # Without is_setup, operation should be blocked
        result = manager.check_operation_blocked(rule, "move_y", is_setup=False)
        assert result is True

    def test_rows_start_excluded(self):
        """Test that rows_start movements are excluded when exclude_rows_start is True"""
        hw = get_hardware_interface()
        manager = SafetyRulesManager(hw)
        manager.rules_data = {"available_directions": {}}

        rule = {
            "blocked_operations": [
                {"operation": "move_x", "exclude_rows_start": True}
            ]
        }

        # With is_rows_start=True, operation should not be blocked
        result = manager.check_operation_blocked(rule, "move_x", is_rows_start=True)
        assert result is False

        # Without is_rows_start, operation should be blocked
        result = manager.check_operation_blocked(rule, "move_x", is_rows_start=False)
        assert result is True


# ==================== TestSafetySystem ====================

class TestSafetySystem:
    """Tests for SafetySystem class"""

    def test_enable_disable(self):
        """Test enabling and disabling safety system"""
        safety = SafetySystem()

        # Should start enabled
        assert safety.safety_enabled is True

        # Disable
        safety.disable_safety()
        assert safety.safety_enabled is False

        # Enable
        safety.enable_safety()
        assert safety.safety_enabled is True

    def test_check_step_safety_passes(self):
        """Test that safe step passes safety check (row marker up, move_y)"""
        safety = SafetySystem()
        hw = safety.hardware

        # Set row marker up (safe state)
        hw.row_marker_up()

        step = {
            "operation": "move_y",
            "parameters": {"position": 25.0},
            "description": "Test Y movement"
        }

        # Should not raise exception
        result = safety.check_step_safety(step)
        assert result is True

    def test_check_step_safety_raises(self, monkeypatch):
        """Test that unsafe step raises SafetyViolation (row marker down, move_y)"""
        # Force mock hardware mode
        def mock_load_config(path="config/settings.json"):
            return {"hardware_config": {"use_real_hardware": False}}

        monkeypatch.setattr("hardware.interfaces.hardware_factory.load_config", mock_load_config)

        hw = get_hardware_interface()
        safety = SafetySystem()

        # Initialize hardware if needed
        if hasattr(hw, 'initialize') and not getattr(hw, 'is_initialized', True):
            hw.initialize()

        # Set row marker down (unsafe for Y movement)
        hw.row_marker_down()

        step = {
            "operation": "move_y",
            "parameters": {"position": 25.0},
            "description": "Test Y movement"
        }

        # Should raise SafetyViolation
        with pytest.raises(SafetyViolation) as exc_info:
            safety.check_step_safety(step)

        assert exc_info.value.safety_code is not None
        assert "Y-axis" in str(exc_info.value) or "row marker" in str(exc_info.value).lower()

    def test_violations_log(self):
        """Test that violations are logged"""
        safety = SafetySystem()

        initial_count = len(safety.violations_log)

        safety.log_violation("TEST_CODE", "Test violation message")

        assert len(safety.violations_log) == initial_count + 1
        last_violation = safety.violations_log[-1]
        assert last_violation["safety_code"] == "TEST_CODE"
        assert last_violation["message"] == "Test violation message"
        assert "timestamp" in last_violation

    def test_violations_log_max_100(self):
        """Test that violations log is capped at 100 entries"""
        safety = SafetySystem()
        safety.violations_log = []  # Clear existing

        # Add 150 violations
        for i in range(150):
            safety.log_violation(f"CODE_{i}", f"Message {i}")

        # Should keep only last 100
        assert len(safety.violations_log) == 100
        # First violation should be #50 (oldest kept)
        assert safety.violations_log[0]["safety_code"] == "CODE_50"
        # Last violation should be #149
        assert safety.violations_log[-1]["safety_code"] == "CODE_149"

    def test_setup_movement_detection(self):
        """Test that setup movements are correctly detected"""
        safety = SafetySystem()

        # These should be detected as setup movements
        assert safety._is_setup_movement("Init: Moving to home position") is True
        assert safety._is_setup_movement("Ensure motor at home") is True
        assert safety._is_setup_movement("Move rows motor to home") is True

        # These should not be detected as setup movements
        assert safety._is_setup_movement("Mark line 1") is False
        assert safety._is_setup_movement("Cut row 5") is False

    def test_rows_start_movement_detection(self):
        """Test that rows_start movements are correctly detected"""
        safety = SafetySystem()

        # Should be detected as rows_start
        assert safety._is_rows_start_movement("Rows start: Move to position") is True

        # Should not be detected as rows_start
        assert safety._is_rows_start_movement("Move to home position") is False
        assert safety._is_rows_start_movement("Mark row 1") is False

    def test_get_safety_status_fields(self):
        """Test that get_safety_status returns expected fields"""
        safety = SafetySystem()

        status = safety.get_safety_status()

        # Check all expected fields are present
        assert "enabled" in status
        assert "global_enabled" in status
        assert "rules_count" in status
        assert "recent_violations" in status
        assert "row_marker_programmed" in status
        assert "row_marker_limit_switch" in status
        assert "current_position" in status

        # Check types
        assert isinstance(status["enabled"], bool)
        assert isinstance(status["global_enabled"], bool)
        assert isinstance(status["rules_count"], int)
        assert isinstance(status["recent_violations"], int)
        assert isinstance(status["current_position"], dict)
        assert "x" in status["current_position"]
        assert "y" in status["current_position"]

    def test_check_step_safety_disabled(self):
        """Test that safety checks are bypassed when disabled"""
        safety = SafetySystem()
        hw = safety.hardware

        # Disable safety
        safety.disable_safety()

        # Set row marker down (would normally block Y movement)
        hw.row_marker_down()

        step = {
            "operation": "move_y",
            "parameters": {"position": 25.0},
            "description": "Test Y movement"
        }

        # Should pass even though row marker is down
        result = safety.check_step_safety(step)
        assert result is True


# ==================== Integration Tests ====================

class TestSafetySystemIntegration:
    """Integration tests for complete safety scenarios"""

    def test_y_axis_blocked_scenario(self, monkeypatch):
        """Test complete Y-axis blocking scenario with real rules"""
        # Force mock hardware mode
        def mock_load_config(path="config/settings.json"):
            return {"hardware_config": {"use_real_hardware": False}}

        monkeypatch.setattr("hardware.interfaces.hardware_factory.load_config", mock_load_config)

        hw = get_hardware_interface()
        safety = SafetySystem()

        # Initialize hardware if needed
        if hasattr(hw, 'initialize') and not getattr(hw, 'is_initialized', True):
            hw.initialize()

        # Scenario: Try to move Y-axis with row marker down
        hw.row_marker_down()

        step = {
            "operation": "move_y",
            "parameters": {"position": 30.0},
            "description": "Move to line position"
        }

        # Should block the movement
        with pytest.raises(SafetyViolation) as exc_info:
            safety.check_step_safety(step)

        # Violation should be logged
        assert len(safety.violations_log) > 0

        # Fix the issue
        hw.row_marker_up()

        # Now should pass
        result = safety.check_step_safety(step)
        assert result is True

    def test_setup_movement_bypass(self):
        """Test that setup movements bypass rules with exclude_setup=True.
        LINES_DOOR_SAFETY has exclude_setup=True, so setup movements bypass it.
        We trigger it via row_motor_limit_switch (not a tool piston) to avoid
        ALL_TOOLS_UP_FOR_END_DIVISION which has exclude_setup=False."""
        safety = SafetySystem()
        hw = safety.hardware

        # Trigger LINES_DOOR_SAFETY via limit switch (not tool piston)
        # rows_door=True → row_motor_limit_switch="down" → triggers LINES_DOOR_SAFETY
        hw.set_limit_switch_state('rows_door', True)

        # Setup movement should bypass LINES_DOOR_SAFETY (exclude_setup=True)
        step = {
            "operation": "move_y",
            "parameters": {"position": 0.0},
            "description": "Init: Move to home position"
        }

        result = safety.check_step_safety(step)
        assert result is True

    def test_multiple_rules_priority(self, monkeypatch):
        """Test that rules are evaluated by priority"""
        # Force mock hardware mode
        def mock_load_config(path="config/settings.json"):
            return {"hardware_config": {"use_real_hardware": False}}

        monkeypatch.setattr("hardware.interfaces.hardware_factory.load_config", mock_load_config)

        hw = get_hardware_interface()
        safety = SafetySystem()

        # Initialize hardware if needed
        if hasattr(hw, 'initialize') and not getattr(hw, 'is_initialized', True):
            hw.initialize()

        # Create a state that could trigger multiple rules
        hw.row_marker_down()

        step = {
            "operation": "move_y",
            "parameters": {"position": 25.0},
            "description": "Test movement"
        }

        # Should raise violation (from highest priority rule)
        with pytest.raises(SafetyViolation) as exc_info:
            safety.check_step_safety(step)

        # Check that the violation has a safety_code (from the rule)
        assert exc_info.value.safety_code is not None

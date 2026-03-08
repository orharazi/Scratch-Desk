#!/usr/bin/env python3
"""
Tests for unexpected tool detection during execution.

Verifies that when a piston (cutter/marker) is manually toggled DOWN during
execution, the system:
1. Detects the unexpected tool state
2. Pauses execution
3. Sends emergency_stop status with correct safety_code and violation_message
4. Auto-recovers when the tool is raised
5. Does NOT false-positive when the engine itself lowers a tool
"""

import pytest
import threading
import time
from unittest.mock import MagicMock, patch, call
from core.execution_engine import ExecutionEngine
from core.machine_state import MachineState, MachineStateManager
from hardware.interfaces.hardware_factory import get_hardware_interface


def _ensure_safety_clear():
    """Disable JSON-based safety rules so only unexpected-tool detection runs."""
    from core.safety_system import safety_system
    safety_system.disable_safety()
    safety_system.rules_manager.rules_data['global_enabled'] = False
    safety_system.rules_manager.rules = []


# ==================== _get_unexpected_tools_down() unit tests ====================

class TestGetUnexpectedToolsDown:
    """Tests for _get_unexpected_tools_down detection logic"""

    def test_no_unexpected_when_all_up(self):
        """All tools up → no unexpected tools"""
        engine = ExecutionEngine()
        engine.current_operation_type = 'lines'
        engine._engine_lowered_tools = set()

        result = engine._get_unexpected_tools_down()
        assert result == []

    def test_detects_line_marker_down_during_lines(self):
        """line_marker manually lowered during lines → detected"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = 'lines'
        engine._engine_lowered_tools = set()

        hw.line_marker_down()
        result = engine._get_unexpected_tools_down()
        assert 'line_marker' in result

    def test_detects_line_cutter_down_during_lines(self):
        """line_cutter manually lowered during lines → detected"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = 'lines'
        engine._engine_lowered_tools = set()

        hw.line_cutter_down()
        result = engine._get_unexpected_tools_down()
        assert 'line_cutter' in result

    def test_detects_row_marker_down_during_rows(self):
        """row_marker manually lowered during rows → detected"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = 'rows'
        engine._engine_lowered_tools = set()

        hw.row_marker_down()
        result = engine._get_unexpected_tools_down()
        assert 'row_marker' in result

    def test_detects_row_cutter_down_during_rows(self):
        """row_cutter manually lowered during rows → detected"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = 'rows'
        engine._engine_lowered_tools = set()

        hw.row_cutter_down()
        result = engine._get_unexpected_tools_down()
        assert 'row_cutter' in result

    def test_detects_multiple_tools_down(self):
        """Multiple tools manually lowered → all detected"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = 'lines'
        engine._engine_lowered_tools = set()

        hw.line_marker_down()
        hw.line_cutter_down()
        result = engine._get_unexpected_tools_down()
        assert len(result) == 2
        assert 'line_marker' in result
        assert 'line_cutter' in result

    def test_engine_lowered_tool_not_flagged(self):
        """Tool lowered by engine (tracked) → NOT flagged as unexpected"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = 'lines'

        # Engine intentionally lowers line_marker
        engine._engine_lowered_tools = {'line_marker'}
        hw.line_marker_down()

        result = engine._get_unexpected_tools_down()
        assert 'line_marker' not in result

    def test_engine_lowered_one_manual_other(self):
        """One tool lowered by engine, another manually → only manual detected"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = 'lines'

        engine._engine_lowered_tools = {'line_marker'}
        hw.line_marker_down()
        hw.line_cutter_down()

        result = engine._get_unexpected_tools_down()
        assert 'line_marker' not in result
        assert 'line_cutter' in result

    def test_no_operation_type_returns_empty(self):
        """No current_operation_type → empty (no checks)"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = None
        engine._engine_lowered_tools = set()

        hw.line_marker_down()
        result = engine._get_unexpected_tools_down()
        assert result == []

    def test_line_tools_ignored_during_rows(self):
        """Line tools down during rows → NOT checked (cross-axis tools irrelevant)"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = 'rows'
        engine._engine_lowered_tools = set()

        hw.line_marker_down()
        hw.line_cutter_down()
        result = engine._get_unexpected_tools_down()
        assert result == []

    def test_row_tools_ignored_during_lines(self):
        """Row tools down during lines → NOT checked by unexpected tool detection
        (row tools during lines are caught by LINES_DOOR_SAFETY monitor rule instead)"""
        engine = ExecutionEngine()
        hw = engine.hardware
        engine.current_operation_type = 'lines'
        engine._engine_lowered_tools = set()

        hw.row_marker_down()
        hw.row_cutter_down()
        result = engine._get_unexpected_tools_down()
        assert result == []


# ==================== Engine tool tracking tests ====================

class TestEngineToolTracking:
    """Tests that _execute_step correctly tracks tools in _engine_lowered_tools"""

    def test_tool_tracked_on_down(self):
        """tool_action down → tool added to _engine_lowered_tools BEFORE hardware call"""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        step = {
            'operation': 'tool_action',
            'parameters': {'tool': 'line_marker', 'action': 'down'},
            'description': 'Lower line marker'
        }
        engine._execute_step(step)

        assert 'line_marker' in engine._engine_lowered_tools

    def test_tool_untracked_on_up(self):
        """tool_action up → tool removed from _engine_lowered_tools AFTER hardware call"""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        # First lower
        step_down = {
            'operation': 'tool_action',
            'parameters': {'tool': 'line_cutter', 'action': 'down'},
            'description': 'Lower line cutter'
        }
        engine._execute_step(step_down)
        assert 'line_cutter' in engine._engine_lowered_tools

        # Then raise
        step_up = {
            'operation': 'tool_action',
            'parameters': {'tool': 'line_cutter', 'action': 'up'},
            'description': 'Raise line cutter'
        }
        engine._execute_step(step_up)
        assert 'line_cutter' not in engine._engine_lowered_tools

    def test_tracking_cleared_on_start(self):
        """_engine_lowered_tools cleared when execution starts"""
        engine = ExecutionEngine()
        engine._engine_lowered_tools = {'line_marker', 'row_cutter'}
        engine.steps = [{'operation': 'program_start', 'parameters': {}, 'description': 'Start'}]

        _ensure_safety_clear()
        engine.start_execution()
        time.sleep(0.2)

        assert engine._engine_lowered_tools == set()
        engine.stop_execution()
        time.sleep(0.1)

    def test_all_four_tools_tracked(self):
        """All 4 tool types are correctly tracked"""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        tools = ['line_marker', 'line_cutter', 'row_marker', 'row_cutter']
        for tool in tools:
            step = {
                'operation': 'tool_action',
                'parameters': {'tool': tool, 'action': 'down'},
                'description': f'Lower {tool}'
            }
            engine._execute_step(step)
            assert tool in engine._engine_lowered_tools, f"{tool} should be tracked after down"

        for tool in tools:
            step = {
                'operation': 'tool_action',
                'parameters': {'tool': tool, 'action': 'up'},
                'description': f'Raise {tool}'
            }
            engine._execute_step(step)
            assert tool not in engine._engine_lowered_tools, f"{tool} should be untracked after up"


# ==================== Safety monitor integration tests ====================

class TestUnexpectedToolSafetyMonitor:
    """Integration tests for unexpected tool detection in the safety monitor loop"""

    def test_unexpected_tool_triggers_emergency_stop(self):
        """Manually lowering a tool during execution triggers emergency_stop status"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        # Capture status callbacks
        status_calls = []
        def capture_status(status, info=None):
            status_calls.append((status, info))

        engine.set_status_callback(capture_status)

        # Use a wait_sensor step to keep execution running
        hw.set_execution_engine_reference(engine)
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': '1'}, 'description': 'Start'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X sensor'},
        ]
        engine.load_steps(steps)
        engine.current_operation_type = 'lines'
        engine.start_execution()

        # Wait for execution to reach the wait_sensor step
        time.sleep(0.5)

        # Manually lower line_marker (simulating user toggle)
        hw.line_marker_down()

        # Wait for safety monitor to detect it (checks every ~100ms)
        time.sleep(0.5)

        # Check that emergency_stop was sent
        emergency_stops = [(s, i) for s, i in status_calls if s == 'emergency_stop']
        assert len(emergency_stops) >= 1, f"Expected emergency_stop status, got: {[s for s, _ in status_calls]}"

        info = emergency_stops[0][1]
        assert info['safety_code'] == 'LINE_TOOLS_UP_FOR_LINES'
        assert 'line_marker' in info['violation_message']
        assert info['monitor_type'] == 'unexpected_tool'

        # Execution should be paused
        assert engine.is_paused is True

        # Cleanup
        engine.stop_execution()
        time.sleep(0.2)

    def test_unexpected_tool_auto_recovery(self):
        """Raising the unexpected tool triggers safety_recovered and resumes execution"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        status_calls = []
        def capture_status(status, info=None):
            status_calls.append((status, info))

        engine.set_status_callback(capture_status)

        hw.set_execution_engine_reference(engine)
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': '1'}, 'description': 'Start'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X sensor'},
        ]
        engine.load_steps(steps)
        engine.current_operation_type = 'lines'
        engine.start_execution()

        time.sleep(0.3)

        # Manually lower tool
        hw.line_cutter_down()
        time.sleep(0.5)

        # Verify paused
        assert engine.is_paused is True

        # Now raise the tool (recovery)
        hw.line_cutter_up()
        time.sleep(0.5)

        # Check for safety_recovered status
        recoveries = [(s, i) for s, i in status_calls if s == 'safety_recovered']
        assert len(recoveries) >= 1, f"Expected safety_recovered status, got: {[s for s, _ in status_calls]}"

        # Execution should have resumed
        assert engine.is_paused is False

        # Cleanup
        engine.stop_execution()
        time.sleep(0.2)

    def test_engine_lowered_tool_no_false_positive(self):
        """Tool lowered by execution engine does NOT trigger unexpected tool detection"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        status_calls = []
        def capture_status(status, info=None):
            status_calls.append((status, info))

        engine.set_status_callback(capture_status)

        hw.set_execution_engine_reference(engine)

        # Steps that intentionally lower and raise line_marker
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': '1'}, 'description': 'Start'},
            {'operation': 'tool_action', 'parameters': {'tool': 'line_marker', 'action': 'down'},
             'description': 'Lower line marker'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X sensor'},
        ]
        engine.load_steps(steps)
        engine.current_operation_type = 'lines'
        engine.start_execution()

        # Wait for tool_action to execute and sensor wait to start
        time.sleep(0.5)

        # line_marker should be tracked as engine-lowered
        assert 'line_marker' in engine._engine_lowered_tools

        # Wait enough time for safety monitor to have checked
        time.sleep(0.3)

        # Should NOT have triggered emergency_stop
        emergency_stops = [(s, i) for s, i in status_calls if s == 'emergency_stop']
        assert len(emergency_stops) == 0, (
            f"Engine-lowered tool should not trigger emergency_stop, but got: "
            f"{[i.get('violation_message', '') for _, i in emergency_stops]}"
        )

        # Cleanup
        engine.stop_execution()
        time.sleep(0.2)

    def test_row_tool_during_rows_triggers_emergency(self):
        """row_marker manually lowered during rows execution triggers emergency_stop"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        status_calls = []
        def capture_status(status, info=None):
            status_calls.append((status, info))

        engine.set_status_callback(capture_status)

        hw.set_execution_engine_reference(engine)
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': '1'}, 'description': 'Start'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'y'}, 'description': 'Wait Y sensor'},
        ]
        engine.load_steps(steps)
        engine.current_operation_type = 'rows'
        engine.start_execution()

        time.sleep(0.3)

        # Manually lower row_marker
        hw.row_marker_down()
        time.sleep(0.5)

        # Check emergency_stop with rows safety code
        emergency_stops = [(s, i) for s, i in status_calls if s == 'emergency_stop']
        assert len(emergency_stops) >= 1
        assert emergency_stops[0][1]['safety_code'] == 'ROW_TOOLS_UP_FOR_ROWS'

        # Cleanup
        engine.stop_execution()
        time.sleep(0.2)

    def test_emergency_stop_info_has_required_fields(self):
        """emergency_stop info dict has all fields needed for dialog display"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        status_calls = []
        def capture_status(status, info=None):
            status_calls.append((status, info))

        engine.set_status_callback(capture_status)

        hw.set_execution_engine_reference(engine)
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': '1'}, 'description': 'Start'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X sensor'},
        ]
        engine.load_steps(steps)
        engine.current_operation_type = 'lines'
        engine.start_execution()

        time.sleep(0.3)
        hw.line_marker_down()
        time.sleep(0.5)

        emergency_stops = [(s, i) for s, i in status_calls if s == 'emergency_stop']
        assert len(emergency_stops) >= 1

        info = emergency_stops[0][1]
        # Required fields for _show_safety_modal in execution_controller
        assert 'safety_code' in info, "Missing safety_code field"
        assert 'violation_message' in info, "Missing violation_message field"
        assert 'monitor_type' in info, "Missing monitor_type field"
        assert info['safety_code'] in ('LINE_TOOLS_UP_FOR_LINES', 'ROW_TOOLS_UP_FOR_ROWS')
        assert len(info['violation_message']) > 0

        # Cleanup
        engine.stop_execution()
        time.sleep(0.2)


# ==================== Safety rule lookup tests ====================

class TestSafetyRuleLookup:
    """Tests that safety_code used by unexpected tool detection exists in safety_rules.json"""

    def test_line_tools_rule_exists(self):
        """LINE_TOOLS_UP_FOR_LINES rule exists in safety_rules.json"""
        import json
        with open('config/safety_rules.json', 'r') as f:
            rules_data = json.load(f)

        rule_ids = [r['id'] for r in rules_data.get('rules', [])]
        assert 'LINE_TOOLS_UP_FOR_LINES' in rule_ids

    def test_row_tools_rule_exists(self):
        """ROW_TOOLS_UP_FOR_ROWS rule exists in safety_rules.json"""
        import json
        with open('config/safety_rules.json', 'r') as f:
            rules_data = json.load(f)

        rule_ids = [r['id'] for r in rules_data.get('rules', [])]
        assert 'ROW_TOOLS_UP_FOR_ROWS' in rule_ids

    def test_rules_have_hebrew_fields(self):
        """Both rules have name_he and message_he for Hebrew dialog display"""
        import json
        with open('config/safety_rules.json', 'r') as f:
            rules_data = json.load(f)

        for rule_id in ('LINE_TOOLS_UP_FOR_LINES', 'ROW_TOOLS_UP_FOR_ROWS'):
            rule = next((r for r in rules_data['rules'] if r['id'] == rule_id), None)
            assert rule is not None, f"Rule {rule_id} not found"
            assert rule.get('name_he'), f"Rule {rule_id} missing name_he"
            assert rule.get('message_he'), f"Rule {rule_id} missing message_he"

    def test_rules_have_reason_type(self):
        """Both rules have a reason type for modal styling"""
        import json
        with open('config/safety_rules.json', 'r') as f:
            rules_data = json.load(f)

        for rule_id in ('LINE_TOOLS_UP_FOR_LINES', 'ROW_TOOLS_UP_FOR_ROWS'):
            rule = next((r for r in rules_data['rules'] if r['id'] == rule_id), None)
            assert rule is not None
            assert rule.get('reason') in ('operational', 'collision', 'mechanical'), \
                f"Rule {rule_id} has invalid/missing reason: {rule.get('reason')}"


# ==================== Surrogate safety in translations ====================

class TestSurrogateStripping:
    """Tests that the _strip_surrogates fix prevents UTF-8 errors in safety dialogs"""

    def test_strip_surrogates_function(self):
        """_strip_surrogates removes lone surrogate characters"""
        from core.translations import _strip_surrogates

        # Clean text passes through
        assert _strip_surrogates("hello") == "hello"
        assert _strip_surrogates("") == ""
        assert _strip_surrogates(None) is None

        # Surrogates are removed
        text_with_surrogates = "abc\ud800def\udfff"
        result = _strip_surrogates(text_with_surrogates)
        assert '\ud800' not in result
        assert '\udfff' not in result
        assert result == "abcdef"

    def test_t_function_safe_for_tkinter(self):
        """t() function output is safe for Tkinter (no surrogates)"""
        from core.translations import t

        # These are strings that go through t() in the emergency_stop handler
        test_strings = [
            "🚨 EMERGENCY STOP - Safety Violation",
            "⚠️  SAFETY VIOLATION: {safety_code}",
            "Unknown safety violation",
            "🔄 RETRY",
        ]

        for s in test_strings:
            result = t(s, safety_code="TEST_CODE")
            # Should be encodable as UTF-8 (no surrogates)
            try:
                result.encode('utf-8')
            except UnicodeEncodeError:
                pytest.fail(f"t({s!r}) produced non-UTF-8 output: {result!r}")

    def test_rtl_function_safe_for_tkinter(self):
        """rtl() function output is safe for Tkinter"""
        from core.translations import rtl

        test_strings = [
            "סכנת התנגשות!",
            "תנאי תפעולי",
            "המערכת תמשיך אוטומטית כשהתנאי ייפתר",
        ]

        for s in test_strings:
            result = rtl(s)
            try:
                result.encode('utf-8')
            except UnicodeEncodeError:
                pytest.fail(f"rtl({s!r}) produced non-UTF-8 output: {result!r}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

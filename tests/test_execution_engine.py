#!/usr/bin/env python3

import pytest
import threading
import time
from unittest.mock import patch, MagicMock
from core.execution_engine import ExecutionEngine
from core.machine_state import MachineState, MachineStateManager
from hardware.interfaces.hardware_factory import get_hardware_interface
from hardware.implementations.mock import mock_hardware


def _ensure_safety_clear():
    """Disable safety system so execution tests don't get blocked by safety rules."""
    from core.safety_system import safety_system
    safety_system.disable_safety()
    # Also disable at rules level to prevent safety monitor thread from blocking
    safety_system.rules_manager.rules_data['global_enabled'] = False
    safety_system.rules_manager.rules = []


class TestLoadSteps:
    def test_load_steps(self):
        """Steps should be stored and index reset"""
        engine = ExecutionEngine()
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'},
            {'operation': 'move_y', 'parameters': {'position': 20.0}, 'description': 'Move Y'}
        ]

        engine.load_steps(steps)

        assert engine.steps == steps
        assert engine.current_step_index == 0
        assert len(engine.step_results) == 0

    def test_load_empty_steps(self):
        """Should accept empty steps list"""
        engine = ExecutionEngine()
        engine.load_steps([])

        assert engine.steps == []
        assert engine.current_step_index == 0

    def test_load_clears_previous_results(self):
        """Loading new steps should clear previous results"""
        engine = ExecutionEngine()

        # Load and execute some steps
        steps1 = [{'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'}]
        engine.load_steps(steps1)
        engine.step_results.append({'step_index': 0, 'result': {'success': True}})

        # Load new steps
        steps2 = [{'operation': 'move_y', 'parameters': {'position': 20.0}, 'description': 'Move Y'}]
        engine.load_steps(steps2)

        assert len(engine.step_results) == 0
        assert engine.current_step_index == 0


class TestStartExecution:
    def test_start_without_steps(self):
        """Should return False when no steps loaded"""
        engine = ExecutionEngine()
        result = engine.start_execution()

        assert result is False
        assert engine.is_running is False

    def test_start_while_running(self):
        """Should return False when already running"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        # Use a sensor wait to keep it running
        steps = [{'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X'}]
        engine.load_steps(steps)

        result1 = engine.start_execution()
        assert result1 is True

        # Try to start again while running
        result2 = engine.start_execution()
        assert result2 is False

        # Cleanup
        engine.stop_execution()
        time.sleep(0.1)


class TestPauseResume:
    def test_pause_not_running(self):
        """Should return False when not running"""
        engine = ExecutionEngine()
        result = engine.pause_execution()

        assert result is False
        assert engine.is_paused is False

    def test_pause_already_paused(self):
        """Should return False when already paused"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = [
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X'}
        ]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.1)

        result1 = engine.pause_execution()
        assert result1 is True

        result2 = engine.pause_execution()
        assert result2 is False

        # Cleanup
        engine.stop_execution()
        time.sleep(0.1)

    def test_resume_not_paused(self):
        """Should return False when not paused"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = [{'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X'}]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.1)

        result = engine.resume_execution()
        assert result is False

        # Cleanup
        engine.stop_execution()
        time.sleep(0.1)


class TestStopExecution:
    def test_stop_not_running(self):
        """Should return False when not running"""
        engine = ExecutionEngine()
        result = engine.stop_execution()

        assert result is False


class TestResetExecution:
    def test_reset_idle(self):
        """Should return True and reset all state when idle"""
        engine = ExecutionEngine()
        steps = [{'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'}]
        engine.load_steps(steps)

        engine.current_step_index = 5
        engine.step_results = [{'step_index': 0, 'result': {'success': True}}]
        engine.execution_completed = True
        engine.execution_failed = False

        result = engine.reset_execution()

        assert result is True
        assert engine.current_step_index == 0
        assert len(engine.step_results) == 0
        assert engine.execution_completed is False
        assert engine.execution_failed is False
        assert engine.is_running is False
        assert engine.is_paused is False

    def test_reset_while_running(self):
        """Should return False when running"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = [
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X'}
        ]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.1)

        result = engine.reset_execution()
        assert result is False

        # Cleanup
        engine.stop_execution()
        time.sleep(0.1)

    def test_reset_with_clear_steps(self):
        """Should clear steps list when clear_steps=True"""
        engine = ExecutionEngine()
        steps = [{'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'}]
        engine.load_steps(steps)

        result = engine.reset_execution(clear_steps=True)

        assert result is True
        assert len(engine.steps) == 0

    def test_reset_without_clear_steps(self):
        """Should preserve steps list when clear_steps=False"""
        engine = ExecutionEngine()
        steps = [{'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'}]
        engine.load_steps(steps)

        result = engine.reset_execution(clear_steps=False)

        assert result is True
        assert engine.steps == steps

    def test_reset_clears_transition_flag(self):
        """Should clear in_transition flag"""
        engine = ExecutionEngine()
        steps = [{'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'}]
        engine.load_steps(steps)

        engine.in_transition = True
        engine.reset_execution()

        assert engine.in_transition is False


class TestStepNavigation:
    def test_step_forward(self):
        """Should move to next step"""
        engine = ExecutionEngine()
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'},
            {'operation': 'move_y', 'parameters': {'position': 20.0}, 'description': 'Move Y'}
        ]
        engine.load_steps(steps)

        assert engine.current_step_index == 0
        result = engine.step_forward()
        assert result is True
        assert engine.current_step_index == 1

    def test_step_forward_at_end(self):
        """Should return False at last step"""
        engine = ExecutionEngine()
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'}
        ]
        engine.load_steps(steps)

        result = engine.step_forward()
        assert result is False
        assert engine.current_step_index == 0

    def test_step_backward(self):
        """Should move to previous step"""
        engine = ExecutionEngine()
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'},
            {'operation': 'move_y', 'parameters': {'position': 20.0}, 'description': 'Move Y'}
        ]
        engine.load_steps(steps)
        engine.current_step_index = 1

        result = engine.step_backward()
        assert result is True
        assert engine.current_step_index == 0

    def test_step_backward_at_start(self):
        """Should return False at first step"""
        engine = ExecutionEngine()
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'}
        ]
        engine.load_steps(steps)

        result = engine.step_backward()
        assert result is False
        assert engine.current_step_index == 0

    def test_go_to_valid_step(self):
        """Should jump to specified step"""
        engine = ExecutionEngine()
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'},
            {'operation': 'move_y', 'parameters': {'position': 20.0}, 'description': 'Move Y'},
            {'operation': 'move_x', 'parameters': {'position': 30.0}, 'description': 'Move X2'}
        ]
        engine.load_steps(steps)

        result = engine.go_to_step(2)
        assert result is True
        assert engine.current_step_index == 2

    def test_go_to_invalid_step(self):
        """Should return False for invalid index"""
        engine = ExecutionEngine()
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'}
        ]
        engine.load_steps(steps)

        result = engine.go_to_step(10)
        assert result is False
        assert engine.current_step_index == 0

    def test_navigation_blocked_while_running(self):
        """Should not navigate while running"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = [
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X'},
            {'operation': 'move_y', 'parameters': {'position': 20.0}, 'description': 'Move Y'}
        ]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.1)

        assert engine.step_forward() is False
        assert engine.step_backward() is False
        assert engine.go_to_step(1) is False

        # Cleanup
        engine.stop_execution()
        time.sleep(0.1)


class TestExecuteStep:
    def test_execute_move_x(self):
        """Should execute move_x and update position"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        step = {'operation': 'move_x', 'parameters': {'position': 25.0}, 'description': 'Move X to 25'}
        result = engine._execute_step(step)

        assert result['success'] is True
        assert result['position'] == 25.0
        assert hw.get_current_x() == 25.0

    def test_execute_move_y(self):
        """Should execute move_y and update position"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        step = {'operation': 'move_y', 'parameters': {'position': 30.0}, 'description': 'Move Y to 30'}
        result = engine._execute_step(step)

        assert result['success'] is True
        assert result['position'] == 30.0
        assert hw.get_current_y() == 30.0

    def test_execute_tool_action_line_marker(self):
        """Should execute line marker tool actions"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        step_down = {'operation': 'tool_action', 'parameters': {'tool': 'line_marker', 'action': 'down'},
                     'description': 'Lower line marker'}
        result_down = engine._execute_step(step_down)

        assert result_down['success'] is True
        assert hw.get_line_marker_state() == 'down'

        step_up = {'operation': 'tool_action', 'parameters': {'tool': 'line_marker', 'action': 'up'},
                   'description': 'Raise line marker'}
        result_up = engine._execute_step(step_up)

        assert result_up['success'] is True
        assert hw.get_line_marker_state() == 'up'

    def test_execute_tool_action_line_cutter(self):
        """Should execute line cutter tool actions"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        step_down = {'operation': 'tool_action', 'parameters': {'tool': 'line_cutter', 'action': 'down'},
                     'description': 'Lower line cutter'}
        result_down = engine._execute_step(step_down)

        assert result_down['success'] is True
        assert hw.get_line_cutter_state() == 'down'

        step_up = {'operation': 'tool_action', 'parameters': {'tool': 'line_cutter', 'action': 'up'},
                   'description': 'Raise line cutter'}
        result_up = engine._execute_step(step_up)

        assert result_up['success'] is True
        assert hw.get_line_cutter_state() == 'up'

    def test_execute_tool_action_row_marker(self):
        """Should execute row marker tool actions"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        step_down = {'operation': 'tool_action', 'parameters': {'tool': 'row_marker', 'action': 'down'},
                     'description': 'Lower row marker'}
        result_down = engine._execute_step(step_down)

        assert result_down['success'] is True
        assert hw.get_row_marker_state() == 'down'

        step_up = {'operation': 'tool_action', 'parameters': {'tool': 'row_marker', 'action': 'up'},
                   'description': 'Raise row marker'}
        result_up = engine._execute_step(step_up)

        assert result_up['success'] is True
        assert hw.get_row_marker_state() == 'up'

    def test_execute_tool_action_row_cutter(self):
        """Should execute row cutter tool actions"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        step_down = {'operation': 'tool_action', 'parameters': {'tool': 'row_cutter', 'action': 'down'},
                     'description': 'Lower row cutter'}
        result_down = engine._execute_step(step_down)

        assert result_down['success'] is True
        assert hw.get_row_cutter_state() == 'down'

        step_up = {'operation': 'tool_action', 'parameters': {'tool': 'row_cutter', 'action': 'up'},
                   'description': 'Raise row cutter'}
        result_up = engine._execute_step(step_up)

        assert result_up['success'] is True
        assert hw.get_row_cutter_state() == 'up'

    def test_execute_unknown_tool(self):
        """Should return error for unknown tool"""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        step = {'operation': 'tool_action', 'parameters': {'tool': 'unknown_tool', 'action': 'down'},
                'description': 'Unknown tool'}
        result = engine._execute_step(step)

        assert result['success'] is False
        assert 'Unknown tool/action' in result['error']

    def test_execute_unknown_sensor(self):
        """Should return error for unknown sensor"""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        step = {'operation': 'wait_sensor', 'parameters': {'sensor': 'unknown_sensor'},
                'description': 'Wait unknown sensor'}
        result = engine._execute_step(step)

        assert result['success'] is False
        assert 'Unknown sensor' in result['error']

    def test_execute_program_start(self):
        """Should execute program_start operation"""
        engine = ExecutionEngine()

        step = {'operation': 'program_start',
                'parameters': {'program_number': '1', 'program_name': 'Test Program'},
                'description': 'Start Program 1'}
        result = engine._execute_step(step)

        assert result['success'] is True
        assert result['program_info']['program_number'] == '1'

    def test_execute_program_complete(self):
        """Should execute program_complete operation"""
        engine = ExecutionEngine()

        step = {'operation': 'program_complete',
                'parameters': {'program_number': '1', 'program_name': 'Test Program'},
                'description': 'Complete Program 1'}
        result = engine._execute_step(step)

        assert result['success'] is True
        assert result['program_info']['program_number'] == '1'

    def test_execute_workflow_separator(self):
        """Should execute workflow_separator operation"""
        engine = ExecutionEngine()

        step = {'operation': 'workflow_separator', 'parameters': {},
                'description': '=== Phase Separator ==='}
        result = engine._execute_step(step)

        assert result['success'] is True

    def test_execute_unknown_operation(self):
        """Should return error for unknown operation"""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        step = {'operation': 'invalid_operation', 'parameters': {},
                'description': 'Invalid operation'}
        result = engine._execute_step(step)

        assert result['success'] is False
        assert 'Unknown operation' in result['error']

    def test_execute_wait_sensor_types(self):
        """Should support all sensor types in wait_sensor"""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware
        hw.set_execution_engine_reference(engine)

        # Map sensor wait types to actual trigger functions
        # 'x' waits for x_left OR x_right, 'y' waits for y_top OR y_bottom
        sensor_triggers = {
            'x': 'trigger_x_left_sensor',
            'y': 'trigger_y_top_sensor',
            'x_left': 'trigger_x_left_sensor',
            'x_right': 'trigger_x_right_sensor',
            'y_top': 'trigger_y_top_sensor',
            'y_bottom': 'trigger_y_bottom_sensor',
        }

        for sensor, trigger_method in sensor_triggers.items():
            def trigger_sensor(method_name):
                time.sleep(0.05)
                getattr(hw, method_name)()

            trigger_thread = threading.Thread(target=trigger_sensor, args=(trigger_method,), daemon=True)
            trigger_thread.start()

            step = {'operation': 'wait_sensor', 'parameters': {'sensor': sensor},
                    'description': f'Wait {sensor} sensor'}
            result = engine._execute_step(step)

            trigger_thread.join(timeout=2.0)

            assert result['success'] is True, f"Sensor {sensor} should be valid"


class TestExecutionLoop:
    def test_full_execution_completes(self):
        """Should execute all steps and complete"""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': '1'},
             'description': 'Start Program'},
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'},
            {'operation': 'move_y', 'parameters': {'position': 15.0}, 'description': 'Move Y'},
            {'operation': 'tool_action', 'parameters': {'tool': 'line_marker', 'action': 'down'},
             'description': 'Lower marker'},
            {'operation': 'tool_action', 'parameters': {'tool': 'line_marker', 'action': 'up'},
             'description': 'Raise marker'},
            {'operation': 'program_complete', 'parameters': {'program_number': '1'},
             'description': 'Complete Program'}
        ]

        engine.load_steps(steps)
        result = engine.start_execution()
        assert result is True

        # Wait for completion (with timeout)
        timeout = 10.0
        start = time.time()
        while engine.is_running and (time.time() - start) < timeout:
            time.sleep(0.05)

        assert engine.is_running is False, "Execution should have completed"
        assert engine.execution_completed is True
        assert engine.execution_failed is False
        assert len(engine.step_results) == len(steps)

        for r in engine.step_results:
            assert r['result'].get('success', False) is True

    def test_execution_stops_on_stop_event(self):
        """Should stop when stop_execution() is called"""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        # Use sensor wait to keep execution blocked
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X'},
            {'operation': 'move_y', 'parameters': {'position': 20.0}, 'description': 'Move Y'}
        ]

        engine.load_steps(steps)
        engine.start_execution()

        # Let first step execute
        time.sleep(0.3)

        result = engine.stop_execution()
        assert result is True

        time.sleep(0.2)

        assert engine.is_running is False
        assert len(engine.step_results) < len(steps)


class TestExecutionStatus:
    def test_get_execution_status_fields(self):
        """Should return all status fields"""
        engine = ExecutionEngine()
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'},
            {'operation': 'move_y', 'parameters': {'position': 20.0}, 'description': 'Move Y'}
        ]
        engine.load_steps(steps)

        status = engine.get_execution_status()

        assert 'is_running' in status
        assert 'is_paused' in status
        assert 'current_step' in status
        assert 'total_steps' in status
        assert 'progress' in status
        assert 'start_time' in status
        assert 'elapsed_time' in status
        assert 'steps_completed' in status

        assert status['total_steps'] == 2
        assert status['current_step'] == 0
        assert status['progress'] == 0.0

    def test_get_execution_summary_no_results(self):
        """Should return None when no results"""
        engine = ExecutionEngine()

        summary = engine.get_execution_summary()
        assert summary is None

    def test_get_execution_summary_with_results(self):
        """Should return summary with counts"""
        engine = ExecutionEngine()

        engine.steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'},
            {'operation': 'move_y', 'parameters': {'position': 20.0}, 'description': 'Move Y'}
        ]
        engine.step_results = [
            {'step_index': 0, 'result': {'success': True}, 'timestamp': time.time()},
            {'step_index': 1, 'result': {'success': True}, 'timestamp': time.time()}
        ]
        engine.start_time = time.time() - 1.0
        engine.end_time = time.time()

        summary = engine.get_execution_summary()

        assert summary is not None
        assert summary['total_steps'] == 2
        assert summary['completed_steps'] == 2
        assert summary['successful_steps'] == 2
        assert summary['failed_steps'] == 0
        assert summary['execution_time'] > 0
        assert 'average_step_time' in summary


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

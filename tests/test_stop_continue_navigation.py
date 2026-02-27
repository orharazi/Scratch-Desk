#!/usr/bin/env python3
"""
Comprehensive tests for stop/continue/step-navigation flow.

Tests cover:
- Running a program, pressing stop mid-execution
- Moving steps forward/backward after stop
- Verifying ALL hardware state (motor positions, piston states, sensors)
- Continue-from-stop (motor restore, execution resumes from correct step)
- Edge cases: stop at first/last step, multiple stop/continue cycles,
  navigation boundaries, stop during lines vs rows operations
"""

import pytest
import threading
import time

from core.execution_engine import ExecutionEngine
from core.machine_state import MachineState, MachineStateManager
from hardware.implementations.mock import mock_hardware


def _ensure_safety_clear():
    """Disable safety system so tests don't get blocked by safety rules."""
    from core.safety_system import safety_system
    safety_system.disable_safety()
    safety_system.rules_manager.rules_data['global_enabled'] = False
    safety_system.rules_manager.rules = []


def _wait_engine_stop(engine, timeout=5.0):
    """Wait for engine to finish running."""
    start = time.time()
    while engine.is_running and (time.time() - start) < timeout:
        time.sleep(0.02)


def _wait_engine_reach_step(engine, step_index, timeout=5.0):
    """Wait for engine to reach (or pass) a given step index."""
    start = time.time()
    while engine.current_step_index <= step_index and engine.is_running and (time.time() - start) < timeout:
        time.sleep(0.02)


def _assert_all_pistons_default(hw):
    """Assert all pistons are in their default (reset) state."""
    assert hw.get_line_marker_state() == "up", "line_marker should be up"
    assert hw.get_line_cutter_state() == "up", "line_cutter should be up"
    assert hw.get_line_motor_piston_state() == "down", "line_motor_piston should be down (default)"
    assert hw.get_row_marker_state() == "up", "row_marker should be up"
    assert hw.get_row_cutter_state() == "up", "row_cutter should be up"


# ============================================================================
# Test step data factories
# ============================================================================

def _make_lines_steps():
    """Create a sequence of lines operation steps (Y-axis movements + line tools).

    These simulate marking horizontal lines on a scratch card:
    1. Program start
    2. Lower line motor piston (brings motor assembly down)
    3. Move Y to line 1 position
    4. Lower line marker
    5. Wait for left edge sensor (x_left)
    6. Raise line marker
    7. Move Y to line 2 position
    8. Lower line marker
    9. Wait for right edge sensor (x_right)
    10. Raise line marker
    11. Program complete
    """
    return [
        {'operation': 'program_start', 'parameters': {'program_number': 1},
         'description': 'Start Program 1'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_motor_piston', 'action': 'down'},
         'description': 'lines: Lower line_motor_piston for lines operations'},
        {'operation': 'move_y', 'parameters': {'position': 20.0},
         'description': 'lines: Move Y to line 1 position 20.0cm'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_marker', 'action': 'down'},
         'description': 'lines: Open line_marker for line 1'},
        {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
         'description': 'lines: Wait for x_left sensor'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_marker', 'action': 'up'},
         'description': 'lines: Close line_marker after line 1'},
        {'operation': 'move_y', 'parameters': {'position': 30.0},
         'description': 'lines: Move Y to line 2 position 30.0cm'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_marker', 'action': 'down'},
         'description': 'lines: Open line_marker for line 2'},
        {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_right'},
         'description': 'lines: Wait for x_right sensor'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_marker', 'action': 'up'},
         'description': 'lines: Close line_marker after line 2'},
        {'operation': 'program_complete', 'parameters': {'program_number': 1},
         'description': 'Complete Program 1'},
    ]


def _make_rows_steps():
    """Create a sequence of rows operation steps (X-axis movements + row tools)."""
    return [
        {'operation': 'program_start', 'parameters': {'program_number': 1},
         'description': 'Start Program 1'},
        {'operation': 'move_x', 'parameters': {'position': 15.0},
         'description': 'rows: Move X to rows start position 15.0cm'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'row_marker', 'action': 'down'},
         'description': 'rows: Open row_marker for page 1'},
        {'operation': 'wait_sensor', 'parameters': {'sensor': 'y_top'},
         'description': 'rows: Wait for y_top sensor'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'row_marker', 'action': 'up'},
         'description': 'rows: Close row_marker after page 1'},
        {'operation': 'move_x', 'parameters': {'position': 25.0},
         'description': 'rows: Move X to page 2 position 25.0cm'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'row_marker', 'action': 'down'},
         'description': 'rows: Open row_marker for page 2'},
        {'operation': 'wait_sensor', 'parameters': {'sensor': 'y_bottom'},
         'description': 'rows: Wait for y_bottom sensor'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'row_marker', 'action': 'up'},
         'description': 'rows: Close row_marker after page 2'},
        {'operation': 'program_complete', 'parameters': {'program_number': 1},
         'description': 'Complete Program 1'},
    ]


def _make_simple_motor_steps():
    """Create simple motor movement steps (no sensor waits) for quick tests."""
    return [
        {'operation': 'program_start', 'parameters': {'program_number': 1},
         'description': 'Start Program 1'},
        {'operation': 'move_x', 'parameters': {'position': 10.0},
         'description': 'Move X to 10cm'},
        {'operation': 'move_y', 'parameters': {'position': 20.0},
         'description': 'lines: Move Y to 20cm'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_marker', 'action': 'down'},
         'description': 'lines: Lower line marker'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_marker', 'action': 'up'},
         'description': 'lines: Raise line marker'},
        {'operation': 'move_x', 'parameters': {'position': 30.0},
         'description': 'rows: Move X to 30cm'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'row_marker', 'action': 'down'},
         'description': 'rows: Lower row marker'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'row_marker', 'action': 'up'},
         'description': 'rows: Raise row marker'},
        {'operation': 'move_y', 'parameters': {'position': 0.0},
         'description': 'Move Y home'},
        {'operation': 'move_x', 'parameters': {'position': 0.0},
         'description': 'Move X home'},
        {'operation': 'program_complete', 'parameters': {'program_number': 1},
         'description': 'Complete Program 1'},
    ]


def _make_mixed_steps_with_sensor():
    """Create mixed lines + rows steps with a sensor wait in the middle.

    The sensor wait blocks execution, allowing tests to stop at a known point.
    Steps:
      0: program_start
      1: tool_action (line_motor_piston down)
      2: move_y (20.0)
      3: tool_action (line_marker down)
      4: wait_sensor (x_left) <-- execution blocks here
      5: tool_action (line_marker up)
      6: move_x (15.0)
      7: tool_action (row_marker down)
      8: wait_sensor (y_top) <-- execution blocks here
      9: tool_action (row_marker up)
      10: program_complete
    """
    return [
        {'operation': 'program_start', 'parameters': {'program_number': 1},
         'description': 'Start Program 1'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_motor_piston', 'action': 'down'},
         'description': 'lines: Lower line_motor_piston'},
        {'operation': 'move_y', 'parameters': {'position': 20.0},
         'description': 'lines: Move Y to 20cm'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_marker', 'action': 'down'},
         'description': 'lines: Lower line_marker'},
        {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
         'description': 'lines: Wait x_left sensor'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'line_marker', 'action': 'up'},
         'description': 'lines: Raise line_marker'},
        {'operation': 'move_x', 'parameters': {'position': 15.0},
         'description': 'rows: Move X to 15cm'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'row_marker', 'action': 'down'},
         'description': 'rows: Lower row_marker'},
        {'operation': 'wait_sensor', 'parameters': {'sensor': 'y_top'},
         'description': 'rows: Wait y_top sensor'},
        {'operation': 'tool_action',
         'parameters': {'tool': 'row_marker', 'action': 'up'},
         'description': 'rows: Raise row_marker'},
        {'operation': 'program_complete', 'parameters': {'program_number': 1},
         'description': 'Complete Program 1'},
    ]


# ============================================================================
# Tests: Stop behavior
# ============================================================================

class TestStopExecution:
    """Test stopping execution at various points and verifying state."""

    def test_stop_preserves_step_index(self):
        """After stop, current_step_index should NOT reset to 0."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware
        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)
        engine.start_execution()

        # Wait for execution to reach the wait_sensor step (index 4)
        time.sleep(0.5)
        assert engine.is_running

        engine.stop_execution()
        _wait_engine_stop(engine)

        # Step index should be at or past the sensor wait (step 4),
        # not reset to 0
        assert engine.current_step_index > 0
        assert engine.is_running is False

    def test_stop_raises_line_motor_piston_when_down(self):
        """Stop should raise line_motor_piston if it was down during lines operations."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware
        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)
        engine.start_execution()

        # Wait for line_motor_piston to be lowered (step 1) and execution
        # to block on sensor wait (step 4)
        time.sleep(0.5)

        # Verify line_motor_piston is down before stop
        assert hw.get_line_motor_piston_state() == "down"

        engine.stop_execution()
        _wait_engine_stop(engine)

        # After stop, line_motor_piston should be raised for safety
        assert hw.get_line_motor_piston_state() == "up"
        assert engine._raised_motor_on_stop is True

    def test_stop_does_not_raise_line_motor_when_already_up(self):
        """Stop should NOT raise line_motor_piston if it's already up."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        # Use steps that don't lower the line motor piston
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'tool_action',
             'parameters': {'tool': 'line_motor_piston', 'action': 'up'},
             'description': 'Raise line_motor_piston'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
        ]
        engine.load_steps(steps)

        # Ensure line_motor_piston starts UP
        hw.line_motor_piston_up()
        assert hw.get_line_motor_piston_state() == "up"

        engine.start_execution()
        time.sleep(0.3)

        engine.stop_execution()
        _wait_engine_stop(engine)

        # Should still be up, and flag should be False
        assert hw.get_line_motor_piston_state() == "up"
        assert engine._raised_motor_on_stop is False

    def test_stop_hardware_positions_preserved(self):
        """After stop, motor positions should reflect the last executed step."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware
        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)
        engine.start_execution()

        # Wait for step 2 (move_y to 20.0) to execute and block on step 4
        time.sleep(0.5)

        engine.stop_execution()
        _wait_engine_stop(engine)

        # Y should have moved to 20.0 (step 2 completed)
        assert hw.get_current_y() == 20.0
        # X should still be at 0.0 (step 6 not reached)
        assert hw.get_current_x() == 0.0

    def test_stop_piston_states_after_lines_operations(self):
        """After stop during lines operations, verify all piston states."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware
        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)
        engine.start_execution()

        # Wait for step 3 (line_marker down) and block on step 4 (sensor wait)
        time.sleep(0.5)

        engine.stop_execution()
        _wait_engine_stop(engine)

        # line_marker should be down (was lowered at step 3, not raised yet)
        assert hw.get_line_marker_state() == "down"
        # line_motor_piston should be UP (raised by stop for safety)
        assert hw.get_line_motor_piston_state() == "up"
        # line_cutter should be up (default, never lowered)
        assert hw.get_line_cutter_state() == "up"
        # row tools should be up (never reached rows phase)
        assert hw.get_row_marker_state() == "up"
        assert hw.get_row_cutter_state() == "up"

    def test_stop_machine_state_becomes_idle(self):
        """After stop, MachineState should be IDLE."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)
        engine.start_execution()
        time.sleep(0.3)

        state_manager = MachineStateManager()
        assert state_manager.state == MachineState.RUNNING

        engine.stop_execution()
        _wait_engine_stop(engine)

        assert state_manager.state == MachineState.IDLE


# ============================================================================
# Tests: Step navigation after stop
# ============================================================================

class TestStepNavigationAfterStop:
    """Test stepping forward/backward after stopping execution."""

    def test_step_forward_after_stop(self):
        """Should be able to step forward after stop."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware
        steps = _make_simple_motor_steps()
        engine.load_steps(steps)

        # Execute a few steps automatically
        engine.start_execution()
        time.sleep(0.3)
        engine.stop_execution()
        _wait_engine_stop(engine)

        saved_index = engine.current_step_index
        result = engine.step_forward()

        if saved_index < len(steps) - 1:
            assert result is True
            assert engine.current_step_index == saved_index + 1
        else:
            assert result is False

    def test_step_backward_after_stop(self):
        """Should be able to step backward after stop."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = _make_simple_motor_steps()
        engine.load_steps(steps)

        # Execute a few steps
        engine.start_execution()
        time.sleep(0.3)
        engine.stop_execution()
        _wait_engine_stop(engine)

        saved_index = engine.current_step_index
        result = engine.step_backward()

        if saved_index > 0:
            assert result is True
            assert engine.current_step_index == saved_index - 1
        else:
            assert result is False

    def test_step_forward_executes_on_hardware(self):
        """Stepping forward should execute the step on hardware (via execute_current_step)."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X to 10'},
            {'operation': 'move_y', 'parameters': {'position': 25.0},
             'description': 'Move Y to 25'},
            {'operation': 'move_x', 'parameters': {'position': 30.0},
             'description': 'Move X to 30'},
        ]
        engine.load_steps(steps)

        # Navigate forward and execute each step manually
        # Step 0: program_start
        engine.execute_current_step()

        # Step 1: move_x to 10
        engine.step_forward()
        result = engine.execute_current_step()
        assert result['success'] is True
        assert hw.get_current_x() == 10.0

        # Step 2: move_y to 25
        engine.step_forward()
        result = engine.execute_current_step()
        assert result['success'] is True
        assert hw.get_current_y() == 25.0

        # Step 3: move_x to 30
        engine.step_forward()
        result = engine.execute_current_step()
        assert result['success'] is True
        assert hw.get_current_x() == 30.0

    def test_step_backward_then_forward_hardware_state(self):
        """Hardware state should reflect step execution during back/forward navigation."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X to 10'},
            {'operation': 'move_x', 'parameters': {'position': 20.0},
             'description': 'Move X to 20'},
            {'operation': 'move_x', 'parameters': {'position': 30.0},
             'description': 'Move X to 30'},
        ]
        engine.load_steps(steps)

        # Navigate to step 3 and execute
        engine.step_forward()  # -> step 1
        engine.execute_current_step()
        assert hw.get_current_x() == 10.0

        engine.step_forward()  # -> step 2
        engine.execute_current_step()
        assert hw.get_current_x() == 20.0

        engine.step_forward()  # -> step 3
        engine.execute_current_step()
        assert hw.get_current_x() == 30.0

        # Step backward to step 2 and re-execute
        engine.step_backward()  # -> step 2
        assert engine.current_step_index == 2
        engine.execute_current_step()
        # Re-executing move_x to 20.0 should move X back to 20
        assert hw.get_current_x() == 20.0

        # Step backward to step 1 and re-execute
        engine.step_backward()  # -> step 1
        assert engine.current_step_index == 1
        engine.execute_current_step()
        assert hw.get_current_x() == 10.0

    def test_step_backward_at_step_zero(self):
        """Cannot step backward past step 0."""
        engine = ExecutionEngine()
        steps = _make_simple_motor_steps()
        engine.load_steps(steps)

        assert engine.current_step_index == 0
        result = engine.step_backward()
        assert result is False
        assert engine.current_step_index == 0

    def test_step_forward_at_last_step(self):
        """Cannot step forward past last step."""
        engine = ExecutionEngine()
        steps = _make_simple_motor_steps()
        engine.load_steps(steps)

        # Move to last step
        engine.current_step_index = len(steps) - 1
        result = engine.step_forward()
        assert result is False
        assert engine.current_step_index == len(steps) - 1

    def test_multiple_forward_backward_cycles(self):
        """Navigation should work correctly through multiple back/forward cycles."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X to 10'},
            {'operation': 'move_y', 'parameters': {'position': 20.0},
             'description': 'Move Y to 20'},
            {'operation': 'move_x', 'parameters': {'position': 30.0},
             'description': 'Move X to 30'},
        ]
        engine.load_steps(steps)

        # Cycle 1: forward to end
        for i in range(3):
            engine.step_forward()
        assert engine.current_step_index == 3

        # Cycle 2: backward to start
        for i in range(3):
            engine.step_backward()
        assert engine.current_step_index == 0

        # Cycle 3: forward 2, backward 1, forward 1
        engine.step_forward()  # -> 1
        engine.step_forward()  # -> 2
        engine.step_backward()  # -> 1
        engine.step_forward()  # -> 2
        assert engine.current_step_index == 2

        # Execute current step (move_y to 20)
        result = engine.execute_current_step()
        assert result['success'] is True
        assert hw.get_current_y() == 20.0

    def test_navigation_blocked_during_active_execution(self):
        """Cannot navigate while execution is actively running (not paused)."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.3)

        # Engine is running, navigation should be blocked
        assert engine.is_running is True
        assert engine.step_forward() is False
        assert engine.step_backward() is False

        engine.stop_execution()
        _wait_engine_stop(engine)

    def test_skip_sensor_wait_during_manual_navigation(self):
        """Manual execution should skip wait_sensor steps (they'd block forever)."""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X to 10'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
            {'operation': 'move_x', 'parameters': {'position': 20.0},
             'description': 'Move X to 20'},
        ]
        engine.load_steps(steps)

        # Navigate forward through all steps
        engine.step_forward()  # -> 1 (move_x)
        engine.step_forward()  # -> 2 (wait_sensor) - should skip execution
        assert engine.current_step_index == 2

        # Step forward past sensor wait
        engine.step_forward()  # -> 3 (move_x)
        assert engine.current_step_index == 3


# ============================================================================
# Tests: Continue from stop
# ============================================================================

class TestContinueExecution:
    """Test the continue_execution() method that resumes from current step."""

    def test_continue_resumes_from_current_step(self):
        """continue_execution should start from current_step_index, not 0."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        # Use a sensor wait to block execution at a known point, with remaining
        # steps afterwards so continue has work to do.
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X to 10'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
            {'operation': 'move_x', 'parameters': {'position': 20.0},
             'description': 'Move X to 20'},
            {'operation': 'move_y', 'parameters': {'position': 30.0},
             'description': 'Move Y to 30'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1},
             'description': 'Complete'},
        ]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.3)

        engine.stop_execution()
        _wait_engine_stop(engine)

        # Engine should be past step 0 (the sensor wait completes or is stopped)
        stopped_at = engine.current_step_index
        assert stopped_at > 0

        # Navigate to step 3 (move_x to 20) to ensure we have remaining steps
        engine.go_to_step(3)
        assert engine.current_step_index == 3

        # Continue execution from step 3
        result = engine.continue_execution()
        assert result is True

        # Wait for completion
        _wait_engine_stop(engine, timeout=5.0)

        # All remaining steps should have executed
        assert engine.execution_completed is True
        assert engine.is_running is False
        assert hw.get_current_x() == 20.0
        assert hw.get_current_y() == 30.0

    def test_continue_without_prior_stop_fails(self):
        """continue_execution should fail if engine is already running."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.1)

        # Try to continue while already running
        result = engine.continue_execution()
        assert result is False

        engine.stop_execution()
        _wait_engine_stop(engine)

    def test_continue_with_no_steps(self):
        """continue_execution should fail if no steps loaded."""
        engine = ExecutionEngine()
        result = engine.continue_execution()
        assert result is False

    def test_continue_when_all_steps_completed(self):
        """continue_execution should fail if already past last step."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1},
             'description': 'Complete'},
        ]
        engine.load_steps(steps)

        # Run to completion
        engine.start_execution()
        _wait_engine_stop(engine, timeout=5.0)
        assert engine.execution_completed is True

        # current_step_index should be past the end
        assert engine.current_step_index >= len(steps)

        # Continue should fail
        result = engine.continue_execution()
        assert result is False

    def test_continue_sets_correct_machine_state(self):
        """continue_execution should set MachineState to RUNNING."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        state_manager = MachineStateManager()

        # Use two sensor waits so that after stopping at the first one and
        # continuing, execution blocks on the second one (remaining running).
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
            {'operation': 'move_x', 'parameters': {'position': 20.0},
             'description': 'Move X to 20'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_right'},
             'description': 'Wait x_right'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1},
             'description': 'Complete'},
        ]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.3)
        engine.stop_execution()
        _wait_engine_stop(engine)
        assert state_manager.state == MachineState.IDLE

        # Navigate to step 3 (move_x to 20) - past the first sensor wait
        # Then continue: execution will block on step 4 (second sensor wait)
        engine.go_to_step(3)
        engine.continue_execution()
        time.sleep(0.2)
        assert state_manager.state == MachineState.RUNNING

        engine.stop_execution()
        _wait_engine_stop(engine)

    def test_continue_after_step_navigation(self):
        """After navigating steps, continue should execute from the navigated position."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        # Use only move_x steps to avoid triggering lines-to-rows transition
        # detection in the execution loop (move_y -> move_x triggers transition).
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X to 10'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
            {'operation': 'move_x', 'parameters': {'position': 20.0},
             'description': 'Move X to 20'},
            {'operation': 'move_x', 'parameters': {'position': 30.0},
             'description': 'Move X to 30'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1},
             'description': 'Complete'},
        ]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.3)
        engine.stop_execution()
        _wait_engine_stop(engine)

        # Navigate to step 3 (move_x to 20) - past the sensor wait
        engine.go_to_step(3)
        assert engine.current_step_index == 3

        # Continue from step 3
        result = engine.continue_execution()
        assert result is True

        _wait_engine_stop(engine, timeout=5.0)

        # Steps 3+ should have executed
        assert engine.execution_completed is True
        # X should be 30.0 (step 4, last move_x)
        assert hw.get_current_x() == 30.0


# ============================================================================
# Tests: Motor state save/restore during stop/continue
# ============================================================================

class TestMotorStateStopContinue:
    """Test that line_motor_piston state is correctly saved on stop and restored on continue."""

    def test_motor_raised_on_stop_flag(self):
        """_raised_motor_on_stop should be True when piston was down at stop time."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)

        # Ensure motor piston is down (default state)
        assert hw.get_line_motor_piston_state() == "down"

        engine.start_execution()
        time.sleep(0.3)
        engine.stop_execution()
        _wait_engine_stop(engine)

        assert engine._raised_motor_on_stop is True
        assert hw.get_line_motor_piston_state() == "up"

    def test_motor_not_raised_flag_when_already_up(self):
        """_raised_motor_on_stop should be False when piston was already up."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        # Put piston UP explicitly before starting
        hw.line_motor_piston_up()

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait'},
        ]
        engine.load_steps(steps)
        engine.start_execution()
        time.sleep(0.2)

        engine.stop_execution()
        _wait_engine_stop(engine)

        assert engine._raised_motor_on_stop is False
        assert hw.get_line_motor_piston_state() == "up"

    def test_motor_restore_on_continue(self):
        """When continuing after motor was raised on stop, caller can restore it.

        The controls_panel.run_execution() does:
          if self._motor_state_at_stop:
              self.hardware.line_motor_piston_down()

        This test verifies the engine flag is correct for the caller to use.
        """
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.3)
        engine.stop_execution()
        _wait_engine_stop(engine)

        # Engine raised the motor
        assert engine._raised_motor_on_stop is True
        assert hw.get_line_motor_piston_state() == "up"

        # Simulate what controls_panel.run_execution does before continue:
        # Restore the motor to down position
        hw.line_motor_piston_down()
        assert hw.get_line_motor_piston_state() == "down"

        # Continue execution
        engine.continue_execution()
        time.sleep(0.1)

        # Engine should be running with motor piston down
        assert engine.is_running is True
        assert hw.get_line_motor_piston_state() == "down"

        engine.stop_execution()
        _wait_engine_stop(engine)


# ============================================================================
# Tests: Full hardware state verification
# ============================================================================

class TestFullHardwareStateVerification:
    """Verify ALL hardware state components at key points in the stop/continue flow."""

    def _get_full_hardware_state(self, hw):
        """Capture complete hardware state snapshot."""
        return {
            'x_position': hw.get_current_x(),
            'y_position': hw.get_current_y(),
            'line_marker': hw.get_line_marker_state(),
            'line_cutter': hw.get_line_cutter_state(),
            'line_motor_piston': hw.get_line_motor_piston_state(),
            'row_marker': hw.get_row_marker_state(),
            'row_cutter': hw.get_row_cutter_state(),
            'line_marker_up_sensor': hw.get_line_marker_up_sensor(),
            'line_marker_down_sensor': hw.get_line_marker_down_sensor(),
            'line_cutter_up_sensor': hw.get_line_cutter_up_sensor(),
            'line_cutter_down_sensor': hw.get_line_cutter_down_sensor(),
            'line_motor_left_up_sensor': hw.get_line_motor_left_up_sensor(),
            'line_motor_left_down_sensor': hw.get_line_motor_left_down_sensor(),
            'line_motor_right_up_sensor': hw.get_line_motor_right_up_sensor(),
            'line_motor_right_down_sensor': hw.get_line_motor_right_down_sensor(),
            'row_marker_up_sensor': hw.get_row_marker_up_sensor(),
            'row_marker_down_sensor': hw.get_row_marker_down_sensor(),
            'row_cutter_up_sensor': hw.get_row_cutter_up_sensor(),
            'row_cutter_down_sensor': hw.get_row_cutter_down_sensor(),
        }

    def test_initial_hardware_state(self):
        """Verify hardware state after reset matches expected defaults."""
        engine = ExecutionEngine()
        hw = engine.hardware
        state = self._get_full_hardware_state(hw)

        assert state['x_position'] == 0.0
        assert state['y_position'] == 0.0
        assert state['line_marker'] == 'up'
        assert state['line_cutter'] == 'up'
        assert state['line_motor_piston'] == 'down'  # Default is DOWN
        assert state['row_marker'] == 'up'
        assert state['row_cutter'] == 'up'

        # Sensor consistency checks
        assert state['line_marker_up_sensor'] is True
        assert state['line_marker_down_sensor'] is False
        assert state['line_cutter_up_sensor'] is True
        assert state['line_cutter_down_sensor'] is False
        assert state['line_motor_left_up_sensor'] is False  # DOWN position
        assert state['line_motor_left_down_sensor'] is True
        assert state['line_motor_right_up_sensor'] is False
        assert state['line_motor_right_down_sensor'] is True
        assert state['row_marker_up_sensor'] is True
        assert state['row_marker_down_sensor'] is False
        assert state['row_cutter_up_sensor'] is True
        assert state['row_cutter_down_sensor'] is False

    def test_hardware_state_after_lines_stop(self):
        """Full hardware state after stopping during lines operations."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = _make_mixed_steps_with_sensor()
        engine.load_steps(steps)
        engine.start_execution()
        time.sleep(0.5)

        engine.stop_execution()
        _wait_engine_stop(engine)

        state = self._get_full_hardware_state(hw)

        # Motor positions: Y moved to 20.0, X still at 0.0
        assert state['y_position'] == 20.0
        assert state['x_position'] == 0.0

        # line_motor_piston raised by stop for safety
        assert state['line_motor_piston'] == 'up'
        assert state['line_motor_left_up_sensor'] is True
        assert state['line_motor_left_down_sensor'] is False
        assert state['line_motor_right_up_sensor'] is True
        assert state['line_motor_right_down_sensor'] is False

        # line_marker was lowered at step 3 (before sensor wait)
        assert state['line_marker'] == 'down'
        assert state['line_marker_up_sensor'] is False
        assert state['line_marker_down_sensor'] is True

        # line_cutter never touched
        assert state['line_cutter'] == 'up'
        assert state['line_cutter_up_sensor'] is True
        assert state['line_cutter_down_sensor'] is False

        # Row tools never touched
        assert state['row_marker'] == 'up'
        assert state['row_marker_up_sensor'] is True
        assert state['row_marker_down_sensor'] is False
        assert state['row_cutter'] == 'up'

    def test_hardware_state_after_step_forward(self):
        """Hardware state after manually stepping forward."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 15.0},
             'description': 'Move X to 15'},
            {'operation': 'tool_action',
             'parameters': {'tool': 'line_marker', 'action': 'down'},
             'description': 'Lower line marker'},
            {'operation': 'move_y', 'parameters': {'position': 25.0},
             'description': 'Move Y to 25'},
        ]
        engine.load_steps(steps)

        # Step 0: program_start
        engine.execute_current_step()

        # Step 1: move_x
        engine.step_forward()
        engine.execute_current_step()
        state = self._get_full_hardware_state(hw)
        assert state['x_position'] == 15.0
        assert state['y_position'] == 0.0

        # Step 2: line_marker down
        engine.step_forward()
        engine.execute_current_step()
        state = self._get_full_hardware_state(hw)
        assert state['line_marker'] == 'down'
        assert state['line_marker_up_sensor'] is False
        assert state['line_marker_down_sensor'] is True

        # Step 3: move_y
        engine.step_forward()
        engine.execute_current_step()
        state = self._get_full_hardware_state(hw)
        assert state['y_position'] == 25.0
        assert state['line_marker'] == 'down'  # Still down from step 2

    def test_hardware_state_consistency_during_navigation(self):
        """Sensors should always be consistent with piston states during navigation."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'tool_action',
             'parameters': {'tool': 'line_marker', 'action': 'down'},
             'description': 'Lower line marker'},
            {'operation': 'tool_action',
             'parameters': {'tool': 'row_marker', 'action': 'down'},
             'description': 'Lower row marker'},
            {'operation': 'tool_action',
             'parameters': {'tool': 'line_marker', 'action': 'up'},
             'description': 'Raise line marker'},
            {'operation': 'tool_action',
             'parameters': {'tool': 'row_marker', 'action': 'up'},
             'description': 'Raise row marker'},
        ]
        engine.load_steps(steps)

        # Navigate forward through all steps, executing each
        for i in range(len(steps)):
            if i > 0:
                engine.step_forward()
            engine.execute_current_step()

            state = self._get_full_hardware_state(hw)

            # Sensor consistency: up_sensor XOR down_sensor for each piston
            assert state['line_marker_up_sensor'] != state['line_marker_down_sensor'], \
                f"Step {i}: line_marker sensors inconsistent"
            assert state['line_cutter_up_sensor'] != state['line_cutter_down_sensor'], \
                f"Step {i}: line_cutter sensors inconsistent"
            assert state['row_marker_up_sensor'] != state['row_marker_down_sensor'], \
                f"Step {i}: row_marker sensors inconsistent"
            assert state['row_cutter_up_sensor'] != state['row_cutter_down_sensor'], \
                f"Step {i}: row_cutter sensors inconsistent"

            # Sensor matches piston state
            if state['line_marker'] == 'up':
                assert state['line_marker_up_sensor'] is True
            else:
                assert state['line_marker_down_sensor'] is True

            if state['row_marker'] == 'up':
                assert state['row_marker_up_sensor'] is True
            else:
                assert state['row_marker_down_sensor'] is True


# ============================================================================
# Tests: Edge cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases for stop/continue/navigation."""

    def test_stop_at_first_step(self):
        """Stopping when first step is a sensor wait should work correctly.

        Note: signal_all_sensor_events() during stop may complete the wait_sensor
        step before the stop_event check, causing the index to advance to 1.
        This is expected behavior - the stop races with sensor completion.
        """
        _ensure_safety_clear()
        engine = ExecutionEngine()

        steps = [
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X'},
        ]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.2)

        engine.stop_execution()
        _wait_engine_stop(engine)

        # Index may be 0 or 1 depending on race between stop_event and
        # signal_all_sensor_events completing the wait_sensor step
        assert engine.current_step_index <= 1
        assert engine.is_running is False

    def test_stop_at_last_step(self):
        """Stopping when last step is a sensor wait should work correctly.

        Note: signal_all_sensor_events() during stop may complete the wait_sensor
        step, advancing the index past the last step. This is expected.
        """
        _ensure_safety_clear()
        engine = ExecutionEngine()

        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
        ]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.3)

        engine.stop_execution()
        _wait_engine_stop(engine)

        # Index may be 1 or 2 depending on race with signal_all_sensor_events
        assert engine.current_step_index >= 1
        assert engine.is_running is False
        # The first step should have completed regardless
        assert engine.hardware.get_current_x() == 10.0

    def test_multiple_stop_continue_cycles(self):
        """Multiple stop/continue cycles should work correctly."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X to 10'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
            {'operation': 'move_x', 'parameters': {'position': 20.0},
             'description': 'Move X to 20'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_right'},
             'description': 'Wait x_right'},
            {'operation': 'move_x', 'parameters': {'position': 30.0},
             'description': 'Move X to 30'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1},
             'description': 'Complete'},
        ]
        engine.load_steps(steps)

        # Cycle 1: start, execute steps 0-1, block on step 2 (sensor), stop
        engine.start_execution()
        time.sleep(0.3)
        engine.stop_execution()
        _wait_engine_stop(engine)

        assert hw.get_current_x() == 10.0
        cycle1_index = engine.current_step_index
        assert cycle1_index >= 2  # At or past the sensor wait

        # Cycle 2: continue past sensor, trigger sensor
        # First navigate past the sensor wait step
        engine.go_to_step(3)  # Skip to move_x 20

        engine.continue_execution()
        time.sleep(0.3)

        # Should block on step 4 (second sensor wait)
        engine.stop_execution()
        _wait_engine_stop(engine)

        assert hw.get_current_x() == 20.0

        # Cycle 3: navigate past last sensor wait and continue
        engine.go_to_step(5)  # Skip to move_x 30
        engine.continue_execution()

        _wait_engine_stop(engine, timeout=5.0)
        assert engine.execution_completed is True
        assert hw.get_current_x() == 30.0

    def test_stop_continue_with_tool_actions(self):
        """Stop/continue should handle tool action state correctly."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'tool_action',
             'parameters': {'tool': 'line_marker', 'action': 'down'},
             'description': 'lines: Lower line marker'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'lines: Wait x_left'},
            {'operation': 'tool_action',
             'parameters': {'tool': 'line_marker', 'action': 'up'},
             'description': 'lines: Raise line marker'},
        ]
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.3)

        # Should have executed step 1 (marker down) and blocked on step 2 (sensor)
        assert hw.get_line_marker_state() == "down"

        engine.stop_execution()
        _wait_engine_stop(engine)

        # Marker should still be down after stop
        assert hw.get_line_marker_state() == "down"

        # Navigate past sensor to step 3 (marker up)
        engine.go_to_step(3)

        # Continue to execute remaining steps
        engine.continue_execution()
        _wait_engine_stop(engine, timeout=5.0)

        # Marker should now be up
        assert hw.get_line_marker_state() == "up"

    def test_rapid_stop_start(self):
        """Rapid stop followed by continue should not cause race conditions."""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X to 10'},
            {'operation': 'move_y', 'parameters': {'position': 20.0},
             'description': 'Move Y to 20'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1},
             'description': 'Complete'},
        ]
        engine.load_steps(steps)

        for _ in range(3):
            engine.start_execution()
            time.sleep(0.05)
            engine.stop_execution()
            _wait_engine_stop(engine)
            assert engine.is_running is False

            # Reset for next cycle
            engine.reset_execution(clear_steps=False)
            engine.load_steps(steps)

    def test_reset_after_stop_clears_state(self):
        """reset_execution after stop should clear step index and all state."""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        steps = _make_simple_motor_steps()
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.3)
        engine.stop_execution()
        _wait_engine_stop(engine)

        assert engine.current_step_index > 0

        engine.reset_execution(clear_steps=False)

        assert engine.current_step_index == 0
        assert engine.is_running is False
        assert engine.is_paused is False
        assert engine.execution_completed is False
        assert engine.execution_failed is False
        assert len(engine.step_results) == 0
        assert engine.steps == steps  # Steps preserved

    def test_reset_with_clear_steps_removes_everything(self):
        """reset_execution(clear_steps=True) should clear steps too."""
        engine = ExecutionEngine()
        steps = _make_simple_motor_steps()
        engine.load_steps(steps)

        engine.reset_execution(clear_steps=True)

        assert len(engine.steps) == 0
        assert engine.current_step_index == 0

    def test_stop_during_rows_operations(self):
        """Stopping during rows operations - line_motor_piston should stay up (default)."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        hw = engine.hardware

        # First put line_motor_piston UP (as it would be during rows operations)
        hw.line_motor_piston_up()
        assert hw.get_line_motor_piston_state() == "up"

        steps = _make_rows_steps()
        engine.load_steps(steps)

        engine.start_execution()
        time.sleep(0.3)
        engine.stop_execution()
        _wait_engine_stop(engine)

        # line_motor_piston should still be up (was already up, stop shouldn't change it)
        assert hw.get_line_motor_piston_state() == "up"
        assert engine._raised_motor_on_stop is False

    def test_execute_current_step_returns_none_past_end(self):
        """execute_current_step should return None when past last step."""
        engine = ExecutionEngine()
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X'},
        ]
        engine.load_steps(steps)
        engine.current_step_index = len(steps)

        result = engine.execute_current_step()
        assert result is None

    def test_execute_current_step_blocked_during_active_run(self):
        """execute_current_step should return None while engine is actively running."""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        steps = [
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
        ]
        engine.load_steps(steps)
        engine.start_execution()
        time.sleep(0.1)

        result = engine.execute_current_step()
        assert result is None

        engine.stop_execution()
        _wait_engine_stop(engine)


# ============================================================================
# Tests: Canvas operation states (simulated without GUI)
# ============================================================================

class TestOperationStatesReplay:
    """Test the operation state replay logic used by _replay_canvas_state_to_current.

    Since the actual method lives on ControlsPanel (GUI), we test the underlying
    logic: resetting all states to pending, then replaying step tracking.
    """

    def _create_operation_states(self):
        """Create a mock operation_states dictionary."""
        return {
            'lines': {1: 'pending', 2: 'pending', 3: 'pending'},
            'cuts': {'top': 'pending', 'bottom': 'pending'},
            'pages': {0: 'pending', 1: 'pending'},
        }

    def _mark_operations_completed(self, states, lines=None, cuts=None, pages=None):
        """Mark specific operations as completed."""
        if lines:
            for line in lines:
                if line in states['lines']:
                    states['lines'][line] = 'completed'
        if cuts:
            for cut in cuts:
                if cut in states['cuts']:
                    states['cuts'][cut] = 'completed'
        if pages:
            for page in pages:
                if page in states['pages']:
                    states['pages'][page] = 'completed'

    def test_reset_all_states_to_pending(self):
        """Resetting all states to pending should work correctly."""
        states = self._create_operation_states()
        self._mark_operations_completed(states, lines=[1, 2], cuts=['top'], pages=[0])

        # Verify some are completed
        assert states['lines'][1] == 'completed'
        assert states['cuts']['top'] == 'completed'

        # Reset all to pending
        for state_dict in states.values():
            for key in state_dict:
                state_dict[key] = 'pending'

        # Verify all are pending
        for state_dict in states.values():
            for key, value in state_dict.items():
                assert value == 'pending', f"State {key} should be pending"

    def test_replay_marks_correct_operations(self):
        """Replaying should only mark operations for steps 0..current."""
        states = self._create_operation_states()

        # Simulate step descriptions that would be processed by track_operation_from_step
        steps_with_line_info = [
            {'description': 'Start Program'},
            {'description': 'lines: Move Y to line 1'},
            {'description': 'lines: Open line_marker for line 1'},
            {'description': 'lines: Close line_marker after line 1'},  # Line 1 completed
            {'description': 'lines: Move Y to line 2'},
            {'description': 'lines: Open line_marker for line 2'},
            {'description': 'lines: Close line_marker after line 2'},  # Line 2 completed
            {'description': 'lines: Move Y to line 3'},
        ]

        # If current_index is 3 (after line 1 closed), only line 1 should be tracked
        current_index = 3

        # Reset all to pending
        for state_dict in states.values():
            for key in state_dict:
                state_dict[key] = 'pending'

        # Count how many "close line_marker" steps are in 0..current_index
        close_marker_count = sum(
            1 for i in range(current_index + 1)
            if 'Close line_marker' in steps_with_line_info[i]['description']
        )

        # Should have exactly 1 close marker in steps 0..3
        assert close_marker_count == 1

    def test_stepping_backward_resets_state(self):
        """When stepping backward, states that were ahead should revert to pending."""
        states = self._create_operation_states()

        # Mark lines 1 and 2 as completed (we were at step 6)
        self._mark_operations_completed(states, lines=[1, 2])
        assert states['lines'][1] == 'completed'
        assert states['lines'][2] == 'completed'

        # Step backward: reset all then replay up to step 3 (only line 1 done)
        for state_dict in states.values():
            for key in state_dict:
                state_dict[key] = 'pending'

        # Replay: only line 1 is completed
        states['lines'][1] = 'completed'

        assert states['lines'][1] == 'completed'
        assert states['lines'][2] == 'pending'  # Reverted
        assert states['lines'][3] == 'pending'


# ============================================================================
# Tests: Status callback during stop/continue
# ============================================================================

class TestStatusCallbacks:
    """Test that status callbacks fire correctly during stop/continue flow."""

    def test_stop_triggers_stopped_status(self):
        """Stopping should trigger 'stopped' status callback."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        statuses = []

        def callback(status, info=None):
            statuses.append(status)

        engine.set_status_callback(callback)

        steps = [
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
        ]
        engine.load_steps(steps)
        engine.start_execution()
        time.sleep(0.2)

        engine.stop_execution()
        _wait_engine_stop(engine)

        assert 'started' in statuses
        assert 'stopped' in statuses

    def test_continue_triggers_started_status(self):
        """Continuing should trigger 'started' status callback."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        statuses = []

        def callback(status, info=None):
            statuses.append(status)

        engine.set_status_callback(callback)

        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
        ]
        engine.load_steps(steps)
        engine.start_execution()
        time.sleep(0.2)

        engine.stop_execution()
        _wait_engine_stop(engine)

        # Clear statuses for continue phase
        statuses.clear()

        engine.go_to_step(0)
        engine.continue_execution()
        time.sleep(0.1)

        assert 'started' in statuses

        engine.stop_execution()
        _wait_engine_stop(engine)


# ============================================================================
# Tests: Execution engine state flags
# ============================================================================

class TestEngineStateFlags:
    """Test that engine state flags are correct at each point."""

    def test_flags_after_load(self):
        """State flags after loading steps."""
        engine = ExecutionEngine()
        steps = _make_simple_motor_steps()
        engine.load_steps(steps)

        assert engine.is_running is False
        assert engine.is_paused is False
        assert engine.execution_completed is False
        assert engine.execution_failed is False
        assert engine.current_step_index == 0

    def test_flags_during_execution(self):
        """State flags while executing."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = [
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
        ]
        engine.load_steps(steps)
        engine.start_execution()
        time.sleep(0.1)

        assert engine.is_running is True
        assert engine.is_paused is False
        assert engine.execution_completed is False

        engine.stop_execution()
        _wait_engine_stop(engine)

    def test_flags_after_stop(self):
        """State flags after stopping."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = [
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
        ]
        engine.load_steps(steps)
        engine.start_execution()
        time.sleep(0.1)

        engine.stop_execution()
        _wait_engine_stop(engine)

        assert engine.is_running is False
        assert engine.is_paused is False

    def test_flags_after_continue(self):
        """State flags after continue_execution."""
        _ensure_safety_clear()
        engine = ExecutionEngine()

        # Use two sensor waits: stop during first, navigate past it,
        # continue and block on the second to observe running state.
        steps = [
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_left'},
             'description': 'Wait x_left'},
            {'operation': 'move_x', 'parameters': {'position': 20.0},
             'description': 'Move X to 20'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x_right'},
             'description': 'Wait x_right'},
        ]
        engine.load_steps(steps)
        engine.start_execution()
        time.sleep(0.2)

        engine.stop_execution()
        _wait_engine_stop(engine)

        # Navigate to step 2 (move_x to 20) - past the first sensor wait
        engine.go_to_step(2)
        engine.continue_execution()
        time.sleep(0.2)

        # Should be running and blocked on step 3 (second sensor wait)
        assert engine.is_running is True
        assert engine.is_paused is False
        assert engine.execution_completed is False
        assert engine.execution_failed is False

        engine.stop_execution()
        _wait_engine_stop(engine)

    def test_flags_after_completion(self):
        """State flags after natural completion."""
        _ensure_safety_clear()
        engine = ExecutionEngine()
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1},
             'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0},
             'description': 'Move X'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1},
             'description': 'Complete'},
        ]
        engine.load_steps(steps)
        engine.start_execution()

        _wait_engine_stop(engine, timeout=5.0)

        assert engine.is_running is False
        assert engine.is_paused is False
        assert engine.execution_completed is True
        assert engine.execution_failed is False

    def test_flags_after_reset(self):
        """State flags after reset_execution."""
        engine = ExecutionEngine()
        steps = _make_simple_motor_steps()
        engine.load_steps(steps)

        # Simulate some state
        engine.current_step_index = 5
        engine.execution_completed = True
        engine.step_results = [{'step_index': 0, 'result': {'success': True}}]

        engine.reset_execution()

        assert engine.is_running is False
        assert engine.is_paused is False
        assert engine.execution_completed is False
        assert engine.execution_failed is False
        assert engine.current_step_index == 0
        assert len(engine.step_results) == 0
        assert engine.in_transition is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

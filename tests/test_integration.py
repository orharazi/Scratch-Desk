#!/usr/bin/env python3

import pytest
import time
from core.csv_parser import CSVParser
from core.step_generator import generate_complete_program_steps
from core.execution_engine import ExecutionEngine
from core.program_model import ScratchDeskProgram
from core.machine_state import MachineState, MachineStateManager
from core.safety_system import SafetyViolation, SafetySystem, check_step_safety
from hardware.implementations.mock import mock_hardware


def _ensure_safety_clear():
    """Disable safety system so execution tests don't get blocked by safety rules."""
    from core.safety_system import safety_system
    safety_system.disable_safety()
    # Also disable at rules level to prevent safety monitor thread from blocking
    safety_system.rules_manager.rules_data['global_enabled'] = False
    safety_system.rules_manager.rules = []


class TestCSVToStepGeneration:
    """Test CSV parsing to step generation pipeline"""

    def test_load_csv_generate_steps(self, csv_file):
        """CSV should parse and generate executable steps"""
        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(csv_file)

        assert len(errors) == 0
        assert len(programs) > 0

        # Generate steps from first program
        program = programs[0]
        steps = generate_complete_program_steps(program)

        assert len(steps) > 0
        # Should have program_start and program_complete
        assert steps[0]['operation'] == 'program_start'
        assert steps[-1]['operation'] == 'program_complete'

    def test_invalid_program_no_steps(self, invalid_program):
        """Invalid program should produce validation errors"""
        validation_errors = invalid_program.validate()
        assert len(validation_errors) > 0
        assert not invalid_program.is_valid()


class TestStepExecutionPipeline:
    """Test step execution from start to finish"""

    def test_execute_simple_program(self, settings_file):
        """Should execute simple movement steps successfully"""
        _ensure_safety_clear()
        from hardware.interfaces.hardware_factory import get_hardware_interface
        hw = get_hardware_interface(settings_file)

        engine = ExecutionEngine()

        # Simple steps without sensor waits
        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1}, 'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 25.0}, 'description': 'Move X'},
            {'operation': 'move_y', 'parameters': {'position': 30.0}, 'description': 'Move Y'},
            {'operation': 'tool_action', 'parameters': {'tool': 'line_marker', 'action': 'down'}, 'description': 'Marker down'},
            {'operation': 'tool_action', 'parameters': {'tool': 'line_marker', 'action': 'up'}, 'description': 'Marker up'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1}, 'description': 'Complete'},
        ]

        engine.load_steps(steps)
        result = engine.start_execution()
        assert result is True

        # Wait for completion
        timeout = 10.0
        start = time.time()
        while engine.is_running and (time.time() - start) < timeout:
            time.sleep(0.05)

        assert engine.is_running is False, "Execution should have completed"

        # Verify positions
        assert mock_hardware.get_current_x() == 25.0
        assert mock_hardware.get_current_y() == 30.0
        assert mock_hardware.get_line_marker_state() == "up"

    def test_pause_resume_execution(self, settings_file):
        """Should pause and resume execution correctly"""
        _ensure_safety_clear()
        from hardware.interfaces.hardware_factory import get_hardware_interface
        hw = get_hardware_interface(settings_file)

        engine = ExecutionEngine()

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1}, 'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X 10'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X'},
            {'operation': 'move_x', 'parameters': {'position': 30.0}, 'description': 'Move X 30'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1}, 'description': 'Complete'},
        ]

        engine.load_steps(steps)
        engine.start_execution()

        # Let first steps execute, then it should block on wait_sensor
        time.sleep(0.5)

        # Pause
        pause_result = engine.pause_execution()
        assert pause_result is True
        assert engine.is_paused is True

        # Resume
        time.sleep(0.1)
        resume_result = engine.resume_execution()
        assert resume_result is True

        # Cleanup - don't wait for sensor, just stop
        engine.stop_execution()
        time.sleep(0.2)

    def test_stop_mid_execution(self, settings_file):
        """Should stop execution mid-run"""
        _ensure_safety_clear()
        from hardware.interfaces.hardware_factory import get_hardware_interface
        hw = get_hardware_interface(settings_file)

        engine = ExecutionEngine()

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1}, 'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X 10'},
            {'operation': 'wait_sensor', 'parameters': {'sensor': 'x'}, 'description': 'Wait X'},
            {'operation': 'move_x', 'parameters': {'position': 30.0}, 'description': 'Move X 30'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1}, 'description': 'Complete'},
        ]

        engine.load_steps(steps)
        engine.start_execution()

        # Let it start
        time.sleep(0.3)

        # Stop
        engine.stop_execution()
        time.sleep(0.2)

        assert engine.is_running is False


class TestSafetyDuringExecution:
    """Test safety system integration during execution.

    Note: These tests create a fresh SafetySystem with mock hardware
    because the module-level safety_system singleton may be initialized
    with real hardware before conftest patches take effect.
    """

    def test_safety_blocks_move_y_when_row_marker_down(self):
        """Safety system should prevent Y movement when row marker is down"""
        from core.safety_system import SafetySystem, SafetyRulesManager
        from hardware.interfaces.hardware_factory import get_hardware_interface

        hw = get_hardware_interface()
        ss = SafetySystem.__new__(SafetySystem)
        ss.safety_enabled = True
        ss.violations_log = []
        ss.hardware = hw
        ss.logger = __import__('core.logger', fromlist=['get_logger']).get_logger()
        ss.rules_manager = SafetyRulesManager(hw)

        # Put row marker down
        mock_hardware.row_marker_down()
        assert hw.get_row_marker_state() == 'down'

        step = {
            'operation': 'move_y',
            'parameters': {'position': 50.0},
            'description': 'Move Y to 50cm'
        }

        with pytest.raises(SafetyViolation):
            ss.check_step_safety(step)

    def test_safety_allows_move_y_when_row_marker_up(self):
        """Safety system should allow Y movement when row marker is up"""
        from core.safety_system import SafetySystem, SafetyRulesManager
        from hardware.interfaces.hardware_factory import get_hardware_interface

        hw = get_hardware_interface()
        ss = SafetySystem.__new__(SafetySystem)
        ss.safety_enabled = True
        ss.violations_log = []
        ss.hardware = hw
        ss.logger = __import__('core.logger', fromlist=['get_logger']).get_logger()
        ss.rules_manager = SafetyRulesManager(hw)

        # Ensure row marker is up and door not blocking
        mock_hardware.row_marker_up()
        mock_hardware.set_limit_switch_state('rows_door', False)  # False = "up" = not blocking
        mock_hardware.line_motor_piston_down()

        step = {
            'operation': 'move_y',
            'parameters': {'position': 50.0},
            'description': 'Move Y to 50cm'
        }

        try:
            ss.check_step_safety(step)
        except SafetyViolation:
            pytest.fail("Safety check should pass when row marker is up")


class TestProgramValidationToExecution:
    """Test program validation through to execution"""

    def test_valid_program_produces_executable_steps(self, valid_program):
        """Valid program should generate executable steps"""
        steps = generate_complete_program_steps(valid_program)

        assert len(steps) > 0
        assert steps[0]['operation'] == 'program_start'
        assert steps[-1]['operation'] == 'program_complete'

        for step in steps:
            assert 'operation' in step
            assert 'parameters' in step
            assert 'description' in step


class TestStateManagementDuringExecution:
    """Test state transitions during execution"""

    def test_state_transitions_during_execution(self, settings_file):
        """State should transition correctly during execution lifecycle"""
        _ensure_safety_clear()
        from hardware.interfaces.hardware_factory import get_hardware_interface
        hw = get_hardware_interface(settings_file)

        engine = ExecutionEngine()
        state_manager = MachineStateManager()

        assert state_manager.state == MachineState.IDLE

        steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1}, 'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 10.0}, 'description': 'Move X'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1}, 'description': 'Complete'},
        ]

        engine.load_steps(steps)
        engine.start_execution()

        # Should transition to RUNNING
        time.sleep(0.05)
        assert state_manager.state == MachineState.RUNNING

        # Wait for completion
        timeout = 10.0
        start = time.time()
        while engine.is_running and (time.time() - start) < timeout:
            time.sleep(0.05)

        # After completion, state should return to IDLE
        assert state_manager.state == MachineState.IDLE


class TestEndToEndPipeline:
    """Test complete pipeline from CSV to execution"""

    def test_complete_pipeline(self, csv_file, settings_file):
        """Complete pipeline: CSV -> Parse -> Generate -> Execute"""
        _ensure_safety_clear()
        from hardware.interfaces.hardware_factory import get_hardware_interface
        hw = get_hardware_interface(settings_file)

        # Step 1: Parse CSV
        parser = CSVParser()
        programs, errors = parser.load_programs_from_csv(csv_file)
        assert len(errors) == 0
        assert len(programs) > 0

        # Step 2: Generate steps from first program
        program = programs[0]
        steps = generate_complete_program_steps(program)
        assert len(steps) > 0

        # Step 3: Use simple steps to test execution (avoid sensor waits)
        simple_steps = [
            {'operation': 'program_start', 'parameters': {'program_number': 1}, 'description': 'Start'},
            {'operation': 'move_x', 'parameters': {'position': 20.0}, 'description': 'Move X'},
            {'operation': 'move_y', 'parameters': {'position': 25.0}, 'description': 'Move Y'},
            {'operation': 'program_complete', 'parameters': {'program_number': 1}, 'description': 'Complete'},
        ]

        # Step 4: Execute
        engine = ExecutionEngine()
        engine.load_steps(simple_steps)
        engine.start_execution()

        # Wait for completion
        timeout = 10.0
        start = time.time()
        while engine.is_running and (time.time() - start) < timeout:
            time.sleep(0.05)

        assert engine.is_running is False, "Execution should have completed"

        # Verify execution
        assert mock_hardware.get_current_x() == 20.0
        assert mock_hardware.get_current_y() == 25.0

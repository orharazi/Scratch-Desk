#!/usr/bin/env python3

import pytest
import threading
import time
from hardware.implementations.mock import mock_hardware
from hardware.implementations.mock.mock_hardware import MockHardware


class TestMovement:
    """Test motor movement functions"""

    def test_move_x_basic(self):
        """Should move X motor to specified position"""
        result = mock_hardware.move_x(25.0)
        assert result is True
        assert mock_hardware.get_current_x() == 25.0

    def test_move_y_basic(self):
        """Should move Y motor to specified position"""
        result = mock_hardware.move_y(30.0)
        assert result is True
        assert mock_hardware.get_current_y() == 30.0

    def test_move_x_clamped_max(self):
        """X position should be clamped to maximum"""
        max_x = mock_hardware.MAX_X_POSITION
        mock_hardware.move_x(max_x + 10.0)
        assert mock_hardware.get_current_x() == max_x

    def test_move_x_clamped_min(self):
        """X position should be clamped to minimum"""
        min_x = mock_hardware.MIN_X_POSITION
        mock_hardware.move_x(min_x - 10.0)
        assert mock_hardware.get_current_x() == min_x

    def test_move_y_clamped_max(self):
        """Y position should be clamped to maximum"""
        max_y = mock_hardware.MAX_Y_POSITION
        mock_hardware.move_y(max_y + 10.0)
        assert mock_hardware.get_current_y() == max_y

    def test_move_y_clamped_min(self):
        """Y position should be clamped to minimum"""
        min_y = mock_hardware.MIN_Y_POSITION
        mock_hardware.move_y(min_y - 10.0)
        assert mock_hardware.get_current_y() == min_y

    def test_get_current_x(self):
        """Should return current X position"""
        mock_hardware.move_x(15.5)
        assert mock_hardware.get_current_x() == 15.5

    def test_get_current_y(self):
        """Should return current Y position"""
        mock_hardware.move_y(20.5)
        assert mock_hardware.get_current_y() == 20.5


class TestPistonControl:
    """Test piston control functions"""

    def test_line_marker_down(self):
        """Line marker should move to down position"""
        mock_hardware.line_marker_down()
        assert mock_hardware.line_marker_piston == "down"
        assert mock_hardware.line_marker_up_sensor is False
        assert mock_hardware.line_marker_down_sensor is True

    def test_line_marker_up(self):
        """Line marker should move to up position"""
        mock_hardware.line_marker_down()
        mock_hardware.line_marker_up()
        assert mock_hardware.line_marker_piston == "up"
        assert mock_hardware.line_marker_up_sensor is True
        assert mock_hardware.line_marker_down_sensor is False

    def test_line_cutter_down(self):
        """Line cutter should move to down position"""
        mock_hardware.line_cutter_down()
        assert mock_hardware.line_cutter_piston == "down"
        assert mock_hardware.line_cutter_up_sensor is False
        assert mock_hardware.line_cutter_down_sensor is True

    def test_line_cutter_up(self):
        """Line cutter should move to up position"""
        mock_hardware.line_cutter_down()
        mock_hardware.line_cutter_up()
        assert mock_hardware.line_cutter_piston == "up"
        assert mock_hardware.line_cutter_up_sensor is True
        assert mock_hardware.line_cutter_down_sensor is False

    def test_row_marker_down(self):
        """Row marker should move to down position"""
        mock_hardware.row_marker_down()
        assert mock_hardware.row_marker_piston == "down"
        assert mock_hardware.row_marker_up_sensor is False
        assert mock_hardware.row_marker_down_sensor is True

    def test_row_marker_up(self):
        """Row marker should move to up position"""
        mock_hardware.row_marker_down()
        mock_hardware.row_marker_up()
        assert mock_hardware.row_marker_piston == "up"
        assert mock_hardware.row_marker_up_sensor is True
        assert mock_hardware.row_marker_down_sensor is False

    def test_row_cutter_down(self):
        """Row cutter should move to down position"""
        mock_hardware.row_cutter_down()
        assert mock_hardware.row_cutter_piston == "down"
        assert mock_hardware.row_cutter_up_sensor is False
        assert mock_hardware.row_cutter_down_sensor is True

    def test_row_cutter_up(self):
        """Row cutter should move to up position"""
        mock_hardware.row_cutter_down()
        mock_hardware.row_cutter_up()
        assert mock_hardware.row_cutter_piston == "up"
        assert mock_hardware.row_cutter_up_sensor is True
        assert mock_hardware.row_cutter_down_sensor is False

    def test_line_motor_default_down(self):
        """Line motor piston should default to down"""
        # After reset, line motor should be down
        assert mock_hardware.line_motor_piston == "down"
        assert mock_hardware.line_motor_left_down_sensor is True
        assert mock_hardware.line_motor_right_down_sensor is True

    def test_air_pressure_valve(self):
        """Air pressure valve should control state"""
        # Default is up (closed)
        mock_hardware.air_pressure_valve_up()
        assert mock_hardware.get_air_pressure_valve_state() == "up"

        mock_hardware.air_pressure_valve_down()
        assert mock_hardware.get_air_pressure_valve_state() == "down"


class TestSensors:
    """Test sensor state functions"""

    def test_dual_sensor_consistency(self):
        """Up and down sensors should be mutually exclusive"""
        # Line marker
        mock_hardware.line_marker_up()
        assert mock_hardware.line_marker_up_sensor is True
        assert mock_hardware.line_marker_down_sensor is False

        mock_hardware.line_marker_down()
        assert mock_hardware.line_marker_up_sensor is False
        assert mock_hardware.line_marker_down_sensor is True

    def test_get_line_marker_state(self):
        """get_line_marker_state should return 'up' or 'down'"""
        mock_hardware.line_marker_up()
        assert mock_hardware.get_line_marker_state() == "up"

        mock_hardware.line_marker_down()
        assert mock_hardware.get_line_marker_state() == "down"

    def test_get_row_marker_state(self):
        """get_row_marker_state should return 'up' or 'down'"""
        mock_hardware.row_marker_up()
        assert mock_hardware.get_row_marker_state() == "up"

        mock_hardware.row_marker_down()
        assert mock_hardware.get_row_marker_state() == "down"

    def test_edge_sensors_default_false(self):
        """Edge sensors should default to False"""
        assert mock_hardware.x_left_edge is False
        assert mock_hardware.x_right_edge is False
        assert mock_hardware.y_top_edge is False
        assert mock_hardware.y_bottom_edge is False


class TestSensorTriggers:
    """Test manual sensor triggering"""

    def test_trigger_x_left_sensor(self):
        """Should trigger left X sensor"""
        mock_hardware.trigger_x_left_sensor()
        assert mock_hardware.sensor_trigger_states['x_left'] is True
        assert mock_hardware.x_left_edge is True

    def test_trigger_x_right_sensor(self):
        """Should trigger right X sensor"""
        mock_hardware.trigger_x_right_sensor()
        assert mock_hardware.sensor_trigger_states['x_right'] is True
        assert mock_hardware.x_right_edge is True

    def test_trigger_y_top_sensor(self):
        """Should trigger top Y sensor"""
        mock_hardware.trigger_y_top_sensor()
        assert mock_hardware.sensor_trigger_states['y_top'] is True
        assert mock_hardware.y_top_edge is True

    def test_trigger_y_bottom_sensor(self):
        """Should trigger bottom Y sensor"""
        mock_hardware.trigger_y_bottom_sensor()
        assert mock_hardware.sensor_trigger_states['y_bottom'] is True
        assert mock_hardware.y_bottom_edge is True

    def test_sensor_states_tracked(self):
        """Sensor trigger states should be tracked correctly"""
        mock_hardware.trigger_x_left_sensor()
        assert 'x_left' in mock_hardware.sensor_trigger_states
        assert mock_hardware.sensor_trigger_states['x_left'] is True


class TestSensorWait:
    """Test sensor wait functions"""

    def test_wait_for_x_left_triggers(self):
        """wait_for_x_left_sensor should unblock when triggered"""
        result = {'value': None}

        def trigger_after_delay():
            time.sleep(0.1)
            mock_hardware.trigger_x_left_sensor()

        def wait_for_sensor():
            result['value'] = mock_hardware.wait_for_x_left_sensor()

        # Start trigger thread
        trigger_thread = threading.Thread(target=trigger_after_delay)
        wait_thread = threading.Thread(target=wait_for_sensor)

        wait_thread.start()
        trigger_thread.start()

        wait_thread.join(timeout=2.0)
        trigger_thread.join(timeout=2.0)

        assert result['value'] == 'left'

    def test_wait_returns_none_on_stop(self):
        """wait_for_x_left_sensor should return None when stop event set"""
        # Create a mock execution engine with stop event
        class MockEngine:
            def __init__(self):
                self.stop_event = threading.Event()
                self.is_paused = False

        engine = MockEngine()
        mock_hardware.current_execution_engine = engine

        result = {'value': 'not set'}

        def wait_for_sensor():
            result['value'] = mock_hardware.wait_for_x_left_sensor()

        def set_stop():
            time.sleep(0.1)
            engine.stop_event.set()

        wait_thread = threading.Thread(target=wait_for_sensor)
        stop_thread = threading.Thread(target=set_stop)

        wait_thread.start()
        stop_thread.start()

        wait_thread.join(timeout=2.0)
        stop_thread.join(timeout=2.0)

        assert result['value'] is None

        # Cleanup
        mock_hardware.current_execution_engine = None


class TestLimitSwitches:
    """Test limit switch functions"""

    def test_get_row_motor_door_piston_state(self):
        """Should return 'up' or 'down' based on row motor door piston state"""
        mock_hardware.row_motor_door_piston_up()
        assert mock_hardware.get_row_motor_door_piston_state() == "up"

        mock_hardware.row_motor_door_piston_down()
        assert mock_hardware.get_row_motor_door_piston_state() == "down"

    def test_set_limit_switch_state(self):
        """Should set limit switch state"""
        mock_hardware.set_limit_switch_state('x_left', True)
        assert mock_hardware.limit_switch_states['x_left'] is True

    def test_toggle_limit_switch(self):
        """Should toggle limit switch state"""
        initial = mock_hardware.limit_switch_states['x_left']
        mock_hardware.toggle_limit_switch('x_left')
        assert mock_hardware.limit_switch_states['x_left'] == (not initial)

    def test_get_limit_switch_state(self):
        """Should get limit switch state"""
        mock_hardware.limit_switch_states['y_top'] = True
        assert mock_hardware.get_limit_switch_state('y_top') is True


class TestSensorBuffers:
    """Test sensor buffer management"""

    def test_flush_clears_events(self):
        """flush_all_sensor_buffers should clear all sensor events"""
        # Trigger some sensors
        mock_hardware.trigger_x_left_sensor()
        mock_hardware.trigger_y_top_sensor()

        # Flush buffers
        mock_hardware.flush_all_sensor_buffers()

        # Events should be cleared
        assert not mock_hardware.sensor_events['x_left'].is_set()
        assert not mock_hardware.sensor_events['y_top'].is_set()

    def test_signal_sets_events(self):
        """signal_all_sensor_events should set all events"""
        # Clear all first
        mock_hardware.flush_all_sensor_buffers()

        # Signal all
        mock_hardware.signal_all_sensor_events()

        # All events should be set
        assert mock_hardware.sensor_events['x_left'].is_set()
        assert mock_hardware.sensor_events['x_right'].is_set()
        assert mock_hardware.sensor_events['y_top'].is_set()
        assert mock_hardware.sensor_events['y_bottom'].is_set()


class TestResetHardware:
    """Test hardware reset function"""

    def test_reset_positions(self):
        """Reset should restore positions to 0"""
        mock_hardware.move_x(50.0)
        mock_hardware.move_y(60.0)
        mock_hardware.reset_hardware()
        assert mock_hardware.get_current_x() == 0.0
        assert mock_hardware.get_current_y() == 0.0

    def test_reset_pistons(self):
        """Reset should restore pistons to default states"""
        mock_hardware.line_marker_down()
        mock_hardware.row_marker_down()
        mock_hardware.reset_hardware()

        assert mock_hardware.line_marker_piston == "up"
        assert mock_hardware.row_marker_piston == "up"
        assert mock_hardware.line_motor_piston == "down"

    def test_reset_sensors(self):
        """Reset should clear sensor states"""
        mock_hardware.trigger_x_left_sensor()
        mock_hardware.trigger_y_top_sensor()
        mock_hardware.reset_hardware()

        assert mock_hardware.sensor_trigger_states['x_left'] is False
        assert mock_hardware.sensor_trigger_states['y_top'] is False

    def test_reset_limit_switches(self):
        """Reset should restore limit switches to defaults"""
        mock_hardware.reset_hardware()

        # At home position (0,0), x_right and y_bottom should be active
        assert mock_hardware.limit_switch_states['x_right'] is True
        assert mock_hardware.limit_switch_states['y_bottom'] is True
        assert mock_hardware.limit_switch_states['x_left'] is False
        assert mock_hardware.limit_switch_states['y_top'] is False


class TestMockHardwareClass:
    """Test MockHardware class wrapper"""

    def test_initialize(self):
        """MockHardware.initialize should succeed"""
        hw = MockHardware()
        result = hw.initialize()
        assert result is True
        assert hw.is_initialized is True

    def test_shutdown(self):
        """MockHardware.shutdown should clear initialized flag"""
        hw = MockHardware()
        hw.initialize()
        hw.shutdown()
        assert hw.is_initialized is False

    def test_class_methods_call_module_functions(self):
        """MockHardware methods should call module-level functions"""
        hw = MockHardware()
        hw.initialize()

        # Test move_x
        hw.move_x(30.0)
        assert mock_hardware.get_current_x() == 30.0

        # Test move_y
        hw.move_y(40.0)
        assert mock_hardware.get_current_y() == 40.0

        # Test piston control
        hw.line_marker_down()
        assert mock_hardware.line_marker_piston == "down"

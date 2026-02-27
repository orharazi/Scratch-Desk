#!/usr/bin/env python3

import pytest
import threading
import time
from core.machine_state import MachineState, MachineStateManager


class TestMachineStateEnum:
    """Test MachineState enum definitions"""

    def test_all_states_exist(self):
        """All expected states should exist"""
        assert hasattr(MachineState, 'IDLE')
        assert hasattr(MachineState, 'HOMING')
        assert hasattr(MachineState, 'RUNNING')
        assert hasattr(MachineState, 'PAUSED')
        assert hasattr(MachineState, 'ERROR')
        assert hasattr(MachineState, 'SWITCHING_MODE')

    def test_state_values(self):
        """States should have correct string values"""
        assert MachineState.IDLE.value == "idle"
        assert MachineState.HOMING.value == "homing"
        assert MachineState.RUNNING.value == "running"
        assert MachineState.PAUSED.value == "paused"
        assert MachineState.ERROR.value == "error"
        assert MachineState.SWITCHING_MODE.value == "switching_mode"


class TestSingletonPattern:
    """Test MachineStateManager singleton behavior"""

    def test_singleton_pattern(self):
        """Multiple instances should return the same object"""
        manager1 = MachineStateManager()
        manager2 = MachineStateManager()
        assert manager1 is manager2

    def test_initial_state_idle(self):
        """Initial state should be IDLE"""
        manager = MachineStateManager()
        assert manager.state == MachineState.IDLE
        assert manager.error_message is None


class TestStateManagement:
    """Test state transitions and error messages"""

    def test_set_state(self):
        """Should update state correctly"""
        manager = MachineStateManager()
        manager.set_state(MachineState.RUNNING)
        assert manager.state == MachineState.RUNNING

    def test_error_message_set(self):
        """Error message should be stored when state is ERROR"""
        manager = MachineStateManager()
        error_msg = "Hardware connection failed"
        manager.set_state(MachineState.ERROR, error_message=error_msg)
        assert manager.state == MachineState.ERROR
        assert manager.error_message == error_msg

    def test_error_message_cleared_on_non_error(self):
        """Error message should be cleared when transitioning from ERROR to other states"""
        manager = MachineStateManager()
        manager.set_state(MachineState.ERROR, error_message="Test error")
        assert manager.error_message == "Test error"

        manager.set_state(MachineState.IDLE)
        assert manager.error_message is None


class TestObserverPattern:
    """Test observer notifications"""

    def test_observer_notified(self):
        """Observer should be called when state changes"""
        manager = MachineStateManager()
        called = {'count': 0, 'old': None, 'new': None}

        def observer(old_state, new_state):
            called['count'] += 1
            called['old'] = old_state
            called['new'] = new_state

        manager.add_observer(observer)
        manager.set_state(MachineState.RUNNING)

        assert called['count'] == 1
        assert called['old'] == MachineState.IDLE
        assert called['new'] == MachineState.RUNNING

    def test_observer_not_duplicated(self):
        """Adding same observer twice should only call it once"""
        manager = MachineStateManager()
        called = {'count': 0}

        def observer(old_state, new_state):
            called['count'] += 1

        manager.add_observer(observer)
        manager.add_observer(observer)  # Add again
        manager.set_state(MachineState.RUNNING)

        assert called['count'] == 1

    def test_remove_observer(self):
        """Removed observer should not be called"""
        manager = MachineStateManager()
        called = {'count': 0}

        def observer(old_state, new_state):
            called['count'] += 1

        manager.add_observer(observer)
        manager.remove_observer(observer)
        manager.set_state(MachineState.RUNNING)

        assert called['count'] == 0

    def test_observer_exception_handled(self):
        """Observer exception should not crash state manager"""
        manager = MachineStateManager()
        called = {'bad': False, 'good': False}

        def bad_observer(old_state, new_state):
            called['bad'] = True
            raise ValueError("Observer error")

        def good_observer(old_state, new_state):
            called['good'] = True

        manager.add_observer(bad_observer)
        manager.add_observer(good_observer)
        manager.set_state(MachineState.RUNNING)

        # Both observers called, exception handled
        assert called['bad'] is True
        assert called['good'] is True
        assert manager.state == MachineState.RUNNING


class TestIsBusy:
    """Test is_busy() method"""

    def test_is_busy_running(self):
        """RUNNING state should be busy"""
        manager = MachineStateManager()
        manager.set_state(MachineState.RUNNING)
        assert manager.is_busy() is True

    def test_is_busy_homing(self):
        """HOMING state should be busy"""
        manager = MachineStateManager()
        manager.set_state(MachineState.HOMING)
        assert manager.is_busy() is True

    def test_is_busy_switching(self):
        """SWITCHING_MODE state should be busy"""
        manager = MachineStateManager()
        manager.set_state(MachineState.SWITCHING_MODE)
        assert manager.is_busy() is True

    def test_is_busy_idle(self):
        """IDLE state should not be busy"""
        manager = MachineStateManager()
        manager.set_state(MachineState.IDLE)
        assert manager.is_busy() is False


class TestCanSwitchMode:
    """Test can_switch_mode() method"""

    def test_can_switch_mode_idle(self):
        """Should allow mode switch when IDLE"""
        manager = MachineStateManager()
        manager.set_state(MachineState.IDLE)
        can_switch, reason = manager.can_switch_mode()
        assert can_switch is True
        assert reason == ""

    def test_can_switch_mode_running(self):
        """Should not allow mode switch when RUNNING"""
        manager = MachineStateManager()
        manager.set_state(MachineState.RUNNING)
        can_switch, reason = manager.can_switch_mode()
        assert can_switch is False
        assert "execution is in progress" in reason.lower()


class TestReset:
    """Test reset() method"""

    def test_reset_to_idle(self):
        """Reset should transition to IDLE state"""
        manager = MachineStateManager()
        manager.set_state(MachineState.ERROR, error_message="Test error")
        assert manager.state == MachineState.ERROR

        manager.reset()
        assert manager.state == MachineState.IDLE
        assert manager.error_message is None


class TestThreadSafety:
    """Test thread-safe operations"""

    def test_thread_safety(self):
        """Concurrent set_state calls should be thread-safe"""
        manager = MachineStateManager()
        results = []

        def set_states():
            for state in [MachineState.RUNNING, MachineState.PAUSED, MachineState.IDLE]:
                manager.set_state(state)
                time.sleep(0.001)
                results.append(manager.state)

        threads = [threading.Thread(target=set_states) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All results should be valid states (no corruption)
        for result in results:
            assert isinstance(result, MachineState)

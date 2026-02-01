#!/usr/bin/env python3

"""
Machine State Manager
=====================

Centralized state management for the Scratch Desk machine.
Uses singleton pattern with observer callbacks for state change notifications.
"""

from enum import Enum
from typing import Callable, List, Optional
import threading
from core.logger import get_logger

logger = get_logger()


class MachineState(Enum):
    """Machine operation states"""
    IDLE = "idle"
    HOMING = "homing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SWITCHING_MODE = "switching_mode"


class MachineStateManager:
    """
    Centralized machine state management with observer pattern.

    Thread-safe singleton that manages machine state and notifies
    observers when state changes.
    """

    _instance: Optional['MachineStateManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._state = MachineState.IDLE
        self._observers: List[Callable[[MachineState, MachineState], None]] = []
        self._state_lock = threading.Lock()
        self._error_message: Optional[str] = None
        self._initialized = True

        logger.debug("MachineStateManager initialized", category="state")

    @property
    def state(self) -> MachineState:
        """Get current machine state"""
        return self._state

    @property
    def error_message(self) -> Optional[str]:
        """Get error message if state is ERROR"""
        return self._error_message

    def set_state(self, new_state: MachineState, error_message: Optional[str] = None):
        """
        Set machine state and notify observers.

        Args:
            new_state: The new machine state
            error_message: Optional error message (used when state is ERROR)
        """
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            self._error_message = error_message if new_state == MachineState.ERROR else None

            logger.info(f"Machine state: {old_state.value} -> {new_state.value}", category="state")

            if error_message and new_state == MachineState.ERROR:
                logger.error(f"Error: {error_message}", category="state")

            # Notify observers (copy list to avoid modification during iteration)
            for observer in list(self._observers):
                try:
                    observer(old_state, new_state)
                except Exception as e:
                    logger.error(f"Observer error: {e}", category="state")

    def add_observer(self, callback: Callable[[MachineState, MachineState], None]):
        """
        Add observer callback for state changes.

        Args:
            callback: Function(old_state, new_state) called on state changes
        """
        if callback not in self._observers:
            self._observers.append(callback)
            logger.debug(f"Added state observer: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}", category="state")

    def remove_observer(self, callback: Callable[[MachineState, MachineState], None]):
        """Remove observer callback"""
        if callback in self._observers:
            self._observers.remove(callback)
            logger.debug(f"Removed state observer", category="state")

    def is_busy(self) -> bool:
        """Check if machine is in a busy state (cannot switch modes)"""
        return self._state in [
            MachineState.HOMING,
            MachineState.RUNNING,
            MachineState.SWITCHING_MODE
        ]

    def can_switch_mode(self) -> tuple:
        """
        Check if it's safe to switch hardware mode.

        Returns:
            Tuple of (can_switch: bool, reason: str)
        """
        if self._state == MachineState.HOMING:
            return False, "Cannot switch during homing sequence"
        elif self._state == MachineState.RUNNING:
            return False, "Cannot switch while execution is in progress"
        elif self._state == MachineState.SWITCHING_MODE:
            return False, "Hardware switch already in progress"
        return True, ""

    def reset(self):
        """Reset state to IDLE (use with caution)"""
        self.set_state(MachineState.IDLE)


def get_state_manager() -> MachineStateManager:
    """Get the singleton state manager instance"""
    return MachineStateManager()

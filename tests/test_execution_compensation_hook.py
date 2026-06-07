import os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.execution_engine as ee
from core.execution_engine import ExecutionEngine


class FakeHW:
    def __init__(self):
        self.x = 20.0
        self.y = 0.0
    def get_current_x(self):
        return self.x
    def get_current_y(self):
        return self.y


def test_compensated_waypoints_disabled_returns_target(monkeypatch):
    monkeypatch.setattr(ee, "load_settings", lambda: {})
    engine = ExecutionEngine()
    engine.hardware = FakeHW()
    assert engine._compensated_waypoints("x", 10.0) == [10.0]


def test_compensated_waypoints_applies_offset_and_backlash(monkeypatch):
    cfg = {"hardware_config": {"arduino_grbl": {"motion_compensation": {
        "x": {"enabled": True, "offset_cm": 0.2, "backlash_cm": 0.3, "approach_direction": 1},
        "y": {"enabled": False},
    }}}}
    monkeypatch.setattr(ee, "load_settings", lambda: cfg)
    engine = ExecutionEngine()
    engine.hardware = FakeHW()           # current x = 20 -> moving to 10 is -1 (opposes +1)
    # corrected = 10 + 0.2 = 10.2 ; overshoot = 10.2 - 0.3 = 9.9
    assert engine._compensated_waypoints("x", 10.0) == pytest.approx([9.9, 10.2])

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


def test_compensated_waypoints_clamped_to_limits(monkeypatch):
    """Engine reads hardware_limits from settings and clamps compensation."""
    cfg = {
        "hardware_config": {
            "arduino_grbl": {
                "motion_compensation": {
                    "x": {"enabled": True, "offset_cm": 50.0},  # large offset
                    "y": {"enabled": False},
                }
            }
        },
        "hardware_limits": {
            "max_x_position": 120.0,
            "max_y_position": 80.0,
            "min_x_position": 0.0,
            "min_y_position": 0.0,
        }
    }
    monkeypatch.setattr(ee, "load_settings", lambda: cfg)
    engine = ExecutionEngine()
    engine.hardware = FakeHW()
    # target=100, offset=50 → corrected=150 → clamped to max 120
    result = engine._compensated_waypoints("x", 100.0)
    assert result == pytest.approx([120.0])


def test_backlash_returns_two_ordered_waypoints(monkeypatch):
    """Engine returns backlash overshoots in correct order: [overshoot, corrected_target]."""
    cfg = {
        "hardware_config": {
            "arduino_grbl": {
                "motion_compensation": {
                    "x": {"enabled": True, "backlash_cm": 0.3, "approach_direction": 1},
                    "y": {"enabled": False},
                }
            }
        },
        "hardware_limits": {
            "max_x_position": 120.0,
            "max_y_position": 80.0,
        }
    }
    monkeypatch.setattr(ee, "load_settings", lambda: cfg)
    engine = ExecutionEngine()
    engine.hardware = FakeHW()  # current x=20
    # current=20, target=10 (opposes +1) → overshoot=9.7, corrected=10
    result = engine._compensated_waypoints("x", 10.0)
    assert len(result) == 2
    assert result[0] == pytest.approx(9.7)  # overshoot first
    assert result[1] == pytest.approx(10.0)  # corrected target last
    # both within limits
    for wp in result:
        assert 0.0 <= wp <= 120.0

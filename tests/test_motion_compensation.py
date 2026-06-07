import os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.motion_compensation import MotionCompensator


def test_disabled_axis_is_noop():
    c = MotionCompensator({"x": {"enabled": False, "offset_cm": 5.0}})
    assert c.compensate("x", 0.0, 10.0) == [10.0]


def test_missing_axis_is_noop():
    c = MotionCompensator({})
    assert c.compensate("x", 0.0, 10.0) == [10.0]


def test_offset_only():
    c = MotionCompensator({"x": {"enabled": True, "offset_cm": 0.2}})
    assert c.compensate("x", 0.0, 10.0) == pytest.approx([10.2])


def test_scale_only():
    c = MotionCompensator({"x": {"enabled": True, "scale": 1.01}})
    assert c.compensate("x", 0.0, 100.0) == pytest.approx([101.0])


def test_scale_and_offset():
    c = MotionCompensator({"x": {"enabled": True, "scale": 1.01, "offset_cm": 0.2}})
    assert c.compensate("x", 0.0, 100.0) == pytest.approx([101.2])


def test_backlash_no_overshoot_when_travel_matches_approach():
    # approach +1, moving 0 -> 10 is +1: no overshoot needed
    c = MotionCompensator({"x": {"enabled": True, "backlash_cm": 0.3, "approach_direction": 1}})
    assert c.compensate("x", 0.0, 10.0) == pytest.approx([10.0])


def test_backlash_overshoot_when_travel_opposes_approach():
    # approach +1, moving 20 -> 10 is -1: overshoot below target then settle up
    c = MotionCompensator({"x": {"enabled": True, "backlash_cm": 0.3, "approach_direction": 1}})
    assert c.compensate("x", 20.0, 10.0) == pytest.approx([9.7, 10.0])


def test_backlash_negative_approach_direction():
    # approach -1, moving 0 -> 10 is +1: overshoot above target then settle down
    c = MotionCompensator({"x": {"enabled": True, "backlash_cm": 0.3, "approach_direction": -1}})
    assert c.compensate("x", 0.0, 10.0) == pytest.approx([10.3, 10.0])


def test_backlash_combines_with_offset():
    # corrected = 10 + 0.2 = 10.2; travel 20->10 is -1 opposes +1 -> overshoot 9.9 then 10.2
    c = MotionCompensator({"x": {"enabled": True, "offset_cm": 0.2,
                                 "backlash_cm": 0.3, "approach_direction": 1}})
    assert c.compensate("x", 20.0, 10.0) == pytest.approx([9.9, 10.2])


def test_y_axis_independent_of_x():
    c = MotionCompensator({"x": {"enabled": True, "offset_cm": 0.2},
                           "y": {"enabled": False}})
    assert c.compensate("y", 0.0, 10.0) == [10.0]

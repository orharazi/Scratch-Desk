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


def test_no_clamping_when_limits_absent():
    """Existing behavior: no limits parameter → no clamping, offset pushes beyond max."""
    c = MotionCompensator({"x": {"enabled": True, "offset_cm": 10.0}})
    result = c.compensate("x", 0.0, 120.0)
    assert result == pytest.approx([130.0])  # 120 + 10 offset, no clamping


def test_clamps_waypoint_to_max():
    """With limits, offset that exceeds max gets clamped."""
    limits = {"x": {"min": 0.0, "max": 120.0}, "y": {"min": 0.0, "max": 80.0}}
    c = MotionCompensator({"x": {"enabled": True, "offset_cm": 10.0}}, limits=limits)
    result = c.compensate("x", 0.0, 120.0)
    assert result == pytest.approx([120.0])  # clamped to max


def test_clamps_waypoint_to_min():
    """Backlash overshoot below min gets clamped to 0."""
    limits = {"x": {"min": 0.0, "max": 120.0}, "y": {"min": 0.0, "max": 80.0}}
    c = MotionCompensator(
        {"x": {"enabled": True, "backlash_cm": 0.5, "approach_direction": 1}},
        limits=limits
    )
    # current=0.5, target=0 (opposes +1) → overshoot = 0 - 0.5 = -0.5 → clamped to 0.0
    result = c.compensate("x", 0.5, 0.0)
    assert result == pytest.approx([0.0, 0.0])


def test_clamps_all_waypoints_in_range():
    """Multiple waypoints all clamped within [min, max]."""
    limits = {"x": {"min": 0.0, "max": 120.0}, "y": {"min": 0.0, "max": 80.0}}
    c = MotionCompensator(
        {"x": {"enabled": True, "backlash_cm": 0.3, "offset_cm": 15.0, "approach_direction": 1}},
        limits=limits
    )
    # current=20, target=110 (forward +1) → no overshoot, corrected = 110 + 15 = 125 → clamped to 120
    result = c.compensate("x", 20.0, 110.0)
    assert result == pytest.approx([120.0])


def test_clamp_does_not_affect_in_range_values():
    """In-range waypoints stay unchanged."""
    limits = {"x": {"min": 0.0, "max": 120.0}, "y": {"min": 0.0, "max": 80.0}}
    c = MotionCompensator({"x": {"enabled": True, "offset_cm": 0.2}}, limits=limits)
    result = c.compensate("x", 0.0, 50.0)
    assert result == pytest.approx([50.2])  # within limits, unchanged


def test_clamps_y_axis():
    """Clamping works for y-axis too."""
    limits = {"x": {"min": 0.0, "max": 120.0}, "y": {"min": 0.0, "max": 80.0}}
    c = MotionCompensator({"y": {"enabled": True, "offset_cm": 5.0}}, limits=limits)
    result = c.compensate("y", 0.0, 78.0)
    assert result == pytest.approx([80.0])  # 78 + 5 = 83 → clamped to 80


def test_clamping_missing_axis_in_limits_dict():
    """If limits dict missing an axis, no clamping for that axis."""
    limits = {"x": {"min": 0.0, "max": 120.0}}  # no y
    c = MotionCompensator({"y": {"enabled": True, "offset_cm": 10.0}}, limits=limits)
    result = c.compensate("y", 0.0, 70.0)
    assert result == pytest.approx([80.0])  # 70 + 10 = 80, not clamped (no limits for y)

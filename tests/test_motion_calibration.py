import os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.motion_calibration import fit_scale_offset, fit_backlash


def test_fit_recovers_offset_only():
    # machine lands 0.2 short: measured = commanded - 0.2
    commanded = [10.0, 30.0, 50.0]
    measured = [9.8, 29.8, 49.8]
    scale, offset = fit_scale_offset(commanded, measured)
    assert scale == pytest.approx(1.0)
    assert offset == pytest.approx(0.2)


def test_fit_recovers_scale():
    # measured = 0.99 * commanded -> correction scale = 1/0.99, offset ~ 0
    commanded = [10.0, 50.0, 100.0]
    measured = [9.9, 49.5, 99.0]
    scale, offset = fit_scale_offset(commanded, measured)
    assert scale == pytest.approx(1.0 / 0.99)
    assert offset == pytest.approx(0.0, abs=1e-9)


def test_fit_requires_two_points():
    with pytest.raises(ValueError):
        fit_scale_offset([10.0], [9.8])


def test_fit_rejects_identical_commands():
    with pytest.raises(ValueError):
        fit_scale_offset([10.0, 10.0], [9.8, 9.9])


def test_backlash_gap():
    assert fit_backlash(10.0, 9.7) == pytest.approx(0.3)
    assert fit_backlash(9.7, 10.0) == pytest.approx(0.3)

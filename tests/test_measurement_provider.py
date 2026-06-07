import os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.measurement_provider import ManualMeasurementProvider, MeasurementProvider


def test_manual_provider_parses_typed_value():
    typed = iter(["9.8"])
    p = ManualMeasurementProvider(input_fn=lambda prompt: next(typed))
    assert p.measure(axis="x", commanded_cm=10.0) == pytest.approx(9.8)


def test_manual_provider_reprompts_on_bad_input():
    typed = iter(["oops", "12.3"])
    p = ManualMeasurementProvider(input_fn=lambda prompt: next(typed))
    assert p.measure(axis="x", commanded_cm=10.0) == pytest.approx(12.3)


def test_is_a_measurement_provider():
    p = ManualMeasurementProvider(input_fn=lambda prompt: "1.0")
    assert isinstance(p, MeasurementProvider)

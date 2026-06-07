"""Measurement providers for motion calibration.

A MeasurementProvider returns the *physically measured* position of an axis
after the machine was commanded to a target. Manual entry is implemented now;
sensor-based auto-measurement is stubbed for later.
"""

from abc import ABC, abstractmethod


class MeasurementProvider(ABC):
    @abstractmethod
    def measure(self, axis: str, commanded_cm: float) -> float:
        """Return the measured physical position (cm) for the given axis."""
        raise NotImplementedError


class ManualMeasurementProvider(MeasurementProvider):
    """Operator reads a ruler/caliper and types the measured position."""

    def __init__(self, input_fn=input):
        self._input = input_fn

    def measure(self, axis: str, commanded_cm: float) -> float:
        while True:
            raw = self._input(
                f"[{axis.upper()}] commanded {commanded_cm:.3f} cm — "
                f"enter MEASURED position in cm: "
            )
            try:
                return float(str(raw).strip())
            except (ValueError, TypeError):
                print("  ! not a number, try again")


class SensorMeasurementProvider(MeasurementProvider):
    """Placeholder for RS485 edge-sensor based auto-measurement (future work)."""

    def __init__(self, hardware):
        self._hardware = hardware

    def measure(self, axis: str, commanded_cm: float) -> float:
        raise NotImplementedError(
            "Sensor-based measurement not implemented yet; use ManualMeasurementProvider"
        )

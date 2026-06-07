"""Fit motion-compensation parameters from measured-vs-commanded positions.

Pure logic, no hardware dependencies.

Model: the machine's transfer is  measured = a * commanded + b  (least squares).
To land on a desired target T we must command  C = (T - b) / a, i.e. the
compensator stores  scale = 1/a  and  offset = -b/a  so that
corrected = scale * T + offset.
"""

from typing import List, Tuple


def fit_scale_offset(commanded: List[float], measured: List[float]) -> Tuple[float, float]:
    """Return (scale, offset) for the compensator from a forward-pass dataset."""
    n = len(commanded)
    if n < 2 or n != len(measured):
        raise ValueError("need >= 2 matched commanded/measured points")

    mean_c = sum(commanded) / n
    mean_m = sum(measured) / n
    sxx = sum((c - mean_c) ** 2 for c in commanded)
    if sxx == 0:
        raise ValueError("commanded positions are all identical")
    sxy = sum((c - mean_c) * (m - mean_m) for c, m in zip(commanded, measured))

    a = sxy / sxx                 # slope of measured vs commanded
    b = mean_m - a * mean_c       # intercept
    if a == 0:
        raise ValueError("degenerate fit (zero slope)")

    scale = 1.0 / a
    offset = -b / a
    return scale, offset


def fit_backlash(forward_measured: float, reverse_measured: float) -> float:
    """Backlash magnitude = gap between forward/reverse landings at one target."""
    return abs(forward_measured - reverse_measured)

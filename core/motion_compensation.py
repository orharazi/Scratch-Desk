"""Feed-forward motion compensation for tool-up (lifted) positioning moves.

Pure logic, no hardware dependencies. Applies a per-axis correction made of
three independently-toggleable terms — fixed offset, distance scale, and
backlash overshoot — to the target of a lifted move. Tool-down marking moves
must never be passed through this module; the execution engine invokes it only
when the motor piston is lifted for a long move.

See docs/superpowers/specs/2026-06-07-tool-up-motion-compensation-design.md
"""

from typing import List


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


class MotionCompensator:
    """Computes corrected waypoints for tool-up positioning moves."""

    def __init__(self, config: dict):
        # config is the `motion_compensation` block: {"x": {...}, "y": {...}}
        self._config = config or {}

    def _axis_cfg(self, axis: str) -> dict:
        return self._config.get(axis, {}) or {}

    def compensate(self, axis: str, current_pos_cm: float, target_cm: float) -> List[float]:
        """Return ordered absolute waypoints (cm) to drive `axis` to `target_cm`.

        axis: 'x' or 'y'
        current_pos_cm: start position, used to decide backlash direction
        target_cm: commanded absolute target

        Returns [target_cm] unchanged when the axis is disabled.
        """
        cfg = self._axis_cfg(axis)
        if not cfg.get("enabled", False):
            return [target_cm]

        scale = cfg.get("scale", 1.0)
        offset_cm = cfg.get("offset_cm", 0.0)
        corrected = scale * target_cm + offset_cm

        backlash_cm = cfg.get("backlash_cm", 0.0)
        if backlash_cm and backlash_cm > 0:
            approach_dir = _sign(cfg.get("approach_direction", 1)) or 1
            travel_dir = _sign(target_cm - current_pos_cm)
            # Overshoot only when natural travel opposes the preferred approach.
            if travel_dir != 0 and travel_dir != approach_dir:
                overshoot = corrected - approach_dir * backlash_cm
                return [overshoot, corrected]

        return [corrected]

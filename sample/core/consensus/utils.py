from __future__ import annotations


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def relative_confidence(top: float, second: float) -> float:
    gap = max(top - second, 0.0)
    denominator = top if top > 0 else 1e-6
    return clamp_confidence(gap / denominator)

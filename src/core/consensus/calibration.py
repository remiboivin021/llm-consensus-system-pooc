from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from src.core.consensus.utils import clamp_confidence


@dataclass
class CalibrationResult:
    raw: float
    calibrated: float
    applied: bool
    version: str
    reason: str | None = None


class Calibrator(Protocol):
    def calibrate(self, confidence: float) -> CalibrationResult:  # pragma: no cover - protocol
        ...


class IdentityCalibrator:
    """Default calibrator that leaves confidence untouched."""

    version = "identity"

    def calibrate(self, confidence: float) -> CalibrationResult:
        value = clamp_confidence(confidence)
        return CalibrationResult(
            raw=value,
            calibrated=value,
            applied=False,
            version=self.version,
            reason=None,
        )


class MapCalibrator:
    """Piecewise-linear calibration using a monotonic (x, y) map."""

    def __init__(
        self,
        points: Iterable[tuple[float, float]],
        *,
        version: str = "map",
        sample_size: int | None = None,
        min_sample_size: int = 20,
    ) -> None:
        self.points = list(points)
        if len(self.points) < 2:
            raise ValueError("at least two points required for calibration")
        self._validate_monotonic(self.points)
        self.version = version
        self.sample_size = sample_size or 0
        self.min_sample_size = min_sample_size

    @staticmethod
    def _validate_monotonic(points: list[tuple[float, float]]) -> None:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        if any(xs[i] >= xs[i + 1] for i in range(len(xs) - 1)):
            raise ValueError("x values must be strictly increasing")
        if any(ys[i] > ys[i + 1] for i in range(len(ys) - 1)):
            raise ValueError("y values must be non-decreasing")
        if any(x < 0 or x > 1 for x in xs) or any(y < 0 or y > 1 for y in ys):
            raise ValueError("calibration map values must be within [0,1]")

    def calibrate(self, confidence: float) -> CalibrationResult:
        raw = clamp_confidence(confidence)

        if self.sample_size < self.min_sample_size:
            return CalibrationResult(
                raw=raw,
                calibrated=raw,
                applied=False,
                version=self.version,
                reason="insufficient_samples",
            )

        calibrated = self._interpolate(raw)
        return CalibrationResult(
            raw=raw,
            calibrated=calibrated,
            applied=True,
            version=self.version,
            reason=None,
        )

    def _interpolate(self, value: float) -> float:
        # Clamp to range first point..last point
        if value <= self.points[0][0]:
            return self.points[0][1]
        if value >= self.points[-1][0]:
            return self.points[-1][1]

        for (x1, y1), (x2, y2) in zip(self.points, self.points[1:]):
            if x1 <= value <= x2:
                # Linear interpolation
                if x2 == x1:
                    return y1
                ratio = (value - x1) / (x2 - x1)
                return clamp_confidence(y1 + ratio * (y2 - y1))

        # Fallback (should not happen due to earlier checks)
        return self.points[-1][1]


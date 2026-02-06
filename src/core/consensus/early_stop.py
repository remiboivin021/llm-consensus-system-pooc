from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.contracts.early_stop import EarlyStopConfig


@dataclass
class EarlyStopDecision:
    stop: bool
    reason: Literal["confidence_reached", "max_samples"] | None


def early_stop_decision(
    samples_used: int,
    confidence: float | None,
    config: EarlyStopConfig,
) -> EarlyStopDecision:
    if not config.enabled:
        return EarlyStopDecision(stop=False, reason=None)

    # enforce minimum sampling before any stop
    if samples_used < config.min_samples:
        return EarlyStopDecision(stop=False, reason=None)

    conf = confidence or 0.0
    if conf >= config.confidence_threshold:
        return EarlyStopDecision(stop=True, reason="confidence_reached")

    if samples_used >= (config.max_samples or samples_used):
        return EarlyStopDecision(stop=True, reason="max_samples")

    return EarlyStopDecision(stop=False, reason=None)

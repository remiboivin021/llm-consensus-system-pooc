from __future__ import annotations


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def apply_calibrator(calibrator, confidence: float):
    """Apply a calibrator if provided, ensuring bounded output."""
    if calibrator is None:
        return confidence, None, None, None

    result = calibrator.calibrate(confidence)
    return result.calibrated, result.version, result.applied, result.reason


def relative_confidence(top: float, second: float) -> float:
    gap = max(top - second, 0.0)
    denominator = top if top > 0 else 1e-6
    return clamp_confidence(gap / denominator)


def suggest_strategy(
    *,
    prompt_chars: int,
    model_count: int,
    include_scores: bool,
    normalize_output: bool = False,
) -> str:
    """
    Deterministic strategy hint based on simple heuristics.
    Pure function; callers remain free to ignore the suggestion.
    """
    from src.core.consensus.registry import DEFAULT_STRATEGY

    if include_scores:
        return "score_preferred"
    if model_count >= 4:
        return "ranked_choice"
    if normalize_output:
        return DEFAULT_STRATEGY
    return DEFAULT_STRATEGY

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from src.contracts.response import ConsensusResult, ScoreStats
from src.core.consensus.base import JudgementResult
from src.adapters.observability.logging import get_logger
from src.policy.models import Policy

logger = get_logger()

@dataclass
class GateDecision:
    gated: bool
    reason: str | None
    stage: Literal["pre", "post"]


def _models_allowed(
    allowed: str | Iterable[str] | None, requested: Iterable[str]
) -> tuple[bool, str | None]:
    requested_norm = [model.strip() for model in requested]
    if allowed is None:
        return True, None
    if isinstance(allowed, str):
        if allowed == "*":
            return True, None
        allowed_models = {item.strip() for item in allowed.split(",") if item.strip()}
        missing = [model for model in requested_norm if model not in allowed_models]
        return (False, f"model_not_allowed:{','.join(missing)}") if missing else (True, None)
    forbidden = [model for model in requested_norm if model not in allowed]
    if forbidden:
        return False, f"model_not_allowed:{','.join(forbidden)}"
    return True, None


def apply_preflight_gating(
    policy: Policy, prompt: str, models: list[str], normalize_requested: bool, request_id: str | None = None
) -> GateDecision | None:
    request_policy = policy.guardrails.request

    if normalize_requested and not policy.normalize_allowed:
        return GateDecision(True, "normalize_not_allowed", stage="pre")

    if len(prompt) < request_policy.prompt_min_chars:
        return GateDecision(True, "prompt_too_short", stage="pre")
    # if len(prompt) > request_policy.prompt_max_chars:
    #     return GateDecision(True, "prompt_too_long", stage="pre")

    model_limits = request_policy.models
    model_count = len(models)
    if model_count < model_limits.min_models:
        return GateDecision(True, "too_few_models", stage="pre")
    if model_count > model_limits.max_models:
        return GateDecision(True, "too_many_models", stage="pre")

    if model_limits.unique_required and len(set(models)) != model_count:
        return GateDecision(True, "duplicate_models", stage="pre")

    allowed_ok, reason = _models_allowed(model_limits.allowed_models, models)
    if not allowed_ok:
        logger.info(
            "policy_gating_models_blocked",
            request_id=request_id,
            models=",".join(models),
            reason=reason,
        )
        return GateDecision(True, reason, stage="pre")

    return None


def apply_post_gating(
    policy: Policy,
    judgement: JudgementResult,
    score_stats: ScoreStats | None,
) -> GateDecision | None:
    accept = policy.consensus.accept
    if accept.require_winner and judgement.winner is None:
        return GateDecision(True, "winner_required", stage="post")

    if accept.min_confidence is not None and judgement.confidence < accept.min_confidence:
        return GateDecision(True, "confidence_too_low", stage="post")

    if accept.min_quality_score is not None:
        mean_score = score_stats.mean if score_stats is not None else None
        if mean_score is None or mean_score < accept.min_quality_score:
            return GateDecision(True, "quality_too_low", stage="post")

    return None


def apply_gating_result(
    result: ConsensusResult,
    decision: GateDecision | None,
    gating_mode: str,
) -> ConsensusResult:
    """
    Attach gating flags to the result. For now we do not drop content in soft mode,
    we only annotate. Shadow mode ignores gating.
    """
    if decision is None or gating_mode == "shadow":
        return result

    result.gated = True
    result.gate_reason = decision.reason
    return result

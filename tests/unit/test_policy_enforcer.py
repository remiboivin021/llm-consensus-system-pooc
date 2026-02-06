import pytest

from src.contracts.response import ConsensusResult, ScoreStats
from src.core.consensus.base import JudgementResult, Vote
from src.policy.enforcer import (
    GateDecision,
    apply_gating_result,
    apply_post_gating,
    apply_preflight_gating,
    _models_allowed,
)
from src.policy.models import Policy


def test_models_allowed_forbidden_list():
    ok, reason = _models_allowed(["a"], ["b"])
    assert ok is False
    assert reason.startswith("model_not_allowed")

def test_models_allowed_none_allows_all():
    ok, reason = _models_allowed(None, ["any"])
    assert ok is True
    assert reason is None


def test_models_allowed_wildcard():
    ok, reason = _models_allowed("*", ["any"])
    assert ok is True
    assert reason is None


def test_models_allowed_whitelist():
    ok, reason = _models_allowed(["allowed"], ["allowed"])
    assert ok is True
    assert reason is None


def test_models_allowed_string_single_match():
    ok, reason = _models_allowed("gpt-4o", ["gpt-4o"])
    assert ok is True
    assert reason is None


def test_models_allowed_string_single_mismatch():
    ok, reason = _models_allowed("gpt-4o", ["gpt-3.5"])
    assert ok is False
    assert reason == "model_not_allowed:gpt-3.5"


def test_models_allowed_string_csv_list():
    ok, reason = _models_allowed("gpt-4o,gpt-4o-mini", ["gpt-4o-mini"])
    assert ok is True
    assert reason is None


def test_models_allowed_string_trims_whitespace():
    ok, reason = _models_allowed("gpt-4o", [" gpt-4o "])
    assert ok is True
    assert reason is None


def test_apply_preflight_gating_blocks_duplicates():
    policy = Policy.model_validate(
        {
            "policy_id": "p",
            "guardrails": {"request": {"models": {"min_models": 1, "max_models": 3, "unique_required": True}}},
        }
    )
    decision = apply_preflight_gating(policy, prompt="hi", models=["m1", "m1"], normalize_requested=False)
    assert decision and decision.reason == "duplicate_models"


def test_apply_preflight_gating_prompt_too_short():
    policy = Policy.model_validate({"policy_id": "p"})
    decision = apply_preflight_gating(policy, prompt="", models=["m1"], normalize_requested=False)
    assert decision and decision.reason == "prompt_too_short"


def test_apply_preflight_gating_too_many_models():
    policy = Policy.model_validate(
        {
            "policy_id": "p",
            "guardrails": {"request": {"models": {"min_models": 1, "max_models": 1}}},
        }
    )
    decision = apply_preflight_gating(policy, prompt="hi", models=["m1", "m2"], normalize_requested=False)
    assert decision and decision.reason == "too_many_models"


def test_apply_preflight_gating_normalize_not_allowed():
    policy = Policy.model_validate({"policy_id": "p", "normalize_allowed": False})
    decision = apply_preflight_gating(policy, prompt="hi", models=["m1"], normalize_requested=True)
    assert decision and decision.reason == "normalize_not_allowed"


def test_apply_post_gating_confidence_and_quality():
    policy = Policy.model_validate(
        {
            "policy_id": "p",
            "consensus": {"accept": {"min_confidence": 0.9, "min_quality_score": 0.8}},
        }
    )
    judgement = JudgementResult(winner="m", confidence=0.5, method="x", votes=[Vote("m", 0.2)])
    decision = apply_post_gating(policy, judgement, score_stats=ScoreStats(mean=0.5, min=0.5, max=0.5, stddev=0, count=1))
    assert decision and decision.reason == "confidence_too_low"


def test_apply_post_gating_requires_winner():
    policy = Policy.model_validate({"policy_id": "p", "consensus": {"accept": {"require_winner": True}}})
    judgement = JudgementResult(winner=None, confidence=1.0, method="m", votes=[])
    decision = apply_post_gating(policy, judgement, score_stats=None)
    assert decision and decision.reason == "winner_required"


def test_apply_gating_result_sets_flags():
    result = ConsensusResult(
        request_id="r",
        winner="m1",
        confidence=1.0,
        responses=[],
        method="m",
        timing={"e2e_ms": 1},
    )
    decision = GateDecision(gated=True, reason="r", stage="post")
    gated = apply_gating_result(result, decision, gating_mode="soft")
    assert gated.gated is True
    assert gated.gate_reason == "r"


def test_apply_gating_result_shadow_leaves_untouched():
    result = ConsensusResult(
        request_id="r",
        winner="m1",
        confidence=1.0,
        responses=[],
        method="m",
        timing={"e2e_ms": 1},
    )
    decision = GateDecision(gated=True, reason="r", stage="post")
    unchanged = apply_gating_result(result, decision, gating_mode="shadow")
    assert unchanged.gated is None or unchanged.gated is False

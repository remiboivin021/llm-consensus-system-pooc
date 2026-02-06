from pathlib import Path

from src.policy.enforcer import apply_post_gating, apply_preflight_gating
from src.policy.loader import load_policy
from src.policy.models import Policy
from src.core.consensus.base import JudgementResult
from src.contracts.response import ScoreStats


def test_load_default_policy():
    tmp_policy = Path(__file__).parent / "tmp.policy.yaml"
    tmp_policy.write_text(
        """
policy_id: default-v1
description: test
guardrails:
  request:
    prompt_min_chars: 1
    prompt_max_chars: 8000
    models:
      min_models: 2
      max_models: 5
      unique_required: true
      allowed_models: '*'
""",
        encoding="utf-8",
    )
    policy = load_policy(str(tmp_policy))
    assert policy.policy_id == "default-v1"
    assert policy.guardrails.request.models.min_models == 2
    assert policy.guardrails.request.prompt_max_chars == 8000
    tmp_policy.unlink()


def test_preflight_blocks_disallowed_model():
    policy = Policy.model_validate(
        {
            "policy_id": "test",
            "consensus": {"judge": {"type": "majority_cosine"}, "accept": {}},
            "guardrails": {
                "request": {
                    "prompt_min_chars": 1,
                    "prompt_max_chars": 100,
                    "models": {
                        "min_models": 1,
                        "max_models": 2,
                        "allowed_models": ["allowed-a"],
                    },
                }
            },
        }
    )
    decision = apply_preflight_gating(policy, "ok", ["not-allowed"], normalize_requested=False)
    assert decision is not None
    assert decision.gated is True


def test_post_gating_blocks_low_confidence():
    policy = Policy.model_validate(
        {
            "policy_id": "test",
            "consensus": {
                "judge": {"type": "majority_cosine"},
                "accept": {"min_confidence": 0.8},
            },
            "guardrails": {
                "request": {
                    "prompt_min_chars": 1,
                    "prompt_max_chars": 100,
                    "models": {"min_models": 1, "max_models": 2},
                }
            },
        }
    )
    judgement = JudgementResult(
        winner="m1",
        confidence=0.2,
        method="majority_cosine",
        votes=[],
    )
    decision = apply_post_gating(policy, judgement, score_stats=None)
    assert decision is not None
    assert decision.reason == "confidence_too_low"


def test_post_gating_blocks_low_quality():
    policy = Policy.model_validate(
        {
            "policy_id": "test",
            "consensus": {
                "judge": {"type": "majority_cosine"},
                "accept": {"min_quality_score": 0.5},
            },
            "guardrails": {
                "request": {
                    "prompt_min_chars": 1,
                    "prompt_max_chars": 100,
                    "models": {"min_models": 1, "max_models": 2},
                }
            },
        }
    )
    judgement = JudgementResult(
        winner="m1",
        confidence=0.9,
        method="majority_cosine",
        votes=[],
    )
    score_stats = ScoreStats(mean=0.1, min=0.1, max=0.1, stddev=0.0, count=1)
    decision = apply_post_gating(policy, judgement, score_stats=score_stats)
    assert decision is not None
    assert decision.reason == "quality_too_low"

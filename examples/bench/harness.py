from __future__ import annotations

import random
from pathlib import Path
from typing import Callable

from src.adapters.observability.logging import get_logger
from src.contracts.response import ConsensusResult, Timing
from src.core.consensus.scoring import ScoreAggregationJudge
from src.core.consensus.strategies import ScorePreferredJudge
from src.core.consensus.voting import MajorityVoteJudge
from src.policy import apply_gating_result, apply_post_gating, apply_preflight_gating, load_policy

from .schema import FixtureCase, FixtureFile, ProviderOutput

logger = get_logger()


class HarnessConfig:
    def __init__(
        self,
        seed: int = 0,
        policy_path: str | None = None,
        strategy: str | None = None,
        stop_on_failure: bool = False,
    ) -> None:
        self.seed = seed
        self.policy_path = policy_path
        self.strategy = strategy
        self.stop_on_failure = stop_on_failure


class CaseResult:
    def __init__(
        self,
        case: FixtureCase,
        winner: str | None,
        confidence: float,
        gated: bool,
        gate_stage: str | None,
        gate_reason: str | None,
        match: bool,
        errors: list[str] | None = None,
        duration_ms: int | None = None,
    ) -> None:
        self.case = case
        self.winner = winner
        self.confidence = confidence
        self.gated = gated
        self.gate_stage = gate_stage
        self.gate_reason = gate_reason
        self.match = match
        self.errors = errors or []
        self.duration_ms = duration_ms

    def to_dict(self) -> dict:
        return {
            "case_id": self.case.case_id,
            "winner": self.winner,
            "confidence": self.confidence,
            "gated": self.gated,
            "gate_stage": self.gate_stage,
            "gate_reason": self.gate_reason,
            "expected_winner": self.case.expected_winner,
            "expected_gate": self.case.expected_gate,
            "match": self.match,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
        }


class HarnessResult:
    def __init__(self, cases: list[CaseResult], duration_ms: int) -> None:
        self.cases = cases
        self.duration_ms = duration_ms

    @property
    def summary(self) -> dict:
        passed = sum(1 for c in self.cases if c.match)
        failed = len(self.cases) - passed
        gated = sum(1 for c in self.cases if c.gated)
        return {"passed": passed, "failed": failed, "gated": gated, "duration_ms": self.duration_ms}

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "cases": [c.to_dict() for c in self.cases],
        }


def _judge_for(strategy: str | None):
    if strategy in (None, "score_preferred"):
        return ScorePreferredJudge()
    if strategy == "majority_vote":
        return MajorityVoteJudge()
    if strategy == "majority_cosine":
        # fall back to majority vote; cosine judge not yet implemented offline
        return MajorityVoteJudge()
    raise ValueError(f"Unsupported strategy: {strategy}")


def _build_responses(models: list[str], outputs: list[ProviderOutput]):
    by_model = {o.model: o for o in outputs}
    return [by_model[m].to_model_response() for m in models]


def run_harness(
    fixtures: FixtureFile,
    config: HarnessConfig | None = None,
    policy_loader: Callable[[str | None], object] = load_policy,
) -> HarnessResult:
    config = config or HarnessConfig(seed=fixtures.seed)
    random.seed(config.seed)

    policy_cache: dict[str | None, object] = {}
    cases: list[CaseResult] = []

    for case in fixtures.cases:
        duration_ms = len(case.models) * 10  # deterministic duration for repeatability
        policy_path = case.policy_path or config.policy_path
        if policy_path not in policy_cache:
            policy_cache[policy_path] = policy_loader(policy_path)
        policy = policy_cache[policy_path]

        pre_decision = apply_preflight_gating(
            policy,
            case.prompt,
            case.models,
            normalize_requested=False,
            request_id=case.case_id,
        )

        gate_stage = None
        gate_reason = None
        gated = False
        winner = None
        confidence = 0.0
        errors: list[str] = []

        if pre_decision and policy.gating_mode == "soft":
            gated = True
            gate_stage = pre_decision.stage
            gate_reason = pre_decision.reason
            case_result = CaseResult(
                case=case,
                winner=None,
                confidence=0.0,
                gated=gated,
                gate_stage=gate_stage,
                gate_reason=gate_reason,
                match=_matches(case, None, gate_stage),
                errors=errors,
                duration_ms=duration_ms,
            )
            cases.append(case_result)
            if config.stop_on_failure and not case_result.match:
                break
            continue

        try:
            responses = _build_responses(case.models, case.provider_outputs)
        except Exception as exc:  # deterministic failure classification
            case_result = CaseResult(
                case=case,
                winner=None,
                confidence=0.0,
                gated=False,
                gate_stage=None,
                gate_reason=str(exc),
                match=False,
                errors=[str(exc)],
                duration_ms=duration_ms,
            )
            cases.append(case_result)
            if config.stop_on_failure:
                break
            continue

        judge = _judge_for(case.strategy or config.strategy)
        judgement = judge.judge(responses, scores=None)
        winner = judgement.winner
        confidence = judgement.confidence

        post_decision = apply_post_gating(policy, judgement, score_stats=None)
        if post_decision and policy.gating_mode == "shadow":
            gate_stage = post_decision.stage
            gate_reason = post_decision.reason
        result = ConsensusResult(
            request_id=case.case_id,
            winner=winner,
            confidence=confidence,
            responses=responses,
            method=getattr(judge, "method", "unknown"),
            timing=Timing(e2e_ms=duration_ms),
        )
        result = apply_gating_result(result, post_decision, policy.gating_mode)
        if result.gated:
            gated = True
            gate_stage = post_decision.stage if post_decision else gate_stage
            gate_reason = post_decision.reason if post_decision else gate_reason

        case_result = CaseResult(
            case=case,
            winner=result.winner,
            confidence=result.confidence,
            gated=gated,
            gate_stage=gate_stage,
            gate_reason=gate_reason,
            match=_matches(case, result.winner, gate_stage),
            errors=errors,
            duration_ms=duration_ms,
        )
        cases.append(case_result)
        if config.stop_on_failure and not case_result.match:
            break

    total_ms = sum(c.duration_ms or 0 for c in cases)
    logger.info(
        "bench_run_summary",
        total_cases=len(cases),
        passed=sum(1 for c in cases if c.match),
        failed=sum(1 for c in cases if not c.match),
        duration_ms=total_ms,
        seed=config.seed,
    )
    return HarnessResult(cases=cases, duration_ms=total_ms)


def _matches(case: FixtureCase, winner: str | None, gate_stage: str | None) -> bool:
    if case.expected_gate is not None:
        return case.expected_gate == gate_stage
    if case.expected_winner is not None:
        return case.expected_winner == winner
    return True

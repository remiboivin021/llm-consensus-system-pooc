from __future__ import annotations

import asyncio
import time
from typing import Iterable

from opentelemetry import trace

from src.config import get_settings
from src.contracts.errors import ErrorEnvelope
from src.contracts.request import ConsensusRequest
from src.contracts.response import ConsensusResult, Timing
from src.adapters.observability.logging import get_logger
from src.adapters.observability.metrics import (
    consensus_duration_seconds,
    llm_call_duration_seconds,
    llm_calls_total,
    quality_score,
    quality_score_stats,
    provider_breaker_open_total,
    provider_breaker_state,
)
from src.adapters.orchestration.models import (
    ProviderResult,
    build_model_responses,
    fetch_provider_result,
)
from src.adapters.orchestration.timeouts import enforce_timeout
from src.core.consensus.base import Judge
from src.core.consensus.strategies import ScorePreferredJudge
from src.core.scoring.engine import compute_scores

from src.adapters.orchestration.breaker import BreakerManager, BreakerState
from src.policy import (
    apply_post_gating,
    apply_gating_result,
    apply_preflight_gating,
    load_policy,
)
from src.policy.loader import PolicyStore
from src.policy.models import ProviderGuard, BreakerConfig

logger = get_logger()
tracer = trace.get_tracer(__name__)

_BREAKER_NUMERIC = {"closed": 0.0, "half_open": 0.5, "open": 1.0}


def _record_breaker_state(model: str, state: BreakerState) -> None:
    value = _BREAKER_NUMERIC.get(state, -1.0)
    try:
        provider_breaker_state.labels(model=model).set(value)
    except Exception:
        logger.warning("metrics_emit_failed", metric="provider_breaker_state", model=model, state=state)


class OrchestrationError(Exception):
    def __init__(self, envelope: ErrorEnvelope):
        super().__init__(envelope.message)
        self.envelope = envelope


def _sanitize_model_label(model: str, allowed: Iterable[str]) -> str:
    return model if model in allowed else "other"


class Orchestrator:
    def __init__(self, judge: Judge | None = None, policy_store: PolicyStore | None = None) -> None:
        self.settings = get_settings()
        self.judge = judge or ScorePreferredJudge()
        self.policy_store = policy_store or PolicyStore(loader=load_policy)
        self.policy = self.policy_store.current()
        self.breakers = BreakerManager(self._breaker_config())

    def _breaker_config(self) -> BreakerConfig:
        # Policy is authoritative; fallback handled by loader defaults.
        return getattr(self.policy, "breaker", BreakerConfig())

    async def _call_single_model(
        self,
        prompt: str,
        model: str,
        request_id: str,
        normalize_output: bool,
        include_scores: bool,
        provider_timeout_ms: int | None,
    ) -> ProviderResult:
        allowed, breaker_state = await self.breakers.should_allow(model)
        if not allowed:
            error = ErrorEnvelope(
                type="provider_error",
                message="provider_circuit_open",
                retryable=True,
                status_code=503,
            )
            result = ProviderResult(
                model=model,
                content=None,
                latency_ms=0,
                error=error,
                breaker_state=breaker_state,
            )
            logger.info(
                "breaker_short_circuit",
                request_id=request_id,
                model=model,
                state=breaker_state,
            )
            _record_breaker_state(model, breaker_state)
        else:
            result = await fetch_provider_result(
                prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms
            )
            if result.error is None:
                breaker_state = await self.breakers.record_success(model)
            else:
                opened, breaker_state = await self.breakers.record_failure(model)
                if opened:
                    reason = getattr(result.error, "type", "unknown")
                    try:
                        provider_breaker_open_total.labels(model=model, reason=reason).inc()
                    except Exception:
                        logger.warning(
                            "metrics_emit_failed",
                            metric="provider_breaker_open_total",
                            request_id=request_id,
                            model=model,
                            reason=reason,
                        )
                    logger.info(
                        "breaker_open",
                        request_id=request_id,
                        model=model,
                        state=breaker_state,
                        reason=reason,
                    )
            result.breaker_state = breaker_state
            _record_breaker_state(model, breaker_state)

        outcome = "ok" if result.error is None else "error"
        model_label = _sanitize_model_label(
            model, self.settings.default_models)
        llm_calls_total.labels(model=model_label, outcome=outcome).inc()
        if result.latency_ms is not None:
            llm_call_duration_seconds.labels(model=model_label, outcome=outcome).observe(
                result.latency_ms / 1000
            )
        return result

    async def run(
        self, consensus_request: ConsensusRequest, request_id: str, strategy_label: str | None = None
    ) -> ConsensusResult:
        start_time = time.perf_counter()
        strategy_label = strategy_label or getattr(self.judge, "method", "unknown")
        policy = self.policy_store.current()
        self.policy = policy
        preflight_decision = apply_preflight_gating(
            policy,
            consensus_request.prompt,
            consensus_request.models,
            consensus_request.normalize_output,
            request_id=request_id,
        )
        if preflight_decision and policy.gating_mode == "soft":
            e2e_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "policy_gated_preflight",
                request_id=request_id,
                reason=preflight_decision.reason,
            )
            return ConsensusResult(
                request_id=request_id,
                winner=None,
                confidence=0.0,
                responses=[],
                method="policy_preflight",
                timing=Timing(e2e_ms=e2e_ms),
                gated=True,
                gate_reason=preflight_decision.reason,
            )

        if preflight_decision and policy.gating_mode == "shadow":
            logger.info(
                "policy_preflight_shadow",
                request_id=request_id,
                reason=preflight_decision.reason,
            )

        effective_prompt_max = min(
            self.settings.max_prompt_chars, policy.guardrails.request.prompt_max_chars
        )
        if len(consensus_request.prompt) > effective_prompt_max:
            envelope = ErrorEnvelope(
                type="config_error", message="Prompt too long", retryable=False, status_code=400
            )
            raise OrchestrationError(envelope)

        # Apply policy timeouts overrides if present
        effective_e2e_timeout = self.settings.e2e_timeout_ms
        if policy.timeouts and policy.timeouts.e2e_timeout_ms:
            effective_e2e_timeout = policy.timeouts.e2e_timeout_ms

        effective_provider_timeout = self.settings.provider_timeout_ms
        if policy.timeouts and policy.timeouts.provider_timeout_ms:
            effective_provider_timeout = policy.timeouts.provider_timeout_ms

        max_models = min(
            self.settings.max_models, policy.guardrails.request.models.max_models
        )
        semaphore = asyncio.Semaphore(max_models)

        async def limited_call(model_name: str) -> ProviderResult:
            async with semaphore:
                return await self._call_single_model(
                    consensus_request.prompt,
                    model_name,
                    request_id,
                    consensus_request.normalize_output,
                    consensus_request.include_scores,
                    effective_provider_timeout,
                )

        tasks = [asyncio.create_task(limited_call(model))
                 for model in consensus_request.models]
        try:
            raw_results = await enforce_timeout(
                asyncio.gather(
                    *tasks, return_exceptions=True), effective_e2e_timeout
            )
        except asyncio.TimeoutError:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            envelope = ErrorEnvelope(
                type="timeout", message="Request timed out", retryable=True, status_code=504
            )
            raise OrchestrationError(envelope)

        responses = build_model_responses(
            consensus_request.models, raw_results)

        # Enforce provider-level guardrails before scoring/judging
        provider_guardrails: ProviderGuard | None = policy.guardrails.providers
        if provider_guardrails:
            success_count = sum(1 for r in responses if r.error is None)
            failure_count = sum(
                1 for r in responses if r.error is not None and getattr(r.error, "type", "") != "timeout"
            )
            timeout_count = sum(
                1 for r in responses if r.error is not None and getattr(r.error, "type", "") == "timeout"
            )
            total = len(responses)
            fail_ratio = failure_count / total if total else 0.0
            timeout_ratio = timeout_count / total if total else 0.0

            if provider_guardrails.require_at_least_n_success is not None and success_count < provider_guardrails.require_at_least_n_success:
                envelope = ErrorEnvelope(
                    type="provider_error",
                    message="Not enough successful providers",
                    retryable=True,
                    status_code=503,
                )
                raise OrchestrationError(envelope)
            if provider_guardrails.max_failure_ratio is not None and fail_ratio > provider_guardrails.max_failure_ratio:
                envelope = ErrorEnvelope(
                    type="provider_error",
                    message="Too many provider failures (guardrail max_failure_ratio breached)",
                    retryable=False,
                    status_code=503,
                )
                raise OrchestrationError(envelope)
            if provider_guardrails.max_timeout_ratio is not None and timeout_ratio >= provider_guardrails.max_timeout_ratio:
                envelope = ErrorEnvelope(
                    type="timeout",
                    message="Too many provider timeouts",
                    retryable=True,
                    status_code=504,
                )
                raise OrchestrationError(envelope)

        scores = None
        score_stats = None

        if consensus_request.include_scores:
            with tracer.start_as_current_span(
                "consensus.scoring",
                attributes={
                    "request_id": request_id,
                    "model_count": len(responses),
                },
            ) as span:
                scores, score_stats = compute_scores(responses)
                scored_count = score_stats.count if score_stats else 0
                if span is not None:
                    span.set_attribute("scored_count", scored_count)
                for detail in scores:
                    outcome = "error" if detail.error else "ok"
                    logger.debug(
                        "score_entry",
                        request_id=request_id,
                        model=detail.model,
                        score=detail.score,
                        performance=detail.performance,
                        complexity=detail.complexity,
                        tests=detail.tests,
                        style=detail.style,
                        documentation=detail.documentation,
                        dead_code=detail.dead_code,
                        security=detail.security,
                        outcome=outcome,
                    )
                    if span is not None:
                        span.add_event(
                            "score_entry",
                            attributes={
                                "model": detail.model,
                                "score": detail.score,
                                "performance": detail.performance,
                                "complexity": detail.complexity,
                                "tests": detail.tests,
                                "style": detail.style,
                                "documentation": detail.documentation,
                                "dead_code": detail.dead_code,
                                "security": detail.security,
                                "outcome": outcome,
                            },
                        )
                    metrics_payload = {
                        "overall": detail.score,
                        "performance": detail.performance,
                        "complexity": detail.complexity,
                        "tests": detail.tests,
                        "style": detail.style,
                        "documentation": detail.documentation,
                        "dead_code": detail.dead_code,
                        "security": detail.security,
                    }
                    for metric_name, metric_value in metrics_payload.items():
                        try:
                            quality_score.labels(
                                strategy=strategy_label,
                                metric=metric_name,
                                outcome=outcome,
                            ).observe(metric_value)
                        except Exception:
                            logger.warning(
                                "metrics_emit_failed",
                                metric="quality_score",
                                request_id=request_id,
                                stat=metric_name,
                            )
                if score_stats:
                    for stat_name, value in [
                        ("mean", score_stats.mean),
                        ("min", score_stats.min),
                        ("max", score_stats.max),
                        ("stddev", score_stats.stddev),
                        ("count", float(score_stats.count)),
                    ]:
                        try:
                            quality_score_stats.labels(
                                strategy=strategy_label, stat=stat_name
                            ).set(value)
                        except Exception:
                            logger.warning(
                                "metrics_emit_failed",
                                metric="quality_score_stats",
                                request_id=request_id,
                                stat=stat_name,
                            )

        judgement = self.judge.judge(
            responses, scores if consensus_request.include_scores else None)
        winner = judgement.winner
        confidence = judgement.confidence
        method = judgement.method

        if consensus_request.include_scores:
            logger.info(
                "scoring_computed",
                request_id=request_id,
                winner=winner,
                model_count=len(responses),
                scored_count=score_stats.count if score_stats else 0,
            )

        e2e_ms = int((time.perf_counter() - start_time) * 1000)
        consensus_duration_seconds.labels(strategy=strategy_label).observe(e2e_ms / 1000)

        post_decision = apply_post_gating(policy, judgement, score_stats)
        if post_decision and policy.gating_mode == "shadow":
            logger.info(
                "policy_post_shadow",
                request_id=request_id,
                reason=post_decision.reason,
            )

        result = ConsensusResult(
            request_id=request_id,
            winner=winner,
            confidence=confidence,
            responses=[] if not consensus_request.include_raw else responses,
            method=method,
            timing=Timing(e2e_ms=e2e_ms),
            scores=scores,
            score_stats=score_stats,
        )
        if post_decision and policy.gating_mode == "soft":
            logger.info(
                "policy_post_gated",
                request_id=request_id,
                reason=post_decision.reason,
            )
        return apply_gating_result(result, post_decision, policy.gating_mode)

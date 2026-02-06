from __future__ import annotations

import asyncio
import time
import random
from typing import Iterable, Callable, Awaitable, Any

from opentelemetry import trace

from src.config import get_settings
from src.contracts.errors import ErrorEnvelope
from src.contracts.request import ConsensusRequest
from src.contracts.response import ConsensusResult, Timing, CostSummary, LatencySummary, ModelResponse, RedactionSummary, RedactionEntry
from src.contracts.early_stop import EarlyStopReport
from src.adapters.observability.logging import get_logger
from src.adapters.observability.metrics import (
    consensus_duration_seconds,
    llm_call_duration_seconds,
    llm_calls_total,
    quality_score,
    quality_score_stats,
    provider_breaker_open_total,
    provider_breaker_state,
    run_event_callback_total,
    run_event_callback_duration_seconds,
    run_events_total,
    early_stop_decisions_total,
    early_stop_samples_used,
    prompt_safety_decisions_total,
    prompt_safety_duration_seconds,
    preamble_usage_total,
    output_validation_total,
    output_validation_reasks_total,
    pii_redaction_runs_total,
    pii_redactions_total,
)
from src.adapters.orchestration.models import (
    ProviderResult,
    build_model_responses,
    fetch_provider_result,
    build_run_event,
)
from src.adapters.orchestration.timeouts import enforce_timeout
from src.core.consensus.base import Judge
from src.core.consensus.strategies import ScorePreferredJudge
from src.core.safety.detector import run_prompt_safety
from src.core.consensus.calibration import IdentityCalibrator
from src.core.validation import resolve_validator
from src.core.consensus.utils import apply_calibrator
from src.core.consensus.early_stop import early_stop_decision
from src.core.scoring.engine import compute_scores
from src.core.consensus.replay import build_replay_token
from src.errors import LcsError

from src.adapters.orchestration.breaker import BreakerManager, BreakerState
from src.adapters.prefilter.pii import redact_prompt
from src.policy import (
    apply_post_gating,
    apply_gating_result,
    apply_preflight_gating,
    load_policy,
)
from src.policy.loader import PolicyStore, get_policy_store
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


def _apply_pricing_hints(
    responses: list[ModelResponse], pricing_hints: dict[str, float] | None
) -> CostSummary | None:
    if not responses:
        return CostSummary(total=0.0)
    hints = pricing_hints or {}
    total = 0.0
    for resp in responses:
        hint = float(hints.get(resp.model, 0.0))
        resp.estimated_cost = max(hint, 0.0)
        total += max(hint, 0.0)
    return CostSummary(total=total)


def _compute_latency_summary(responses: list[ModelResponse]) -> LatencySummary | None:
    latencies = [r.latency_ms for r in responses if r.latency_ms is not None]
    if not latencies:
        return None
    avg_ms = sum(latencies) / len(latencies)
    return LatencySummary(avg_ms=avg_ms, min_ms=min(latencies), max_ms=max(latencies))


class Orchestrator:
    def __init__(
        self,
        judge: Judge | None = None,
        policy_store: PolicyStore | None = None,
        run_event_callback: Callable[[Any], Awaitable[None] | None] | None = None,
        callback_timeout_ms: int | None = 250,
        calibrator=None,
        output_validator: Callable[[str], tuple[bool, str | None]] | None = None,
    ) -> None:
        self.settings = get_settings()
        self.calibrator = calibrator or IdentityCalibrator()
        self.judge = judge or ScorePreferredJudge()
        self.policy_store = policy_store or PolicyStore(loader=load_policy)
        self.breakers = BreakerManager(self._breaker_config())
        self.run_event_callback = run_event_callback
        self.callback_timeout_ms = callback_timeout_ms
        self.output_validator = output_validator

    def _breaker_config(self) -> BreakerConfig:
        # Policy is authoritative; fallback handled by loader defaults.
        policy = self.policy_store.current()
        return getattr(policy, "breaker", BreakerConfig())

    def _select_preamble(self, normalize_output: bool, preamble_key: str | None, policy):
        if not normalize_output:
            return None, None
        key = preamble_key
        if key:
            from src.config.prompts import get_preamble, PreambleCatalogError

            allowed = policy.preambles.allow
            if allowed != "*" and key not in allowed:
                try:
                    preamble_usage_total.labels(key=key, outcome="denied").inc()
                except Exception:
                    pass
                return "preamble_not_allowed", None
            try:
                content, version = get_preamble(key)
                try:
                    preamble_usage_total.labels(key=key, outcome="used").inc()
                except Exception:
                    pass
                return content, version
            except PreambleCatalogError:
                try:
                    preamble_usage_total.labels(key=key, outcome="unknown").inc()
                except Exception:
                    pass
                raise OrchestrationError(
                    ErrorEnvelope(
                        type="config_error",
                        message="unknown_preamble",
                        retryable=False,
                        status_code=400,
                    )
                )
        from src.adapters.providers.openrouter import STRUCTURED_PREAMBLE

        try:
            preamble_usage_total.labels(key="default", outcome="used").inc()
        except Exception:
            pass
        return STRUCTURED_PREAMBLE, "default"

    async def _call_single_model(
        self,
        prompt: str,
        model: str,
        request_id: str,
        normalize_output: bool,
        include_scores: bool,
        provider_timeout_ms: int | None,
        provider_overrides: dict[str, str] | None = None,
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
                prompt,
                model,
                request_id,
                normalize_output,
                include_scores,
                provider_timeout_ms,
                provider_overrides,
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
        model_label = _sanitize_model_label(result.model, self.settings.default_models)
        provider_label = result.provider or "unknown"
        llm_calls_total.labels(provider=provider_label, model=model_label, outcome=outcome).inc()
        if result.latency_ms is not None:
            llm_call_duration_seconds.labels(
                provider=provider_label, model=model_label, outcome=outcome
            ).observe(result.latency_ms / 1000)
        return result

    async def run(
        self, consensus_request: ConsensusRequest, request_id: str, strategy_label: str | None = None
    ) -> ConsensusResult:
        start_time = time.perf_counter()
        strategy_label = strategy_label or getattr(self.judge, "method", "unknown")
        if consensus_request.early_stop and consensus_request.early_stop.enabled:
            return await self._run_early_stop(consensus_request, request_id, strategy_label, start_time)
        policy = self.policy_store.current()
        token = build_replay_token(consensus_request.seed, consensus_request.models, strategy_label, policy)
        if policy.breaker.model_dump() != self.breakers.config.model_dump():
            self.breakers = BreakerManager(policy.breaker)
        if consensus_request.seed is not None:
            random.seed(consensus_request.seed)
        # Ensure default provider is registered before any resolution
        from src.adapters.providers.openrouter import register_default_openrouter

        register_default_openrouter()

        responses = None
        scores = None
        score_stats = None
        result: ConsensusResult | None = None
        winner = None
        confidence = None
        calibrated_confidence = None
        calibration_version = None
        calibration_applied = None
        calibration_reason = None
        safety_decision: PromptSafetyDecision | None = None
        safety_decision: PromptSafetyDecision | None = None
        cost_summary = None
        latency_summary = None
        prompt_for_processing = consensus_request.prompt
        redaction_summary: RedactionSummary | None = None

        try:
            if policy.prefilter.pii.enabled:
                redaction_result = redact_prompt(prompt_for_processing, policy.prefilter.pii)
                prompt_for_processing = redaction_result.masked_prompt
                counts = redaction_result.counts
                try:
                    pii_redaction_runs_total.labels(applied=str(redaction_result.applied).lower()).inc()
                    for rtype, count in counts.items():
                        pii_redactions_total.labels(type=rtype).inc(count)
                except Exception:
                    logger.warning("metrics_emit_failed", metric="pii_redaction_runs_total")
                entries = (
                    [
                        RedactionEntry(type=e.type, mask=e.mask, start=e.start, end=e.end)
                        for e in redaction_result.entries
                    ]
                    if redaction_result.entries
                    else None
                )
                redaction_summary = RedactionSummary(
                    applied=redaction_result.applied,
                    total=sum(counts.values()),
                    types=counts,
                    truncated=redaction_result.truncated,
                    entries=entries,
                )

            preflight_decision = apply_preflight_gating(
                policy,
                prompt_for_processing,
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
                result = ConsensusResult(
                    request_id=request_id,
                    winner=None,
                    confidence=0.0,
                    responses=[],
                    method="policy_preflight",
                    timing=Timing(e2e_ms=e2e_ms),
                    gated=True,
                    gate_reason=preflight_decision.reason,
                    redaction=redaction_summary,
                )
                await self._fire_run_event(
                    consensus_request,
                    request_id=request_id,
                    strategy=strategy_label,
                    responses=[],
                    winner=None,
                    confidence=0.0,
                    e2e_ms=e2e_ms,
                    gated=True,
                    gate_reason=preflight_decision.reason,
                    error_type=None,
                    include_scores=consensus_request.include_scores,
                    score_stats=None,
                    prompt_text=prompt_for_processing,
                )
                return result

            if preflight_decision and policy.gating_mode == "shadow":
                logger.info(
                    "policy_preflight_shadow",
                    request_id=request_id,
                    reason=preflight_decision.reason,
                )

            effective_prompt_max = min(
                self.settings.max_prompt_chars, policy.guardrails.request.prompt_max_chars
            )
            if len(prompt_for_processing) > effective_prompt_max:
                envelope = ErrorEnvelope(
                    type="config_error", message="Prompt too long", retryable=False, status_code=400
                )
                raise OrchestrationError(envelope)

            effective_e2e_timeout = self.settings.e2e_timeout_ms
            if policy.timeouts and policy.timeouts.e2e_timeout_ms:
                effective_e2e_timeout = policy.timeouts.e2e_timeout_ms

            effective_provider_timeout = self.settings.provider_timeout_ms
            if policy.timeouts and policy.timeouts.provider_timeout_ms:
                effective_provider_timeout = policy.timeouts.provider_timeout_ms

            # Validate provider resolution up front to fail fast on misconfiguration
            from src.adapters.providers import registry

            for model_name in consensus_request.models:
                override_name = None
                if consensus_request.provider_overrides:
                    override_name = consensus_request.provider_overrides.get(model_name)
                try:
                    registry.resolve_provider(model_name, override_name=override_name)
                except LcsError as exc:
                    envelope = ErrorEnvelope(
                        type="config_error",
                        message=str(exc),
                        retryable=getattr(exc, "retryable", False),
                        status_code=400,
                    )
                    raise OrchestrationError(envelope) from exc

            max_models = min(
                self.settings.max_models, policy.guardrails.request.models.max_models
            )
            semaphore = asyncio.Semaphore(max_models)

            async def limited_call(model_name: str) -> ProviderResult:
                async with semaphore:
                    return await self._call_single_model(
                        prompt_for_processing,
                        model_name,
                        request_id,
                        consensus_request.normalize_output,
                        consensus_request.include_scores,
                        effective_provider_timeout,
                        consensus_request.provider_overrides,
                    )

            tasks = [asyncio.create_task(limited_call(model)) for model in consensus_request.models]
            try:
                raw_results = await enforce_timeout(
                    asyncio.gather(*tasks, return_exceptions=True), effective_e2e_timeout
                )
            except asyncio.TimeoutError:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                envelope = ErrorEnvelope(
                    type="timeout", message="Request timed out", retryable=True, status_code=504
                )
                raise OrchestrationError(envelope)

            responses = build_model_responses(consensus_request.models, raw_results)
            cost_summary = _apply_pricing_hints(responses, consensus_request.pricing_hints)
            latency_summary = _compute_latency_summary(responses)

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
            calibrated_confidence, calibration_version, calibration_applied, calibration_reason = apply_calibrator(
                self.calibrator, confidence
            )
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

            validation_cfg = consensus_request.output_validation
            if validation_cfg and getattr(validation_cfg, "enabled", False) and winner:
                validator = resolve_validator(getattr(validation_cfg, "kind", None), self.output_validator)
                if validator is None:
                    logger.warning(
                        "output_validator_unavailable",
                        request_id=request_id,
                        kind=getattr(validation_cfg, "kind", None),
                    )
                else:
                    target_idx = next((idx for idx, r in enumerate(responses) if r.model == winner), None)

                    def _validate(resp: ModelResponse):
                        if resp.content is None or (isinstance(resp.content, str) and not resp.content.strip()):
                            return False, "empty"
                        return validator(resp.content)

                    if target_idx is not None:
                        valid, reason = _validate(responses[target_idx])
                        validation_failed = False
                        reask_outcome = None

                        if not valid:
                            validation_reason = reason or "invalid"
                            remaining_ms = effective_e2e_timeout - int(
                                (time.perf_counter() - start_time) * 1000
                            )
                            if validation_cfg.max_reask and validation_cfg.max_reask > 0 and remaining_ms > 0:
                                reask_timeout = effective_provider_timeout
                                if reask_timeout is not None:
                                    reask_timeout = min(reask_timeout, remaining_ms)
                                reask_result = await fetch_provider_result(
                                    prompt=consensus_request.prompt,
                                    model=winner,
                                    request_id=request_id,
                                    normalize_output=consensus_request.normalize_output,
                                    include_scores=consensus_request.include_scores,
                                    provider_timeout_ms=reask_timeout,
                                    provider_overrides=consensus_request.provider_overrides,
                                )
                                responses[target_idx] = reask_result.to_contract()
                                latency_summary = _compute_latency_summary(responses)
                                valid, reason = _validate(responses[target_idx])
                                reask_outcome = "success" if valid else "failed"
                            else:
                                reask_outcome = "skipped_timeout" if remaining_ms <= 0 else "disabled"

                            try:
                                output_validation_reasks_total.labels(outcome=reask_outcome).inc()
                            except Exception:
                                pass

                            if not valid:
                                validation_failed = True
                                validation_reason = reason or validation_reason or "invalid"
                                try:
                                    output_validation_total.labels(
                                        outcome="fail", reason=str(validation_reason)
                                    ).inc()
                                except Exception:
                                    pass
                            else:
                                try:
                                    output_validation_total.labels(outcome="reask_pass", reason="").inc()
                                except Exception:
                                    pass
                        else:
                            try:
                                output_validation_total.labels(outcome="pass", reason="").inc()
                            except Exception:
                                pass

                        if validation_failed:
                            result = ConsensusResult(
                                request_id=request_id,
                                winner=None,
                                confidence=0.0,
                                calibrated_confidence=None,
                                calibration_version=calibration_version,
                                calibration_applied=False,
                                calibration_reason="validation_failed",
                                responses=[] if not consensus_request.include_raw else responses,
                                method="validation_failed",
                                seed=consensus_request.seed,
                                replay_token=token,
                                timing=Timing(e2e_ms=e2e_ms),
                                scores=scores,
                                score_stats=score_stats,
                                gated=True,
                                gate_reason=f"validation_failed:{validation_reason}",
                                cost_summary=cost_summary,
                                latency_summary=latency_summary or _compute_latency_summary(responses),
                                redaction=redaction_summary,
                            )
                            await self._fire_run_event(
                                consensus_request,
                                request_id=request_id,
                                strategy=strategy_label,
                                responses=responses,
                                winner=None,
                                confidence=0.0,
                                e2e_ms=e2e_ms,
                                gated=True,
                                gate_reason=result.gate_reason,
                                error_type="validation_failed",
                                include_scores=consensus_request.include_scores,
                                score_stats=score_stats.dict() if score_stats else None,
                            )
                            return result

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
                calibrated_confidence=calibrated_confidence,
                calibration_version=calibration_version,
                calibration_applied=calibration_applied,
                calibration_reason=calibration_reason,
                responses=[] if not consensus_request.include_raw else responses,
                method=method,
                seed=consensus_request.seed,
                replay_token=token,
                timing=Timing(e2e_ms=e2e_ms),
                scores=scores,
                score_stats=score_stats,
                cost_summary=cost_summary,
                latency_summary=latency_summary,
                redaction=redaction_summary,
            )
            if post_decision and policy.gating_mode == "soft":
                logger.info(
                    "policy_post_gated",
                    request_id=request_id,
                    reason=post_decision.reason,
                )
            result = apply_gating_result(result, post_decision, policy.gating_mode)
        except OrchestrationError as exc:
            e2e_ms = int((time.perf_counter() - start_time) * 1000)
            await self._fire_run_event(
                consensus_request,
                request_id=request_id,
                strategy=strategy_label,
                responses=responses,
                winner=winner,
                confidence=calibrated_confidence if 'calibrated_confidence' in locals() else confidence,
                e2e_ms=e2e_ms,
                gated=getattr(result, "gated", None) if result else None,
                gate_reason=getattr(result, "gate_reason", None) if result else None,
                error_type=getattr(exc.envelope, "type", None),
                include_scores=consensus_request.include_scores,
                score_stats=score_stats.dict() if score_stats else None,
            )
            raise
        except Exception:
            e2e_ms = int((time.perf_counter() - start_time) * 1000)
            await self._fire_run_event(
                consensus_request,
                request_id=request_id,
                strategy=strategy_label,
                responses=responses,
                winner=winner,
                confidence=calibrated_confidence if 'calibrated_confidence' in locals() else confidence,
                e2e_ms=e2e_ms,
                gated=getattr(result, "gated", None) if result else None,
                gate_reason=getattr(result, "gate_reason", None) if result else None,
                error_type="internal",
                include_scores=consensus_request.include_scores,
                score_stats=score_stats.dict() if score_stats else None,
            )
            raise
        else:
            await self._fire_run_event(
                consensus_request,
                request_id=request_id,
                strategy=strategy_label,
                responses=responses,
                winner=winner,
                confidence=calibrated_confidence,
                e2e_ms=result.timing.e2e_ms if result else int((time.perf_counter() - start_time) * 1000),
                gated=result.gated if result else None,
                gate_reason=result.gate_reason if result else None,
                error_type=None,
                include_scores=consensus_request.include_scores,
                score_stats=score_stats.dict() if score_stats else None,
            )
            return result

    async def _run_early_stop(
        self,
        consensus_request: ConsensusRequest,
        request_id: str,
        strategy_label: str,
        start_time: float,
    ) -> ConsensusResult:
        policy = self.policy_store.current()
        config = consensus_request.early_stop
        assert config is not None and config.enabled  # validated upstream

        responses = []
        scores = None
        score_stats = None
        winner = None
        confidence = None
        result: ConsensusResult | None = None
        stop_reason = "max_samples"

        try:
            preflight_decision = apply_preflight_gating(
                policy,
                consensus_request.prompt,
                consensus_request.models,
                consensus_request.normalize_output,
                request_id=request_id,
            )
            safety_decision = self._prompt_safety_check(consensus_request, policy, request_id)
            if safety_decision and safety_decision.action == "block":
                e2e_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info(
                    "prompt_safety_blocked",
                    request_id=request_id,
                    reason=safety_decision.reason,
                )
                result = ConsensusResult(
                    request_id=request_id,
                    winner=None,
                    confidence=0.0,
                    calibrated_confidence=None,
                    calibration_version=None,
                    calibration_applied=None,
                    calibration_reason=None,
                    responses=[],
                    method="prompt_safety_block",
                    timing=Timing(e2e_ms=e2e_ms),
                    gated=True,
                    gate_reason=safety_decision.reason,
                    prompt_safety=safety_decision,
                )
                await self._fire_run_event(
                    consensus_request,
                    request_id=request_id,
                    strategy=strategy_label,
                    responses=[],
                    winner=None,
                    confidence=0.0,
                    e2e_ms=e2e_ms,
                    gated=True,
                    gate_reason=safety_decision.reason,
                    error_type=None,
                    include_scores=consensus_request.include_scores,
                    score_stats=None,
                )
                return result
            if preflight_decision and policy.gating_mode == "soft":
                e2e_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info(
                    "policy_gated_preflight",
                    request_id=request_id,
                    reason=preflight_decision.reason,
                )
                result = ConsensusResult(
                    request_id=request_id,
                    winner=None,
                    confidence=0.0,
                    responses=[],
                    method="policy_preflight",
                    seed=consensus_request.seed,
                    replay_token=token,
                    timing=Timing(e2e_ms=e2e_ms),
                    gated=True,
                    gate_reason=preflight_decision.reason,
                )
                await self._fire_run_event(
                    consensus_request,
                    request_id=request_id,
                    strategy=strategy_label,
                    responses=[],
                    winner=None,
                    confidence=0.0,
                    e2e_ms=e2e_ms,
                    gated=True,
                    gate_reason=preflight_decision.reason,
                    error_type=None,
                    include_scores=consensus_request.include_scores,
                    score_stats=None,
                )
                return result

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

            effective_e2e_timeout = self.settings.e2e_timeout_ms
            if policy.timeouts and policy.timeouts.e2e_timeout_ms:
                effective_e2e_timeout = policy.timeouts.e2e_timeout_ms

            effective_provider_timeout = self.settings.provider_timeout_ms
            if policy.timeouts and policy.timeouts.provider_timeout_ms:
                effective_provider_timeout = policy.timeouts.provider_timeout_ms

            max_samples = config.max_samples or len(consensus_request.models)
            selected_models = consensus_request.models[:max_samples]

            from src.adapters.providers import registry
            from src.adapters.providers.openrouter import register_default_openrouter

            register_default_openrouter()
            for model_name in selected_models:
                override_name = None
                if consensus_request.provider_overrides:
                    override_name = consensus_request.provider_overrides.get(model_name)
                try:
                    registry.resolve_provider(model_name, override_name=override_name)
                except LcsError as exc:
                    envelope = ErrorEnvelope(
                        type="config_error",
                        message=str(exc),
                        retryable=getattr(exc, "retryable", False),
                        status_code=400,
                    )
                    raise OrchestrationError(envelope) from exc

            for model_name in selected_models:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                remaining_ms = effective_e2e_timeout - elapsed_ms
                if remaining_ms <= 0:
                    envelope = ErrorEnvelope(
                        type="timeout", message="Request timed out", retryable=True, status_code=504
                    )
                    raise OrchestrationError(envelope)

                provider_result = await enforce_timeout(
                    self._call_single_model(
                        consensus_request.prompt,
                        model_name,
                        request_id,
                        consensus_request.normalize_output,
                        consensus_request.include_scores,
                        effective_provider_timeout,
                        consensus_request.provider_overrides,
                    ),
                    remaining_ms,
                )
                responses.append(provider_result.to_contract())

                if consensus_request.include_scores:
                    scores, score_stats = compute_scores(responses)

                judgement = self.judge.judge(
                    responses, scores if consensus_request.include_scores else None
                )
                winner = judgement.winner
                confidence = judgement.confidence
                method = judgement.method

                decision = early_stop_decision(
                    samples_used=len(responses),
                    confidence=confidence,
                    config=config,
                )
                if decision.stop:
                    stop_reason = decision.reason or "max_samples"
                    break

            # Ensure final scoring/judgement are consistent
            if consensus_request.include_scores:
                scores, score_stats = compute_scores(responses)
                judgement = self.judge.judge(responses, scores)
                winner = judgement.winner
                confidence = judgement.confidence
                method = judgement.method
            else:
                judgement = self.judge.judge(responses, None)
                winner = judgement.winner
                confidence = judgement.confidence
                method = judgement.method

            # Guardrails
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
                early_stop=EarlyStopReport(
                    samples_used=len(responses),
                    stop_reason=stop_reason,
                    current_confidence=confidence or 0.0,
                    winner=winner,
                ),
            )
            if post_decision and policy.gating_mode == "soft":
                logger.info(
                    "policy_post_gated",
                    request_id=request_id,
                    reason=post_decision.reason,
                )
            result = apply_gating_result(result, post_decision, policy.gating_mode)
        except OrchestrationError as exc:
            e2e_ms = int((time.perf_counter() - start_time) * 1000)
            await self._fire_run_event(
                consensus_request,
                request_id=request_id,
                strategy=strategy_label,
                responses=responses,
                winner=winner,
                confidence=confidence,
                e2e_ms=e2e_ms,
                gated=getattr(result, "gated", None) if result else None,
                gate_reason=getattr(result, "gate_reason", None) if result else None,
                error_type=getattr(exc.envelope, "type", None),
                include_scores=consensus_request.include_scores,
                score_stats=score_stats.dict() if score_stats else None,
            )
            raise
        except Exception:
            e2e_ms = int((time.perf_counter() - start_time) * 1000)
            await self._fire_run_event(
                consensus_request,
                request_id=request_id,
                strategy=strategy_label,
                responses=responses,
                winner=winner,
                confidence=confidence,
                e2e_ms=e2e_ms,
                gated=getattr(result, "gated", None) if result else None,
                gate_reason=getattr(result, "gate_reason", None) if result else None,
                error_type="internal",
                include_scores=consensus_request.include_scores,
                score_stats=score_stats.dict() if score_stats else None,
            )
            raise
        else:
            try:
                early_stop_samples_used.labels(strategy=strategy_label).observe(len(responses))
                early_stop_decisions_total.labels(strategy=strategy_label, reason=stop_reason).inc()
            except Exception:
                logger.warning("metrics_emit_failed", metric="early_stop", reason=stop_reason)

            await self._fire_run_event(
                consensus_request,
                request_id=request_id,
                strategy=strategy_label,
                responses=responses,
                winner=winner,
                confidence=confidence,
                e2e_ms=result.timing.e2e_ms if result else int((time.perf_counter() - start_time) * 1000),
                gated=result.gated if result else None,
                gate_reason=result.gate_reason if result else None,
                error_type=None,
                include_scores=consensus_request.include_scores,
                score_stats=score_stats.dict() if score_stats else None,
            )
            return result

    def _prompt_safety_check(
        self,
        consensus_request: ConsensusRequest,
        policy,
        request_id: str,
    ) -> PromptSafetyDecision | None:
        config = consensus_request.prompt_safety
        if config is None and hasattr(policy, "prefilter"):
            config = getattr(policy.prefilter, "prompt_safety", None)
        if config is None:
            config = PromptSafetyConfig()
        if config.mode == "off":
            return None

        start = time.perf_counter()
        decision = run_prompt_safety(consensus_request.prompt, config)
        elapsed = time.perf_counter() - start

        try:
            prompt_safety_decisions_total.labels(mode=config.mode, action=decision.action, reason=decision.reason).inc()
            prompt_safety_duration_seconds.labels(mode=config.mode).observe(elapsed)
        except Exception:
            logger.warning("metrics_emit_failed", metric="prompt_safety")

        with tracer.start_as_current_span(
            "prompt_safety.detect",
            attributes={
                "request_id": request_id,
                "mode": config.mode,
                "action": decision.action,
                "reason": decision.reason,
            },
        ):
            logger.info(
                "prompt_safety_decision",
                request_id=request_id,
                mode=config.mode,
                action=decision.action,
                reason=decision.reason,
            )
        return decision

    async def _fire_run_event(
        self,
        consensus_request: ConsensusRequest,
        *,
        request_id: str,
        strategy: str,
        responses,
        winner: str | None,
        confidence: float | None,
        e2e_ms: int,
        gated: bool | None,
        gate_reason: str | None,
        error_type: str | None,
        include_scores: bool,
        score_stats: dict | None,
        prompt_text: str | None = None,
    ) -> None:
        event = build_run_event(
            request_id=request_id,
            strategy=strategy,
            prompt=prompt_text or consensus_request.prompt,
            models=consensus_request.models,
            responses=responses,
            winner=winner,
            confidence=confidence,
            timing_ms=e2e_ms,
            gated=gated,
            gate_reason=gate_reason,
            error_type=error_type,
            include_scores=include_scores,
            score_stats=score_stats,
        )
        try:
            run_events_total.labels(outcome=event.outcome).inc()
        except Exception:
            logger.warning("metrics_emit_failed", metric="run_events_total", outcome=event.outcome)

        if self.run_event_callback is None:
            return

        await self._safe_fire_callback(event)

    async def _safe_fire_callback(self, event) -> None:
        outcome = "ok"
        start = time.perf_counter()
        timeout_s = self.callback_timeout_ms / 1000 if self.callback_timeout_ms else None
        with tracer.start_as_current_span(
            "run_event_callback",
            attributes={"event_id": event.event_id, "outcome": event.outcome},
        ):
            try:
                if asyncio.iscoroutinefunction(self.run_event_callback):
                    await asyncio.wait_for(self.run_event_callback(event), timeout=timeout_s)
                else:
                    await asyncio.wait_for(
                        asyncio.to_thread(self.run_event_callback, event), timeout=timeout_s
                    )
            except asyncio.TimeoutError:
                outcome = "timeout"
                logger.warning(
                    "run_event_callback_timeout",
                    request_id=event.event_id,
                    callback_timeout_ms=self.callback_timeout_ms,
                )
            except Exception as exc:  # pragma: no cover - defensive
                outcome = "error"
                logger.warning(
                    "run_event_callback_error",
                    request_id=event.event_id,
                    error=str(exc),
                )
            finally:
                elapsed = time.perf_counter() - start
                try:
                    run_event_callback_total.labels(outcome=outcome).inc()
                    run_event_callback_duration_seconds.labels(outcome=outcome).observe(elapsed)
                except Exception:
                    logger.warning("metrics_emit_failed", metric="run_event_callback", outcome=outcome)

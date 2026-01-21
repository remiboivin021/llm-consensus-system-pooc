from __future__ import annotations

import asyncio
import time
from typing import Iterable

from opentelemetry import trace

from sample.config import get_settings
from sample.contracts.errors import ErrorEnvelope
from sample.contracts.request import ConsensusRequest
from sample.contracts.response import ConsensusResult, Timing
from sample.adapters.observability.logging import get_logger
from sample.adapters.observability.metrics import (
    consensus_duration_seconds,
    llm_call_duration_seconds,
    llm_calls_total,
    quality_score,
    quality_score_stats,
)
from sample.adapters.orchestration.models import (
    ProviderResult,
    build_model_responses,
    fetch_provider_result,
)
from sample.adapters.orchestration.timeouts import enforce_timeout
from sample.core.consensus.base import Judge
from sample.core.consensus.strategies import ScorePreferredJudge
from sample.core.scoring.engine import compute_scores

logger = get_logger()
tracer = trace.get_tracer(__name__)


class OrchestrationError(Exception):
    def __init__(self, envelope: ErrorEnvelope):
        super().__init__(envelope.message)
        self.envelope = envelope


def _sanitize_model_label(model: str, allowed: Iterable[str]) -> str:
    return model if model in allowed else "other"


class Orchestrator:
    def __init__(self, judge: Judge | None = None) -> None:
        self.settings = get_settings()
        self.judge = judge or ScorePreferredJudge()

    async def _call_single_model(
        self,
        prompt: str,
        model: str,
        request_id: str,
        normalize_output: bool,
        include_scores: bool,
    ) -> ProviderResult:
        result = await fetch_provider_result(
            prompt, model, request_id, normalize_output, include_scores
        )
        outcome = "ok" if result.error is None else "error"
        model_label = _sanitize_model_label(model, self.settings.default_models)
        llm_calls_total.labels(model=model_label, outcome=outcome).inc()
        if result.latency_ms is not None:
            llm_call_duration_seconds.labels(model=model_label, outcome=outcome).observe(
                result.latency_ms / 1000
            )
        return result

    async def run(self, consensus_request: ConsensusRequest, request_id: str) -> ConsensusResult:
        max_prompt_chars = min(self.settings.max_prompt_chars, 10000)
        if len(consensus_request.prompt) > max_prompt_chars:
            envelope = ErrorEnvelope(
                type="config_error", message="Prompt too long", retryable=False, status_code=400
            )
            raise OrchestrationError(envelope)

        start_time = time.perf_counter()
        semaphore = asyncio.Semaphore(self.settings.max_models)

        async def limited_call(model_name: str) -> ProviderResult:
            async with semaphore:
                return await self._call_single_model(
                    consensus_request.prompt,
                    model_name,
                    request_id,
                    consensus_request.normalize_output,
                    consensus_request.include_scores,
                )

        tasks = [asyncio.create_task(limited_call(model)) for model in consensus_request.models]
        try:
            raw_results = await enforce_timeout(
                asyncio.gather(*tasks, return_exceptions=True), self.settings.e2e_timeout_ms
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
                                mode=consensus_request.mode,
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
                                mode=consensus_request.mode, stat=stat_name
                            ).set(value)
                        except Exception:
                            logger.warning(
                                "metrics_emit_failed",
                                metric="quality_score_stats",
                                request_id=request_id,
                                stat=stat_name,
                            )

        judgement = self.judge.judge(responses, scores if consensus_request.include_scores else None)
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
        consensus_duration_seconds.labels(mode=consensus_request.mode).observe(e2e_ms / 1000)

        return ConsensusResult(
            request_id=request_id,
            winner=winner,
            confidence=confidence,
            responses=[] if not consensus_request.include_raw else responses,
            method=method,
            timing=Timing(e2e_ms=e2e_ms),
            scores=scores,
            score_stats=score_stats,
        )

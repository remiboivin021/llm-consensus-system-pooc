from __future__ import annotations

import time
from typing import Awaitable, Callable

from opentelemetry import trace

from src.adapters.observability.logging import get_logger
from src.adapters.observability.metrics import (
    early_stop_confidence,
    early_stop_decisions_total,
    early_stop_samples_used,
)
from src.adapters.orchestration.models import ProviderResult
from src.contracts.errors import ErrorEnvelope
from src.contracts.response import ModelResponse, Timing
from src.contracts.self_consistency import SelfConsistencyConfig, SelfConsistencyResult

logger = get_logger()
tracer = trace.get_tracer(__name__)


async def run_self_consistency(
    *,
    prompt: str,
    model: str,
    request_id: str,
    fetch_fn: Callable[[str, str, str, bool, bool, int | None], Awaitable[ProviderResult]],
    config: SelfConsistencyConfig,
) -> SelfConsistencyResult:
    """
    Sample a single model multiple times and stop early once confidence crosses threshold.

    Deterministic ordering, defensive metric/log emission, no new deps.
    """
    samples: list[ModelResponse] = []
    start = time.perf_counter()
    stop_reason = "max_samples"
    confidence = 0.0
    winner: str | None = None

    loop_deadline = (
        start + (config.loop_timeout_ms / 1000) if config.loop_timeout_ms is not None else None
    )

    for idx in range(1, config.max_samples + 1):
        if loop_deadline and time.perf_counter() >= loop_deadline:
            stop_reason = "timeout"
            break

        # Each sample call; include_scores/normalize_output both False for speed.
        try:
            result = await fetch_fn(
                prompt,
                model,
                request_id,
                False,
                False,
                config.per_sample_timeout_ms,
            )
        except Exception as exc:  # defensive: convert to envelope
            logger.warning("self_consistency_fetch_failed", request_id=request_id, error=str(exc))
            result = ProviderResult(
                model=model,
                content=None,
                latency_ms=None,
                error=ErrorEnvelope(type="internal", message=str(exc), retryable=False),
            )

        samples.append(result.to_contract())

        with tracer.start_as_current_span(
            "self_consistency.sample",
            attributes={
                "request_id": request_id,
                "model": model,
                "sample_idx": idx,
                "latency_ms": result.latency_ms,
                "error": getattr(result.error, "type", None),
            },
        ):
            winner, confidence = _aggregate_confidence(samples, model)

        if idx >= config.min_samples and winner and confidence >= config.threshold:
            stop_reason = "threshold"
            break

    if stop_reason == "max_samples" and loop_deadline and time.perf_counter() >= loop_deadline:
        stop_reason = "timeout"

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    _emit_metrics(confidence, len(samples), stop_reason)
    logger.info(
        "self_consistency_finished",
        request_id=request_id,
        model=model,
        samples_used=len(samples),
        stop_reason=stop_reason,
        confidence=confidence,
        threshold=config.threshold,
    )

    return SelfConsistencyResult(
        winner=winner,
        confidence=confidence,
        samples_used=len(samples),
        stop_reason=stop_reason if winner or stop_reason != "max_samples" else "no_winner",
        responses=samples,
        timing=Timing(e2e_ms=elapsed_ms),
    )


def _emit_metrics(confidence: float, samples_used: int, reason: str) -> None:
    try:
        early_stop_samples_used.labels(strategy="self_consistency").observe(samples_used)
        early_stop_decisions_total.labels(strategy="self_consistency", reason=reason).inc()
        early_stop_confidence.labels(strategy="self_consistency").observe(confidence)
    except Exception:
        logger.warning("self_consistency_metrics_failed", reason=reason)


def _aggregate_confidence(responses: list[ModelResponse], model: str) -> tuple[str | None, float]:
    """Compute simple frequency-based confidence across successful samples."""
    successes = [r for r in responses if r.error is None and r.content is not None]
    if not successes:
        return None, 0.0
    counts: dict[str, int] = {}
    for r in successes:
        counts[r.content] = counts.get(r.content, 0) + 1
    top_content, top_count = max(counts.items(), key=lambda item: item[1])
    total = len(successes)
    confidence = top_count / total if total else 0.0
    # Winner tied? pick first matching model (all are same model in this helper).
    return model if top_content else None, confidence

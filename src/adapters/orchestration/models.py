from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.contracts.errors import ErrorEnvelope
from src.contracts.response import ModelResponse
from src.contracts.run_event import RunEvent
from src.adapters.providers.openrouter import (
    STRUCTURED_PREAMBLE,
    call_model,
    get_python_code_format_preamble,
)


@dataclass
class ProviderResult:
    model: str
    content: str | None
    latency_ms: int | None
    error: ErrorEnvelope | None = None
    breaker_state: str | None = None

    def to_contract(self) -> ModelResponse:
        return ModelResponse(
            model=self.model,
            content=self.content,
            latency_ms=self.latency_ms,
            error=self.error,
            breaker_state=self.breaker_state,
        )


def build_model_responses(
    models: Iterable[str], results: Iterable[ProviderResult | Exception]
) -> list[ModelResponse]:
    responses: list[ModelResponse] = []
    for model, result in zip(models, results):
        if isinstance(result, Exception):
            error = ErrorEnvelope(type="internal", message=str(result), retryable=False)
            responses.append(ModelResponse(model=model, content=None, latency_ms=None, error=error))
        else:
            responses.append(result.to_contract())
    return responses


def build_run_event(
    *,
    request_id: str,
    strategy: str,
    prompt: str,
    models: list[str],
    responses: list[ModelResponse] | None,
    winner: str | None,
    confidence: float | None,
    timing_ms: int,
    gated: bool | None,
    gate_reason: str | None,
    error_type: str | None,
    include_scores: bool,
    score_stats: dict | None,
) -> RunEvent:
    success_count = error_count = timeout_count = 0
    if responses:
        for r in responses:
            if r.error is None:
                success_count += 1
            elif getattr(r.error, "type", None) == "timeout":
                timeout_count += 1
            else:
                error_count += 1

    provider_counts = {
        "success": success_count,
        "error": error_count,
        "timeout": timeout_count,
    }

    provider_avg = None
    if responses:
        latencies = [r.latency_ms for r in responses if r.latency_ms is not None]
        if latencies:
            provider_avg = int(sum(latencies) / len(latencies))

    timing = {"e2e": timing_ms, "provider_avg": provider_avg}

    return RunEvent(
        event_id=request_id,
        timestamp_ms=RunEvent.now_ts(),
        outcome=_derive_outcome(gated=gated, error_type=error_type),
        strategy=strategy,
        models=models,
        model_count=len(models),
        prompt_chars=len(prompt),
        winner=winner,
        confidence=confidence,
        gated=gated,
        gate_reason=gate_reason,
        timing_ms=timing,
        provider_counts=provider_counts,
        error_type=error_type,
        include_scores=include_scores,
        score_stats=score_stats,
    )


def _derive_outcome(*, gated: bool | None, error_type: str | None) -> str:
    if error_type == "timeout":
        return "timeout"
    if error_type is not None:
        return "error"
    if gated:
        return "gated"
    return "success"


async def fetch_provider_result(
    prompt: str,
    model: str,
    request_id: str,
    normalize_output: bool,
    include_scores: bool = False,
    provider_timeout_ms: int | None = None,
) -> ProviderResult:
    system_preamble = None
    if normalize_output:
        system_preamble = STRUCTURED_PREAMBLE
    elif include_scores:
        system_preamble = get_python_code_format_preamble()
    
    content, latency_ms, error = await call_model(
        prompt,
        model,
        request_id,
        system_preamble=system_preamble,
        provider_timeout_ms=provider_timeout_ms,
    )
    return ProviderResult(model=model, content=content, latency_ms=latency_ms, error=error)

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.contracts.errors import ErrorEnvelope
from src.contracts.response import ModelResponse
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

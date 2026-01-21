from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sample.contracts.errors import ErrorEnvelope
from sample.contracts.response import ModelResponse
from sample.adapters.providers.openrouter import (
    PYTHON_CODE_FORMAT_PREAMBLE,
    STRUCTURED_PREAMBLE,
    call_model,
)


@dataclass
class ProviderResult:
    model: str
    content: str | None
    latency_ms: int | None
    error: ErrorEnvelope | None = None

    def to_contract(self) -> ModelResponse:
        return ModelResponse(
            model=self.model,
            content=self.content,
            latency_ms=self.latency_ms,
            error=self.error,
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
) -> ProviderResult:
    system_preamble = None
    if normalize_output:
        system_preamble = STRUCTURED_PREAMBLE
    elif include_scores:
        system_preamble = PYTHON_CODE_FORMAT_PREAMBLE
    
    content, latency_ms, error = await call_model(
        prompt, model, request_id, system_preamble=system_preamble
    )
    return ProviderResult(model=model, content=content, latency_ms=latency_ms, error=error)

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.contracts.errors import ErrorEnvelope
from src.contracts.response import ModelResponse


class FixtureError(BaseModel):
    type: ErrorEnvelope.__annotations__["type"]  # reuse literal types
    message: str
    retryable: bool | None = None
    status_code: int | None = None

    def to_envelope(self) -> ErrorEnvelope:
        return ErrorEnvelope(
            type=self.type,
            message=self.message,
            retryable=self.retryable or False,
            status_code=self.status_code,
        )


class ProviderOutput(BaseModel):
    model: str
    content: str | None = None
    latency_ms: int | None = None
    error: FixtureError | None = None

    @field_validator("content")
    @classmethod
    def ensure_content_or_error(cls, value: str | None, info) -> str | None:
        error = info.data.get("error")
        if value is None and error is None:
            raise ValueError("content or error must be provided")
        if value is not None and error is not None:
            raise ValueError("content and error are mutually exclusive")
        return value

    def to_model_response(self) -> ModelResponse:
        return ModelResponse(
            model=self.model,
            content=self.content,
            latency_ms=self.latency_ms,
            error=self.error.to_envelope() if self.error else None,
        )


class FixtureCase(BaseModel):
    case_id: str
    prompt: str
    models: list[str] = Field(min_length=1)
    provider_outputs: list[ProviderOutput] = Field(min_length=1)
    policy_path: str | None = None
    strategy: Literal["score_preferred", "majority_vote", "majority_cosine"] | None = None
    expected_winner: str | None = None
    expected_gate: Literal["pre", "post"] | None = None

    @field_validator("provider_outputs")
    @classmethod
    def align_lengths(cls, outputs: list[ProviderOutput], info) -> list[ProviderOutput]:
        models = info.data.get("models") or []
        if models and len(outputs) != len(models):
            raise ValueError("provider_outputs length must match models length")
        return outputs


class FixtureFile(BaseModel):
    seed: int = 0
    cases: list[FixtureCase]


def load_fixture_file(path: str | Path) -> FixtureFile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return FixtureFile.model_validate(data)

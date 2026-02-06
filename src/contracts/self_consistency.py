from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.contracts.response import ModelResponse, Timing


class SelfConsistencyConfig(BaseModel):
    min_samples: int = Field(default=2, ge=1)
    max_samples: int = Field(default=5, ge=1)
    threshold: float = Field(default=0.66, ge=0.0, le=1.0)
    loop_timeout_ms: int | None = Field(default=None, ge=1)
    per_sample_timeout_ms: int | None = Field(default=None, ge=1)

    @field_validator("max_samples")
    @classmethod
    def validate_bounds(cls, value: int, info) -> int:
        min_val = info.data.get("min_samples", 1)
        if value < min_val:
            raise ValueError("max_samples must be >= min_samples")
        return value


class SelfConsistencyResult(BaseModel):
    winner: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    samples_used: int = Field(ge=0)
    stop_reason: Literal["threshold", "max_samples", "timeout", "no_winner"]
    responses: list[ModelResponse]
    timing: Timing


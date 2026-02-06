from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.contracts.errors import ErrorEnvelope


class ModelResponse(BaseModel):
    model: str
    content: str | None = None
    latency_ms: int | None = None
    error: ErrorEnvelope | None = None
    breaker_state: str | None = None


class Timing(BaseModel):
    e2e_ms: int

    @field_validator("e2e_ms")
    @classmethod
    def validate_positive(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Timing values must be non-negative")
        return value


class ScoreDetail(BaseModel):
    model: str
    performance: float = Field(ge=0.0, le=1.0)
    complexity: float = Field(ge=0.0, le=1.0)
    tests: float = Field(ge=0.0, le=1.0)
    style: float = Field(ge=0.0, le=1.0)
    documentation: float = Field(ge=0.0, le=1.0)
    dead_code: float = Field(ge=0.0, le=1.0)
    security: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)
    error: bool = False
    metadata: dict | None = None


class ScoreStats(BaseModel):
    mean: float = Field(ge=0.0, le=1.0)
    min: float = Field(ge=0.0, le=1.0)
    max: float = Field(ge=0.0, le=1.0)
    stddev: float = Field(ge=0.0)
    count: int = Field(ge=0)


class ConsensusResult(BaseModel):
    request_id: str
    winner: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    responses: list[ModelResponse]
    method: str
    timing: Timing
    scores: list[ScoreDetail] | None = None
    score_stats: ScoreStats | None = None
    gated: bool | None = None
    gate_reason: str | None = None

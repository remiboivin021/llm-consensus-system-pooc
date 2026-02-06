from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.contracts.errors import ErrorEnvelope
from src.contracts.early_stop import EarlyStopReport
from src.contracts.safety import PromptSafetyDecision


class ModelResponse(BaseModel):
    model: str
    provider: str = Field(default="openrouter")
    content: str | None = None
    latency_ms: int | None = None
    error: ErrorEnvelope | None = None
    breaker_state: str | None = None
    estimated_cost: float = Field(default=0.0, ge=0.0)


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


class CostSummary(BaseModel):
    total: float = Field(ge=0.0, default=0.0)
    currency: str = Field(default="usd", min_length=1)


class LatencySummary(BaseModel):
    avg_ms: float = Field(ge=0.0)
    min_ms: int | None = Field(default=None, ge=0)
    max_ms: int | None = Field(default=None, ge=0)


class RedactionEntry(BaseModel):
    type: str
    mask: str
    start: int
    end: int


class RedactionSummary(BaseModel):
    applied: bool = False
    total: int = Field(ge=0, default=0)
    types: dict[str, int] = Field(default_factory=dict)
    truncated: bool = False
    entries: list[RedactionEntry] | None = None


class ConsensusResult(BaseModel):
    request_id: str
    winner: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    calibrated_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    calibration_version: str | None = None
    calibration_applied: bool | None = None
    calibration_reason: str | None = None
    responses: list[ModelResponse]
    method: str
    seed: int | None = Field(default=None, ge=0)
    replay_token: dict | None = None
    timing: Timing
    scores: list[ScoreDetail] | None = None
    score_stats: ScoreStats | None = None
    gated: bool | None = None
    gate_reason: str | None = None
    cost_summary: CostSummary | None = None
    latency_summary: LatencySummary | None = None
    early_stop: EarlyStopReport | None = None
    redaction: RedactionSummary | None = None
    prompt_safety: PromptSafetyDecision | None = None

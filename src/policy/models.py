from __future__ import annotations

from functools import lru_cache
from typing import Literal
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from src.contracts.safety import PromptSafetyConfig


class JudgeConfig(BaseModel):
    type: Literal["score_preferred", "majority_cosine", "majority_vote"] = "score_preferred"


class AcceptConfig(BaseModel):
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    min_quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    require_winner: bool = False


class ConsensusConfig(BaseModel):
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    accept: AcceptConfig = Field(default_factory=AcceptConfig)


class ModelLimits(BaseModel):
    min_models: int = Field(ge=1, default=1)
    max_models: int = Field(ge=1, default=5)
    unique_required: bool = True
    allowed_models: str | list[str] | None = "*"

    @field_validator("max_models")
    @classmethod
    def validate_bounds(cls, value: int, info) -> int:
        min_val = info.data.get("min_models")
        if min_val and value < min_val:
            raise ValueError("max_models must be >= min_models")
        return value


class RequestGuard(BaseModel):
    prompt_min_chars: int = Field(ge=0, default=1)
    prompt_max_chars: int = Field(ge=1, default=8000)
    models: ModelLimits = Field(default_factory=ModelLimits)

    @field_validator("prompt_max_chars")
    @classmethod
    def validate_prompt_bounds(cls, value: int, info) -> int:
        min_val = info.data.get("prompt_min_chars", 0)
        if value < min_val:
            raise ValueError("prompt_max_chars must be >= prompt_min_chars")
        return value


class ProviderGuard(BaseModel):
    require_at_least_n_success: int | None = Field(default=None, ge=0)
    max_failure_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    max_timeout_ratio: float | None = Field(default=None, ge=0.0, le=1.0)


class Guardrails(BaseModel):
    request: RequestGuard = Field(default_factory=RequestGuard)
    providers: ProviderGuard | None = None


class Timeouts(BaseModel):
    provider_timeout_ms: int | None = Field(default=None, ge=1)
    e2e_timeout_ms: int | None = Field(default=None, ge=1)


class BreakerConfig(BaseModel):
    enabled: bool = True
    failure_threshold: int = Field(default=3, ge=1)
    open_ms: int = Field(default=15000, ge=1)
    failure_decay_ms: int = Field(default=60000, ge=1)


class PreambleConfig(BaseModel):
    allow: list[str] | str = "*"


class PiiPrefilter(BaseModel):
    enabled: bool = False
    rules: list[str] = Field(default_factory=lambda: ["email", "phone", "ipv4"])
    map_limit: int = Field(default=500, ge=0)


class PrefilterConfig(BaseModel):
    pii: PiiPrefilter = Field(default_factory=PiiPrefilter)
    prompt_safety: PromptSafetyConfig = Field(default_factory=PromptSafetyConfig)


class Policy(BaseModel):
    policy_id: str
    description: str | None = None
    version: str | int | None = None
    gating_mode: Literal["shadow", "soft"] = "shadow"
    normalize_allowed: bool = True
    consensus: ConsensusConfig = Field(default_factory=ConsensusConfig)
    guardrails: Guardrails = Field(default_factory=Guardrails)
    timeouts: Timeouts | None = None
    breaker: BreakerConfig = Field(default_factory=BreakerConfig)
    preambles: PreambleConfig = Field(default_factory=PreambleConfig)
    prefilter: PrefilterConfig = Field(default_factory=PrefilterConfig)


class PolicyMeta(BaseModel):
    path: str | None = None
    mtime: float | None = None
    content_hash: str | None = None
    loaded_at: datetime
    source: Literal["startup", "manual", "watcher"] = "startup"


class PolicyReloadRequest(BaseModel):
    path: str | None = None
    source: Literal["manual", "watcher", "startup"] = "manual"
    force: bool = False


class PolicyReloadResult(BaseModel):
    status: Literal["accepted", "rejected", "unchanged"]
    policy_id: str | None
    version: str | int | None = None
    path: str | None = None
    reason: str | None = None
    validation_errors: list[str] | None = None
    loaded_at: datetime
    previous_policy_id: str | None = None


@lru_cache(maxsize=1)
def default_policy_path() -> str:
    return "policies/default.policy.yaml"

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, FieldValidationInfo

from src.config import get_settings
from src.contracts.early_stop import EarlyStopConfig
from src.contracts.safety import PromptSafetyConfig


class ConsensusRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str = Field(min_length=1)
    models: list[str] = Field(default_factory=lambda: get_settings().default_models)
    provider_overrides: dict[str, str] | None = None
    pricing_hints: dict[str, float] | None = None
    output_validation: "OutputValidationConfig | None" = None
    strategy: str | None = None
    include_raw: bool = True
    normalize_output: bool = False
    preamble_key: str | None = None
    include_scores: bool = False
    seed: int | None = Field(default=None, ge=0)
    early_stop: EarlyStopConfig | None = None
    prompt_safety: PromptSafetyConfig | None = None

    @field_validator("models")
    @classmethod
    def validate_models(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one model is required")
        settings = get_settings()
        if len(value) > settings.max_models:
            raise ValueError(f"At most {settings.max_models} models are allowed")
        return value

    @field_validator("provider_overrides")
    @classmethod
    def validate_overrides(
        cls, value: dict[str, str] | None, info: FieldValidationInfo
    ) -> dict[str, str] | None:
        if value is None:
            return value
        cleaned = {}
        for model, provider in value.items():
            if not model or not model.strip():
                raise ValueError("provider_overrides keys must be non-empty model names")
            if not provider or not provider.strip():
                raise ValueError("provider_overrides values must be non-empty provider ids")
            cleaned[model.strip()] = provider.strip()
        models = info.data.get("models") if hasattr(info, "data") else None
        if models:
            missing = [key for key in cleaned if key not in models]
            if missing:
                raise ValueError(f"provider_overrides contain unknown models: {','.join(missing)}")
        return cleaned

    @field_validator("pricing_hints")
    @classmethod
    def validate_pricing_hints(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is None:
            return value
        cleaned: dict[str, float] = {}
        for model, hint in value.items():
            if not model or not model.strip():
                raise ValueError("pricing_hints keys must be non-empty model names")
            try:
                num = float(hint)
            except (TypeError, ValueError):
                raise ValueError("pricing_hints values must be numeric")
            if num < 0:
                raise ValueError("pricing_hints values must be non-negative")
            cleaned[model.strip()] = num
        return cleaned

    @field_validator("preamble_key")
    @classmethod
    def validate_preamble_key(cls, value: str | None) -> str | None:
        if value is None:
            return value
        key = value.strip()
        if not key:
            raise ValueError("preamble_key cannot be empty")
        return key

    @field_validator("early_stop")
    @classmethod
    def validate_early_stop(cls, value: EarlyStopConfig | None, info):
        if value is None or not value.enabled:
            return value
        models = info.data.get("models") or []
        if value.max_samples is None:
            value.max_samples = len(models)
        if value.max_samples < value.min_samples:
            raise ValueError("early_stop.max_samples must be >= min_samples")
        if value.min_samples > len(models):
            raise ValueError("early_stop.min_samples cannot exceed number of models")
        return value

    @field_validator("prompt_safety")
    @classmethod
    def validate_prompt_safety(cls, value: PromptSafetyConfig | None):
        if value is None:
            return value
        if value.mode not in {"off", "warn", "block"}:
            raise ValueError("prompt_safety.mode must be off|warn|block")
        if value.max_eval_ms <= 0:
            raise ValueError("prompt_safety.max_eval_ms must be > 0")
        return value


class OutputValidationConfig(BaseModel):
    enabled: bool = False
    kind: str = Field(default="json", description="Validation kind (e.g., json)")
    max_reask: int = Field(default=1, ge=0, le=1)


ConsensusRequest.model_rebuild()

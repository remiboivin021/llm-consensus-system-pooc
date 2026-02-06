from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from src.config import get_settings


class ConsensusRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str = Field(min_length=1)
    models: list[str] = Field(default_factory=lambda: get_settings().default_models)
    strategy: str | None = None
    include_raw: bool = True
    normalize_output: bool = False
    include_scores: bool = False

    @field_validator("models")
    @classmethod
    def validate_models(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one model is required")
        settings = get_settings()
        if len(value) > settings.max_models:
            raise ValueError(f"At most {settings.max_models} models are allowed")
        return value

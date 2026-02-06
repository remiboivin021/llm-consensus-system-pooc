from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        enable_decoding=False,
        populate_by_name=True,
    )

    openrouter_api_key: str | None = Field(
        default=None,
        alias="OPENROUTER_API_KEY",
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "OPEN_ROUTER_API_KEY"),
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    default_models: List[str] | str = Field(
        default_factory=lambda: [
            "qwen/qwen3-coder:free",
            "mistralai/devstral-2512:free",
            "xiaomi/mimo-v2-flash:free",
        ],
        alias="DEFAULT_MODELS",
    )
    provider_timeout_ms: int = Field(default=5000, alias="PROVIDER_TIMEOUT_MS")
    e2e_timeout_ms: int = Field(default=10000, alias="E2E_TIMEOUT_MS")
    max_prompt_chars: int = Field(default=8000, alias="MAX_PROMPT_CHARS")
    max_models: int = Field(default=5, alias="MAX_MODELS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://otel-collector:4318", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    service_name: str = Field(default="LCS", alias="SERVICE_NAME")
    policy_file: str | None = Field(default=None, alias="POLICY_FILE")

    @field_validator("default_models", mode="before")
    @classmethod
    def parse_default_models(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            models = [m.strip() for m in value.split(",") if m.strip()]
        else:
            models = list(value or [])
        if not models:
            raise ValueError("DEFAULT_MODELS must contain at least one model")
        return models

    @field_validator("provider_timeout_ms", "e2e_timeout_ms", "max_prompt_chars", "max_models")
    @classmethod
    def ensure_positive(cls, value: int, info: ValidationInfo) -> int:
        if value <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return value

    @field_validator("policy_file")
    @classmethod
    def validate_policy_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        path = Path(value)
        if not path.is_file():
            raise ValueError(f"Policy file not found at {path}")
        return str(path)

    @classmethod
    def load(cls) -> "Settings":
        return cls()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.load()

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PromptSafetyConfig(BaseModel):
    mode: Literal["off", "warn", "block"] = "off"
    allowlist: list[str] = Field(default_factory=list)
    detector: str | None = None
    max_eval_ms: int = Field(default=5, gt=0)


class PromptSafetyDecision(BaseModel):
    action: Literal["allow", "warn", "block"]
    reason: str
    details: dict | None = None


class PromptTruncationInfo(BaseModel):
    enabled: bool = False
    applied: bool = False
    original_chars: int = Field(default=0, ge=0)
    truncated_chars: int = Field(default=0, ge=0)
    removed_bytes: int = Field(default=0, ge=0)
    note: str | None = None

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EarlyStopConfig(BaseModel):
    enabled: bool = False
    min_samples: int = Field(default=3, ge=1)
    max_samples: int | None = Field(default=None, ge=1)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    tie_break_required: bool = True


class EarlyStopReport(BaseModel):
    samples_used: int = Field(ge=0)
    stop_reason: Literal["confidence_reached", "max_samples", "guardrail_fail"]
    current_confidence: float = Field(ge=0.0, le=1.0)
    winner: str | None = None


from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field


class RunEvent(BaseModel):
    event_id: str = Field(description="Identifier of the consensus request")
    timestamp_ms: int = Field(description="UTC timestamp in milliseconds")
    outcome: Literal["success", "gated", "error", "timeout"]
    strategy: str
    models: list[str]
    model_count: int = Field(ge=0)
    prompt_chars: int = Field(ge=0)
    winner: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    gated: bool | None = None
    gate_reason: str | None = None
    timing_ms: dict
    provider_counts: dict
    error_type: str | None = None
    include_scores: bool = False
    score_stats: dict | None = None

    @classmethod
    def now_ts(cls) -> int:
        return int(time.time() * 1000)


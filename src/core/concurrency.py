from __future__ import annotations

import math

from pydantic import BaseModel, Field, field_validator


class ConcurrencyBudgetInput(BaseModel):
    """Inputs for computing a safe concurrency/semaphore setting."""

    p95_latency_ms: float = Field(gt=0, description="Observed or assumed p95 latency in milliseconds.")
    target_rps: float = Field(gt=0, description="Desired request rate (requests per second).")
    safety_factor: float = Field(default=1.2, gt=0, description="Headroom multiplier to absorb spikes.")
    max_concurrency_cap: int | None = Field(default=None, ge=1, description="Optional hard upper cap.")
    min_concurrency: int = Field(default=1, ge=1, description="Minimum concurrency to allow.")

    @field_validator("max_concurrency_cap")
    @classmethod
    def _cap_not_below_min(cls, value: int | None, info) -> int | None:
        if value is None:
            return value
        min_c = info.data.get("min_concurrency", 1)
        if value < min_c:
            raise ValueError("max_concurrency_cap must be >= min_concurrency")
        return value


class ConcurrencyBudgetResult(BaseModel):
    recommended_concurrency: int = Field(ge=1)
    raw_concurrency: float = Field(ge=0.0)
    predicted_utilization: float = Field(ge=0.0)
    capped: bool = False
    notes: str | None = None


def calculate_concurrency_budget(params: ConcurrencyBudgetInput) -> ConcurrencyBudgetResult:
    """
    Deterministic, side-effect free concurrency estimator.

    Formula (ceil):
        raw = target_rps * (p95_latency_ms / 1000) * safety_factor
        recommended = clamp(raw, min_concurrency, max_concurrency_cap)
        predicted_utilization = raw / recommended
    """
    raw = params.target_rps * (params.p95_latency_ms / 1000.0) * params.safety_factor
    recommended = max(params.min_concurrency, math.ceil(raw))
    capped = False
    notes = None

    if params.max_concurrency_cap is not None and recommended > params.max_concurrency_cap:
        recommended = params.max_concurrency_cap
        capped = True
        notes = "capped_by_max_concurrency"

    predicted_utilization = raw / recommended if recommended > 0 else 0.0

    return ConcurrencyBudgetResult(
        recommended_concurrency=recommended,
        raw_concurrency=raw,
        predicted_utilization=predicted_utilization,
        capped=capped,
        notes=notes,
    )


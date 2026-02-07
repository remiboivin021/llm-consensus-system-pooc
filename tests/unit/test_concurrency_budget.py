import pytest

from src.core.concurrency import (
    ConcurrencyBudgetInput,
    calculate_concurrency_budget,
)


def test_basic_calculation_rounds_up():
    params = ConcurrencyBudgetInput(p95_latency_ms=500, target_rps=2.0, safety_factor=1.0)
    result = calculate_concurrency_budget(params)
    # raw = 2 * 0.5 = 1 -> ceil to 1
    assert result.recommended_concurrency == 1
    assert pytest.approx(result.raw_concurrency, rel=1e-3) == 1.0
    assert result.predicted_utilization == pytest.approx(1.0)


def test_min_concurrency_enforced():
    params = ConcurrencyBudgetInput(p95_latency_ms=10, target_rps=0.1, safety_factor=1.0, min_concurrency=3)
    result = calculate_concurrency_budget(params)
    assert result.recommended_concurrency == 3
    assert result.predicted_utilization < 1.0


def test_cap_applied_and_flagged():
    params = ConcurrencyBudgetInput(
        p95_latency_ms=1000,
        target_rps=10,
        safety_factor=1.5,
        max_concurrency_cap=5,
    )
    result = calculate_concurrency_budget(params)
    assert result.recommended_concurrency == 5
    assert result.capped is True
    assert result.notes == "capped_by_max_concurrency"


def test_validation_rejects_bad_cap():
    with pytest.raises(ValueError):
        ConcurrencyBudgetInput(
            p95_latency_ms=100,
            target_rps=1,
            max_concurrency_cap=0,
        )


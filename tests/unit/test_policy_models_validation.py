import pytest

from src.policy.models import ModelLimits, RequestGuard


def test_model_limits_max_at_least_min():
    with pytest.raises(ValueError):
        ModelLimits(min_models=2, max_models=1)


def test_request_guard_prompt_bounds():
    with pytest.raises(ValueError):
        RequestGuard(prompt_min_chars=5, prompt_max_chars=1)

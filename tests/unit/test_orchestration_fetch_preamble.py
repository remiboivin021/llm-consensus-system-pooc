import pytest

from src.adapters.orchestration.models import fetch_provider_result
from src.adapters.providers.openrouter import get_python_code_format_preamble
from src.adapters.providers import openrouter


@pytest.mark.asyncio
async def test_fetch_provider_result_uses_code_preamble(monkeypatch):
    captured = {}

    async def fake_call_model(prompt, model, request_id, system_preamble=None, provider_timeout_ms=None):
        captured["preamble"] = system_preamble
        return "out", 10, None

    monkeypatch.setattr("src.adapters.providers.openrouter.call_model", fake_call_model)
    openrouter.register_default_openrouter()

    await fetch_provider_result(
        "prompt", "model", "req", normalize_output=False, include_scores=True
    )

    assert captured["preamble"] == get_python_code_format_preamble()

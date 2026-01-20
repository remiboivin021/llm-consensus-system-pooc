import pytest

from sample.core.models import fetch_provider_result
from sample.providers.openrouter import STRUCTURED_PREAMBLE


@pytest.mark.asyncio
async def test_fetch_provider_result_passes_preamble(monkeypatch):
    captured = {}

    async def fake_call_model(prompt, model, request_id, system_preamble=None):
        captured["system_preamble"] = system_preamble
        return "content", 42, None

    monkeypatch.setattr("sample.core.models.call_model", fake_call_model)

    result = await fetch_provider_result(
        "prompt", "model-x", "req-1", normalize_output=True
    )

    assert captured["system_preamble"] == STRUCTURED_PREAMBLE
    assert result.model == "model-x"
    assert result.content == "content"
    assert result.latency_ms == 42
    assert result.error is None

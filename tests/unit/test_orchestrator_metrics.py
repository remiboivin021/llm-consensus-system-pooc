import pytest

from sample.adapters.orchestration.orchestrator import Orchestrator
from sample.adapters.orchestration.models import ProviderResult


class DummySettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 5
        self.e2e_timeout_ms = 1000
        self.default_models = ["known-model"]


@pytest.mark.asyncio
async def test_call_single_model_sanitizes_metric_labels(monkeypatch):
    async def fake_fetch_provider_result(
        prompt, model, request_id, normalize_output, include_scores=False
    ):
        return ProviderResult(model=model, content="ok", latency_ms=120, error=None)

    class DummyCounter:
        def __init__(self):
            self.calls = []
            self.incremented = False

        def labels(self, **labels):
            self.calls.append(labels)
            return self

        def inc(self):
            self.incremented = True

    class DummyHistogram:
        def __init__(self):
            self.calls = []
            self.observed = None

        def labels(self, **labels):
            self.calls.append(labels)
            return self

        def observe(self, value):
            self.observed = value

    counter = DummyCounter()
    histogram = DummyHistogram()

    monkeypatch.setattr("sample.core.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("sample.core.orchestrator.fetch_provider_result", fake_fetch_provider_result)
    monkeypatch.setattr("sample.core.orchestrator.llm_calls_total", counter)
    monkeypatch.setattr("sample.core.orchestrator.llm_call_duration_seconds", histogram)

    service = Orchestrator()
    result = await service._call_single_model(
        prompt="hi",
        model="rogue-model",
        request_id="req-1",
        normalize_output=False,
        include_scores=False,
    )

    assert counter.calls == [{"model": "other", "outcome": "ok"}]
    assert counter.incremented is True
    assert histogram.calls == [{"model": "other", "outcome": "ok"}]
    assert histogram.observed == pytest.approx(0.12)
    assert result.model == "rogue-model"

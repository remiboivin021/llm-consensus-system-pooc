import pytest

from sample.api import routes
from sample.core.models import ProviderResult


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

    monkeypatch.setattr(routes, "fetch_provider_result", fake_fetch_provider_result)
    monkeypatch.setattr(routes, "llm_calls_total", counter)
    monkeypatch.setattr(routes, "llm_call_duration_seconds", histogram)

    result = await routes._call_single_model(
        prompt="hi",
        model="rogue-model",
        request_id="req-1",
        allowed_labels=["known-model"],
        normalize_output=False,
    )

    assert counter.calls == [{"model": "other", "outcome": "ok"}]
    assert counter.incremented is True
    assert histogram.calls == [{"model": "other", "outcome": "ok"}]
    assert histogram.observed == pytest.approx(0.12)
    assert result.model == "rogue-model"

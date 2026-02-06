import httpx
import pytest

from src.adapters.providers import openrouter


class DummyResponse:
    def __init__(self, status_code=500):
        self.status_code = status_code

    def json(self):
        return {}

    def raise_for_status(self):
        raise httpx.HTTPStatusError("bad", request=None, response=self)


class DummyClient:
    def __init__(self, exc):
        self.exc = exc

    async def post(self, *args, **kwargs):
        if isinstance(self.exc, Exception):
            raise self.exc
        return DummyResponse()


@pytest.mark.asyncio
async def test_call_model_handles_timeout(monkeypatch):
    monkeypatch.setattr(openrouter, "get_client", lambda timeout_ms=None: DummyClient(httpx.TimeoutException("late")))
    content, latency_ms, error = await openrouter.call_model("p", "m", "r")
    assert content is None
    assert error.type == "timeout"


@pytest.mark.asyncio
async def test_call_model_handles_request_error(monkeypatch):
    monkeypatch.setattr(openrouter, "get_client", lambda timeout_ms=None: DummyClient(httpx.RequestError("boom")))
    content, latency_ms, error = await openrouter.call_model("p", "m", "r")
    assert error.type == "http_error"

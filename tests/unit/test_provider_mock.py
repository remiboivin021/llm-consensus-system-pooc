import httpx
import json
import pytest
import respx

from src.adapters.providers.openrouter import call_model
from src.adapters.providers.transport import close_client


@pytest.fixture
async def live_client(monkeypatch):
    client = httpx.AsyncClient(base_url="https://openrouter.ai/api/v1")
    monkeypatch.setattr("src.adapters.providers.openrouter.get_client", lambda timeout_ms=None: client)
    yield
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_call_model_parses_content(live_client):
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "hello"}}]},
        )
    )

    content, latency_ms, error = await call_model("hi", "gpt", "req-1")

    assert route.called
    assert content == "hello"
    assert error is None
    assert latency_ms is not None
    await close_client()


@pytest.mark.asyncio
@respx.mock
async def test_call_model_maps_rate_limit(live_client):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(429, json={"error": "rate"})
    )

    content, latency_ms, error = await call_model("hi", "gpt", "req-1")

    assert content is None
    assert error is not None
    assert error.type == "rate_limited"
    await close_client()


@pytest.mark.asyncio
@respx.mock
async def test_call_model_handles_invalid_json(live_client):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"unexpected": "shape"})
    )

    content, latency_ms, error = await call_model("hi", "gpt", "req-1")

    assert content is None
    assert error is not None
    assert error.type == "invalid_response"
    await close_client()


@pytest.mark.asyncio
@respx.mock
async def test_call_model_maps_server_error(live_client):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "oops"})
    )

    content, latency_ms, error = await call_model("hi", "gpt", "req-1")

    assert content is None
    assert error is not None
    assert error.type == "http_error"
    assert error.retryable is True
    await close_client()


@pytest.mark.asyncio
@respx.mock
async def test_call_model_includes_system_preamble(live_client):
    called_with_preamble = {}

    def _callback(request: httpx.Request):
        body = json.loads(request.content)
        called_with_preamble["messages"] = body.get("messages", [])
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(side_effect=_callback)

    await call_model("hi", "gpt", "req-1", system_preamble="SYSTEM")

    assert called_with_preamble["messages"][0]["role"] == "system"
    assert called_with_preamble["messages"][0]["content"] == "SYSTEM"
    await close_client()


@pytest.mark.asyncio
@respx.mock
async def test_call_model_handles_json_decode_error(live_client):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=b"{not json")
    )

    content, latency_ms, error = await call_model("hi", "gpt", "req-1")

    assert content is None
    assert error is not None
    assert error.type == "invalid_response"
    await close_client()

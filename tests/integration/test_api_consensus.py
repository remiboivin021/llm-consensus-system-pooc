import asyncio
import json

import httpx
import pytest
import respx

from sample.adapters.api.app import app


@pytest.mark.asyncio
@respx.mock
async def test_api_consensus_flow():
    responses = [
        httpx.Response(200, json={"choices": [{"message": {"content": "alpha answer"}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": "alpha answer"}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": "beta answer"}}]}),
    ]
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(side_effect=responses)

    models = ["model-a", "model-b", "model-c"]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"prompt": "test prompt", "models": models}
        resp = await client.post("/v1/consensus", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"]
        assert len(data["responses"]) == 3
        assert data["winner"] == "model-a"

        metrics_resp = await client.get("/metrics")
        assert metrics_resp.status_code == 200
        assert "http_requests_total" in metrics_resp.text


@pytest.mark.asyncio
@respx.mock
async def test_api_consensus_respects_include_raw():
    responses = [
        httpx.Response(200, json={"choices": [{"message": {"content": "alpha answer"}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": "alpha answer"}}]}),
    ]
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(side_effect=responses)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"prompt": "test prompt", "models": ["model-a", "model-b"], "include_raw": False}
        resp = await client.post("/v1/consensus", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["winner"] == "model-a"
        assert data["responses"] == []

@pytest.mark.asyncio
@respx.mock
async def test_api_consensus_returns_scores_and_metrics():
    responses = [
        httpx.Response(200, json={"choices": [{"message": {"content": "def a():\n    return 'a'"}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": "def b():\n    return 'b'"}}]}),
    ]
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(side_effect=responses)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "prompt": "test prompt",
            "models": ["model-a", "model-b"],
            "include_scores": True,
            "include_raw": False,
        }
        resp = await client.post("/v1/consensus", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["scores"]
        assert data["score_stats"]
        assert data["score_stats"]["count"] == 2
        assert all("score" in entry for entry in data["scores"])
        assert all("performance" in entry for entry in data["scores"])

        metrics_resp = await client.get("/metrics")
        text = metrics_resp.text
        assert "quality_score_bucket" in text
        assert "quality_score_stats" in text


@pytest.mark.asyncio
@respx.mock
async def test_api_consensus_scores_handle_provider_error():
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(429, json={"error": "rate"}),
            httpx.Response(200, json={"choices": [{"message": {"content": "def ok():\n    return 1"}}]}),
        ]
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "prompt": "test prompt",
            "models": ["model-a", "model-b"],
            "include_scores": True,
            "include_raw": False,
        }
        resp = await client.post("/v1/consensus", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["scores"]) == 2
        assert any(entry["error"] for entry in data["scores"])
        assert data["score_stats"]["count"] == 1


@pytest.mark.asyncio
async def test_api_rejects_prompt_too_long():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"prompt": "a" * 10001, "models": ["model-a"]}
        resp = await client.post("/v1/consensus", json=payload)

        assert resp.status_code == 400
        data = resp.json()
        assert data["type"] == "config_error"
        assert data["status_code"] == 400


@pytest.mark.asyncio
async def test_api_times_out_returns_504(monkeypatch):
    async def fake_enforce(awaitable, timeout_ms):
        raise asyncio.TimeoutError()

    monkeypatch.setattr("sample.core.orchestrator.enforce_timeout", fake_enforce)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"prompt": "test prompt", "models": ["model-a"]}
        resp = await client.post("/v1/consensus", json=payload)

        assert resp.status_code == 504
        data = resp.json()
        assert data["type"] == "timeout"
        assert data["status_code"] == 504


@pytest.mark.asyncio
@respx.mock
async def test_api_normalize_output_injects_system_message():
    captured = {}

    def _callback(request: httpx.Request):
        body = json.loads(request.content)
        captured["messages"] = body.get("messages", [])
        return httpx.Response(200, json={"choices": [{"message": {"content": "alpha answer"}}]})

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(side_effect=_callback)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"prompt": "test prompt", "models": ["model-a"], "normalize_output": True}
        resp = await client.post("/v1/consensus", json=payload)
        assert resp.status_code == 200
        assert captured["messages"][0]["role"] == "system"
        assert "TREE" in captured["messages"][0]["content"]


@pytest.mark.asyncio
async def test_tracing_instrumented_before_lifespan(monkeypatch):
    monkeypatch.setattr("sample.observability.logging._configure_otlp_logging", lambda *_, **__: None)
    original_stack = app.middleware_stack
    app.middleware_stack = app.build_middleware_stack()
    try:
        async with app.router.lifespan_context(app):
            pass
    finally:
        app.middleware_stack = original_stack

    assert any(m.cls.__name__ == "OpenTelemetryMiddleware" for m in app.user_middleware)

import pytest
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from sample.adapters.api.middleware import RequestContextMiddleware


def create_app(raise_error: bool = False) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/err")
    async def err():
        if raise_error:
            raise RuntimeError("boom")
        return JSONResponse({"status": "ok"})

    return app


@pytest.mark.asyncio
async def test_middleware_sets_request_id_header():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/ok")
        assert resp.status_code == 200
        assert resp.headers.get("x-request-id")


@pytest.mark.asyncio
async def test_middleware_returns_envelope_on_exception():
    app = create_app(raise_error=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/err")
        assert resp.status_code == 500
        body = resp.json()
        assert body["type"] == "internal"
        assert body["status_code"] == 500


@pytest.mark.asyncio
async def test_middleware_logs_exception_with_stack(monkeypatch):
    class LoggerStub:
        def __init__(self):
            self.calls = []

        def exception(self, event, *args, **kwargs):
            self.calls.append({"event": event, **kwargs})

    logger_stub = LoggerStub()
    monkeypatch.setattr("sample.adapters.api.middleware.logger", logger_stub)

    app = create_app(raise_error=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/err")

    assert resp.status_code == 500
    assert logger_stub.calls
    call = logger_stub.calls[0]
    assert call["event"] == "unhandled_exception"
    assert call["path"] == "/err"
    assert call["request_id"]
    assert call.get("exc_info") is True
    assert resp.headers.get("x-request-id") == call["request_id"]

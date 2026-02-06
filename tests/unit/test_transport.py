import asyncio

import pytest

from src.adapters.providers import transport


class DummyClient:
    def __init__(self, base_url=None, timeout=None, headers=None):
        self.base_url = base_url
        self.timeout = timeout
        self.headers = headers or {}
        self.closed = False

    @property
    def is_closed(self):
        return self.closed

    async def aclose(self):
        self.closed = True
        return None


class DummySettings:
    def __init__(self, api_key=None):
        self.openrouter_base_url = "https://example.com"
        self.provider_timeout_ms = 4000
        self.openrouter_api_key = api_key


def test_get_client_sets_auth_header(monkeypatch):
    monkeypatch.setattr(transport, "_client", None)
    monkeypatch.setattr(transport, "httpx", type("X", (), {"AsyncClient": DummyClient}))
    monkeypatch.setattr(transport, "get_settings", lambda: DummySettings(api_key="secret"))

    client = transport.get_client()

    assert isinstance(client, DummyClient)
    assert client.headers["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_close_client_handles_closed_loop(monkeypatch):
    class RaisingClient(DummyClient):
        async def aclose(self):
            raise RuntimeError("Event loop is closed")

    monkeypatch.setattr(transport, "_client", RaisingClient())
    # Should not raise
    await transport.close_client()
    assert transport._client is None


def test_get_client_recreates_if_closed(monkeypatch):
    monkeypatch.setattr(transport, "httpx", type("X", (), {"AsyncClient": DummyClient}))
    monkeypatch.setattr(transport, "get_settings", lambda: DummySettings())

    first = transport.get_client()
    first.closed = True
    second = transport.get_client()
    assert first is not second


def test_get_client_recreates_closes_prior_without_loop(monkeypatch):
    monkeypatch.setattr(transport, "httpx", type("X", (), {"AsyncClient": DummyClient}))
    monkeypatch.setattr(transport, "get_settings", lambda: DummySettings())
    transport._client = DummyClient()

    run_called = False

    def fake_run(coro):
        nonlocal run_called
        run_called = True
        return asyncio.run(coro)

    monkeypatch.setattr(transport.asyncio, "get_running_loop", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(transport.asyncio, "run", fake_run)

    new_client = transport.get_client(timeout_ms=1234)

    assert run_called is True
    assert transport._client is new_client
    # prior client should have been closed by the async close path
    assert isinstance(new_client, DummyClient)


def test_get_client_recreates_closes_prior_with_running_loop(monkeypatch):
    monkeypatch.setattr(transport, "httpx", type("X", (), {"AsyncClient": DummyClient}))
    monkeypatch.setattr(transport, "get_settings", lambda: DummySettings())
    prior = DummyClient()
    transport._client = prior

    class DummyLoop:
        def __init__(self):
            self.tasks = []

        def create_task(self, coro):
            # Run immediately to keep deterministic tests
            asyncio.run(coro)
            self.tasks.append(coro)
            return coro

    dummy_loop = DummyLoop()
    monkeypatch.setattr(transport.asyncio, "get_running_loop", lambda: dummy_loop)

    new_client = transport.get_client(timeout_ms=9999)

    assert prior.closed is True
    assert transport._client is new_client
    assert dummy_loop.tasks, "close coroutine should have been scheduled"


def test_get_client_reuses_when_open(monkeypatch):
    monkeypatch.setattr(transport, "httpx", type("X", (), {"AsyncClient": DummyClient}))
    monkeypatch.setattr(transport, "get_settings", lambda: DummySettings())
    transport._client = None

    first = transport.get_client()
    second = transport.get_client()
    assert first is second

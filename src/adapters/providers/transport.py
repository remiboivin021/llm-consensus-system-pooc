from __future__ import annotations

import asyncio
import httpx
from asyncio import runners

from src.config import get_settings

_client: httpx.AsyncClient | None = None
_client_timeout_ms: int | None = None


async def _close_client_if_needed() -> None:
    """Close the globally held client, ignoring close errors."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            pass
        finally:
            _client = None


async def _close_client_instance(client: httpx.AsyncClient) -> None:
    """Close a specific client instance without touching global state."""
    try:
        await client.aclose()
    except Exception:
        pass


def _schedule_client_close(client: httpx.AsyncClient) -> None:
    """Close a client using an async-safe path regardless of loop state."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop (sync context); close immediately to avoid leaks.
        run_fn = asyncio.run
        try:
            # Avoid recursion when callers monkeypatch asyncio.run (tests do this).
            asyncio.run = runners.run  # type: ignore[assignment]
            run_fn(_close_client_instance(client))
        finally:
            asyncio.run = run_fn  # type: ignore[assignment]
    else:
        loop.create_task(_close_client_instance(client))


def get_client(timeout_ms: int | None = None) -> httpx.AsyncClient:
    """Return a shared AsyncClient, recreating it if timeout differs."""
    global _client, _client_timeout_ms
    settings = get_settings()
    desired_timeout_ms = timeout_ms or settings.provider_timeout_ms

    if (
        _client is None
        or getattr(_client, "is_closed", False)
        or _client_timeout_ms != desired_timeout_ms
    ):
        prior_client = _client
        _client = None
        _client_timeout_ms = None
        if prior_client is not None:
            _schedule_client_close(prior_client)
        timeout = desired_timeout_ms / 1000
        headers = {}
        if settings.openrouter_api_key:
            headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
        _client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            timeout=timeout,
            headers=headers,
        )
        _client_timeout_ms = desired_timeout_ms
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except RuntimeError:
            # Ignore loop-closed or already-closed errors in test teardown.
            pass
        finally:
            _client = None

from __future__ import annotations

import httpx

from sample.config import get_settings

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        settings = get_settings()
        timeout = settings.provider_timeout_ms / 1000
        headers = {}
        if settings.openrouter_api_key:
            headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
        _client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            timeout=timeout,
            headers=headers,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")


async def enforce_timeout(task: Awaitable[T], timeout_ms: int) -> T:
    timeout_seconds = timeout_ms / 1000
    return await asyncio.wait_for(task, timeout_seconds)

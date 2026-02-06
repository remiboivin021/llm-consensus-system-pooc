from __future__ import annotations

import asyncio
import time
from typing import Callable, Dict, Literal, Tuple

from src.policy.models import BreakerConfig

BreakerState = Literal["closed", "open", "half_open"]


class CircuitBreaker:
    """
    Minimal in-memory circuit breaker (per model) with decay and half-open probe.

    States:
    - closed: calls flow; failures accumulate.
    - open: calls short-circuit until open_ms elapses.
    - half_open: one probe allowed; success -> closed, failure -> open.
    """

    def __init__(self, config: BreakerConfig, clock: Callable[[], float] = time.monotonic):
        self.config = config
        self._clock = clock
        self._state: BreakerState = "closed"
        self._failures: int = 0
        self._opened_at: float | None = None
        self._last_failure_at: float | None = None
        self._half_open_in_flight: bool = False
        self._lock = asyncio.Lock()

    def _now(self) -> float:
        return self._clock()

    def _reset_failures_if_decayed(self, now: float) -> None:
        if self._last_failure_at is None:
            return
        if (now - self._last_failure_at) * 1000 >= self.config.failure_decay_ms:
            self._failures = 0
            self._last_failure_at = None

    async def should_allow(self) -> Tuple[bool, BreakerState]:
        if not self.config.enabled:
            return True, "closed"

        async with self._lock:
            now = self._now()
            self._reset_failures_if_decayed(now)

            if self._state == "open":
                assert self._opened_at is not None  # defensive
                if (now - self._opened_at) * 1000 >= self.config.open_ms:
                    # Move to half-open and allow one probe
                    self._state = "half_open"
                    self._half_open_in_flight = False
                else:
                    return False, "open"

            if self._state == "half_open":
                if self._half_open_in_flight:
                    return False, "half_open"
                self._half_open_in_flight = True
                return True, "half_open"

            # closed
            return True, "closed"

    async def record_success(self) -> BreakerState:
        if not self.config.enabled:
            return "closed"

        async with self._lock:
            self._failures = 0
            self._last_failure_at = None
            self._half_open_in_flight = False
            self._state = "closed"
            self._opened_at = None
            return self._state

    async def record_failure(self) -> Tuple[bool, BreakerState]:
        """
        Returns tuple (opened_now, state_after).
        """
        if not self.config.enabled:
            return False, "closed"

        async with self._lock:
            now = self._now()
            self._reset_failures_if_decayed(now)

            self._failures += 1
            self._last_failure_at = now
            self._half_open_in_flight = False

            opened_now = False
            if self._failures >= self.config.failure_threshold:
                self._state = "open"
                self._opened_at = now
                opened_now = True
            elif self._state == "half_open":
                # any failure in half-open re-opens immediately
                self._state = "open"
                self._opened_at = now
                opened_now = True
            else:
                self._state = "closed"

            return opened_now, self._state

    async def state(self) -> BreakerState:
        if not self.config.enabled:
            return "closed"
        async with self._lock:
            return self._state


class BreakerManager:
    """Per-model breaker registry."""

    def __init__(self, config: BreakerConfig, clock: Callable[[], float] = time.monotonic):
        self.config = config
        self._clock = clock
        self._breakers: Dict[str, CircuitBreaker] = {}

    def _get(self, model: str) -> CircuitBreaker:
        if model not in self._breakers:
            self._breakers[model] = CircuitBreaker(self.config, self._clock)
        return self._breakers[model]

    async def should_allow(self, model: str) -> Tuple[bool, BreakerState]:
        return await self._get(model).should_allow()

    async def record_success(self, model: str) -> BreakerState:
        return await self._get(model).record_success()

    async def record_failure(self, model: str) -> Tuple[bool, BreakerState]:
        return await self._get(model).record_failure()

    async def state(self, model: str) -> BreakerState:
        return await self._get(model).state()

import pytest

from src.adapters.orchestration.breaker import CircuitBreaker
from src.policy.models import BreakerConfig


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def advance_ms(self, ms: int):
        self.now += ms / 1000

    def __call__(self):
        return self.now


@pytest.mark.asyncio
async def test_breaker_opens_after_threshold():
    clock = FakeClock()
    config = BreakerConfig(failure_threshold=2, open_ms=1000, failure_decay_ms=10000)
    breaker = CircuitBreaker(config, clock)

    allowed, state = await breaker.should_allow()
    assert allowed and state == "closed"

    opened, state = await breaker.record_failure()
    assert opened is False
    opened, state = await breaker.record_failure()
    assert opened is True
    assert state == "open"

    allowed, state = await breaker.should_allow()
    assert allowed is False
    assert state == "open"

    clock.advance_ms(1000)
    allowed, state = await breaker.should_allow()
    assert allowed is True
    assert state == "half_open"


@pytest.mark.asyncio
async def test_half_open_success_closes():
    clock = FakeClock()
    config = BreakerConfig(failure_threshold=1, open_ms=100, failure_decay_ms=1000)
    breaker = CircuitBreaker(config, clock)

    await breaker.record_failure()  # open
    clock.advance_ms(100)
    allowed, state = await breaker.should_allow()
    assert allowed and state == "half_open"

    await breaker.record_success()
    state_after = await breaker.state()
    assert state_after == "closed"
    allowed, state = await breaker.should_allow()
    assert allowed and state == "closed"


@pytest.mark.asyncio
async def test_half_open_failure_reopens():
    clock = FakeClock()
    config = BreakerConfig(failure_threshold=1, open_ms=50, failure_decay_ms=1000)
    breaker = CircuitBreaker(config, clock)

    await breaker.record_failure()  # opens
    clock.advance_ms(60)
    allowed, state = await breaker.should_allow()
    assert allowed and state == "half_open"

    opened, state = await breaker.record_failure()
    assert opened is True
    assert state == "open"

    allowed, state = await breaker.should_allow()
    assert allowed is False
    assert state == "open"


@pytest.mark.asyncio
async def test_failure_decay_resets_counter():
    clock = FakeClock()
    config = BreakerConfig(failure_threshold=2, open_ms=1000, failure_decay_ms=200)
    breaker = CircuitBreaker(config, clock)

    await breaker.record_failure()
    clock.advance_ms(500)  # past decay window
    opened, state = await breaker.record_failure()
    assert opened is False
    assert state == "closed"

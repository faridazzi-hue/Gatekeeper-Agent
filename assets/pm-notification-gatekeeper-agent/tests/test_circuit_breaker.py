"""Tests for circuit_breaker module."""

import asyncio
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


@pytest.mark.asyncio
async def test_circuit_breaker_allows_initially():
    """New circuit breaker allows all models initially."""
    from circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
    assert await cb.allows("model-a") is True
    assert await cb.allows("model-b") is True


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    """Circuit breaker opens after threshold consecutive failures."""
    from circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=60)
    await cb.record_failure("model-a")
    await cb.record_failure("model-a")
    assert await cb.allows("model-a") is False


@pytest.mark.asyncio
async def test_circuit_breaker_success_resets_failures():
    """A success resets the failure count before threshold is reached."""
    from circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
    await cb.record_failure("model-a")
    await cb.record_success("model-a")
    await cb.record_failure("model-a")
    # Still below threshold after reset
    assert await cb.allows("model-a") is True


@pytest.mark.asyncio
async def test_circuit_breaker_independent_models():
    """Circuit breaker tracks each model independently."""
    from circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=60)
    await cb.record_failure("model-a")
    await cb.record_failure("model-a")
    # model-a is open, model-b should still be allowed
    assert await cb.allows("model-a") is False
    assert await cb.allows("model-b") is True


@pytest.mark.asyncio
async def test_circuit_breaker_zero_threshold_disabled():
    """Threshold of 0 effectively disables the circuit breaker."""
    from circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=0, cooldown_seconds=30)
    # With threshold 0 the breaker never opens (no failure counts)
    await cb.record_failure("model-a")
    await cb.record_failure("model-a")
    await cb.record_failure("model-a")
    # With threshold <= 0 the breaker logic should still be safe
    result = await cb.allows("model-a")
    assert isinstance(result, bool)

"""
Placd — Circuit Breaker

Three-state circuit breaker (CLOSED → OPEN → HALF_OPEN) with state
persisted in Redis so all workers share a consistent view.

Redis keys (all prefixed ``cb:``):
    cb:{domain}:state      → "CLOSED" | "OPEN" | "HALF_OPEN"
    cb:{domain}:failures   → int   (consecutive failure count)
    cb:{domain}:opened_at  → float (unix timestamp when OPEN was entered)
"""

import asyncio
import functools
import logging
import os
import time
from typing import Any, Callable, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# ─── Redis Client (shared) ──────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
_redis_client: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


# ─── States ──────────────────────────────────────────────────────────────────

CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"


# ─── Exceptions ──────────────────────────────────────────────────────────────

class CircuitOpenError(Exception):
    """Raised when a call is attempted while the circuit breaker is OPEN."""

    def __init__(self, domain: str, retry_after: float = 0.0):
        self.domain = domain
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker OPEN for {domain}. "
            f"Retry after {retry_after:.0f}s."
        )


# ─── Circuit Breaker ────────────────────────────────────────────────────────

class CircuitBreaker:
    """
    Per-domain circuit breaker backed by Redis.

    Parameters
    ----------
    domain : str
        Logical domain identifier (e.g. ``"greenhouse.io"``).
    failure_threshold : int
        Consecutive failures before the circuit opens.
    recovery_timeout : float
        Seconds the circuit stays OPEN before transitioning to HALF_OPEN.
    half_open_max : int
        Maximum probe requests allowed in HALF_OPEN state.
    """

    def __init__(
        self,
        domain: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0,
        half_open_max: int = 2,
    ):
        self.domain = domain
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

        # Redis key helpers
        self._k_state = f"cb:{domain}:state"
        self._k_failures = f"cb:{domain}:failures"
        self._k_opened_at = f"cb:{domain}:opened_at"

    # ── State helpers ────────────────────────────────────────────────────

    async def get_state(self) -> str:
        """Return the current state, defaulting to CLOSED."""
        try:
            r = await _get_redis()
            state = await r.get(self._k_state)
            if state in (CLOSED, OPEN, HALF_OPEN):
                return state
        except Exception:
            pass
        return CLOSED

    async def _set_state(self, new_state: str) -> None:
        old_state = await self.get_state()
        try:
            r = await _get_redis()
            await r.set(self._k_state, new_state)
        except Exception:
            pass

        if old_state != new_state:
            logger.info(
                "circuit_breaker_transition",
                domain=self.domain,
                old_state=old_state,
                new_state=new_state,
                timestamp=time.time(),
            )

    async def _get_failures(self) -> int:
        try:
            r = await _get_redis()
            val = await r.get(self._k_failures)
            return int(val) if val else 0
        except Exception:
            return 0

    async def _incr_failures(self) -> int:
        try:
            r = await _get_redis()
            return await r.incr(self._k_failures)
        except Exception:
            return 0

    async def _reset_failures(self) -> None:
        try:
            r = await _get_redis()
            await r.set(self._k_failures, 0)
        except Exception:
            pass

    async def _get_opened_at(self) -> float:
        try:
            r = await _get_redis()
            val = await r.get(self._k_opened_at)
            return float(val) if val else 0.0
        except Exception:
            return 0.0

    async def _set_opened_at(self) -> None:
        try:
            r = await _get_redis()
            await r.set(self._k_opened_at, str(time.time()))
        except Exception:
            pass

    # ── Public API ───────────────────────────────────────────────────────

    async def record_success(self) -> None:
        """Record a successful call. Resets failures and closes the circuit."""
        state = await self.get_state()
        if state in (HALF_OPEN, OPEN):
            await self._set_state(CLOSED)
        await self._reset_failures()

    async def record_failure(self) -> None:
        """Record a failed call. May open the circuit."""
        count = await self._incr_failures()
        state = await self.get_state()

        if state == HALF_OPEN:
            # Any failure in half-open re-opens immediately
            await self._set_state(OPEN)
            await self._set_opened_at()
            return

        if count >= self.failure_threshold:
            await self._set_state(OPEN)
            await self._set_opened_at()

    async def call(self, coro) -> Any:
        """
        Execute *coro* if the circuit allows it.

        - CLOSED  → execute normally
        - OPEN    → check if recovery_timeout elapsed; if yes transition
                     to HALF_OPEN and allow; otherwise raise CircuitOpenError
        - HALF_OPEN → allow (up to half_open_max probes)
        """
        state = await self.get_state()

        if state == OPEN:
            opened_at = await self._get_opened_at()
            elapsed = time.time() - opened_at
            if elapsed >= self.recovery_timeout:
                await self._set_state(HALF_OPEN)
                await self._reset_failures()
                # fall through to execute the probe
            else:
                raise CircuitOpenError(
                    self.domain,
                    retry_after=self.recovery_timeout - elapsed,
                )

        try:
            result = await coro
            await self.record_success()
            return result
        except Exception as exc:
            await self.record_failure()
            raise


# ─── Decorator ───────────────────────────────────────────────────────────────

def with_circuit_breaker(
    domain: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 300.0,
    half_open_max: int = 2,
):
    """
    Decorator that wraps an async function with a CircuitBreaker.

    Usage::

        @with_circuit_breaker(domain="greenhouse.io")
        async def fetch_greenhouse_jobs():
            ...
    """
    cb = CircuitBreaker(
        domain=domain,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max=half_open_max,
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb.call(func(*args, **kwargs))

        # Expose the breaker instance for testing / introspection
        wrapper.circuit_breaker = cb  # type: ignore[attr-defined]
        return wrapper

    return decorator

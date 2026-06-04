"""
Placd — Async Utilities for Celery Workers

Problem: Celery workers are synchronous, but our scrapers are async.
         Calling asyncio.run() per task creates (and tears down) a new
         event loop every time, which is expensive and can leak resources.

Solution: Reuse a single event loop per worker *process*.  The loop is
          created lazily on first use and kept alive for the lifetime of
          the process.
"""

import asyncio

_loop: asyncio.AbstractEventLoop | None = None


def get_or_create_loop() -> asyncio.AbstractEventLoop:
    """Return the per-process event loop, creating it if necessary."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def run_async(coro):
    """
    Run an async coroutine from a synchronous Celery task.

    Reuses the same event loop for the lifetime of the worker process,
    avoiding the overhead of asyncio.run() which creates a new loop each time.
    """
    loop = get_or_create_loop()
    return loop.run_until_complete(coro)

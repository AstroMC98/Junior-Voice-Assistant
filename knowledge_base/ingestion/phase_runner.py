import asyncio
from typing import Any, Coroutine


async def run_phase(
    coros: list[Coroutine],
    max_concurrency: int = 10
) -> list[Any]:
    """
    Runs all coroutines concurrently, bounded to max_concurrency at a time.
    Preserves result order matching input order.
    Raises on first exception (fails fast).
    """
    if not coros:
        return []
    semaphore = asyncio.Semaphore(max_concurrency)

    async def bounded(coro: Coroutine) -> Any:
        async with semaphore:
            return await coro

    return await asyncio.gather(*[bounded(c) for c in coros])

import asyncio
import time
from typing import Callable


class TokenBucketLimiter:
    """
    Asynchronous token bucket rate limiter for staying below OpenRouter RPM limits.
    Refills capacity/60 tokens per second.
    Supports dependency-injected clock and sleep functions for deterministic unit testing.
    """

    def __init__(
        self,
        rpm_limit: int = 16,
        clock: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ):
        self.capacity = float(rpm_limit)
        self.tokens = float(rpm_limit)
        self.refill_rate = float(rpm_limit) / 60.0  # tokens per second
        self.clock = clock or time.time
        self.sleep_fn = sleep_fn
        self.last_refill = self.clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self.clock()
        elapsed = now - self.last_refill
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        while True:
            async with self._lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                # Calculate sleep time until 1 token is available
                needed = 1.0 - self.tokens
                wait_time = needed / self.refill_rate if self.refill_rate > 0 else 1.0

            if self.sleep_fn:
                self.sleep_fn(wait_time)
            else:
                await asyncio.sleep(wait_time)

    def try_acquire(self) -> bool:
        """Non-blocking attempt to acquire a token immediately."""
        self._refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

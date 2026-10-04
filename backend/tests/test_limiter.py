import pytest
from backend.app.llm.limiter import TokenBucketLimiter


def test_limiter_immediate_acquire():
    fake_time = 1000.0

    def clock():
        return fake_time

    limiter = TokenBucketLimiter(rpm_limit=10, clock=clock)
    assert limiter.try_acquire() is True
    assert limiter.tokens == 9.0


def test_limiter_depletion_and_refill():
    fake_time = 1000.0

    def clock():
        return fake_time

    limiter = TokenBucketLimiter(rpm_limit=2, clock=clock)
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    # Bucket now empty
    assert limiter.try_acquire() is False

    # Advance clock by 30 seconds -> refill 1 token (2 tokens per 60s)
    fake_time += 30.0
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is False


@pytest.mark.asyncio
async def test_limiter_async_acquire_with_custom_sleep():
    fake_time = 1000.0

    def clock():
        return fake_time

    slept_durations = []

    def fake_sleep(duration):
        nonlocal fake_time
        slept_durations.append(duration)
        fake_time += duration

    limiter = TokenBucketLimiter(rpm_limit=2, clock=clock, sleep_fn=fake_sleep)
    # Drain tokens
    await limiter.acquire()
    await limiter.acquire()
    assert limiter.tokens == 0.0

    # Acquire third token -> should trigger sleep
    await limiter.acquire()
    assert len(slept_durations) == 1
    assert slept_durations[0] == 30.0  # 1 token needed / (2 / 60)

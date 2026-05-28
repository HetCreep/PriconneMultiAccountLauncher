"""Full-jitter sleep helper. Used wherever a retry / repeat-with-pause sequence
risks looking mechanical (anti-detection signal). Fixed delays are forbidden.
"""

import secrets
import time


def jitter_delay(attempt: int, *, base: float = 0.5, cap: float = 30.0) -> float:
    """AWS full-jitter: returns next delay in seconds for attempt index (0-based)."""
    expo = min(cap, base * (2 ** max(0, attempt)))
    return (secrets.randbits(32) / 0xFFFFFFFF) * expo


def sleep_with_jitter(attempt: int, *, base: float = 0.5, cap: float = 30.0) -> float:
    """Sleep with full jitter. Returns how long we slept."""
    delay = jitter_delay(attempt, base=base, cap=cap)
    time.sleep(delay)
    return delay

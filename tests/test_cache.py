"""
Tests for CacheManager and ETFCache change/stale handling.
"""

import time

from src.data.models import ETFQuote
from src.data.cache import CacheManager


def make_quote(code: str, price: float, pre_close: float, change_percent: float) -> ETFQuote:
    return ETFQuote(
        code=code,
        name=f"ETF{code}",
        price=price,
        change=price - pre_close,
        change_percent=change_percent,
        volume=1000,
        pre_close=pre_close,
        update_time="14:30:00",
        timestamp=time.time(),
    )


def test_cache_update_and_changed():
    cm = CacheManager(cache_expire_seconds=300)
    q1 = make_quote("512170", 1.00, 1.00, 0.0)
    changed1 = cm.update(q1)
    assert changed1 is True
    q2 = make_quote("512170", 1.01, 1.00, 1.0)
    changed2 = cm.update(q2)
    assert changed2 is True
    got = cm.get("512170")
    assert got is not None and abs(got.price - 1.01) < 1e-6


def test_cache_stale_cleanup():
    cm = CacheManager(cache_expire_seconds=1)
    q = make_quote("512170", 1.00, 1.00, 0.0)
    cm.update(q)
    time.sleep(1.2)
    assert cm.is_stale("512170") is True
    removed = cm.cleanup_stale()
    assert removed >= 1


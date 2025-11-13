"""
Tests for DataFetcher failover and single-quote retry behavior.
"""

import time
from typing import Optional

from src.data.models import ETFQuote
from src.data.cache import CacheManager
from src.data.fetcher import DataFetcher
from src.data.api_adapter import QuoteAPIAdapter


class DummyAdapter(QuoteAPIAdapter):
    def __init__(self, name: str, succeed: bool):
        super().__init__(base_url=f"http://{name}")
        self._succeed = succeed
        self._name = name

    def fetch_quote(self, code: str) -> Optional[ETFQuote]:
        if not self._succeed:
            return None
        return ETFQuote(
            code=code,
            name=f"ETF{code}",
            price=1.01,
            change=0.01,
            change_percent=1.0,
            volume=1000,
            pre_close=1.00,
            update_time="14:30:00",
            timestamp=time.time(),
        )


def test_single_quote_retry_and_failover():
    primary = DummyAdapter("primary", succeed=False)
    backup = DummyAdapter("backup", succeed=True)
    cm = CacheManager()
    fetcher = DataFetcher(
        etf_codes=["512170"],
        primary_adapter=primary,
        backup_adapters=[backup],
        cache_manager=cm,
        refresh_interval=1,
        retry_count=1,
        retry_interval=0,
        failover_threshold=1,
    )
    q = fetcher._fetch_single_quote("512170")
    assert q is None
    # After failure threshold reached, switch to backup on next failure
    fetcher._handle_fetch_failure("512170")
    assert fetcher.get_status()["adapter_type"].startswith("backup")


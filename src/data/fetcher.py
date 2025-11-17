"""
Data fetcher with multi-threading, concurrent requests, retry logic, and failover.

Runs in background thread to fetch ETF quotes periodically without blocking UI.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable
from queue import Queue

from .models import ETFQuote
from .api_adapter import QuoteAPIAdapter, APIAdapterFactory
from .cache import CacheManager
from ..utils.logger import get_logger
from ..utils.helpers import is_trading_time, get_next_trading_time


class DataFetcher:
    """
    Background data fetcher with failover support.
    
    Features:
    - Runs in separate thread
    - Concurrent fetching with ThreadPoolExecutor
    - Retry logic with exponential backoff
    - Primary/backup API failover
    - Event-driven notifications
    """
    
    def __init__(
        self,
        etf_codes: List[str],
        primary_adapter: QuoteAPIAdapter,
        backup_adapters: List[QuoteAPIAdapter],
        cache_manager: CacheManager,
        refresh_interval: int = 5,
        retry_count: int = 3,
        retry_interval: int = 1,
        failover_threshold: int = 3,
        data_callback: Optional[Callable] = None
    ):
        """
        Initialize data fetcher.
        
        Args:
            etf_codes: List of ETF codes to fetch
            primary_adapter: Primary API adapter
            backup_adapters: List of backup API adapters
            cache_manager: Cache manager instance
            refresh_interval: Refresh interval in seconds
            retry_count: Number of retries per request
            retry_interval: Interval between retries in seconds
            failover_threshold: Consecutive failures before failover
            data_callback: Callback function for data updates (receives dict of quotes)
        """
        self._etf_codes = etf_codes.copy()
        self._primary_adapter = primary_adapter
        self._backup_adapters = backup_adapters
        self._current_adapter = primary_adapter
        self._cache_manager = cache_manager
        self._refresh_interval = refresh_interval
        self._retry_count = retry_count
        self._retry_interval = retry_interval
        self._failover_threshold = failover_threshold
        self._data_callback = data_callback
        
        self._logger = get_logger(__name__)
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        # Failover tracking
        self._consecutive_failures = 0
        self._current_adapter_index = -1  # -1 means primary, 0+ means backup index
        self._last_failover_time = 0
        
        # Performance tracking
        self._last_fetch_time = 0
        self._last_fetch_duration = 0
        
        # Thread pool for concurrent requests (persistently reused)
        self._max_workers = min(len(etf_codes), 10) if etf_codes else 1
        self._executor: Optional[ThreadPoolExecutor] = None
    
    def start(self) -> None:
        """Start the fetcher thread."""
        if self._running:
            self._logger.warning("Fetcher already running")
            return
        
        # Ensure executor is ready before starting loop
        self._ensure_executor()

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self._thread.start()
        
        self._logger.info(
            f"Data fetcher started: {len(self._etf_codes)} ETFs, "
            f"{self._refresh_interval}s interval"
        )
    
    def stop(self) -> None:
        """Stop the fetcher thread gracefully."""
        if not self._running:
            return
        
        self._logger.info("Stopping data fetcher...")
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        # Shutdown executor to release threads
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            finally:
                self._executor = None
        
        self._logger.info("Data fetcher stopped")
    
    def pause(self) -> None:
        """Pause data fetching."""
        self._paused = True
        self._logger.info("Data fetcher paused")
    
    def resume(self) -> None:
        """Resume data fetching."""
        self._paused = False
        self._pause_event.set()
        self._logger.info("Data fetcher resumed")
    
    def update_etf_list(self, etf_codes: List[str]) -> None:
        """
        Update ETF codes list.
        
        Args:
            etf_codes: New list of ETF codes
        """
        self._etf_codes = etf_codes.copy()
        self._max_workers = min(len(etf_codes), 10) if etf_codes else 1
        self._ensure_executor()
        self._logger.info(f"Updated ETF list: {len(etf_codes)} codes")
    
    def update_refresh_interval(self, interval: int) -> None:
        """
        Update refresh interval.
        
        Args:
            interval: New refresh interval in seconds
        """
        self._refresh_interval = interval
        self._logger.info(f"Updated refresh interval: {interval}s")
    
    def trigger_refresh(self) -> None:
        """Trigger immediate refresh (manual refresh)."""
        if self._running and not self._paused:
            self._pause_event.set()
            self._logger.info("Manual refresh triggered")
    
    def _fetch_loop(self) -> None:
        """Main fetch loop running in background thread."""
        while self._running:
            try:
                # Pause handling
                if self._paused:
                    self._logger.debug("Fetcher paused, waiting...")
                    self._pause_event.wait()
                    self._pause_event.clear()
                    if not self._running:
                        break
                    continue
                
                # Trading time check
                trading = is_trading_time()
                if not trading:
                    wait_interval = 60
                    trading_status = get_next_trading_time()
                    self._logger.info(f"[闭市检测] {trading_status}，停止API调用，等待{wait_interval}秒")
                    if self._stop_event.wait(timeout=wait_interval):
                        break
                    continue
                
                # Perform fetch cycle
                start_time = time.time()
                self._fetch_all_quotes()
                duration = time.time() - start_time
                self._last_fetch_time = start_time
                self._last_fetch_duration = duration
                self._logger.debug(f"Fetch completed in {duration:.2f}s ({len(self._etf_codes)} ETFs)")
                
                # Wait for next interval or stop event
                if self._stop_event.wait(timeout=self._refresh_interval):
                    break
                    
            except Exception as e:
                self._logger.error(f"Error in fetch loop: {e}", exc_info=True)
                # Continue running despite errors
                time.sleep(1)
    
    def _fetch_all_quotes(self) -> None:
        """Fetch quotes for all ETF codes concurrently."""
        if not self._etf_codes:
            return
        
        # Ensure executor exists and submit tasks
        self._ensure_executor()
        future_to_code = {
            self._executor.submit(self._fetch_single_quote, code): code
            for code in self._etf_codes
        }
        
        quotes = {}
        changed_codes = []
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                quote = future.result()
                if quote:
                    quotes[code] = quote
                    if self._cache_manager.update(quote):
                        changed_codes.append(code)
            except Exception as e:
                self._logger.error(f"Error fetching {code}: {e}")
        
        # Invoke callback if data was fetched successfully
        if quotes and self._data_callback:
            try:
                self._logger.info(
                    f"[数据回调] 成功获取 {len(quotes)} 个ETF数据，"
                    f"其中 {len(changed_codes)} 个有变化"
                )
                if changed_codes:
                    self._logger.info(f"[数据回调] 变化的ETF: {', '.join(changed_codes)}")
                self._data_callback(quotes, changed_codes)
            except Exception as e:
                self._logger.error(f"[数据回调] 回调函数执行异常: {e}")
        elif not quotes:
            # 本轮一个都没成功，主动触发接口切换（若有备用）
            try:
                if self._backup_adapters and self._current_adapter_index < len(self._backup_adapters) - 1:
                    self._logger.warning("[接口切换] 当前接口本轮无数据，尝试切换到下一个备用接口")
                    self._switch_to_next_backup()
                else:
                    # 没有可切换的备用接口或已在最后一个备用接口
                    self._logger.warning("[接口切换] 当前接口本轮无数据，暂无可用备用接口")
            except Exception as e:
                self._logger.error(f"[接口切换] 自动切换失败: {e}")

    def _ensure_executor(self) -> None:
        """Ensure the persistent ThreadPoolExecutor is initialized with current max_workers."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="fetcher")
            return
        # Recreate executor if worker count changed
        try:
            if getattr(self._executor, "_max_workers", self._max_workers) != self._max_workers:
                self._executor.shutdown(wait=False, cancel_futures=True)
                self._executor = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="fetcher")
        except Exception:
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="fetcher")
    
    def _fetch_single_quote(self, code: str) -> Optional[ETFQuote]:
        """
        Fetch quote for single ETF code with retry logic and request-level caching.

        Implements:
        - Request-level cache check (prevents duplicate API calls within TTL window)
        - Exponential backoff retry logic
        - Incremental update detection

        Args:
            code: ETF code

        Returns:
            ETFQuote object or None if failed
        """
        # Check request-level cache first
        if not self._cache_manager.should_fetch(code):
            cached_quote = self._cache_manager.get_request_cached(code)
            if cached_quote:
                self._logger.debug(f"[Request Cache] Using cached data for {code}")
                return cached_quote

        # Fetch with exponential backoff retry
        for attempt in range(self._retry_count + 1):
            try:
                quote = self._current_adapter.fetch_quote(code)

                if quote:
                    # Success - reset failure tracking
                    if self._consecutive_failures > 0:
                        self._consecutive_failures = 0

                    # Try to switch back to higher priority adapter after 5 minutes
                    if self._current_adapter_index >= 0:
                        self._try_switch_to_higher_priority()

                    return quote

                # No data returned, will retry with exponential backoff
                if attempt < self._retry_count:
                    # Exponential backoff: base_interval * (2 ^ attempt) with jitter
                    backoff_time = self._retry_interval * (2 ** attempt)
                    # Add jitter (±20%) to prevent thundering herd
                    import random
                    jitter = backoff_time * 0.2 * (random.random() * 2 - 1)
                    wait_time = backoff_time + jitter

                    self._logger.debug(
                        f"[Retry] {code} attempt {attempt + 1}/{self._retry_count}, "
                        f"waiting {wait_time:.2f}s (exponential backoff)"
                    )
                    time.sleep(wait_time)
                    
            except Exception as e:
                # 减少403错误的日志频率
                if '403' in str(e):
                    if not hasattr(self, '_last_403_log') or \
                       time.time() - self._last_403_log > 60:  # 1分钟记录一次
                        self._logger.debug(f"Attempt {attempt + 1} failed for {code}: {e}")
                        self._last_403_log = time.time()
                else:
                    self._logger.debug(f"Attempt {attempt + 1} failed for {code}: {e}")
                    
                if attempt < self._retry_count:
                    time.sleep(self._retry_interval)
        
        # All retries failed
        self._handle_fetch_failure(code)
        return None
    
    def _handle_fetch_failure(self, code: str) -> None:
        """
        Handle fetch failure with failover logic.
        
        Args:
            code: Failed ETF code
        """
        # Increment cache error count
        self._cache_manager.increment_error(code)
        
        # Track consecutive failures
        self._consecutive_failures += 1
        
        # Check if failover needed
        if self._consecutive_failures >= self._failover_threshold:
            # Try to switch to next available backup adapter
            if self._current_adapter_index < len(self._backup_adapters) - 1:
                self._logger.warning(
                    f"Current API failed {self._consecutive_failures} times, "
                    "switching to next backup"
                )
                self._switch_to_next_backup()
            else:
                # 减少日志频率，避免刷屏
                if not hasattr(self, '_last_all_exhausted_log') or \
                   time.time() - self._last_all_exhausted_log > 300:  # 5分钟记录一次
                    self._logger.error(
                        f"All adapters exhausted, staying with current adapter"
                    )
                    self._last_all_exhausted_log = time.time()
    
    def _switch_to_next_backup(self) -> None:
        """
        Switch to next backup API adapter in priority order.
        
        Priority order: Primary -> Backup[0] -> Backup[1] -> Backup[2]
        """
        if not self._backup_adapters:
            self._logger.error("[接口切换] 无备用接口可用")
            return
        
        # Increment to next backup adapter
        old_index = self._current_adapter_index
        self._current_adapter_index += 1
        
        # Ensure we don't exceed available backups
        if self._current_adapter_index >= len(self._backup_adapters):
            self._current_adapter_index = len(self._backup_adapters) - 1
            self._logger.warning("[接口切换] 已使用最后一个备用接口，无法继续切换")
            return
        
        # Switch to next backup
        old_adapter_name = self._current_adapter.__class__.__name__
        self._current_adapter = self._backup_adapters[self._current_adapter_index]
        self._last_failover_time = time.time()
        self._consecutive_failures = 0
        
        adapter_name = self._current_adapter.__class__.__name__
        self._logger.warning(
            f"[接口切换] {old_adapter_name} → {adapter_name} "
            f"(优先级: {old_index} → {self._current_adapter_index})"
        )
    
    def _try_switch_to_higher_priority(self) -> None:
        """
        Try to switch back to higher priority adapter after cooldown period.
        
        Will try to switch back in reverse priority order:
        Backup[2] -> Backup[1] -> Backup[0] -> Primary
        """
        # Only try every 5 minutes
        time_since_failover = time.time() - self._last_failover_time
        if time_since_failover < 300:
            return
        
        if not self._etf_codes:
            return
        
        # Test next higher priority adapter
        test_code = self._etf_codes[0]
        target_index = self._current_adapter_index - 1
        
        # Determine which adapter to test
        if target_index >= 0:
            test_adapter = self._backup_adapters[target_index]
            adapter_type = "backup"
        else:
            test_adapter = self._primary_adapter
            adapter_type = "primary"
        
        test_adapter_name = test_adapter.__class__.__name__
        self._logger.info(f"[接口恢复] 尝试切回上一级接口 {adapter_type}[{target_index}]: {test_adapter_name}")
        
        try:
            quote = test_adapter.fetch_quote(test_code)
            if quote:
                # Higher priority adapter is working again
                old_adapter_name = self._current_adapter.__class__.__name__
                self._current_adapter = test_adapter
                self._current_adapter_index = target_index
                self._last_failover_time = time.time()
                
                self._logger.info(
                    f"[接口恢复] 成功切回 {adapter_type}[{target_index}]: "
                    f"{old_adapter_name} → {test_adapter_name}"
                )
        except Exception as e:
            # Higher priority adapter still failing, will try again later
            self._logger.info(
                f"[接口恢复] 上一级接口 {adapter_type}[{target_index}] 仍不可用: {e}，"
                f"将在5分钟后重试"
            )
    
    def get_status(self) -> dict:
        """
        Get fetcher status information.
        
        Returns:
            Dictionary with status information
        """
        # Determine adapter type
        if self._current_adapter_index < 0:
            adapter_type = "primary"
        else:
            adapter_type = f"backup[{self._current_adapter_index}]"
        
        return {
            'running': self._running,
            'paused': self._paused,
            'etf_count': len(self._etf_codes),
            'refresh_interval': self._refresh_interval,
            'adapter_index': self._current_adapter_index,
            'adapter_type': adapter_type,
            'current_adapter': self._current_adapter.__class__.__name__,
            'consecutive_failures': self._consecutive_failures,
            'last_fetch_time': self._last_fetch_time,
            'last_fetch_duration': self._last_fetch_duration,
        }

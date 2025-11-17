"""
Cache manager for ETF quote data with change detection and expiration.

Provides thread-safe in-memory caching with automatic staleness detection.
"""

from typing import Dict, List, Optional, Tuple
from threading import Lock
from datetime import datetime
import time

from .models import ETFQuote, ETFCache
from ..utils.logger import get_logger


class CacheManager:
    """
    Thread-safe cache manager for ETF quotes.

    Features:
    - In-memory dictionary storage
    - Change detection (price, change_percent)
    - Stale data detection
    - Request-level caching (prevents duplicate API calls)
    - Thread-safe operations
    - Cache statistics and monitoring
    """

    def __init__(self, cache_expire_seconds: int = 300, request_cache_ttl_ms: int = 300):
        """
        Initialize cache manager.

        Args:
            cache_expire_seconds: Data expiration time in seconds (default 5 minutes)
            request_cache_ttl_ms: Request-level cache TTL in milliseconds (default 300ms)
                                  Prevents duplicate API calls within this window
        """
        self._cache: Dict[str, ETFCache] = {}
        self._lock = Lock()
        self._cache_expire_seconds = cache_expire_seconds
        self._request_cache_ttl_ms = request_cache_ttl_ms
        self._logger = get_logger(__name__)

        # Request-level cache: {code: (timestamp_ms, quote)}
        # Prevents duplicate API calls within short time window
        self._request_cache: Dict[str, Tuple[float, Optional[ETFQuote]]] = {}

        # Statistics
        self._stats = {
            'total_updates': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'request_cache_hits': 0,
            'changes_detected': 0
        }
    
    def should_fetch(self, code: str) -> bool:
        """
        Check if we should fetch new data for this code.
        Uses request-level cache to prevent duplicate API calls within TTL window.

        Args:
            code: ETF code

        Returns:
            True if should fetch, False if recent data exists in request cache
        """
        with self._lock:
            if code in self._request_cache:
                timestamp_ms, _ = self._request_cache[code]
                age_ms = (time.time() * 1000) - timestamp_ms

                if age_ms < self._request_cache_ttl_ms:
                    self._stats['request_cache_hits'] += 1
                    self._logger.debug(
                        f"[Request Cache Hit] {code} - age: {age_ms:.0f}ms < {self._request_cache_ttl_ms}ms"
                    )
                    return False

            return True

    def get_request_cached(self, code: str) -> Optional[ETFQuote]:
        """
        Get data from request-level cache if available and fresh.

        Args:
            code: ETF code

        Returns:
            ETFQuote from request cache or None if not available/stale
        """
        with self._lock:
            if code in self._request_cache:
                timestamp_ms, quote = self._request_cache[code]
                age_ms = (time.time() * 1000) - timestamp_ms

                if age_ms < self._request_cache_ttl_ms:
                    return quote

            return None

    def update(self, quote: ETFQuote) -> bool:
        """
        Update cache with new quote data.
        Also updates request-level cache.

        Args:
            quote: ETF quote data

        Returns:
            True if data changed, False otherwise
        """
        with self._lock:
            code = quote.code
            self._stats['total_updates'] += 1

            # Update request-level cache
            self._request_cache[code] = (time.time() * 1000, quote)

            # Get or create cache entry
            if code not in self._cache:
                self._cache[code] = ETFCache()
                self._logger.debug(f"Created cache entry for {code}")
                self._stats['cache_misses'] += 1
            else:
                self._stats['cache_hits'] += 1

            # Update cache and detect changes
            changed = self._cache[code].update(quote)

            if changed:
                self._stats['changes_detected'] += 1
                self._logger.info(
                    f"[缓存更新] {code} 价格变化: {quote.name} {quote.price} ({quote.change_percent:+.2f}%)"
                )
            else:
                self._logger.debug(
                    f"[缓存更新] {code} 无变化: {quote.price} ({quote.change_percent:+.2f}%)"
                )

            return changed
    
    def get(self, code: str) -> Optional[ETFQuote]:
        """
        Get cached quote data by code.
        
        Args:
            code: ETF code
            
        Returns:
            ETFQuote object or None if not found
        """
        with self._lock:
            if code in self._cache:
                return self._cache[code].data
            return None
    
    def get_all(self) -> Dict[str, ETFQuote]:
        """
        Get all cached quote data.
        
        Returns:
            Dictionary mapping code to ETFQuote
        """
        with self._lock:
            return {
                code: cache.data
                for code, cache in self._cache.items()
                if cache.has_data()
            }
    
    def get_changed(self) -> List[str]:
        """
        Get list of codes that have changed since last check.
        
        Returns:
            List of ETF codes with changed data
        """
        with self._lock:
            changed_codes = [
                code for code, cache in self._cache.items()
                if cache.changed
            ]
            
            # Reset changed flags
            for code in changed_codes:
                self._cache[code].changed = False
            
            return changed_codes
    
    def is_stale(self, code: str) -> bool:
        """
        Check if cached data is stale.
        
        Args:
            code: ETF code
            
        Returns:
            True if data is stale or doesn't exist
        """
        with self._lock:
            if code not in self._cache:
                return True
            
            return self._cache[code].is_stale(self._cache_expire_seconds)
    
    def get_error_count(self, code: str) -> int:
        """
        Get consecutive error count for code.
        
        Args:
            code: ETF code
            
        Returns:
            Error count (0 if not found)
        """
        with self._lock:
            if code in self._cache:
                return self._cache[code].error_count
            return 0
    
    def increment_error(self, code: str) -> None:
        """
        Increment error count for code.
        
        Args:
            code: ETF code
        """
        with self._lock:
            if code not in self._cache:
                self._cache[code] = ETFCache()
            
            self._cache[code].increment_error()
            self._logger.warning(
                f"Error count for {code}: {self._cache[code].error_count}"
            )
    
    def clear_errors(self, code: str) -> None:
        """
        Clear error count for code.
        
        Args:
            code: ETF code
        """
        with self._lock:
            if code in self._cache:
                self._cache[code].error_count = 0
    
    def remove(self, code: str) -> None:
        """
        Remove code from cache.
        
        Args:
            code: ETF code
        """
        with self._lock:
            if code in self._cache:
                del self._cache[code]
                self._logger.debug(f"Removed {code} from cache")
    
    def clear(self) -> None:
        """Clear all cache data."""
        with self._lock:
            self._cache.clear()
            self._logger.info("Cache cleared")
    
    def cleanup_stale(self) -> int:
        """
        Remove stale entries from cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            stale_codes = [
                code for code, cache in self._cache.items()
                if cache.is_stale(self._cache_expire_seconds)
            ]
            
            for code in stale_codes:
                del self._cache[code]
            
            if stale_codes:
                self._logger.info(f"Removed {len(stale_codes)} stale cache entries")
            
            return len(stale_codes)
    
    def cleanup_request_cache(self) -> int:
        """
        Remove expired entries from request-level cache.

        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time_ms = time.time() * 1000
            expired_codes = [
                code for code, (timestamp_ms, _) in self._request_cache.items()
                if (current_time_ms - timestamp_ms) > self._request_cache_ttl_ms
            ]

            for code in expired_codes:
                del self._request_cache[code]

            if expired_codes:
                self._logger.debug(f"Cleaned up {len(expired_codes)} expired request cache entries")

            return len(expired_codes)

    def get_cache_stats(self) -> dict:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary with cache statistics including:
            - total_entries: Total cache entries
            - entries_with_data: Entries with valid data
            - stale_entries: Entries with stale data
            - entries_with_errors: Entries with errors
            - request_cache_size: Request-level cache size
            - total_updates: Total update operations
            - cache_hits: Cache hit count
            - cache_misses: Cache miss count
            - request_cache_hits: Request cache hit count
            - changes_detected: Number of changes detected
            - hit_rate: Cache hit rate percentage
        """
        with self._lock:
            total_entries = len(self._cache)
            entries_with_data = sum(1 for cache in self._cache.values() if cache.has_data())
            stale_entries = sum(
                1 for cache in self._cache.values()
                if cache.is_stale(self._cache_expire_seconds)
            )
            entries_with_errors = sum(
                1 for cache in self._cache.values() if cache.error_count > 0
            )

            total_cache_ops = self._stats['cache_hits'] + self._stats['cache_misses']
            hit_rate = (self._stats['cache_hits'] / total_cache_ops * 100) if total_cache_ops > 0 else 0

            return {
                'total_entries': total_entries,
                'entries_with_data': entries_with_data,
                'stale_entries': stale_entries,
                'entries_with_errors': entries_with_errors,
                'request_cache_size': len(self._request_cache),
                'total_updates': self._stats['total_updates'],
                'cache_hits': self._stats['cache_hits'],
                'cache_misses': self._stats['cache_misses'],
                'request_cache_hits': self._stats['request_cache_hits'],
                'changes_detected': self._stats['changes_detected'],
                'hit_rate': round(hit_rate, 2)
            }


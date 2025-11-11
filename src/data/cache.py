"""
Cache manager for ETF quote data with change detection and expiration.

Provides thread-safe in-memory caching with automatic staleness detection.
"""

from typing import Dict, List, Optional
from threading import Lock
from datetime import datetime

from .models import ETFQuote, ETFCache
from ..utils.logger import get_logger


class CacheManager:
    """
    Thread-safe cache manager for ETF quotes.
    
    Features:
    - In-memory dictionary storage
    - Change detection (price, change_percent)
    - Stale data detection
    - Thread-safe operations
    """
    
    def __init__(self, cache_expire_seconds: int = 300):
        """
        Initialize cache manager.
        
        Args:
            cache_expire_seconds: Data expiration time in seconds (default 5 minutes)
        """
        self._cache: Dict[str, ETFCache] = {}
        self._lock = Lock()
        self._cache_expire_seconds = cache_expire_seconds
        self._logger = get_logger(__name__)
    
    def update(self, quote: ETFQuote) -> bool:
        """
        Update cache with new quote data.
        
        Args:
            quote: ETF quote data
            
        Returns:
            True if data changed, False otherwise
        """
        with self._lock:
            code = quote.code
            
            # Get or create cache entry
            if code not in self._cache:
                self._cache[code] = ETFCache()
                self._logger.debug(f"Created cache entry for {code}")
            
            # Update cache and detect changes
            changed = self._cache[code].update(quote)
            
            if changed:
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
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
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
            
            return {
                'total_entries': total_entries,
                'entries_with_data': entries_with_data,
                'stale_entries': stale_entries,
                'entries_with_errors': entries_with_errors
            }


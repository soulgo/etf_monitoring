"""
Data models for ETF quotes and cache structures.

Uses dataclasses for type-safe, immutable data structures with clear field definitions.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass(frozen=True)
class ETFQuote:
    """
    Immutable ETF quote data model.
    
    Attributes:
        code: ETF code (6-digit string, e.g., "512170")
        name: ETF name (e.g., "医疗ETF")
        price: Current price
        change: Price change amount
        change_percent: Price change percentage
        volume: Trading volume
        pre_close: Previous close price
        update_time: Update time string (HH:MM:SS)
        timestamp: Unix timestamp of data
    """
    code: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    pre_close: float
    update_time: str
    timestamp: float
    
    def __post_init__(self):
        if not self.code:
            raise ValueError("Invalid code")
        
        if not self.name:
            raise ValueError("ETF name cannot be empty")
    
    @property
    def is_up(self) -> bool:
        """Check if price is up."""
        return self.change_percent > 0
    
    @property
    def is_down(self) -> bool:
        """Check if price is down."""
        return self.change_percent < 0
    
    @property
    def is_flat(self) -> bool:
        """Check if price is unchanged."""
        return self.change_percent == 0


@dataclass
class ETFCache:
    """
    Mutable cache entry for ETF data with change tracking.
    
    Attributes:
        data: Current quote data
        prev_data: Previous quote data (for change detection)
        changed: Whether data has changed since last update
        last_update: Timestamp of last successful update
        error_count: Consecutive error count
    """
    data: Optional[ETFQuote] = None
    prev_data: Optional[ETFQuote] = None
    changed: bool = False
    last_update: float = 0.0
    error_count: int = 0
    
    def update(self, new_data: ETFQuote) -> bool:
        """
        Update cache with new data and detect changes.
        
        Args:
            new_data: New quote data
            
        Returns:
            True if data changed, False otherwise
        """
        # Save previous data
        self.prev_data = self.data
        
        # Detect if price or change_percent has changed
        if self.data is None:
            self.changed = True
        else:
            self.changed = (
                abs(self.data.price - new_data.price) > 0.001 or
                abs(self.data.change_percent - new_data.change_percent) > 0.01
            )
        
        # Update current data
        self.data = new_data
        self.last_update = new_data.timestamp
        self.error_count = 0  # Reset error count on successful update
        
        return self.changed
    
    def increment_error(self) -> None:
        """Increment consecutive error count."""
        self.error_count += 1
    
    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """
        Check if cache data is stale.
        
        Args:
            max_age_seconds: Maximum age in seconds (default 5 minutes)
            
        Returns:
            True if data is older than max_age_seconds
        """
        if self.last_update == 0:
            return True
        
        current_time = datetime.now().timestamp()
        age = current_time - self.last_update
        return age > max_age_seconds
    
    def has_data(self) -> bool:
        """Check if cache contains valid data."""
        return self.data is not None


"""
Circuit breaker pattern implementation for API fault tolerance.

Prevents cascading failures by temporarily blocking requests to failing services.
"""

import time
from enum import Enum
from typing import Optional, Callable, Any
from threading import Lock
from ..utils.logger import get_logger


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Too many failures, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for API calls.
    
    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, requests are blocked immediately
    - HALF_OPEN: After timeout, allow limited requests to test recovery
    
    Configuration:
    - failure_threshold: Number of failures before opening circuit
    - success_threshold: Number of successes in HALF_OPEN to close circuit
    - timeout: Seconds to wait before trying HALF_OPEN state
    - window_size: Time window for counting failures (seconds)
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        if breaker.can_execute():
            try:
                result = api_call()
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise
        else:
            # Circuit is open, skip the call
            return None
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        window_size: int = 120
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Failures needed to open circuit
            success_threshold: Successes needed to close circuit from HALF_OPEN
            timeout: Seconds before trying HALF_OPEN
            window_size: Time window for counting failures (seconds)
        """
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._timeout = timeout
        self._window_size = window_size
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0
        self._opened_at = 0
        
        self._lock = Lock()
        self._logger = get_logger(__name__)
    
    def can_execute(self) -> bool:
        """
        Check if request can be executed.
        
        Returns:
            True if request should proceed, False if blocked
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                # Check if timeout elapsed
                if time.time() - self._opened_at >= self._timeout:
                    self._logger.info("[Circuit Breaker] Transitioning to HALF_OPEN state")
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    return True
                return False
            
            # HALF_OPEN state - allow limited requests
            return True
    
    def record_success(self) -> None:
        """Record successful request."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._logger.debug(
                    f"[Circuit Breaker] Success in HALF_OPEN: "
                    f"{self._success_count}/{self._success_threshold}"
                )
                
                if self._success_count >= self._success_threshold:
                    self._logger.info("[Circuit Breaker] Closing circuit after successful recovery")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0
    
    def record_failure(self) -> None:
        """Record failed request."""
        with self._lock:
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._logger.warning("[Circuit Breaker] Failure in HALF_OPEN, reopening circuit")
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                self._success_count = 0
                return
            
            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                self._logger.debug(
                    f"[Circuit Breaker] Failure recorded: "
                    f"{self._failure_count}/{self._failure_threshold}"
                )
                
                if self._failure_count >= self._failure_threshold:
                    self._logger.warning(
                        f"[Circuit Breaker] Opening circuit after {self._failure_count} failures"
                    )
                    self._state = CircuitState.OPEN
                    self._opened_at = time.time()

    def get_state(self) -> CircuitState:
        """
        Get current circuit state.

        Returns:
            Current CircuitState
        """
        with self._lock:
            return self._state

    def reset(self) -> None:
        """Reset circuit breaker to CLOSED state."""
        with self._lock:
            self._logger.info("[Circuit Breaker] Manual reset to CLOSED state")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._opened_at = 0

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with circuit breaker stats
        """
        with self._lock:
            return {
                'state': self._state.value,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'failure_threshold': self._failure_threshold,
                'success_threshold': self._success_threshold,
                'timeout': self._timeout,
                'opened_at': self._opened_at,
                'time_until_half_open': max(0, self._timeout - (time.time() - self._opened_at))
                    if self._state == CircuitState.OPEN else 0
            }


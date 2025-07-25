"""
Simple Circuit Breaker Pattern for API Resilience
Prevents cascading failures when external services (like Zep) are down
"""

import time
import logging
from typing import Callable, Any, Optional
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Service is down, reject requests  
    HALF_OPEN = "half_open" # Testing if service is back up


class CircuitBreaker:
    """
    Simple circuit breaker implementation for external API calls
    """
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        timeout: int = 60,
        recovery_timeout: int = 30,
        expected_exception: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.last_attempt_time = None
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN - not executing call")
        
        try:
            self.last_attempt_time = time.time()
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful function execution"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker SUCCESS in HALF_OPEN - resetting to CLOSED")
            self.state = CircuitState.CLOSED
        
        self.failure_count = 0
        self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed function execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
        else:
            logger.debug(f"Circuit breaker failure count: {self.failure_count}/{self.failure_threshold}")
    
    def is_open(self) -> bool:
        """Check if circuit breaker is currently open"""
        return self.state == CircuitState.OPEN
    
    def get_state(self) -> dict:
        """Get current circuit breaker state for monitoring"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "last_attempt_time": self.last_attempt_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and call is rejected"""
    pass


def circuit_breaker_decorator(
    failure_threshold: int = 5,
    timeout: int = 60,
    recovery_timeout: int = 30,
    expected_exception: tuple = (Exception,),
    circuit_name: str = "default"
):
    """
    Decorator to apply circuit breaker pattern to functions
    """
    # Store circuit breakers by name to maintain state across calls
    if not hasattr(circuit_breaker_decorator, '_breakers'):
        circuit_breaker_decorator._breakers = {}
    
    if circuit_name not in circuit_breaker_decorator._breakers:
        circuit_breaker_decorator._breakers[circuit_name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            timeout=timeout,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = circuit_breaker_decorator._breakers[circuit_name]
            return breaker.call(func, *args, **kwargs)
        
        # Attach breaker reference for monitoring
        wrapper._circuit_breaker = circuit_breaker_decorator._breakers[circuit_name]
        return wrapper
    
    return decorator


def get_circuit_breaker_status(circuit_name: str = "default") -> Optional[dict]:
    """Get status of a named circuit breaker"""
    if (hasattr(circuit_breaker_decorator, '_breakers') and 
        circuit_name in circuit_breaker_decorator._breakers):
        return circuit_breaker_decorator._breakers[circuit_name].get_state()
    return None


def get_all_circuit_breaker_status() -> dict:
    """Get status of all circuit breakers"""
    if not hasattr(circuit_breaker_decorator, '_breakers'):
        return {}
    
    return {
        name: breaker.get_state() 
        for name, breaker in circuit_breaker_decorator._breakers.items()
    }
# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Cache Utilities
Implements request coalescing (singleflight) pattern to prevent cache stampedes.
"""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Dict, Tuple

# Global lock registry for singleflight
_locks: Dict[str, asyncio.Lock] = {}
_results: Dict[str, Tuple[Any, asyncio.Event]] = {}  # key -> (result, event)
_registry_lock = asyncio.Lock()


def single_flight(key_builder: Callable[..., str]):
    """
    Decorator to coalesce concurrent requests for the same resource.
    
    If multiple concurrent requests come in for the same key (as determined by key_builder),
    only the first one will execute the underlying function. The others will wait
    and return the result of the first execution.
    
    This is useful for preventing "dog-piling" or "cache stampedes" on expensive
    operations or external API calls.
    
    Args:
        key_builder: Function that takes the same arguments as the decorated function
                     and returns a unique string key.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = key_builder(*args, **kwargs)

            # Check if there's already a result or an in-progress request
            async with _registry_lock:
                if key in _results:
                    result, event = _results[key]
                    # Wait for the event to be set (request completed)
                    await event.wait()
                    return result

                # No result yet, create lock and event for this key
                if key not in _locks:
                    _locks[key] = asyncio.Lock()
                lock = _locks[key]
                event = asyncio.Event()
                # Reserve the spot with a placeholder
                _results[key] = (None, event)

            # Try to acquire lock - first one wins and executes
            acquired = lock.locked()
            async with lock:
                # Check if we're the first request or a waiter
                if acquired:
                    # We waited for another request, result should be ready
                    result, event = _results[key]
                    return result
                else:
                    # We're the first request, execute the function
                    try:
                        result = await func(*args, **kwargs)
                        # Store result and signal waiters
                        async with _registry_lock:
                            _results[key] = (result, event)
                        event.set()
                        return result
                    except Exception as e:
                        # On error, clean up and propagate
                        async with _registry_lock:
                            if key in _results:
                                del _results[key]
                            if key in _locks:
                                del _locks[key]
                        event.set()  # Unblock waiters
                        raise e

        return wrapper
    return decorator

import functools
import time
import logging
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """
    A simple cache manager that uses a dictionary to store cached results.
    Supports:
        - Time-based expiration
        - Function result caching using a decorator
    Enhancements:
        - Added support for custom key generation functions.
        - Added a max_size parameter to limit the cache size and implement a basic eviction policy (LRU).
        - Added a lock to ensure thread safety.
        - Improved logging for debugging purposes.
    """

    def __init__(self, default_expiration: int = 60, max_size: int = 128):
        """
        Initializes the CacheManager.

        Args:
            default_expiration: The default expiration time in seconds for cached items.
            max_size: The maximum number of items to store in the cache.  When the cache is full,
                      the least recently used item is evicted.
        """
        self.cache: Dict[Any, Any] = {}  # key: (value, expiration_time, last_used)
        self.default_expiration = default_expiration
        self.max_size = max_size
        self._lock = functools.lru_cache(maxsize=1)(lambda: __import__('threading').Lock()) # Lazy load threading only if needed
        self.hits = 0
        self.misses = 0

    def get(self, key: Any) -> Any:
        """
        Retrieves a value from the cache.

        Args:
            key: The key of the item to retrieve.

        Returns:
            The value if found and not expired, otherwise None.
        """
        with self._lock():
            if key in self.cache:
                value, expiration_time, last_used = self.cache[key]
                if expiration_time is None or expiration_time > time.time():
                    # Update last used time
                    self.cache[key] = (value, expiration_time, time.time())
                    self.hits += 1
                    logger.debug(f"Cache hit for key: {key}")
                    return value
                else:
                    # Remove expired item
                    del self.cache[key]
                    self.misses += 1
                    logger.debug(f"Cache expired for key: {key}")
                    return None
            else:
                self.misses += 1
                logger.debug(f"Cache miss for key: {key}")
                return None

    def set(self, key: Any, value: Any, expiration: Optional[int] = None) -> None:
        """
        Adds a value to the cache.

        Args:
            key: The key of the item to add.
            value: The value of the item to add.
            expiration: The expiration time in seconds. If None, uses the default expiration.
        """
        with self._lock():
            if expiration is None:
                expiration_time = None
            else:
                expiration_time = time.time() + expiration

            self.cache[key] = (value, expiration_time, time.time())
            logger.debug(f"Cache set for key: {key} with expiration: {expiration}")

            # Enforce max size
            self._enforce_max_size()

    def delete(self, key: Any) -> None:
        """
        Removes an item from the cache.

        Args:
            key: The key of the item to remove.
        """
        with self._lock():
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache delete for key: {key}")

    def clear(self) -> None:
        """
        Clears the entire cache.
        """
        with self._lock():
            self.cache.clear()
            logger.debug("Cache cleared")

    def _enforce_max_size(self):
        """
        Enforces the maximum size of the cache by evicting the least recently used item.
        """
        if len(self.cache) > self.max_size:
            # Find the least recently used item
            lru_key = None
            lru_time = time.time() + 1  # Initialize to future time to ensure first item is always smaller
            for key, (value, expiration_time, last_used) in self.cache.items():
                if last_used < lru_time:
                    lru_time = last_used
                    lru_key = key

            # Evict the LRU item
            if lru_key:
                del self.cache[lru_key]
                logger.debug(f"Cache eviction for key: {lru_key} due to max size limit")

    def cache_result(self, expiration: Optional[int] = None, key_func: Optional[Callable[..., Any]] = None):
        """
        A decorator to cache the result of a function.

        Args:
            expiration: The expiration time in seconds. If None, uses the default expiration.
            key_func: A function that takes the same arguments as the decorated function and returns a cache key.
                      If None, the arguments themselves are used as the key.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Generate the cache key
                if key_func:
                    key = key_func(*args, **kwargs)
                else:
                    key = (func.__name__, args, tuple(sorted(kwargs.items())))  # Include function name and sort kwargs for consistent key

                # Try to retrieve the result from the cache
                result = self.get(key)
                if result is not None:
                    return result

                # If not in cache, call the function and cache the result
                result = func(*args, **kwargs)
                self.set(key, result, expiration)
                return result

            return wrapper

        return decorator

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Returns cache statistics.
        """
        with self._lock():
            size = len(self.cache)
            return {"size": size, "hits": self.hits, "misses": self.misses, "max_size": self.max_size}
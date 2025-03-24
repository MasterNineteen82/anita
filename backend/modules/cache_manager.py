import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Union
import time
import json

# Import centralized models
from backend.models import (
    SuccessResponse, ErrorResponse
)
from backend.models import CacheItem, CacheStats, CachePolicy  # Import CacheItem
from backend.utils.utils import Singleton



# Configure logging
logger = logging.getLogger(__name__)

# Determine if cache service is available (replace with actual check)
CACHE_SERVICE_AVAILABLE = os.environ.get('CACHE_SERVICE', 'True').lower() == 'true'

# Simulation mode
SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'

class CacheManager(metaclass=Singleton):
    """Manager for caching data"""
    
    def __init__(self, default_ttl: int = 300):
        self.cache: Dict[str, CacheItem] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
        self.cache_policy = CachePolicy(max_size=1000, eviction_policy="LRU")  # Example policy
        self.load_cache_from_env()

    def load_cache_from_env(self):
        """Load initial cache data from environment variable."""
        cache_data_json = os.environ.get("CACHE_DATA")
        if cache_data_json:
            try:
                cache_data = json.loads(cache_data_json)
                if isinstance(cache_data, dict):
                    for key, value in cache_data.items():
                        self.set(key, value)
                    logger.info("Cache loaded from environment variable.")
            except json.JSONDecodeError:
                logger.error("Failed to decode CACHE_DATA environment variable.")

    def get(self, key: str) -> Optional[Any]:
        item = self.cache.get(key)
        if item:
            if item.expiry is None or item.expiry > time.time():
                self.hits += 1
                logger.debug(f"Cache hit for key: {key}")
                return item.value
            else:
                self.delete(key)  # Automatically remove expired item
                self.misses += 1
                logger.debug(f"Cache expired for key: {key}")
                return None
        else:
            self.misses += 1
            logger.debug(f"Cache miss for key: {key}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        expiry = time.time() + (ttl or self.default_ttl) if ttl is not None else None
        new_item = CacheItem(key=key, value=value, expiry=expiry)
        self.cache[key] = new_item
        logger.debug(f"Cache set for key: {key} with TTL: {ttl}")
        self.enforce_cache_policy()

    def delete(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache delete for key: {key}")
            return True
        return False

    def clear(self):
        self.cache.clear()
        logger.debug("Cache cleared")

    def get_keys(self):
        return list(self.cache.keys())

    def get_stats(self) -> CacheStats:
        return CacheStats(
            size=len(self.cache),
            hits=self.hits,
            misses=self.misses,
            policy=self.cache_policy
        )

    def enforce_cache_policy(self):
        """Enforce the cache eviction policy if the cache exceeds max_size."""
        if len(self.cache) > self.cache_policy.max_size:
            if self.cache_policy.eviction_policy == "LRU":
                # Sort cache items by last access (not implemented in this example)
                # For simplicity, just delete the oldest item
                oldest_key = next(iter(self.cache))
                self.delete(oldest_key)
                logger.info("Cache eviction (LRU): Removed oldest item.")
            else:
                logger.warning("Unknown cache eviction policy. No eviction performed.")
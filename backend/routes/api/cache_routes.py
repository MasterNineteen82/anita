from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

from backend.modules.cache_manager import CacheManager
from backend.models import CacheItem, CacheStats

router = APIRouter()

@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats(cache: CacheManager = Depends(CacheManager)):
    """Retrieve cache statistics."""
    return cache.get_stats()

@router.get("/cache/keys", response_model=List[str])
async def get_cache_keys(cache: CacheManager = Depends(CacheManager)):
    """Retrieve all cache keys."""
    return cache.get_keys()

@router.get("/cache/{key}", response_model=CacheItem)
async def get_cache_item(key: str, cache: CacheManager = Depends(CacheManager)):
    """Retrieve a specific item from the cache."""
    item = cache.get(key)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return CacheItem(key=key, value=item)

@router.post("/cache/{key}")
async def set_cache_item(key: str, value: Any, ttl: int = None, cache: CacheManager = Depends(CacheManager)):
    """Set a specific item in the cache."""
    cache.set(key, value, ttl)
    return {"message": f"Item '{key}' set in cache"}

@router.delete("/cache/{key}")
async def delete_cache_item(key: str, cache: CacheManager = Depends(CacheManager)):
    """Delete a specific item from the cache."""
    if not cache.delete(key):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": f"Item '{key}' deleted from cache"}

@router.delete("/cache")
async def clear_cache(cache: CacheManager = Depends(CacheManager)):
    """Clear the entire cache."""
    cache.clear()
    return {"message": "Cache cleared"}
"""Response caching layer.

Exact-hash match cache with TTL and LRU eviction.

Usage:
    cache = ResponseCache(max_size=500)
    cached = cache.get_exact(query)
    if cached:
        return cached
    # ... run full pipeline ...
    cache.put(query, response)
"""

import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    response: str
    timestamp: float
    hit_count: int = 0


class ResponseCache:
    """In-memory exact-match response cache with TTL and LRU eviction."""

    def __init__(self, max_size: int = 500, ttl_seconds: int = 86400):
        """
        Args:
            max_size: Maximum number of cached responses (>= 1).
            ttl_seconds: Time-to-live in seconds (>= 1, default: 24 hours).

        Raises:
            ValueError: If max_size or ttl_seconds is less than 1.
        """
        if max_size < 1:
            raise ValueError(f"max_size must be >= 1, got {max_size}")
        if ttl_seconds < 1:
            raise ValueError(f"ttl_seconds must be >= 1, got {ttl_seconds}")
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _hash_query(query: str) -> str:
        """Normalise and hash a query string."""
        normalised = query.lower().strip()
        return hashlib.sha256(normalised.encode()).hexdigest()

    def get_exact(self, query: str) -> str | None:
        """Check for an exact cache hit.

        Returns:
            Cached response string, or None on miss.
        """
        key = self._hash_query(query)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        if time.time() - entry.timestamp > self._ttl:
            del self._cache[key]
            self._misses += 1
            return None

        self._cache.move_to_end(key)
        entry.hit_count += 1
        self._hits += 1

        logger.debug("Cache HIT (exact) for query hash %s", key[:12])
        return entry.response

    def put(self, query: str, response: str) -> None:
        """Store a response in the cache."""
        key = self._hash_query(query)

        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(
            response=response,
            timestamp=time.time(),
        )

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total:.1%}" if total > 0 else "N/A",
        }

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

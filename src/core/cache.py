"""Response caching layer — session-scoped (FAB-2101 Sprint 3.2, D9).

Cache key is `(session_id, sha256(normalised_message))`. Two users asking the
same question in different sessions never see each other's answers; the same
user repeating a question within one session hits the cache.

Calling `get_exact` / `put` without a session_id is supported for
back-compatibility but bypasses session isolation (treats `""` as the
namespace). New callers should always pass a real session_id.
"""

from __future__ import annotations

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
    """In-memory session-scoped response cache with TTL and LRU eviction.

    LRU operates across the global entry set, not per session — a hot session
    naturally evicts colder ones. If that behaviour changes requirements,
    switch to a per-session OrderedDict map.
    """

    def __init__(self, max_size: int = 500, ttl_seconds: int = 86400):
        if max_size < 1:
            raise ValueError(f"max_size must be >= 1, got {max_size}")
        if ttl_seconds < 1:
            raise ValueError(f"ttl_seconds must be >= 1, got {ttl_seconds}")
        self._cache: OrderedDict[tuple[str, str], CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _hash_query(query: str) -> str:
        normalised = query.lower().strip()
        return hashlib.sha256(normalised.encode()).hexdigest()

    def _key(self, session_id: str | None, query: str) -> tuple[str, str]:
        return (session_id or "", self._hash_query(query))

    def get_exact(self, query: str, session_id: str | None = None) -> str | None:
        """Return a cached response or None on miss/expiry.

        A session_id of None is treated as the empty-string namespace.
        """
        key = self._key(session_id, query)
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
        logger.debug(
            "Cache HIT session=%s hash=%s", session_id or "(global)", key[1][:12]
        )
        return entry.response

    def put(self, query: str, response: str, session_id: str | None = None) -> None:
        """Store a response under (session_id, normalised_hash)."""
        key = self._key(session_id, query)
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[key] = CacheEntry(response=response, timestamp=time.time())

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total:.1%}" if total > 0 else "N/A",
        }

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0

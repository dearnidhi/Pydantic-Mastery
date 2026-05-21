"""
week7_production/cache.py
==========================
Simple response cache for AI agents.
Prevents re-calling the LLM for identical prompts.
In production: swap _store for Redis (redis-py) or Memcached.
"""

import hashlib
import time
import json
from typing import Any, Optional


class ResponseCache:
    """
    In-memory LRU-style cache for agent responses.

    Usage:
        cache = ResponseCache(ttl_seconds=300)
        key = cache.make_key("groq:llama-3.1-8b", "What is Python?")

        hit = cache.get(key)
        if hit is None:
            response = agent.run_sync(...)
            cache.set(key, response.data)
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 500):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._store: dict[str, dict] = {}
        self.hits = 0
        self.misses = 0

    def make_key(self, model: str, prompt: str, **extra_params) -> str:
        """Create a deterministic cache key from model + prompt."""
        payload = json.dumps(
            {"model": model, "prompt": prompt, **extra_params},
            sort_keys=True
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Return cached value if present and not expired."""
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        if time.time() - entry["timestamp"] > self.ttl:
            del self._store[key]  # expired
            self.misses += 1
            return None
        self.hits += 1
        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """Store a value. Evict oldest entry if at max capacity."""
        if len(self._store) >= self.max_size:
            # Evict oldest
            oldest_key = min(self._store, key=lambda k: self._store[k]["timestamp"])
            del self._store[oldest_key]
        self._store[key] = {"value": value, "timestamp": time.time()}

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def stats(self) -> dict:
        return {
            "size": len(self._store),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(self.hit_rate * 100, 1),
        }

    def __repr__(self) -> str:
        return f"ResponseCache(size={len(self._store)}, hit_rate={self.hit_rate:.1%})"

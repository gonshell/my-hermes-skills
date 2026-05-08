from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from weibo_cli import constants


class Cache:
    """Simple file-based cache with TTL support."""

    def __init__(self, ttl: int = 300) -> None:
        self.ttl = ttl
        cache_path = Path(os.path.expanduser(constants.CACHE_DIR))
        cache_path.mkdir(parents=True, exist_ok=True)
        self.cache_dir = cache_path

    def _key(self, key: str) -> str:
        """Hash key to safe filename."""
        return hashlib.sha256(key.encode()).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        """Get cached value, returns None if missing or expired."""
        cache_file = self.cache_dir / self._key(key)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                entry = json.load(f)

            # Check TTL
            if time.time() - entry["_ts"] > self.ttl:
                cache_file.unlink(missing_ok=True)
                return None

            return entry.get("data")
        except (json.JSONDecodeError, IOError, KeyError):
            return None

    def set(self, key: str, data: dict[str, Any]) -> None:
        """Set cached value with current timestamp."""
        cache_file = self.cache_dir / self._key(key)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"_ts": time.time(), "data": data}, f, ensure_ascii=False)
        except IOError:
            pass  # Cache write failure is non-fatal

    def clear(self) -> None:
        """Clear all cache entries."""
        for cache_file in self.cache_dir.glob("*"):
            cache_file.unlink(missing_ok=True)

"""Local file + in-memory cache for API responses, keyed by request signature."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Optional

from cachetools import TTLCache

from config import CACHE_DIR, settings


class CacheManager:
    _instance: Optional[CacheManager] = None
    _memory: TTLCache

    def __new__(cls) -> CacheManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._memory = TTLCache(
                maxsize=2048, ttl=settings.CACHE_TTL_SECONDS
            )
        return cls._instance

    @staticmethod
    def _key(namespace: str, params: dict) -> str:
        raw = json.dumps({"ns": namespace, **params}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, namespace: str, params: dict) -> Optional[dict]:
        key = self._key(namespace, params)
        if key in self._memory:
            return self._memory[key]
        disk_path = CACHE_DIR / f"{key}.json"
        if disk_path.exists():
            age = time.time() - disk_path.stat().st_mtime
            if age < settings.CACHE_TTL_SECONDS:
                data = json.loads(disk_path.read_text(encoding="utf-8"))
                self._memory[key] = data
                return data
            disk_path.unlink(missing_ok=True)
        return None

    def put(self, namespace: str, params: dict, data: dict) -> None:
        key = self._key(namespace, params)
        self._memory[key] = data
        disk_path = CACHE_DIR / f"{key}.json"
        disk_path.write_text(
            json.dumps(data, default=str), encoding="utf-8"
        )

    def invalidate(self, namespace: str, params: dict) -> None:
        key = self._key(namespace, params)
        self._memory.pop(key, None)
        disk_path = CACHE_DIR / f"{key}.json"
        disk_path.unlink(missing_ok=True)


def cache_api_call(namespace: str):
    """Decorator: cache the return value of an API function.

    The decorated function must accept keyword arguments that serve as
    the cache key components.
    """

    def decorator(func: Callable[..., dict]) -> Callable[..., dict]:
        def wrapper(**kwargs: Any) -> dict:
            cm = CacheManager()
            cached = cm.get(namespace, kwargs)
            if cached is not None:
                cached["_cached"] = True
                return cached
            result = func(**kwargs)
            if result:
                cm.put(namespace, kwargs, result)
            return result

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator

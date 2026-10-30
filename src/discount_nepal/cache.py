"""Thread-safe, TTL-based in-memory cache."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional


class TTLCache:
    """A simple in-memory cache with time-to-live expiration.

    All public methods are thread-safe. The cache holds a single payload and
    tracks when it was fetched. Consumers call :meth:`get` to read (and
    optionally reload) and :meth:`snapshot` for a read-only view.

    When a load is already in progress, :meth:`get` waits for it to complete
    instead of returning stale data or starting a duplicate load.
    """

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._data: Optional[Any] = None
        self._fetched_at: float = 0.0
        self._ready: bool = False
        self._loading: bool = False
        self._load_condition = threading.Condition(self._lock)

    def get(self, force: bool = False, loader: Callable[[], Any] | None = None) -> Any:
        """Return cached data, or (re)load via *loader* when stale/forced.

        If a load is already in progress, waits for it to complete and returns
        the fresh result. Avoids starting duplicate loads.
        """
        with self._load_condition:
            fresh = (
                self._ready
                and self._data is not None
                and time.time() - self._fetched_at < self._ttl
            )
            if fresh and not force:
                return self._data

            # Wait if a load is already in progress.
            if self._loading:
                if loader is None:
                    return self._data
                self._load_condition.wait_for(lambda: not self._loading)
                # After wait, data may have been refreshed by the other thread.
                # If it's now fresh, return it regardless of force (the other
                # thread already did the work).
                fresh = (
                    self._ready
                    and self._data is not None
                    and time.time() - self._fetched_at < self._ttl
                )
                if fresh:
                    return self._data

            if loader is None:
                return self._data

            self._loading = True

        # Load outside the lock to avoid blocking concurrent readers.
        try:
            data = loader()
        except Exception:
            with self._load_condition:
                self._loading = False
                self._load_condition.notify_all()
            raise

        with self._load_condition:
            self._data = data
            self._fetched_at = time.time()
            self._ready = True
            self._loading = False
            self._load_condition.notify_all()
        return data

    def snapshot(self) -> dict:
        """Return a read-only dict view of cache state."""
        with self._lock:
            return {
                "products": list(self._data or []),
                "fetched_at": self._fetched_at,
                "ready": self._ready,
                "loading": self._loading,
            }

    @property
    def ready(self) -> bool:
        with self._lock:
            return self._ready

    @property
    def data(self) -> list:
        with self._lock:
            return list(self._data or [])

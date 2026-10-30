"""Tests for the TTL cache."""

import sys
import threading
import time

sys.path.insert(0, "src")

from discount_nepal.cache import TTLCache


class TestTTLCache:
    def test_returns_loader_result(self):
        cache = TTLCache(ttl_seconds=60)
        assert cache.get(loader=lambda: [1, 2, 3]) == [1, 2, 3]

    def test_serves_from_cache_within_ttl(self):
        cache = TTLCache(ttl_seconds=60)
        calls = []

        def loader():
            calls.append(1)
            return ["data"]

        cache.get(loader=loader)
        cache.get(loader=loader)
        assert len(calls) == 1, "second read must not reload within TTL"

    def test_reloads_after_ttl_expires(self):
        cache = TTLCache(ttl_seconds=0)
        calls = []

        def loader():
            calls.append(1)
            return len(calls)

        cache.get(loader=loader)
        time.sleep(0.01)
        cache.get(loader=loader)
        assert len(calls) == 2, "expired entry must be reloaded"

    def test_force_bypasses_freshness(self):
        cache = TTLCache(ttl_seconds=60)
        calls = []

        def loader():
            calls.append(1)
            return len(calls)

        cache.get(loader=loader)
        cache.get(force=True, loader=loader)
        assert len(calls) == 2

    def test_snapshot_reports_state(self):
        cache = TTLCache(ttl_seconds=60)
        assert cache.snapshot()["ready"] is False
        cache.get(loader=lambda: ["x"])
        snap = cache.snapshot()
        assert snap["ready"] is True
        assert snap["products"] == ["x"]
        assert snap["fetched_at"] > 0

    def test_failed_load_does_not_poison_cache(self):
        cache = TTLCache(ttl_seconds=60)

        def loader():
            raise RuntimeError("scrape failed")

        try:
            cache.get(loader=loader)
        except RuntimeError:
            pass
        # A later load must still work and the cache must not report ready.
        assert cache.snapshot()["ready"] is False
        assert cache.get(loader=lambda: ["recovered"]) == ["recovered"]

    def test_concurrent_loaders_run_once(self):
        cache = TTLCache(ttl_seconds=60)
        calls = []
        lock = threading.Lock()

        def loader():
            with lock:
                calls.append(1)
            time.sleep(0.05)
            return ["once"]

        results = []
        threads = [
            threading.Thread(target=lambda: results.append(cache.get(loader=loader)))
            for _ in range(8)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(calls) == 1, "concurrent readers must share one load"
        assert all(r == ["once"] for r in results)

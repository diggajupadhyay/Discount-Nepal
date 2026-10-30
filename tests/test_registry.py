"""Tests for the store registry and product de-duplication."""

import sys

sys.path.insert(0, "src")

from discount_nepal.app import _dedupe_products
from discount_nepal.registry import REGISTRY, all_scrapers, get_scraper, list_stores


def _product(url: str, name: str = "Item", website: str = "Store") -> dict:
    return {
        "website": website,
        "name": name,
        "regular_price": "Rs. 1,000",
        "sale_price": "Rs. 800",
        "url": url,
        "image_url": "N/A",
        "timestamp": "2026-01-01T00:00:00+00:00",
    }


class TestRegistry:
    def test_known_store_resolves(self):
        assert get_scraper("dolpo") is not None
        assert get_scraper("sonamgear") is not None

    def test_unknown_store_returns_none(self):
        assert get_scraper("nonexistent-store") is None

    def test_all_scrapers_instantiates_every_registered_class(self):
        scrapers = all_scrapers()
        assert len(scrapers) == len(REGISTRY)
        assert all(s.store_name for s in scrapers)

    def test_list_stores_excludes_disabled(self):
        """Disabled stores (e.g. a rate-limited one) must not reach the UI."""
        disabled_keys = {key for key, cls in REGISTRY if not cls.enabled}
        assert disabled_keys, "expected at least one disabled store to exercise this"
        listed = {s["key"] for s in list_stores()}
        assert listed.isdisjoint(disabled_keys)
        for store in list_stores():
            assert set(store) == {"key", "name", "url"}


class TestDedupe:
    def test_duplicate_urls_are_removed(self):
        p = _product("https://x.com/p/1")
        assert len(_dedupe_products([p, dict(p)])) == 1

    def test_distinct_urls_are_kept(self):
        items = [_product("https://x.com/p/1"), _product("https://x.com/p/2")]
        assert len(_dedupe_products(items)) == 2

    def test_urlless_products_are_not_all_dropped(self):
        """A store with no URLs must still show its products (by name)."""
        items = [
            _product("N/A", name="Hat"),
            _product("N/A", name="Cap"),
        ]
        assert len(_dedupe_products(items)) == 2

    def test_urlless_duplicates_are_removed(self):
        items = [_product("N/A", name="Hat"), _product("N/A", name="Hat")]
        assert len(_dedupe_products(items)) == 1

    def test_same_name_from_different_stores_kept(self):
        items = [
            _product("N/A", name="Jacket", website="Store A"),
            _product("N/A", name="Jacket", website="Store B"),
        ]
        assert len(_dedupe_products(items)) == 2

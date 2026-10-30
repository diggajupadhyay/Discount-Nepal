"""Tests for the shared BaseScraper parsing/HTTP helpers."""

import sys

sys.path.insert(0, "src")

import requests
from bs4 import BeautifulSoup

from discount_nepal.scrapers.base import BaseScraper


def _tag(html: str):
    return BeautifulSoup(html, "html.parser").find()


class TestAttr:
    """_attr() must return a plain string for every BeautifulSoup shape."""

    def test_returns_string_attribute(self):
        tag = _tag('<a href="/product/1">x</a>')
        assert BaseScraper._attr(tag, "href") == "/product/1"

    def test_missing_attribute_returns_empty_string(self):
        tag = _tag("<a>x</a>")
        assert BaseScraper._attr(tag, "href") == ""

    def test_multi_valued_attribute_is_joined(self):
        # BeautifulSoup returns class as a list; the DOM serialises it
        # space-separated, so _attr must match that.
        tag = _tag('<div class="a b c">x</div>')
        assert BaseScraper._attr(tag, "class") == "a b c"

    def test_none_attribute_returns_empty_string(self):
        tag = _tag("<img src=''>")
        assert BaseScraper._attr(tag, "src") == ""


class TestRetryPolicy:
    """Only transient failures (network/429/5xx) may be retried."""

    @staticmethod
    def _exc_with_status(status: int | None) -> Exception:
        exc = requests.HTTPError("boom")
        if status is not None:
            response = requests.Response()
            response.status_code = status
            exc.response = response
        return exc

    def test_network_error_is_retryable(self):
        assert BaseScraper._is_retryable(self._exc_with_status(None)) is True

    def test_client_errors_are_not_retryable(self):
        # A 404/403 is a definitive answer — retrying only hammers the store.
        assert BaseScraper._is_retryable(self._exc_with_status(404)) is False
        assert BaseScraper._is_retryable(self._exc_with_status(403)) is False

    def test_server_errors_and_rate_limits_are_retryable(self):
        assert BaseScraper._is_retryable(self._exc_with_status(429)) is True
        assert BaseScraper._is_retryable(self._exc_with_status(500)) is True
        assert BaseScraper._is_retryable(self._exc_with_status(503)) is True


class TestUrlHelpers:
    def test_abs_resolves_relative(self):
        assert BaseScraper._abs("/p/1", "https://x.com") == "https://x.com/p/1"

    def test_abs_handles_missing(self):
        assert BaseScraper._abs("", "https://x.com") == "N/A"
        assert BaseScraper._abs("N/A", "https://x.com") == "N/A"

    def test_fix_protocol_upgrades_protocol_relative(self):
        assert BaseScraper._fix_protocol("//cdn.x.com/a.jpg") == "https://cdn.x.com/a.jpg"

    def test_fix_protocol_leaves_https_alone(self):
        assert BaseScraper._fix_protocol("https://x.com/a.jpg") == "https://x.com/a.jpg"

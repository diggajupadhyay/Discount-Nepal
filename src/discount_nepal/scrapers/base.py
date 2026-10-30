"""Base class for all store scrapers.

Every scraper must subclass :class:`BaseScraper` and implement :meth:`scrape`.
The base class provides a shared :class:`requests.Session`, retries, timeouts,
and small helpers for extracting clean product data from HTML.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from ..config import config
from ..models import Product

logger = logging.getLogger("discount_nepal")


class BaseScraper(ABC):
    """Abstract base scraper for a single store."""

    #: Human-readable store name shown on the frontend.
    store_name: str = "Store"
    #: Base URL of the store (used to resolve relative links).
    base_url: str = ""
    #: Whether the store is currently enabled (can be disabled if broken).
    enabled: bool = True
    #: Seconds to sleep between requests to the same host (politeness delay).
    request_delay: float = 0.5

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
            }
        )
        self.results: list[Product] = []
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------ #
    # HTTP helpers
    # ------------------------------------------------------------------ #
    def _rate_limit(self) -> None:
        """Enforce a minimum delay between requests to the same host."""
        if self.request_delay <= 0:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """Only transient failures are worth retrying.

        Network errors, timeouts, HTTP 429 and HTTP 5xx are transient. Any
        other 4xx (404, 403, …) is a definitive answer — retrying just
        wastes time and hammers the store.
        """
        response = getattr(exc, "response", None)
        if response is None:
            return True
        status: int = response.status_code
        return status == 429 or status >= 500

    @staticmethod
    def _backoff_for(exc: Exception, attempt: float) -> float:
        """Seconds to wait before the next attempt."""
        backoff = 0.5 * attempt
        response = getattr(exc, "response", None)
        if response is not None:
            if response.status_code == 429:
                backoff = max(backoff, 3.0 * attempt)
            elif response.status_code >= 500:
                backoff = max(backoff, 1.0 * attempt)
        return backoff

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        """GET with timeout, retry, rate limiting, and error logging."""
        timeout = kwargs.pop("timeout", config.request_timeout)
        last_error: Exception | None = None
        max_attempts = config.max_retries + 1
        for attempt in range(1, max_attempts + 1):
            self._rate_limit()
            try:
                response = self.session.get(url, timeout=timeout, **kwargs)
                response.raise_for_status()
                self._last_request_time = time.time()
                return response
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                retryable = self._is_retryable(exc)
                logger.warning(
                    "[%s] GET %s failed (attempt %d/%d): %s",
                    self.store_name,
                    url,
                    attempt,
                    max_attempts,
                    exc,
                )
                if not retryable or attempt >= max_attempts:
                    break
                time.sleep(self._backoff_for(exc, attempt))
        raise last_error or RuntimeError(f"GET {url} failed after {max_attempts} attempts")

    def _post(self, url: str, **kwargs: Any) -> requests.Response:
        """POST with timeout, retry, rate limiting, and error logging."""
        timeout = kwargs.pop("timeout", config.request_timeout)
        last_error: Exception | None = None
        max_attempts = config.max_retries + 1
        for attempt in range(1, max_attempts + 1):
            self._rate_limit()
            try:
                response = self.session.post(url, timeout=timeout, **kwargs)
                response.raise_for_status()
                self._last_request_time = time.time()
                return response
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                retryable = self._is_retryable(exc)
                logger.warning(
                    "[%s] POST %s failed (attempt %d/%d): %s",
                    self.store_name,
                    url,
                    attempt,
                    max_attempts,
                    exc,
                )
                if not retryable or attempt >= max_attempts:
                    break
                time.sleep(self._backoff_for(exc, attempt))
        raise last_error or RuntimeError(f"POST {url} failed after {max_attempts} attempts")

    def _soup(self, url: str, **kwargs: Any) -> BeautifulSoup:
        """Fetch *url* and return a BeautifulSoup document."""
        response = self._get(url, **kwargs)
        return BeautifulSoup(response.content, "html.parser")

    def _post_json(self, url: str, **kwargs: Any) -> Any:
        """POST *url* and return the parsed JSON body.

        Raises a clear error if the response is not JSON.
        """
        headers = kwargs.pop("headers", {})
        headers.setdefault("Accept", "application/json")
        headers.setdefault("X-Requested-With", "XMLHttpRequest")
        response = self._post(url, headers=headers, **kwargs)
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise ValueError(
                f"Expected JSON response from {url}, got Content-Type: {content_type}"
            )
        return response.json()

    @staticmethod
    def _abs(url: str, base: str) -> str:
        """Resolve *url* against *base*, returning 'N/A' when unresolvable."""
        if not url or str(url).strip().lower() in {"n/a", "none", ""}:
            return "N/A"
        try:
            resolved = urljoin(base, url)
        except ValueError:
            return "N/A"
        return resolved if resolved else "N/A"

    @staticmethod
    def _fix_protocol(url: str) -> str:
        """Ensure a URL has a scheme (protocol-relative → https:)."""
        if not url or url == "N/A":
            return "N/A"
        if url.startswith("//"):
            return "https:" + url
        return url

    @staticmethod
    def _attr(tag: Tag, name: str) -> str:
        """Return an HTML attribute as a plain string.

        BeautifulSoup types ``Tag.get`` as ``str | AttributeValueList | None``
        (multi-valued attributes such as ``class`` yield a list). Scrapers
        always want the string form, so coerce here once instead of casting at
        every call site. Lists are joined with spaces, matching the DOM.
        """
        value = tag.get(name)
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return " ".join(str(item) for item in value)
        return str(value)

    # ------------------------------------------------------------------ #
    # Parsing helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _clean_price(text: str) -> str:
        """Return a cleaned price string (e.g. ``Rs. 2,599``)."""
        if not text:
            return "N/A"
        cleaned = " ".join(text.split())
        return cleaned if cleaned else "N/A"

    @staticmethod
    def _extract_prices(container: Tag) -> tuple[str, str]:
        """Best-effort extraction of (regular, sale) price from a product node.

        Looks for common ``<del>``/``<ins>`` or ``.price`` structures. Falls
        back to any text that looks like a currency amount.
        """
        regular = "N/A"
        sale = "N/A"

        # <del> / <ins> pattern (WooCommerce-style).
        del_tag = container.find("del")
        ins_tag = container.find("ins")
        if del_tag or ins_tag:
            if del_tag:
                regular = BaseScraper._clean_price(del_tag.get_text())
            if ins_tag:
                sale = BaseScraper._clean_price(ins_tag.get_text())
            if sale == "N/A" and regular != "N/A":
                sale = regular
            if regular == "N/A" and sale != "N/A":
                regular = sale
            return regular, sale

        # Single price element.
        price_el = (
            container.select_one(".price")
            or container.select_one(".product-price")
            or container.select_one(".sale-price")
            or container.select_one(".current-price")
        )
        if price_el:
            text = BaseScraper._clean_price(price_el.get_text())
            regular = sale = text
        return regular, sale

    @staticmethod
    def _extract_image(container: Tag, base: str) -> str:
        """Return the best candidate image URL from a product node."""
        img = container.find("img")
        if not img:
            return "N/A"
        for attr in ("data-src", "data-lazy-src", "src"):
            value = BaseScraper._attr(img, attr)
            if value:
                return BaseScraper._abs(value, base)
        return "N/A"

    @staticmethod
    def _extract_link(container: Tag, base: str) -> str:
        """Return the first meaningful link from a product node."""
        link = container.find("a", href=True)
        if not link:
            return "N/A"
        return BaseScraper._abs(BaseScraper._attr(link, "href"), base)

    # ------------------------------------------------------------------ #
    # Subclass interface
    # ------------------------------------------------------------------ #
    @abstractmethod
    def scrape(self) -> list[Product]:
        """Scrape the store and return a list of :class:`Product`."""

    def get_results(self) -> list[Product]:
        """Return the last scrape results (convenience for legacy callers)."""
        return self.results

    def run(self) -> list[Product]:
        """Run the scrape, capturing exceptions so one store cannot fail others."""
        if not self.enabled:
            logger.info("[%s] scraper disabled, skipping.", self.store_name)
            return []
        try:
            self.results = self.scrape()
            logger.info("[%s] scraped %d products.", self.store_name, len(self.results))
            return self.results
        except Exception as exc:  # noqa: BLE001 — one store must not kill others
            logger.exception("[%s] scraper raised an exception: %s", self.store_name, exc)
            self.results = []
            return []

    def to_dicts(self) -> list[dict]:
        return [p.to_dict() for p in self.results]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.__class__.__name__}(store={self.store_name!r})>"

"""Zoot scraper — https://zoot.com.np

Zoot's homepage is JavaScript-heavy, but it exposes a `sitemap.xml` listing all
product URLs. Product pages are server-rendered and contain `.new-price`,
`.old-price`, and the product image in the DOM — no JS required.
"""

from __future__ import annotations

import logging
import re

from ..models import Product
from .base import BaseScraper

logger = logging.getLogger("discount_nepal")


class ZootScraper(BaseScraper):
    store_name = "Zoot"
    base_url = "https://zoot.com.np"

    SITEMAP_URL = base_url + "/sitemap.xml"
    MAX_PRODUCTS = 120  # safety cap so a single store never dominates

    def scrape(self) -> list:
        product_urls = self._discover_product_urls()
        products: list = []
        seen = set()

        for url in product_urls:
            if url in seen or len(products) >= self.MAX_PRODUCTS:
                break
            seen.add(url)
            try:
                product = self._parse_product(url)
                if product and product.name != "N/A":
                    products.append(product)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[%s] parse error for %s: %s", self.store_name, url, exc)
                continue

        return products

    def _discover_product_urls(self) -> list[str]:
        """Parse sitemap.xml for /product/ URLs."""
        try:
            response = self._get(self.SITEMAP_URL)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] sitemap fetch failed: %s", self.store_name, exc)
            return []

        urls = re.findall(r"<loc>(https://zoot\.com\.np/product/[^<]+)</loc>", response.text)
        # De-duplicate while preserving order.
        seen = set()
        ordered = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                ordered.append(u)
        logger.info("[%s] discovered %d product URLs from sitemap", self.store_name, len(ordered))
        return ordered

    def _parse_product(self, url: str) -> Product | None:

        soup = self._soup(url)

        # Title.
        h1 = soup.select_one("h1")
        name = h1.get_text(strip=True) if h1 else "N/A"

        # Prices.
        new_price_el = soup.select_one(".new-price")
        old_price_el = soup.select_one(".old-price")
        sale_price = self._clean_price(new_price_el.get_text()) if new_price_el else "N/A"
        regular_price = self._clean_price(old_price_el.get_text()) if old_price_el else "N/A"

        # Fallback: combined price block `.zo-product_price`.
        if sale_price == "N/A":
            combined = soup.select_one(".zo-product_price")
            if combined:
                text = combined.get_text(" ", strip=True)
                parts = [p for p in re.split(r"\s+", text) if p]
                if len(parts) >= 2:
                    sale_price, regular_price = parts[0], parts[1]

        if regular_price == "N/A" and sale_price != "N/A":
            regular_price = sale_price
        if sale_price == "N/A" and regular_price != "N/A":
            sale_price = regular_price

        # Image: first product image in the gallery.
        image_url = "N/A"
        for img in soup.find_all("img"):
            src = self._attr(img, "src") or self._attr(img, "data-src")
            if "storage/uploads/product" in src:
                image_url = src
                break

        return Product(
            website=self.store_name,
            name=name,
            regular_price=regular_price,
            sale_price=sale_price,
            url=url,
            image_url=image_url,
        )

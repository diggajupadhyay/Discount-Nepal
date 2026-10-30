"""Instyle Nepal scraper — https://www.instylenepal.com

Custom store (Brodox). Product cards are ``.starlight-product-card-2025``
divs with title, current price and lazy-loaded image. We scrape the shop
index plus a few category pages.
"""

from __future__ import annotations

import logging

from bs4.element import Tag

from ..models import Product
from .base import BaseScraper

logger = logging.getLogger("discount_nepal")


class InstyleNepalScraper(BaseScraper):
    store_name = "Instyle Nepal"
    base_url = "https://www.instylenepal.com"

    LIST_URLS = [
        base_url + "/shop",
        base_url + "/category/t-shirts/15864",
        base_url + "/category/hoodies/15875",
        base_url + "/category/jackets-coats/15856",
        base_url + "/category/sweatshirts/15881",
        base_url + "/category/pants/15884",
        base_url + "/category/shorts/15885",
    ]
    request_delay = 0.6

    def scrape(self) -> list:
        products: list = []
        seen_urls = set()

        for url in self.LIST_URLS:
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                soup = self._soup(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] failed to load %s: %s", self.store_name, url, exc)
                continue

            cards = soup.select(".starlight-product-card-2025")
            if not cards:
                continue

            for card in cards:
                try:
                    product = self._parse_card(card)
                    if (
                        product
                        and product.url != "N/A"
                        and product.url not in seen_urls
                    ):
                        seen_urls.add(product.url)
                        products.append(product)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("[%s] parse error: %s", self.store_name, exc)
                    continue

        return products

    def _parse_card(self, card: Tag) -> Product | None:
        title_el = card.select_one(".starlight-product-title a")
        if not title_el:
            return None
        name = title_el.get_text(strip=True) or "N/A"
        url = self._abs(self._attr(title_el, "href"), self.base_url)

        price_el = card.select_one(".starlight-product-price .current-price")
        price = self._clean_price(price_el.get_text()) if price_el else "N/A"
        regular_price = price
        sale_price = price

        image_url = "N/A"
        img = card.select_one(".starlight-product-image")
        if img:
            image_url = self._attr(img, "data-src") or self._attr(img, "src") or "N/A"
            image_url = self._fix_protocol(image_url)

        return Product(
            website=self.store_name,
            name=name,
            regular_price=regular_price,
            sale_price=sale_price,
            url=url,
            image_url=image_url,
        )

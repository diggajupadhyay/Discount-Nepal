"""Evan Mens scraper — https://evanmens.com

Evan Mens is a server-rendered shop (Next.js / Zalient). Product cards are in
`.product-item` with `.product-title`, `.product-price` (sale) and a
`<p class="text-gray-500 text-sm line-through">` for the regular price.
"""

from __future__ import annotations

import logging

from bs4.element import Tag

from ..models import Product
from .base import BaseScraper

logger = logging.getLogger("discount_nepal")


class EvanMensScraper(BaseScraper):
    store_name = "Evan Mens"
    base_url = "https://evanmens.com"

    # The /products route is client-rendered (Next.js), so we scrape the
    # homepage which renders product cards server-side.
    LIST_URL = base_url

    def scrape(self) -> list:
        try:
            soup = self._soup(self.LIST_URL)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] failed to load %s: %s", self.store_name, self.LIST_URL, exc)
            return []

        cards = soup.select(".product-item")
        if not cards:
            logger.warning("[%s] no product cards found on %s", self.store_name, self.LIST_URL)
            return []

        products: list = []
        seen_urls = set()
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

        link_el = card.select_one("a.product-card-link")
        if not link_el:
            return None
        name_el = card.select_one(".product-title")
        name = name_el.get_text(strip=True) if name_el else "N/A"
        url = self._abs(self._attr(link_el, "href"), self.base_url)

        # Sale price.
        sale_el = card.select_one(".product-price")
        sale_price = self._clean_price(sale_el.get_text()) if sale_el else "N/A"

        # Regular price: the line-through paragraph.
        regular_price = "N/A"
        for p in card.find_all("p"):
            if "line-through" in self._attr(p, "class").split():
                regular_price = self._clean_price(p.get_text())
                break

        if regular_price == "N/A" and sale_price != "N/A":
            regular_price = sale_price
        if sale_price == "N/A" and regular_price != "N/A":
            sale_price = regular_price

        image_url = self._extract_image(card, self.base_url)

        return Product(
            website=self.store_name,
            name=name,
            regular_price=regular_price,
            sale_price=sale_price,
            url=url,
            image_url=image_url,
        )

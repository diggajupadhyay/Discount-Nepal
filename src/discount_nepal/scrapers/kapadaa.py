"""Kapadaa scraper — https://kapadaa.com

WooCommerce store. Product cards are ``.product`` list items with
``.woocommerce-loop-product__title``, ``.price`` (``<del>``/``<ins>``) and
image.
"""

from __future__ import annotations

import logging

from bs4.element import Tag

from ..models import Product
from .base import BaseScraper

logger = logging.getLogger("discount_nepal")


class KapadaaScraper(BaseScraper):
    store_name = "Kapadaa"
    base_url = "https://kapadaa.com"

    LIST_URL = base_url + "/shop/?paged={page}"
    MAX_PAGES = 15
    request_delay = 0.8

    def scrape(self) -> list:
        products: list = []
        seen_urls: set[str] = set()

        for page in range(1, self.MAX_PAGES + 1):
            url = self.LIST_URL.format(page=page)
            if url in seen_urls:
                break
            seen_urls.add(url)

            try:
                soup = self._soup(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] failed to load %s: %s", self.store_name, url, exc)
                break

            cards = soup.select(".product")
            if not cards:
                break

            new_on_page = 0
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
                        new_on_page += 1
                except Exception as exc:  # noqa: BLE001
                    logger.debug("[%s] parse error: %s", self.store_name, exc)
                    continue

            if new_on_page == 0:
                break

        return products

    def _parse_card(self, card: Tag) -> Product | None:

        link = card.select_one(".woocommerce-LoopProduct-link") or card.find(
            "a", href=True
        )
        if not link:
            return None
        url = self._abs(self._attr(link, "href") or self._attr(link, "data-href"), self.base_url)

        title_el = card.select_one(".woocommerce-loop-product__title")
        name = title_el.get_text(strip=True) if title_el else "N/A"

        regular_price, sale_price = self._extract_prices(card)
        image_url = self._extract_image(card, self.base_url)

        return Product(
            website=self.store_name,
            name=name,
            regular_price=regular_price,
            sale_price=sale_price,
            url=url,
            image_url=image_url,
        )

"""Dolpo scraper — https://dolpo.com.np

Dolpo is a WooCommerce store. Products live in `.card-product` nodes across
paginated shop pages (`/shop/?paged=N`). Each node has title/link, image, and
a `<del>`/`<ins>` price wrapper.
"""

from __future__ import annotations

import logging

from bs4.element import Tag

from ..models import Product
from .base import BaseScraper

logger = logging.getLogger("discount_nepal")


class DolpoScraper(BaseScraper):
    store_name = "Dolpo"
    base_url = "https://dolpo.com.np"

    LIST_URL = base_url + "/shop/?paged={page}"
    MAX_PAGES = 20

    def scrape(self) -> list:
        products: list = []
        seen_urls = set()

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

            cards = soup.select("div.card-product")
            if not cards:
                cards = soup.find_all("div", class_="sale")
            if not cards:
                # No more products on this page → stop paginating.
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

        # Title + URL.
        title_el = card.select_one("a.title") or card.select_one(".card-product-info a")
        name = "N/A"
        url = "N/A"
        if title_el:
            name = title_el.get_text(strip=True) or "N/A"
            url = self._attr(title_el, "href") or "N/A"
        if name == "N/A":
            name_tag = (
                card.find("p", class_="name")
                or card.find("h2")
                or card.find("h3")
                or card.find("h4")
            )
            name = name_tag.get_text(strip=True) if name_tag else "N/A"
        if url == "N/A":
            link = card.find("a", href=True)
            url = self._attr(link, "href") if link else "N/A"
        url = self._abs(url, self.base_url)

        # Image.
        image_url = "N/A"
        img = card.find("img")
        if img:
            image_url = self._attr(img, "data-src") or self._attr(img, "src") or "N/A"
            image_url = self._abs(image_url, self.base_url)

        # Price.
        regular_price, sale_price = self._extract_prices(card)

        return Product(
            website=self.store_name,
            name=name,
            regular_price=regular_price,
            sale_price=sale_price,
            url=url,
            image_url=image_url,
        )

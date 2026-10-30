"""Harrington Wear scraper — https://np.harringtonwear.com

Shopify store. Collection pages render ``.grid-product`` cards server-side
with title, compare-at price, sale price and image. We scrape a few
representative collections with polite delays to avoid rate limiting.
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urljoin

from bs4.element import Tag

from ..models import Product
from .base import BaseScraper

logger = logging.getLogger("discount_nepal")


class HarringtonWearScraper(BaseScraper):
    store_name = "Harrington Wear"
    base_url = "https://np.harringtonwear.com"

    # DISABLED (2025-10-29): Shopify returns HTTP 429 for every request,
    # including a single polite one — the store is effectively blocking us.
    # The scraper is kept intact so it can be re-enabled once the block lifts.
    enabled = False

    # New arrivals alone covers ~150 products. A few extra collections
    # add sale items. Keep the list short to avoid Shopify rate limits.
    COLLECTIONS = [
        "/collections/new-arrivals-spring-summer",
        "/collections/festive-sale",
        "/collections/polo-t-shirts",
        "/collections/summer-winter-jackets",
    ]

    MAX_PAGES_PER_COLLECTION = 2
    # Seconds to sleep between collections (Shopify rate-limits rapid hits).
    DELAY_BETWEEN_COLLECTIONS = 2.0

    def scrape(self) -> list:
        products: list = []
        seen_urls = set()

        for idx, collection in enumerate(self.COLLECTIONS):
            # Be polite: delay before each collection except the first.
            if idx > 0:
                time.sleep(self.DELAY_BETWEEN_COLLECTIONS)

            collection_url = urljoin(self.base_url, collection)
            for page in range(1, self.MAX_PAGES_PER_COLLECTION + 1):
                url = (
                    f"{collection_url}?page={page}" if page > 1 else collection_url
                )
                if url in seen_urls:
                    break
                seen_urls.add(url)

                try:
                    soup = self._soup(url)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[%s] failed to load %s: %s", self.store_name, url, exc
                    )
                    break

                cards = soup.select(".grid-product")
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

        meta = card.select_one(".grid-product__meta")
        if not meta:
            return None
        url = self._abs(self._attr(meta, "href"), self.base_url)

        title_el = card.select_one(".grid-product__title")
        name = title_el.get_text(strip=True) if title_el else "N/A"

        price_wrap = card.select_one(".grid-product__price-wrap")
        regular_price = "N/A"
        sale_price = "N/A"
        if price_wrap:
            compare = price_wrap.select_one(".product-single__price--compare-at")
            sale = price_wrap.select_one(".grid-product__price")
            if compare:
                regular_price = self._clean_price(compare.get_text())
            if sale:
                sale_price = self._clean_price(sale.get_text())
            if sale_price == "N/A" and regular_price != "N/A":
                sale_price = regular_price
            if regular_price == "N/A" and sale_price != "N/A":
                regular_price = sale_price

        image_url = "N/A"
        img = card.select_one("img.product--image") or card.find("img")
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

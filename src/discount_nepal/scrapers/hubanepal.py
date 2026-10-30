"""Huba Nepal scraper — https://www.hubanepal.com

Wix store. Product cards are ``[data-hook="product-item-root"]`` divs. Title and
price are embedded in the product link text (e.g.
``HUBA Waffle Hoodie - Blue Price NPR 3,350.00`` or ``... Out of stock``).
We scrape the shop homepage which renders ~40 products server-side.
"""

from __future__ import annotations

import logging
import re

from bs4.element import Tag

from ..models import Product
from .base import BaseScraper

logger = logging.getLogger("discount_nepal")

_PRICE_RE = re.compile(r"Price\s*NPR\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)


class HubaNepalScraper(BaseScraper):
    store_name = "Huba Nepal"
    base_url = "https://www.hubanepal.com"

    LIST_URL = base_url + "/shop"

    def scrape(self) -> list:
        try:
            soup = self._soup(self.LIST_URL)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] failed to load %s: %s", self.store_name, self.LIST_URL, exc)
            return []

        roots = soup.select('[data-hook="product-item-root"]')
        if not roots:
            logger.warning("[%s] no product roots found", self.store_name)
            return []

        products: list = []
        seen_urls = set()
        for root in roots:
            try:
                product = self._parse_root(root)
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

    def _parse_root(self, root: Tag) -> Product | None:

        container = root.select_one('[data-hook="product-item-container"]')
        if not container or not self._attr(container, "href"):
            return None
        url = self._abs(self._attr(container, "href"), self.base_url)

        text = root.get_text(" ", strip=True)
        # Text like: "HUBA Waffle Hoodie - Blue Price NPR 3,350.00"
        # or: "HUBA Waffle Joggers - Grey Out of stock"
        name = "N/A"
        regular_price = "N/A"
        sale_price = "N/A"

        if "Out of stock" in text:
            name = text.split("Out of stock")[0].strip().replace("HUBA ", "", 1)
        else:
            m = _PRICE_RE.search(text)
            if m:
                sale_price = f"Rs {m.group(1)}"
                regular_price = sale_price
            name = text.split("Price")[0].strip().replace("HUBA ", "", 1)

        image_url = "N/A"
        img = root.find("img")
        if img:
            image_url = self._attr(img, "src") or self._attr(img, "data-src") or "N/A"
            image_url = self._fix_protocol(image_url)

        return Product(
            website=self.store_name,
            name=name or "N/A",
            regular_price=regular_price,
            sale_price=sale_price,
            url=url,
            image_url=image_url,
        )

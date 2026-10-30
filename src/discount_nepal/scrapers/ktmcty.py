"""KTM CTY scraper — https://www.ktmcty.com/nepal/home

KTM CTY renders product category pages server-side. Each category page lists
products with current + old price, so we scrape a handful of representative
categories and follow their pagination.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from bs4.element import Tag

from ..models import Product
from .base import BaseScraper

logger = logging.getLogger("discount_nepal")


class KTMCTYScraper(BaseScraper):
    store_name = "KTM CTY"
    base_url = "https://www.ktmcty.com/nepal"

    # Representative categories with sale items. Adding more categories
    # increases coverage at the cost of scrape time.
    CATEGORIES = [
        "/nepal/categories/winter-jacket",
        "/nepal/categories/jacket",
        "/nepal/categories/jackets-1",
        "/nepal/categories/hoodie-1",
        "/nepal/categories/sweat-shirt",
        "/nepal/categories/t-shirt",
        "/nepal/categories/polo-t-shirt-1",
        "/nepal/category/for-him",
        "/nepal/category/for-her",
        "/nepal/category/unisex",
        "/nepal/category/new-arrivals",
    ]

    MAX_PAGES_PER_CATEGORY = 3

    def scrape(self) -> list:

        products: list = []
        seen_urls = set()

        for category in self.CATEGORIES:
            category_url = urljoin(self.base_url, category)
            for page in range(1, self.MAX_PAGES_PER_CATEGORY + 1):
                url = f"{category_url}?page={page}" if page > 1 else category_url
                if url in seen_urls:
                    break
                seen_urls.add(url)

                try:
                    soup = self._soup(url)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[%s] failed to load %s: %s", self.store_name, url, exc)
                    break

                articles = soup.select("article.b-goods")
                if not articles:
                    break

                for article in articles:
                    try:
                        product = self._parse_article(article)
                        if product and product.url not in seen_urls:
                            seen_urls.add(product.url)
                            products.append(product)
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("[%s] parse error: %s", self.store_name, exc)
                        continue

        return products

    def _parse_article(self, article: Tag) -> Product | None:

        title_el = article.select_one("a.b-goods__title")
        if not title_el:
            return None
        name = title_el.get_text(strip=True) or "N/A"
        url = self._attr(title_el, "href") or "N/A"
        url = self._abs(url, self.base_url)

        # Image: prefer the high-res cover thumb, fall back to img-responsive.
        image_url = "N/A"
        media = article.select_one("a.b-goods__media[href]")
        if media and self._attr(media, "href"):
            image_url = self._attr(media, "href")
        else:
            img = article.select_one("img.img-responsive, img.zoom")
            if img:
                image_url = self._attr(img, "src") or self._attr(img, "data-src") or "N/A"
                image_url = self._abs(image_url, self.base_url)

        # Price: current + old price are in .b-goods__price / .b-goods-det__price-old.
        regular_price = "N/A"
        sale_price = "N/A"
        price_wrap = article.select_one(".b-goods__price")
        if price_wrap:
            current = price_wrap.select_one("span")
            old = price_wrap.select_one(".b-goods-det__price-old")
            hidden = price_wrap.select_one("input.product_price")
            if hidden and self._attr(hidden, "value"):
                sale_price = self._attr(hidden, "value").strip()
            elif current:
                sale_price = current.get_text(strip=True)
            if old:
                regular_price = old.get_text(strip=True).replace("रू", "").strip() or "N/A"
            if sale_price == "N/A" and regular_price != "N/A":
                sale_price = regular_price
            if regular_price == "N/A" and sale_price != "N/A":
                regular_price = sale_price

        return Product(
            website=self.store_name,
            name=name,
            regular_price=regular_price,
            sale_price=sale_price,
            url=url,
            image_url=image_url,
        )

"""Sonam Gear scraper — https://sonamgear.com

Sonam Gear lists product IDs on a category page, then serves each product's
detail HTML via a `POST /getproductdetail` AJAX endpoint. We fetch all IDs
concurrently, then parse each detail block.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..models import Product
from .base import BaseScraper

logger = logging.getLogger("discount_nepal")


class SonamGearScraper(BaseScraper):
    store_name = "Sonam Gear"
    base_url = "https://sonamgear.com"

    LIST_URL = base_url + "/products?cat=1&n=1"
    DETAIL_URL = base_url + "/getproductdetail"
    MAX_WORKERS = 12

    def scrape(self) -> list:
        try:
            product_ids = self._get_product_ids()
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] failed to load product list: %s", self.store_name, exc)
            return []

        products: list = []

        def fetch(product_id: str) -> Product | None:
            try:
                detail = self._fetch_product(product_id)
                return self._parse_product(detail)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[%s] error for product %s: %s", self.store_name, product_id, exc)
                return None

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as pool:
            futures = [pool.submit(fetch, pid) for pid in product_ids]
            for future in as_completed(futures):
                product = future.result()
                if product:
                    products.append(product)

        return products

    def _get_product_ids(self) -> list[str]:
        soup = self._soup(self.LIST_URL)
        ids = []
        for element in soup.select(".product-list"):
            pid = self._attr(element, "data-product_id")
            if pid and pid not in ids:
                ids.append(pid)
        logger.info("[%s] discovered %d product IDs", self.store_name, len(ids))
        return ids

    def _fetch_product(self, product_id: str) -> BeautifulSoup:
        response = self._post(
            self.DETAIL_URL,
            headers={"X-Requested-With": "XMLHttpRequest", "Referer": self.LIST_URL},
            data={"product_id": product_id},
        )
        payload = response.json()
        view_html = payload.get("view", "")
        return BeautifulSoup(view_html, "html.parser")

    def _parse_product(self, product: Tag) -> Product | None:

        name_tag = product.find("h4", class_="mt-3 text-height")
        name = name_tag.get_text(strip=True) if name_tag else "N/A"

        regular_price = "N/A"
        sale_price = "N/A"
        sale_price_tag = product.find("span", class_="underline")
        if sale_price_tag:
            regular_tag = sale_price_tag.find("span", class_="price-actual")
            if regular_tag:
                regular_price = self._clean_price(regular_tag.get_text())
            sale_spans = [
                span
                for span in sale_price_tag.find_all("span", recursive=False)
                if "price-actual" not in self._attr(span, "class").split()
            ]
            if sale_spans:
                sale_price = self._clean_price(sale_spans[0].get_text())
            elif regular_price == "N/A":
                sale_price = self._clean_price(sale_price_tag.get_text())

        if sale_price == "N/A":
            sale_price = regular_price
        if regular_price == "N/A" and sale_price != "N/A":
            regular_price = sale_price

        img_container = product.find("div", class_="img-container")
        link = img_container.find("a", href=True) if img_container else product.find("a", href=True)
        product_url = self._attr(link, "href") if link else "N/A"
        product_url = self._abs(product_url, self.base_url)

        image_tag = img_container.find("img") if img_container else product.find("img")
        image_url = "N/A"
        if image_tag:
            image_url = self._attr(image_tag, "src") or self._attr(image_tag, "data-src") or "N/A"
            image_url = self._abs(image_url, self.base_url)

        return Product(
            website=self.store_name,
            name=name,
            regular_price=regular_price,
            sale_price=sale_price,
            url=product_url,
            image_url=image_url,
        )

import sys

sys.path.insert(0, "src")

from discount_nepal.scrapers.base import BaseScraper


class DummyScraper(BaseScraper):
    store_name = "Dummy"
    base_url = "https://example.com"

    def scrape(self):
        return [
            self._make("Test Product", "Rs. 2,000", "Rs. 1,500", "https://example.com/p/1"),
            self._make("No Sale Item", "Rs. 999", "Rs. 999", "https://example.com/p/2"),
        ]

    def _make(self, name, reg, sale, url):
        from discount_nepal.models import Product
        return Product(
            website=self.store_name,
            name=name,
            regular_price=reg,
            sale_price=sale,
            url=url,
            image_url="https://example.com/img.jpg",
        )


def test_price_parsing():
    s = DummyScraper()
    products = s.scrape()
    assert len(products) == 2
    on_sale = products[0]
    not_sale = products[1]
    assert on_sale.is_on_sale is True
    assert on_sale.discount_percent == 25
    assert not_sale.is_on_sale is False
    assert not_sale.discount_percent is None
    print("test_price_parsing passed")


def test_to_dict():
    s = DummyScraper()
    products = s.scrape()
    d = products[0].to_dict()
    assert set(d.keys()) == {"website", "name", "regular_price", "sale_price", "url", "image_url", "timestamp"}
    assert d["website"] == "Dummy"
    print("test_to_dict passed")


if __name__ == "__main__":
    test_price_parsing()
    test_to_dict()
    print("All model tests passed.")

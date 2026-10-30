"""Scrape every enabled store and print a short summary.

Usage:
    python scripts/scrape.py          # summary counts
    python scripts/scrape.py --full   # include sample products per store
"""

import argparse
import logging
import sys

# Allow running from repo root without installing.
sys.path.insert(0, "src")

from discount_nepal.registry import all_scrapers


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape all enabled stores.")
    parser.add_argument(
        "--full", action="store_true", help="print up to 3 sample products per store"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    total = 0
    for scraper in all_scrapers():
        if not scraper.enabled:
            print(f"{scraper.store_name}: disabled, skipped")
            continue
        products = scraper.run()
        total += len(products)
        print(f"{scraper.store_name}: {len(products)} products")
        if args.full:
            for product in products[:3]:
                print(f"  - {product.name} | {product.sale_price} (was {product.regular_price})")

    print(f"\nTotal: {total} products")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

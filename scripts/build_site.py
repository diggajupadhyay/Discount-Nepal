"""Build the static site for GitHub Pages.

Scrapes every enabled store and writes:

    site/index.html       the frontend (copied from the package template)
    site/products.json    {products, fetched_at, stores, count}
    site/assets/og.png    Open Graph share image (copied from ./assets)

The frontend fetches ``products.json`` relative to itself, so the same
template works both here (static hosting) and under the local dev server,
which serves the same payload shape at ``/products.json``.

Usage:
    python scripts/build_site.py          # write ./site
    python scripts/build_site.py out/dir  # write somewhere else
"""

import json
import logging
import shutil
import sys
import time
from pathlib import Path

# Allow running from repo root without installing.
sys.path.insert(0, "src")

from discount_nepal.app import scrape_all_stores
from discount_nepal.registry import list_stores

TEMPLATE = Path("src/discount_nepal/templates/index.html")
ASSETS = Path("assets")

# Refuse to publish a suspiciously small result: a partial scrape (e.g. most
# stores unreachable) should not replace good data on the live site.
MIN_PRODUCTS = 50


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("site")
    if not TEMPLATE.exists():
        print(f"ERROR: template not found: {TEMPLATE}", file=sys.stderr)
        return 1

    started = time.time()
    products = scrape_all_stores()
    elapsed = time.time() - started

    if len(products) < MIN_PRODUCTS:
        print(
            f"ERROR: only {len(products)} products scraped (minimum {MIN_PRODUCTS}). "
            "Refusing to publish a likely-broken scrape.",
            file=sys.stderr,
        )
        return 1

    payload = {
        "products": products,
        "fetched_at": int(time.time()),
        "stores": list_stores(),
        "count": len(products),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "products.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    shutil.copyfile(TEMPLATE, out_dir / "index.html")
    # Share image(s) referenced by og:image — must be served next to index.html.
    if ASSETS.is_dir():
        shutil.copytree(ASSETS, out_dir / "assets", dirs_exist_ok=True)

    size_kb = (out_dir / "products.json").stat().st_size / 1024
    stores = len({p["website"] for p in products})
    print(
        f"Built {out_dir}/ — {len(products)} products from {stores} stores "
        f"in {elapsed:.1f}s ({size_kb:.0f} KB JSON)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Discount Nepal HTTP server + CLI.

Serves a single-page frontend at ``/`` and a JSON API at ``/api/products``.
All registered stores are scraped concurrently and cached with a TTL.
"""

from __future__ import annotations

import argparse
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .__version__ import __version__
from .cache import TTLCache
from .config import config
from .registry import all_scrapers, list_stores

logger = logging.getLogger("discount_nepal")

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "index.html"

_cache: TTLCache | None = None
_cache_lock = threading.Lock()


def _dedupe_products(products: list[dict]) -> list[dict]:
    """De-duplicate products by URL.

    Products with a real URL are de-duplicated by that URL. Products without
    a URL ("N/A") are kept but de-duplicated by (website, name) to avoid
    dropping entire stores' worth of products.
    """
    seen_urls: set[str] = set()
    seen_no_url: set[tuple[str, str]] = set()
    unique: list[dict] = []

    for p in products:
        url = p.get("url") or "N/A"
        if url != "N/A":
            if url in seen_urls:
                continue
            seen_urls.add(url)
        else:
            key = (p.get("website", ""), p.get("name", ""))
            if key in seen_no_url:
                continue
            seen_no_url.add(key)
        unique.append(p)

    return unique


def scrape_all_stores() -> list[dict]:
    """Scrape every enabled store concurrently and return product dicts.

    One failing store never breaks the others — exceptions are caught and
    logged per-scraper.
    """
    scrapers = all_scrapers()
    enabled = [s for s in scrapers if s.enabled]
    logger.info("Scraping %d store(s) concurrently...", len(enabled))

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=config.concurrent_workers) as pool:
        futures = {pool.submit(s.run): s for s in enabled}
        for future in as_completed(futures):
            scraper = futures[future]
            try:
                future.result()  # scraper.run() already populated scraper.results
                store_results = scraper.to_dicts()
                results.extend(store_results)
                logger.debug(
                    "[%s] contributed %d products", scraper.store_name, len(store_results)
                )
            except Exception as exc:  # noqa: BLE001 — one store must not kill others
                logger.exception(
                    "[%s] unexpected error during scrape: %s", scraper.store_name, exc
                )

    unique = _dedupe_products(results)
    logger.info(
        "Scrape complete: %d unique products (%d raw) across %d store(s).",
        len(unique),
        len(results),
        len(enabled),
    )
    return unique


def _refresh_cache() -> None:
    """Populate the global cache with a fresh scrape.

    Safe to call from a background thread — uses :meth:`TTLCache.get` which
    prevents duplicate concurrent loads.
    """
    global _cache
    with _cache_lock:
        cache = _cache
        if cache is None:
            cache = TTLCache(config.cache_ttl_seconds)
            _cache = cache

    def _loader() -> list[dict]:
        return scrape_all_stores()

    try:
        cache.get(force=True, loader=_loader)
    except Exception:
        logger.exception("Background cache refresh failed")


def get_products(force: bool = False) -> dict:
    """Return cached products, refreshing if stale or forced.

    Never blocks for long: returns whatever is in cache immediately (even if
    empty on cold start) and starts a background refresh when needed. The
    frontend shows loading skeletons while data arrives.
    """
    global _cache
    with _cache_lock:
        cache = _cache
        if cache is None:
            cache = TTLCache(config.cache_ttl_seconds)
            _cache = cache

    snapshot = cache.snapshot()
    has_data = snapshot["ready"] and bool(snapshot["products"])
    fresh = has_data and (time.time() - snapshot["fetched_at"] < config.cache_ttl_seconds)

    # Cold start or stale → kick off a background refresh and return what we have.
    if not has_data or not fresh or force:
        thread = threading.Thread(target=_refresh_cache, daemon=True)
        thread.start()

    return {
        "products": cache.data,
        "fetched_at": snapshot["fetched_at"],
        "stores": list_stores(),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = f"DiscountNepal/{__version__}"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # /products.json is what the frontend fetches (same shape as the
        # static build); /api/products is kept for backward compatibility.
        if path in ("/api/products", "/products.json"):
            self._handle_products(parsed.query)
            return

        if path in ("/", "/index.html"):
            self._send_file(TEMPLATE_PATH, "text/html; charset=utf-8")
            return

        self.send_error(404, "Not Found")

    def _handle_products(self, query: str) -> None:
        force = parse_qs(query).get("refresh", ["0"])[0] == "1"
        try:
            payload = get_products(force=force)
        except Exception as exc:  # noqa: BLE001
            logger.exception("API error: %s", exc)
            self._send_json(
                b'{"error":"internal server error","products":[],"stores":[],"count":0}',
                status=500,
            )
            return

        body = json.dumps(
            {
                "products": payload["products"],
                "fetched_at": payload["fetched_at"],
                "stores": payload["stores"],
                "count": len(payload["products"]),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self._send_json(body)

    def _send_json(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(500, "index.html missing")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: str) -> None:  # pragma: no cover - quiet server
        logger.info("%s - %s", self.address_string(), fmt % args)


def serve(host: str = config.host, port: int = config.port) -> None:
    """Start the HTTP server, warming the cache in the background."""
    # Warm cache so the first page load is instant.
    threading.Thread(target=_refresh_cache, daemon=True).start()

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Discount Nepal running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="discount-nepal",
        description="Web app listing discounted gear from Nepali online stores.",
    )
    parser.add_argument("--host", default=config.host)
    parser.add_argument("--port", type=int, default=config.port)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    serve(args.host, args.port)


if __name__ == "__main__":
    main()

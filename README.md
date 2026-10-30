# Discount Nepal

**Open-source price tracker for discounted outdoor, trekking, and streetwear gear from Nepali online stores.**

**[Live site](https://diggajupadhyay.github.io/Discount-Nepal/)** · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![CI](https://github.com/diggajupadhyay/Discount-Nepal/actions/workflows/ci.yml/badge.svg)](https://github.com/diggajupadhyay/Discount-Nepal/actions/workflows/ci.yml)

## Stores supported

| Store | URL | Category | Status |
|-------|-----|----------|--------|
| Dolpo | https://dolpo.com.np | Trekking / outdoor gear | ✅ |
| Sonam Gear | https://sonamgear.com | Trekking / outdoor gear | ✅ |
| KTM CTY | https://www.ktmcty.com/nepal/home | Streetwear & outerwear | ✅ |
| Zoot | https://zoot.com.np | Men's streetwear | ✅ |
| Evan Mens | https://evanmens.com | Men's streetwear | ✅ |
| Huba Nepal | https://www.hubanepal.com | Streetwear & outerwear | ✅ |
| Instyle Nepal | https://www.instylenepal.com | Men's streetwear & footwear | ✅ |
| Kapadaa | https://kapadaa.com | Traditional & ethnic wear | ✅ |
| UFO Nepal | https://www.ufonepal.com | Women's & men's apparel | ✅ |
| Harrington Wear | https://np.harringtonwear.com | Men's premium shirts, jackets & suits | ⏸️ disabled (rate-limited) |

More stores are easy to add — see [Adding a store](#adding-a-store).

## Features

*   **Hosted site** — visit the [live site](https://diggajupadhyay.github.io/Discount-Nepal/) and see discounted products; no install needed.
*   **Scheduled scraping** — a GitHub Action scrapes all stores every 6 hours and republishes the data.
*   **Concurrent** — all stores are scraped in parallel.
*   **Cached** — instant page loads; the local server also caches with a short TTL.
*   **Filtering & search** — client-side search, store, discount, price filters and sorting.
*   **Zero-config** — run locally with one command, no API keys or database required.
*   **MIT licensed** — free to use, modify, and redistribute.

## Hosting & architecture

The public site is static and hosted on **GitHub Pages** — a free host with no card required:

*   Every 6 hours, the `deploy-site.yml` GitHub Action runs `scripts/build_site.py`, which scrapes all enabled stores and writes `site/index.html` + `site/products.json` (refusing to publish fewer than 50 products, so a partial scrape can't wipe the live data).
*   Pages serves those files at <https://diggajupadhyay.github.io/Discount-Nepal/> — visitors just open the URL and the page loads the pre-built JSON. No server runs per visitor.
*   Scraping on a schedule (rather than per request) keeps loads fast, avoids serverless time limits, and stays polite to the stores.

The same frontend template serves both the hosted site and the local server: it fetches `products.json` relative to itself, which both hosts provide.

## Install

### Using a virtual environment (recommended)

```bash
# 1. Create a virtual environment
python3 -m venv .venv

# 2. Activate it
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 3. Install Discount Nepal
pip install -e .
```

### Or system-wide

```bash
pip install discount-nepal
```

## Run

```bash
discount-nepal
# or: discount-nepal --host 0.0.0.0 --port 8000
```

Then open <http://127.0.0.1:8000>.

### CLI options

```
--host   Bind address (default: 127.0.0.1)
--port   Port to listen on (default: 8000)
```

### Environment variables

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCOUNT_NEPAL_HOST` | `127.0.0.1` | Bind address |
| `DISCOUNT_NEPAL_PORT` | `8000` | Port to listen on |
| `DISCOUNT_NEPAL_CACHE_TTL` | `120` | Cache TTL in seconds |
| `DISCOUNT_NEPAL_TIMEOUT` | `20` | HTTP request timeout (seconds) |
| `DISCOUNT_NEPAL_MAX_RETRIES` | `2` | Max retries per request |
| `DISCOUNT_NEPAL_WORKERS` | `8` | Concurrent store scrapers |
| `DISCOUNT_NEPAL_USER_AGENT` | … | Custom User-Agent string |

## API

The local server exposes the same payload shape the static site uses:

| Endpoint | Description |
|----------|-------------|
| `GET /` | Product listing page |
| `GET /products.json` | Cached products (JSON, 120 s TTL) — what the frontend fetches |
| `GET /api/products` | Identical to `/products.json` (kept for backward compatibility) |
| `GET /products.json?refresh=1` | Force a fresh scrape of all stores |

Payload shape (both endpoints and the static build):

```json
{
  "products": [{"website": "Dolpo", "name": "…", "regular_price": "Rs. 2,000",
                "sale_price": "Rs. 1,500", "url": "https://…", "image_url": "https://…",
                "timestamp": "2026-10-30T…"}],
  "fetched_at": 1761800000,
  "stores": [{"key": "dolpo", "name": "Dolpo", "url": "https://dolpo.com.np"}],
  "count": 736
}
```

## Docker

```bash
docker build -t discount-nepal .
docker run -p 8000:8000 discount-nepal
```

## Adding a store

1. Create `src/discount_nepal/scrapers/<store>.py` subclassing `BaseScraper`.
2. Implement `scrape()` returning a list of product dicts.
3. Register the scraper in `src/discount_nepal/registry.py`.
4. Add a row to the stores table in this README.

See `src/discount_nepal/scrapers/base.py` for the full interface and an example.

## Development

```bash
# 1. Set up
make install        # creates .venv and installs in editable mode
source .venv/bin/activate
# or, with an existing venv: pip install -e ".[dev]"

# 2. Run
make run            # or: discount-nepal

# 3. Quality gates (same as CI)
make lint           # ruff check src tests scripts
mypy src            # type-check
make test           # pytest tests/
```

## Project structure

```
├── src/discount_nepal/
│   ├── __init__.py        # package metadata
│   ├── __version__.py     # version number
│   ├── app.py             # HTTP server + CLI
│   ├── cache.py           # in-memory cache with TTL
│   ├── config.py          # shared settings
│   ├── models.py          # Product dataclass
│   ├── registry.py        # store scraper registry
│   ├── scrapers/
│   │   ├── base.py        # BaseScraper (HTTP, retries, parsing helpers)
│   │   └── <store>.py     # one file per store (10 enabled + 1 disabled)
│   └── templates/
│       └── index.html     # single-page frontend (serves both hosts)
├── scripts/
│   ├── build_site.py      # static build → site/index.html + site/products.json
│   └── scrape.py          # scrape all stores, print summary
├── tests/                 # pytest suite (34 tests)
└── .github/workflows/
    ├── ci.yml             # ruff + mypy + pytest on push/PR
    └── deploy-site.yml    # scheduled scrape → GitHub Pages deploy
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on scraping etiquette, adding stores, and submitting pull requests.

## License

MIT License — see [LICENSE](LICENSE).

**Disclaimer:** This tool scrapes public product pages. Prices and availability shown are as observed at scrape time and may differ from the live store. Always verify on the retailer's site before purchasing. The project is not affiliated with any of the listed stores.

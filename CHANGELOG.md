# Changelog

## [0.4.0] — 2026-10-30

### Added
*   **SEO & link previews** — Open Graph image (`assets/og.png`, 1200×630, rendered from `assets/og-card.html`), full `og:*` tags, Twitter/X `summary_large_image` card tags, canonical URL, `theme-color`, and JSON-LD `WebSite` structured data. Shared links now show a logo card with title and description on WhatsApp, X, Discord, Facebook, Slack, etc.
*   **GitHub Pages hosting** — the app is now a hosted static site: a scheduled GitHub Action (`deploy-site.yml`) scrapes all stores every 6 hours and deploys the result. Visit <https://diggajupadhyay.github.io/Discount-Nepal/> with no install.
*   `scripts/build_site.py` — static site build (`site/index.html` + `site/products.json`) with a minimum-product guard so partial scrapes are never published.
*   `ci.yml` workflow — ruff, mypy and pytest run on every push and pull request.
*   Frontend: footer with disclaimer, Open Graph tags, inline SVG favicon, associated `<label>`s (accessibility), inline SVG image placeholder (no external service), `http(s)`-only product links.
*   Local server now serves `/products.json` (same payload as the static build); `/api/products` kept for backward compatibility.
*   Top-level `app.py` compatibility shim (`python app.py` still works alongside the `src/` package).
*   Test suite expanded from 2 to 34 tests (cache, registry, dedupe, config, `BaseScraper` helpers, retry policy).

### Changed
*   Bumped version to 0.4.0.
*   Requires Python >= 3.10 (3.9 is EOL).
*   Retries now apply only to transient failures (network errors, timeouts, HTTP 429/5xx) — definitive 4xx responses like 404 are no longer retried.
*   `list_stores()` excludes disabled stores; the version string is derived from `__version__`.
*   Frontend fetches `products.json` relative to itself so one template serves both the local server and static hosting.
*   `scripts/scrape.py` is now registry-driven (covers every enabled store instead of a hardcoded subset).

### Fixed
*   Removed thread-unsafe shared `seen_ids` set in the Sonam Gear scraper.
*   Removed duplicate `_fix_protocol` overrides in three scrapers; moved function-level `Product` imports to module level.
*   mypy (18 errors) and ruff (19 errors) now pass cleanly.

### Disabled
*   **Harrington Wear** scraper — Shopify returns HTTP 429 for every request, yielding 0 products while burning retries. Kept in the registry and re-enable once the block lifts.

## [0.3.0] — 2025-10-29

### Added
*   New scrapers: **Harrington Wear** (np.harringtonwear.com), **Huba Nepal** (hubanepal.com), **Instyle Nepal** (instylenepal.com), **Kapadaa** (kapadaa.com), **UFO Nepal** (ufonepal.com).
*   Frontend upgrades: min-discount filter, max-price filter, sort dropdown (discount / price / newest), load-more button + infinite scroll, loading skeletons, toast notifications.
*   Polite scraping: delays between collections, HTTP 429 rate-limit backoff.

### Changed
*   Bumped version to 0.3.0 (10 stores, 800+ products).
*   Reduced Harrington Wear collections to avoid Shopify rate limiting.

## [0.2.0] — 2025-10-28

### Added
*   New scrapers: **Zoot** (zoot.com.np), **KTM CTY** (ktmcty.com), **Evan Mens** (evanmens.com).
*   `BaseScraper` class with shared HTTP client, retries, timeouts, and parsing helpers.
*   Store registry (`registry.py`) for declarative store registration.
*   `Product` dataclass (`models.py`) with validation.
*   In-memory TTL cache (`cache.py`).
*   Professional project layout under `src/`, pyproject-based packaging.
*   Dockerfile, CONTRIBUTING.md, CHANGELOG.md.
*   Test suite (`tests/`) and dev tooling (ruff, mypy, pytest).

### Changed
*   Reorganized flat scripts into a proper Python package (`src/discount_nepal`).
*   Existing Dolpo and Sonam Gear scrapers rewritten on top of `BaseScraper`.
*   Frontend now lists all supported stores dynamically.
*   README rewritten with store table, API docs, and contribution guide.

### Removed
*   Legacy top-level scripts (`app.py`, `dolpo.py`, `sonamgear_scraper.py`, etc.).

## [0.1.0] — 2024-10-14

### Added
*   Initial release with Dolpo and Sonam Gear scrapers.
*   Simple HTTP server + JSON API.
*   Basic HTML frontend.

# Contributing to Discount Nepal

Thank you for wanting to contribute! This project is a community-maintained, open-source price tracker for Nepali online stores.

## How to contribute

1. **Fork the repo** and create a feature branch (`git checkout -b feature/your-store`).
2. **Add a store scraper** (see below) or fix a bug / improve the frontend.
3. **Run the checks** (`ruff`, `mypy`, `pytest`).
4. **Open a pull request** with a clear description.

## Adding a new store

1. Create `src/discount_nepal/scrapers/<store>.py` subclassing `BaseScraper`.
2. Implement `scrape()` → `list[Product]`.
3. Register the scraper in `src/discount_nepal/registry.py`.
4. Add the store to the table in `README.md`.
5. Add a test in `tests/` (optional but encouraged).

## Scraping etiquette

*   Set a realistic `User-Agent`.
*   Use timeouts on every request.
*   Respect `robots.txt` where practical.
*   Do not hammer a single store — scrape concurrently but politely (one request at a time per store, small delays between pages).
*   Handle errors gracefully so one failing store never breaks the whole run.

## Code style

*   Follow [PEP 8](https://peps.python.org/pep-0008/).
*   Run `ruff check` and `ruff format` before committing.
*   Type annotations are required for public functions (`mypy` strict-ish).

## License

By contributing, you agree your contributions will be licensed under the MIT License.

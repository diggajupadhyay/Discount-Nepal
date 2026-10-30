.PHONY: install run dev test lint format clean

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip

install: ## Create venv and install package in editable mode
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .

run: ## Run the Discount Nepal server
	$(PYTHON) -m discount_nepal.app

dev: install run ## Install and run

test: ## Run the test suite
	$(PYTHON) -m pytest tests/ -v

lint: ## Run ruff linting
	$(VENV)/bin/ruff check src tests

format: ## Format code with ruff
	$(VENV)/bin/ruff format src tests

clean: ## Remove build artifacts and caches
	rm -rf build dist src/discount_nepal.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

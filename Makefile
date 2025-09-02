.PHONY: help lint audit test test-fast test-cov clean install install-dev

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package in production mode
	pip install -e .

install-dev:  ## Install package with development dependencies
	pip install -e ".[dev]"

audit:  ## Run Ruff for code auditing (check-only, no fixes)
	@echo "Running Ruff audit (no auto-fixes)..."
	ruff check src/ tests/ --no-fix --output-format=full
	@echo "Running Ruff format check (no changes)..."
	ruff format src/ tests/ --check --diff

lint:  ## Run all linting checks (Ruff, mypy, black check)
	@echo "Running Ruff checks..."
	ruff check src/ tests/ --no-fix
	@echo "Running Black format check..."
	black --check src/ tests/
	@echo "Running isort check..."
	isort --check-only src/ tests/
	@echo "Running mypy..."
	mypy src/

test:  ## Run all tests with coverage
	pytest tests/ -v --cov=egokit --cov-report=term-missing

test-fast:  ## Run tests without coverage
	pytest tests/ -v

test-cov:  ## Run tests and generate HTML coverage report
	pytest tests/ -v --cov=egokit --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

clean:  ## Clean up generated files and caches
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/ .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Convenience aliases
check: audit  ## Alias for audit
qa: lint test  ## Run all quality checks (lint + test)
.PHONY: setup cleanup test lint format typecheck install help

# Default target
help:
	@echo "Available targets:"
	@echo "  setup      - Create virtual environment and install dependencies"
	@echo "  cleanup    - Remove Python artifacts and cache directories"
	@echo "  install    - Install package in development mode"
	@echo "  test       - Run tests with pytest"
	@echo "  test-cov   - Run tests with coverage report"
	@echo "  lint       - Run ruff linter"
	@echo "  format     - Format code with ruff"
	@echo "  typecheck  - Run mypy type checker"

# Create venv and install dependencies
setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	@echo ""
	@echo "Setup complete! Activate the virtual environment with:"
	@echo "  source .venv/bin/activate"

# Remove all Python test/runtime artifacts
cleanup:
	#rm -rf .venv
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .hypothesis
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".DS_Store" -delete

# Install package in development mode
install:
	pip install -e ".[dev]"

# Run tests
test:
	pytest

# Run tests with coverage
test-cov:
	pytest --cov=src/podtext --cov-report=html --cov-report=term

# Run linter
lint:
	ruff check src tests

# Format code
format:
	ruff format src tests

# Run type checker
typecheck:
	mypy src/podtext

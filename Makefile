.PHONY: install lint format test build clean

# Install dependencies
install:
	uv sync

# Run linting
lint:
	ruff check src/ tests/
	mypy src/

# Format code
format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# Run tests
test:
	pytest --cov=src --cov-fail-under=90

# Build Docker image
build:
	docker build -t sdlc-mcp .

# Clean up
clean:
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Run all quality checks
check: lint test

# Setup development environment
setup: install
	pre-commit install

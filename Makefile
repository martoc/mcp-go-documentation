# Description: Makefile for Python MCP Go Documentation Server

PROJECT_NAME := mcp-go-documentation
TARGET := ./target
PYTHON := uv run python
PYTEST := uv run pytest
RUFF := uv run ruff
MYPY := uv run mypy

.PHONY: all
all: clean init build ## Run all targets

.PHONY: clean
clean: ## Clean build artefacts
	@echo "==> Cleaning..."
	rm -rf $(TARGET)
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf src/*.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

.PHONY: init
init: ## Initialise development environment
	@echo "==> Initialising..."
	uv sync --all-groups
	@echo "==> Python version:"
	$(PYTHON) --version

.PHONY: test
test: ## Run tests with coverage
	@echo "==> Running tests..."
	@mkdir -p $(TARGET)
	$(PYTEST)

.PHONY: lint
lint: ## Run linter
	@echo "==> Running linter..."
	$(RUFF) check src tests

.PHONY: format
format: ## Format code
	@echo "==> Formatting code..."
	$(RUFF) format src tests
	$(RUFF) check --fix src tests

.PHONY: typecheck
typecheck: ## Run type checker
	@echo "==> Running type checker..."
	$(MYPY)

.PHONY: build
build: clean lint typecheck test ## Run full build (lint, typecheck, test)
	@echo "==> Build complete"

.PHONY: generate
generate: ## Generate/update lock file
	@echo "==> Generating lock file..."
	uv lock

.PHONY: index
index: ## Build the documentation index
	@echo "==> Building documentation index..."
	$(PYTHON) -m mcp_go_documentation.cli index

.PHONY: run
run: ## Run the MCP server
	@echo "==> Running MCP server..."
	$(PYTHON) -m mcp_go_documentation.server

DOCKER_IMAGE := mcp-go-documentation

.PHONY: docker-build
docker-build: ## Build Docker image
	@echo "==> Building Docker image..."
	docker build -t $(DOCKER_IMAGE) .

.PHONY: docker-run
docker-run: ## Run MCP server in Docker
	@echo "==> Running MCP server in Docker..."
	docker run -i --rm $(DOCKER_IMAGE)

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

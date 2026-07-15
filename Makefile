.PHONY: help dev stop build test lint clean celery

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start all services in development mode
	docker compose up -d

stop: ## Stop all services
	docker compose down

build: ## Build all Docker images
	docker compose build

celery: ## Start Celery worker locally (for development without Docker)
	cd backend && celery -A app.core.celery_app worker --loglevel=info --concurrency=2

test-backend: ## Run backend tests
	cd backend && python -m pytest tests/ -v

test-frontend: ## Run frontend tests
	cd frontend && npm run test

lint-backend: ## Lint backend code
	cd backend && python -m ruff check .

lint-frontend: ## Lint frontend code
	cd frontend && npm run lint

clean: ## Remove all containers, volumes, and build artifacts
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

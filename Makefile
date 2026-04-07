.PHONY: help sync run dev test make-migration migrate docker-dev docker-dev-down docker-dev-build

.DEFAULT_GOAL := help

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

sync: pyproject.toml ## Install dependencies via pdm sync
	pdm sync

run: pyproject.toml ## Run the application
	pdm run start

dev: pyproject.toml ## Run the application in development mode
	pdm run dev

test: pyproject.toml ## Run the test suite
	pdm run test

make-migration: pyproject.toml ## Generate a new database migration
	pdm run make_migration

migrate: pyproject.toml ## Apply database migrations
	pdm run migrate

docker-dev-run: dev/docker-compose.yml ## Start development containers
	docker-compose -f dev/docker-compose.yml up

docker-dev-down: dev/docker-compose.yml ## Stop development containers
	docker-compose -f dev/docker-compose.yml down

docker-dev-build: dev/docker-compose.yml ## Build development containers
	docker-compose -f dev/docker-compose.yml build

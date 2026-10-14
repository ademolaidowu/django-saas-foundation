.PHONY: help up down logs test lint format typecheck migrate migrations seed shell check

help:  ## Show this help
	@awk 'BEGIN{FS=":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up:  ## Start the full stack (api + postgres + redis)
	docker compose up --build -d
	@echo "api on http://localhost:8000 — try /api/docs/"

down:  ## Stop the stack (keeps the pgdata volume)
	docker compose down

logs:  ## Tail api logs
	docker compose logs -f api

test:  ## Run the full pytest suite with coverage
	uv run pytest

lint:  ## Ruff lint + format check
	uv run ruff check .
	uv run ruff format --check .

format:  ## Autoformat with Ruff
	uv run ruff check . --fix
	uv run ruff format .

typecheck:  ## mypy with django-stubs
	uv run mypy apps config

check:  ## Django system check + migrations consistency
	uv run python manage.py check
	uv run python manage.py makemigrations --check --dry-run

migrate:  ## Apply migrations
	uv run python manage.py migrate

migrations:  ## Create migrations from model edits
	uv run python manage.py makemigrations

seed:  ## seed_rbac + seed_demo
	uv run python manage.py seed_rbac
	uv run python manage.py seed_demo

shell:  ## Django shell
	uv run python manage.py shell

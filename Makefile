VENV := $(CURDIR)/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
COMPOSE := docker compose

.PHONY: tree api-install api-dev console-dev seed docker-seed test-api test-api-db docker-up docker-down docker-logs lint-api format-api typecheck-api

tree:
	find . -maxdepth 4 | sort

$(PYTHON):
	python3 -m venv .venv

api-install: $(PYTHON)
	$(PIP) install --upgrade pip
	cd apps/api && $(PIP) install -r requirements-dev.txt

api-dev: $(PYTHON)
	cd apps/api && PYTHONPATH=. $(UVICORN) app.main:app --reload

console-dev:
	cd apps/console && npm run dev

docker-up:
	$(COMPOSE) up -d --wait postgres
	$(COMPOSE) up -d --build api

docker-down:
	$(COMPOSE) down

docker-logs:
	$(COMPOSE) logs -f --tail=200

seed: $(PYTHON)
	$(PYTHON) scripts/seed/bootstrap_registry.py

docker-seed:
	$(COMPOSE) up -d --wait postgres
	$(COMPOSE) build api-test
	$(COMPOSE) run --rm -e AUTOCLAW_DATABASE_URL=postgresql+asyncpg://autoclaw:autoclaw@postgres:5432/autoclaw api-test sh -lc "cd /app/apps/api && PYTHONPATH=. python /app/scripts/seed/bootstrap_registry.py"

test-api: $(PYTHON)
	cd apps/api && PYTHONPATH=. $(PYTEST) tests/unit

test-api-db:
	$(COMPOSE) up -d --wait postgres
	$(COMPOSE) exec -T postgres sh -lc "psql -U autoclaw -d postgres -c \"DROP DATABASE IF EXISTS autoclaw_test WITH (FORCE)\" && psql -U autoclaw -d postgres -c \"CREATE DATABASE autoclaw_test\""
	$(COMPOSE) build api-test
	$(COMPOSE) run --rm api-test

lint-api: $(PYTHON)
	cd apps/api && $(RUFF) check .

format-api: $(PYTHON)
	cd apps/api && $(RUFF) format .

typecheck-api: $(PYTHON)
	cd apps/api && $(MYPY) app tests

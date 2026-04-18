VENV := $(CURDIR)/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
COMPOSE := docker compose
COMPOSE_ENV := AUTOCLAW_API_KEY=$${AUTOCLAW_API_KEY:-autoclaw-operator-dev-key} AUTOCLAW_INTERNAL_API_KEY=$${AUTOCLAW_INTERNAL_API_KEY:-autoclaw-internal-dev-key}
TEST_COMPOSE_ENV := AUTOCLAW_API_KEY=autoclaw-operator-test-key AUTOCLAW_INTERNAL_API_KEY=autoclaw-internal-test-key

.PHONY: tree api-install api-dev console-dev console-build seed docker-seed test-api test-api-db docker-up docker-down docker-logs lint-api format-api typecheck-api pyright-api check-api install-user-service

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

console-build:
	cd apps/console && npm run build

docker-up:
	$(COMPOSE_ENV) $(COMPOSE) up -d --wait postgres
	$(COMPOSE_ENV) $(COMPOSE) up -d --build api

docker-down:
	$(COMPOSE_ENV) $(COMPOSE) down

docker-logs:
	$(COMPOSE_ENV) $(COMPOSE) logs -f --tail=200

seed: $(PYTHON)
	$(PYTHON) scripts/seed/bootstrap_registry.py

docker-seed:
	$(TEST_COMPOSE_ENV) $(COMPOSE) up -d --wait postgres
	$(TEST_COMPOSE_ENV) $(COMPOSE) build api-test
	$(TEST_COMPOSE_ENV) $(COMPOSE) run --rm -e AUTOCLAW_DATABASE_URL=postgresql+asyncpg://autoclaw:autoclaw@postgres:5432/autoclaw api-test sh -lc "cd /app/apps/api && PYTHONPATH=. python /app/scripts/seed/bootstrap_registry.py"

test-api: $(PYTHON)
	cd apps/api && PYTHONPATH=. $(PYTEST) tests/unit

test-api-db:
	$(TEST_COMPOSE_ENV) $(COMPOSE) up -d --wait postgres
	$(TEST_COMPOSE_ENV) $(COMPOSE) exec -T postgres sh -lc "psql -U autoclaw -d postgres -c \"DROP DATABASE IF EXISTS autoclaw_test WITH (FORCE)\" && psql -U autoclaw -d postgres -c \"CREATE DATABASE autoclaw_test\""
	$(TEST_COMPOSE_ENV) $(COMPOSE) build api-test
	$(TEST_COMPOSE_ENV) $(COMPOSE) run --rm api-test

lint-api: $(PYTHON)
	cd apps/api && $(RUFF) check .

format-api: $(PYTHON)
	cd apps/api && $(RUFF) format .

typecheck-api: $(PYTHON)
	cd apps/api && $(MYPY) app tests

pyright-api:
	cd apps/api && npx --yes pyright

check-api: $(PYTHON)
	$(MAKE) lint-api
	$(MAKE) typecheck-api
	$(MAKE) pyright-api

install-user-service:
	bash scripts/install-systemd-user.sh

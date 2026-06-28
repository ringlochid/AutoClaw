VENV := $(CURDIR)/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
COMPOSE := docker compose
COMPOSE_ENV := AUTOCLAW_API_KEY=$${AUTOCLAW_API_KEY:-autoclaw-operator-dev-key} AUTOCLAW_INTERNAL_API_KEY=$${AUTOCLAW_INTERNAL_API_KEY:-autoclaw-internal-dev-key}
TEST_COMPOSE_ENV := AUTOCLAW_API_KEY=autoclaw-operator-test-key AUTOCLAW_INTERNAL_API_KEY=autoclaw-internal-test-key AUTOCLAW_OPENCLAW__GATEWAY_TOKEN=gateway-config-token
TEST_COMPOSE := COMPOSE_PROJECT_NAME=autoclaw-test-db $(TEST_COMPOSE_ENV) $(COMPOSE)

.PHONY: tree clean-local api-install api-dev test-api test-api-unit test-api-integration test-api-integration-local test-api-db test-api-e2e test-api-e2e-minimal test-api-e2e-normal test-api-e2e-maximal docker-up docker-down docker-logs lint-api format-api typecheck-api pyright-api check-api install-user-service

tree:
	@tree -a -L 7 --gitignore --dirsfirst -I '.git'
	
clean-local:
	rm -rf .openclaw-run-logs tmp .pytest_cache .mypy_cache .ruff_cache
	rm -rf apps/api/.pytest_cache apps/api/.mypy_cache apps/api/.ruff_cache
	rm -rf apps/console/dist apps/console/node_modules

$(PYTHON):
	python3 -m venv .venv

api-install: $(PYTHON)
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -e ".[dev]"

api-dev: $(PYTHON)
	PYTHONPATH=$(CURDIR)/apps/api/src $(UVICORN) autoclaw.main:app --reload --reload-dir $(CURDIR)/apps/api

docker-up:
	$(COMPOSE_ENV) $(COMPOSE) up -d --wait postgres
	$(COMPOSE_ENV) $(COMPOSE) up -d --build api

docker-down:
	$(COMPOSE_ENV) $(COMPOSE) down

docker-logs:
	$(COMPOSE_ENV) $(COMPOSE) logs -f --tail=200

test-api: test-api-unit

test-api-unit: $(PYTHON)
	cd apps/api && PYTHONPATH=src $(PYTEST) tests/unit

test-api-integration: $(PYTHON)
	PYTEST_BIN=$(PYTEST) PYTHONPATH=$(CURDIR)/apps/api/src sh scripts/testing/run_api_pytest_groups.sh integration

test-api-integration-local: test-api-integration

test-api-db:
	@set -eu; \
	cleanup() { $(TEST_COMPOSE) down --volumes --remove-orphans; }; \
	trap cleanup EXIT INT TERM; \
	$(TEST_COMPOSE) up -d --wait postgres-test; \
	$(TEST_COMPOSE) exec -T postgres-test sh -lc "psql -U autoclaw -d postgres -c \"DROP DATABASE IF EXISTS autoclaw_test WITH (FORCE)\" && psql -U autoclaw -d postgres -c \"CREATE DATABASE autoclaw_test\""; \
	$(TEST_COMPOSE) build api-test; \
	$(TEST_COMPOSE) run --rm -e PYTEST_ADDOPTS api-test

test-api-e2e: $(PYTHON)
	PYTEST_BIN=$(PYTEST) PYTHONPATH=$(CURDIR)/apps/api/src sh scripts/testing/run_api_pytest_groups.sh e2e-all

test-api-e2e-minimal: $(PYTHON)
	PYTEST_BIN=$(PYTEST) PYTHONPATH=$(CURDIR)/apps/api/src sh scripts/testing/run_api_pytest_groups.sh e2e-minimal

test-api-e2e-normal: $(PYTHON)
	PYTEST_BIN=$(PYTEST) PYTHONPATH=$(CURDIR)/apps/api/src sh scripts/testing/run_api_pytest_groups.sh e2e-normal

test-api-e2e-maximal: $(PYTHON)
	PYTEST_BIN=$(PYTEST) PYTHONPATH=$(CURDIR)/apps/api/src sh scripts/testing/run_api_pytest_groups.sh e2e-maximal

lint-api: $(PYTHON)
	cd apps/api && $(RUFF) check .

format-api: $(PYTHON)
	cd apps/api && $(RUFF) format .

typecheck-api: $(PYTHON)
	cd apps/api && MYPYPATH=src $(MYPY) src tests

pyright-api:
	cd apps/api && npx --yes pyright

check-api: $(PYTHON)
	$(MAKE) lint-api
	$(MAKE) typecheck-api
	$(MAKE) pyright-api

install-user-service:
	bash scripts/install-systemd-user.sh

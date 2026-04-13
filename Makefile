.PHONY: tree api-install api-dev console-dev seed test-api lint-api format-api typecheck-api

tree:
	find . -maxdepth 4 | sort

api-install:
	cd apps/api && python3 -m pip install -r requirements-dev.txt

api-dev:
	cd apps/api && uvicorn app.main:app --reload

console-dev:
	cd apps/console && npm run dev

seed:
	python3 scripts/seed/bootstrap_registry.py

test-api:
	cd apps/api && pytest

lint-api:
	cd apps/api && ruff check .

format-api:
	cd apps/api && ruff format .

typecheck-api:
	cd apps/api && mypy app tests

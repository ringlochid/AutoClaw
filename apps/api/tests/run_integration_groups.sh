#!/bin/sh
set -eu

export PYTHONPATH="${PYTHONPATH:-/app/apps/api}"

run_group() {
  label="$1"
  shift
  printf '\n== %s ==\n' "$label"
  pytest "$@" -q
}

run_group \
  "definition-registry-and-runtime-schema" \
  apps/api/tests/integration/definition_registry \
  apps/api/tests/integration/runtime_schema_contract \
  apps/api/tests/integration/test_readyz_real_db.py \
  apps/api/tests/integration/test_startup_schema_guard.py \
  apps/api/tests/integration/test_db_reset_db.py

run_group "phase2" apps/api/tests/integration/phase2
run_group "phase3-routes-control" apps/api/tests/integration/phase3/routes apps/api/tests/integration/phase3/control
run_group "phase3-db" apps/api/tests/integration/phase3/db
run_group "phase3-contracts" apps/api/tests/integration/phase3/contracts
run_group "phase4a" apps/api/tests/integration/phase4a
run_group "phase4b-mcp" apps/api/tests/integration/phase4b/mcp
run_group "phase4b-watchdog" apps/api/tests/integration/phase4b/watchdog
run_group "phase5a" apps/api/tests/integration/phase5a

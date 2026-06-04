#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
API_ROOT="$REPO_ROOT/apps/api"

export PYTHONPATH="${PYTHONPATH:-$API_ROOT/src:$API_ROOT/tests/compat}"

run_group() {
  label="$1"
  shift
  printf '\n== %s ==\n' "$label"
  pytest "$@" -q
}

cd "$API_ROOT"

run_group \
  "definition-registry-and-runtime-schema" \
  tests/integration/definition_registry \
  tests/integration/runtime_schema_contract \
  tests/integration/test_readyz_real_db.py \
  tests/integration/test_startup_schema_guard.py \
  tests/integration/test_db_reset_db.py

run_group "phase2" tests/integration/phase2
run_group "phase3-routes-control" tests/integration/phase3/routes tests/integration/phase3/control
run_group "phase3-db" tests/integration/phase3/db
run_group "phase3-contracts" tests/integration/phase3/contracts
run_group "phase4a" tests/integration/phase4a
run_group "phase4b-mcp" tests/integration/phase4b/mcp
run_group "phase4b-watchdog" tests/integration/phase4b/watchdog
run_group "phase5a" tests/integration/phase5a

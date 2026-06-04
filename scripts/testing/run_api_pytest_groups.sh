#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
API_ROOT="$REPO_ROOT/apps/api"
API_SRC_ROOT="$API_ROOT/src"
PYTEST_BIN="${PYTEST_BIN:-pytest}"
PYTHONPATH="${PYTHONPATH:-$API_SRC_ROOT:$API_ROOT/tests/compat}"

export PYTHONPATH

print_usage() {
  cat <<'EOF'
Usage:
  run_api_pytest_groups.sh list
  run_api_pytest_groups.sh integration-local
  run_api_pytest_groups.sh integration-db
  run_api_pytest_groups.sh e2e-minimal
  run_api_pytest_groups.sh e2e-normal
  run_api_pytest_groups.sh e2e-maximal
  run_api_pytest_groups.sh e2e-all
EOF
}

describe_group() {
  label="$1"
  shift
  printf '%s:' "$label"
  for path in "$@"; do
    printf ' %s' "$path"
  done
  printf '\n'
}

run_group() {
  label="$1"
  shift
  printf '\n== %s ==\n' "$label"
  "$PYTEST_BIN" "$@" -q
}

list_suite() {
  suite="$1"
  printf '\n[%s]\n' "$suite"
  case "$suite" in
    integration-local|integration-db)
      describe_group \
        "definition-registry-and-runtime-schema" \
        tests/integration/definition_registry \
        tests/integration/runtime_schema_contract \
        tests/integration/test_readyz_real_db.py \
        tests/integration/test_startup_schema_guard.py \
        tests/integration/test_db_reset_db.py
      describe_group "phase2" tests/integration/phase2
      describe_group \
        "phase3-routes-control" \
        tests/integration/phase3/routes \
        tests/integration/phase3/control
      describe_group "phase3-db" tests/integration/phase3/db
      describe_group "phase3-contracts" tests/integration/phase3/contracts
      describe_group "phase4a" tests/integration/phase4a
      describe_group "phase4b-mcp" tests/integration/phase4b/mcp
      describe_group "phase4b-watchdog" tests/integration/phase4b/watchdog
      describe_group "phase5a" tests/integration/phase5a
      ;;
    e2e-minimal)
      describe_group "e2e-minimal" tests/e2e/phase2/test_minimal_runtime_lane.py
      ;;
    e2e-normal)
      describe_group "e2e-normal" tests/e2e/phase3/normal_lane/test_normal_lane.py
      ;;
    e2e-maximal)
      describe_group "e2e-maximal" tests/e2e/phase4/maximal_lane/test_maximal_lane.py
      ;;
    e2e-all)
      list_suite e2e-minimal
      list_suite e2e-normal
      list_suite e2e-maximal
      ;;
    *)
      print_usage >&2
      exit 1
      ;;
  esac
}

run_integration_groups() {
  run_group \
    "definition-registry-and-runtime-schema" \
    tests/integration/definition_registry \
    tests/integration/runtime_schema_contract \
    tests/integration/test_readyz_real_db.py \
    tests/integration/test_startup_schema_guard.py \
    tests/integration/test_db_reset_db.py
  run_group "phase2" tests/integration/phase2
  run_group \
    "phase3-routes-control" \
    tests/integration/phase3/routes \
    tests/integration/phase3/control
  run_group "phase3-db" tests/integration/phase3/db
  run_group "phase3-contracts" tests/integration/phase3/contracts
  run_group "phase4a" tests/integration/phase4a
  run_group "phase4b-mcp" tests/integration/phase4b/mcp
  run_group "phase4b-watchdog" tests/integration/phase4b/watchdog
  run_group "phase5a" tests/integration/phase5a
}

run_e2e_suite() {
  suite="$1"
  case "$suite" in
    e2e-minimal)
      run_group "e2e-minimal" tests/e2e/phase2/test_minimal_runtime_lane.py
      ;;
    e2e-normal)
      run_group "e2e-normal" tests/e2e/phase3/normal_lane/test_normal_lane.py
      ;;
    e2e-maximal)
      run_group "e2e-maximal" tests/e2e/phase4/maximal_lane/test_maximal_lane.py
      ;;
    e2e-all)
      run_e2e_suite e2e-minimal
      run_e2e_suite e2e-normal
      run_e2e_suite e2e-maximal
      ;;
    *)
      print_usage >&2
      exit 1
      ;;
  esac
}

main() {
  if [ "$#" -ne 1 ]; then
    print_usage >&2
    exit 1
  fi

  cd "$API_ROOT"

  case "$1" in
    list)
      list_suite integration-local
      list_suite integration-db
      list_suite e2e-all
      ;;
    integration-local|integration-db)
      run_integration_groups
      ;;
    e2e-minimal|e2e-normal|e2e-maximal|e2e-all)
      run_e2e_suite "$1"
      ;;
    *)
      print_usage >&2
      exit 1
      ;;
  esac
}

main "$@"

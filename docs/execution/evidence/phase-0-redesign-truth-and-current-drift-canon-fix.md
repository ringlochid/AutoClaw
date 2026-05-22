# Phase 0 Redesign Truth And Current Drift Canon-Fix Evidence

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP1, P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: redesign-truth authority lock plus current-drift doc repair
- slice type: edit
- date: 2026-05-21

## Plan and review links

- approved plan: `../plans/phase-0-redesign-truth-and-current-drift-canon-fix.md`
- mandatory review: `../reviews/phase-0-redesign-truth-and-current-drift-canon-fix.md`
- review artifact: `../reviews/phase-0-redesign-truth-and-current-drift-canon-fix.md`

## Commands run

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli` outcome: passed
- `./.venv/bin/ruff check scripts/docs` outcome: passed
- `./.venv/bin/mypy scripts/docs` outcome: passed
- `rg -n "bootstrap shape|execution shape|manifest to acknowledge|ack their manifest|not a public HTTP route|wait_for_response=true|Init and local bootstrap" docs/current docs/README.md AGENTS.md` before patch outcome: found stale drift hits in `docs/current/architecture/openclaw-dispatch-and-session-contract.md`, `docs/current/interfaces/definitions-compiler-and-launch.md`, `docs/current/operations/inspect-approvals-and-watchdog.md`, and `docs/current/interfaces/cli-surface-and-config-precedence.md`
- `rg -n "bootstrap shape|execution shape|manifest to acknowledge|ack their manifest|not a public HTTP route|wait_for_response=true|Init and local bootstrap" docs/current docs/README.md AGENTS.md` after patch outcome: only `docs/current/architecture/watchdog-and-runtime-monitoring.md:17` still matched because the heading `## Current execution shape` contains the generic term `execution shape`; no routed current page still teaches live dispatch `bootstrap | execution`, manifest acknowledgement, the stale launch-route claim, the unsupported synchronous dispatch flag, or operator-facing `Init and local bootstrap`
- `PYTHONPATH=apps/api ./.venv/bin/python - <<'PY' ...` config-load repro for `runtime.watchdog_bootstrap_first_progress_timeout_seconds` outcome: failed with `ValidationError` and the exact message `runtime.watchdog_bootstrap_first_progress_timeout_seconds Extra inputs are not permitted`

## Gate and validator summary

- docs or prompt validators: `docs_freeze` passed
- language gates: not applicable
- reset or package checks: not applicable

## Test lanes

- unit: not applicable
- integration: not applicable
- e2e: not applicable
- SQLite: not applicable
- Postgres or Docker: not applicable

## Artifacts changed

- `AGENTS.md`
- `docs/README.md`
- `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- `docs/current/README.md`
- `docs/current/architecture/README.md`
- `docs/current/architecture/openclaw-dispatch-and-session-contract.md`
- `docs/current/interfaces/definitions-compiler-and-launch.md`
- `docs/current/architecture/runtime-control-plane.md`
- `docs/current/architecture/manifest-projection-and-acknowledgement.md`
- `docs/current/operations/inspect-approvals-and-watchdog.md`
- `docs/current/interfaces/cli-surface-and-config-precedence.md`
- `docs/current/architecture/openclaw-and-bridge-plugin.md`
- `docs/current/interfaces/current-definition-bootstrap-and-task-upload.md`
- `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`
- `scripts/docs/docs_freeze/phase_records/rules.py`
- `docs/execution/plans/phase-0-redesign-truth-and-current-drift-canon-fix.md`
- `docs/execution/evidence/phase-0-redesign-truth-and-current-drift-canon-fix.md`
- `docs/execution/reviews/phase-0-redesign-truth-and-current-drift-canon-fix.md`

## Residual blockers

- none

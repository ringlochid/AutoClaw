# Phase 0-3 Closeout Review Exceptions

Status: Reference

This page records the explicit phase-bounded review exceptions accepted during
the Phase 0-3 exact-canon closeout.

These exceptions do not waive correctness, test, reset, or gate requirements.
They only document remaining measurable split debt from `STYLE.md` that was not
cleanly reduced inside the current closeout slice without introducing broader
cross-module churn.

This file is also summary-only. It does not create authoritative aggregate work
package numbers or closure waivers.

## Exceptions

### `apps/api/app/runtime/bootstrap_persistence.py`

- current size exceeds the `>600` line no-growth threshold
- reason: Phase 1 and Phase 3 launch, registry-pinning, lease, and bootstrap
  persistence fixes are still concentrated in one owning persistence path after
  the control-state and lease closeout
- boundary: do not further grow this file in follow-up work without first
  extracting launch-persistence, lease, and checkpoint/bootstrap helpers
- owning follow-up: record the cleanup package under the next phase-scoped
  Phase 3 runtime persistence review artifact

### `scripts/docs/prompt_catalog_tools.py`

- current size exceeds the `>600` line no-growth threshold
- reason: prompt asset migration, mirror validation, and live-render example
  generation remain centralized in one docs-tooling surface for this closeout
- boundary: do not further grow this file in follow-up work without splitting
  asset loading, generated-example rendering, and validation passes
- owning follow-up: record the cleanup package under the next phase-scoped
  Phase 0 docs-tooling review artifact

### `scripts/docs/docs_freeze_validate.py`

- current size exceeds the `>600` line no-growth threshold
- reason: existing docs-freeze checks remain centralized and were only touched
  narrowly for closeout compatibility
- boundary: do not expand this validator further without extracting focused
  execution-pack and router checks
- owning follow-up: record the cleanup package under the next phase-scoped
  Phase 0 docs-tooling review artifact

### `apps/api/tests/integration/test_phase3_runtime_db.py`

- current size exceeds the `>600` line no-growth threshold
- reason: the runtime closeout landed several targeted regression proofs into
  the existing Phase 3 integration lane to keep reset and persistence coverage
  close to the owning runtime slice
- boundary: new runtime DB proofs should be split into focused launch, release,
  replay, and persistence files before this file grows again
- owning follow-up: record the cleanup package under the next phase-scoped
  Phase 3 runtime DB review artifact

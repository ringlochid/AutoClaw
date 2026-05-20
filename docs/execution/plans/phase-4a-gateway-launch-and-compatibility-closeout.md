# Phase 4A Gateway Launch And Compatibility Closeout Plan

Status: Reference

selected phase: Phase 4A
current phase page: docs/execution/phases/phase-4a-openclaw-gateway-session-and-continuity.md
selected work packages: P4A-WP1, P4A-WP2
summary-only: no
delegated slices: listed
slice id: phase4a-launch-taxonomy
slice type: edit
owned surfaces: apps/api/app/runtime/control/dispatch/**, apps/api/tests/integration/phase4a/**
touched surfaces: apps/api/app/runtime/control/dispatch/gateway/__init__.py, apps/api/tests/integration/phase4a/runtime_dispatch_gateway/test_launch_integration.py
slice id: phase4a-compatibility-pin
slice type: edit
owned surfaces: apps/api/app/runtime/openclaw/**, apps/api/tests/integration/phase4a/**, docs/redesign/architecture/openclaw-gateway-rpc-subset.md
touched surfaces: apps/api/app/runtime/openclaw/**, apps/api/tests/integration/phase4a/**, docs/redesign/architecture/openclaw-gateway-rpc-subset.md
slice id: phase4a-review
slice type: review-only
owned surfaces: apps/api/app/runtime/control/dispatch/**, apps/api/app/runtime/openclaw/**, apps/api/tests/integration/phase4a/**, docs/redesign/architecture/openclaw-gateway-rpc-subset.md, docs/execution/plans/phase-4a-gateway-launch-and-compatibility-closeout.md, docs/execution/evidence/phase-4a-gateway-launch-and-compatibility-closeout.md, docs/execution/reviews/phase-4a-gateway-launch-and-compatibility-closeout.md
touched surfaces: none

## Goal

Close the remaining Gateway correctness gaps:

- pre-send payload-policy failures must not be treated as post-send ambiguity
- explicit advertised-empty `features.methods` must fail closed
- the repo protocol pin must match the installed live Gateway contract
- transport-facing session-key normalization must be owned in one canonical helper
- request-local `observed_events` and dead response tuple ballast must not survive as the Phase 4A target transport shape
- the wire-facing `agent` launch contract must stay smaller than the controller-owned dispatch launch context

## Ordered Work

1. Fix the pre-send/post-send launch boundary and cover it with a focused integration test.
2. Preserve omitted-vs-explicit-empty method discovery and fix fixtures so empty lists are representable.
3. Bump the typed Gateway subset to the live `2026.5.x` / protocol `4` contract and accept live optional `pluginSurfaceUrls`.
4. Compact the transport boundary so one canonical session-key normalizer, one wire-facing launch input, and one launch wrapper own the Gateway call path.
5. Reprove compatibility and live machine control against the installed gateway.

## Validation

- focused Phase 4A compatibility and gateway integration tests
- live `adapter.check_compatibility()`
- live `launch_run -> abort_run -> wait_for_run`

## Delegated Slice Briefs

### phase4a-launch-taxonomy

- do-not-edit surfaces:
  - `apps/api/app/runtime/openclaw/**`
  - docs and execution artifacts
- required reads:
  - Phase 4A page, exact Gateway subset docs, launch integration tests
- expected outputs:
  - pre-send/post-send launch taxonomy fixed
  - focused gateway integration test coverage
- required validators:
  - focused Phase 4A integration lane
  - narrow lint on owned files
- dependencies:
  - live Gateway subset contract already patched in docs
- parent-owned decisions:
  - exact pre-send vs post-send launch taxonomy
- evidence to return:
  - changed file list
  - focused command outcomes
- stop conditions:
  - if protocol/model/docs changes are required outside owned surfaces

### phase4a-compatibility-pin

- do-not-edit surfaces:
  - dispatch control files outside read/reference
  - execution artifacts
- required reads:
  - Phase 4A page, typed protocol models, live compatibility docs, adapter/fixture tests
- expected outputs:
  - explicit-empty methods fix
  - protocol 4 pin and optional live field support
- required validators:
  - focused compatibility/adapter tests
- dependencies:
  - current host Gateway contract verified
- parent-owned decisions:
  - exact protocol pin and accepted optional live fields
- evidence to return:
  - changed file list
  - focused command outcomes
- stop conditions:
  - if broader runtime state-machine changes are required

### phase4a-review

- do-not-edit surfaces:
  - all repo-tracked files
- required reads:
  - Phase 4A page, plan, evidence, touched code/tests/docs
- expected outputs:
  - strict review verdict and closure-draft content only
- required validators:
  - non-mutating proof checks only
- dependencies:
  - both edit slices integrated
- parent-owned decisions:
  - none; this slice reports review truth only
- evidence to return:
  - exact findings or pass verdict
  - draft-ready review text
- stop conditions:
  - if any repo edit seems necessary

## Exit Evidence

- protocol pin matches the installed gateway
- launch taxonomy is correct
- compatibility and live machine-control proofs pass

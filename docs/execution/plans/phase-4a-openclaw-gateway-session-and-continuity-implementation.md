# Phase 4A OpenClaw Gateway, Session, And Continuity Implementation Plan

Status: Reference

selected phase: Phase 4A
current phase page: docs/execution/phases/phase-4a-openclaw-gateway-session-and-continuity.md
selected work packages: P4A-WP1, P4A-WP2
summary-only: no
delegated slices: listed
slice id: phase4a-openclaw-protocol-config-and-launch
slice type: edit
owned surfaces: apps/api/app/runtime/openclaw/**, apps/api/app/config.py, apps/api/app/main.py, apps/api/tests/unit/test_config.py, apps/api/tests/integration/phase4a/**
touched surfaces: apps/api/app/runtime/openclaw/adapter.py, apps/api/app/runtime/openclaw/__init__.py, apps/api/app/runtime/openclaw/fixtures.py, apps/api/app/runtime/openclaw/request_builders.py, apps/api/app/main.py, apps/api/tests/integration/phase4a/test_openclaw_gateway_adapter.py, apps/api/tests/unit/test_config.py
slice id: phase4a-dispatch-persistence-and-projections
slice type: edit
owned surfaces: apps/api/app/runtime/control/dispatch/**, apps/api/app/runtime/projection/dispatch/**, apps/api/app/db/models/runtime/dispatch/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/phase3/**
touched surfaces: apps/api/app/runtime/control/dispatch/opening.py, apps/api/app/runtime/control/dispatch/gateway.py, apps/api/tests/integration/phase4a/test_runtime_dispatch_gateway_integration.py
slice id: phase4a-wait-abort-continuity-and-node-session
slice type: edit
owned surfaces: apps/api/app/runtime/control/flow/**, apps/api/app/runtime/control/dispatch/**, apps/api/app/runtime/effects/worker.py, apps/api/app/runtime/effects/__init__.py, apps/api/app/runtime/launch/**, apps/api/app/db/models/runtime/dispatch/support.py, apps/api/app/main.py, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/phase3/**
touched surfaces: apps/api/app/runtime/control/clock.py, apps/api/app/runtime/control/dispatch/control.py, apps/api/app/runtime/control/flow/service.py, apps/api/app/runtime/launch/service.py, apps/api/tests/integration/phase4a/test_foreground_lifecycle_gateway.py, apps/api/tests/integration/phase3/control/test_abort_cases.py, apps/api/tests/integration/phase3/control/test_boundary_cases.py, apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py
slice id: phase4a-review
slice type: review-only
owned surfaces: apps/api/app/runtime/openclaw/**, apps/api/app/config.py, apps/api/app/main.py, apps/api/app/runtime/control/dispatch/**, apps/api/app/runtime/control/flow/**, apps/api/app/runtime/effects/worker.py, apps/api/app/runtime/launch/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/phase3/**, apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py, docs/execution/plans/phase-4a-openclaw-gateway-session-and-continuity-implementation.md, docs/execution/evidence/phase-4a-openclaw-gateway-session-and-continuity-implementation.md, docs/execution/reviews/phase-4a-openclaw-gateway-session-and-continuity-implementation.md
touched surfaces: none

## 2026-05-14 foreground lifecycle preservation slice

- scope: preserve the Phase 2/3 foreground inactivity-proof and boundary-drain
  rules after the Gateway integration, without widening into watchdog or route
  ownership
- owned surfaces exercised:
  - `apps/api/app/runtime/control/clock.py`
  - `apps/api/app/runtime/control/dispatch/control.py`
  - `apps/api/app/runtime/control/flow/service.py`
  - `apps/api/app/runtime/launch/service.py`
  - `apps/api/tests/integration/phase4a/test_foreground_lifecycle_gateway.py`
  - `apps/api/tests/integration/phase3/control/test_abort_cases.py`
  - `apps/api/tests/integration/phase3/control/test_boundary_cases.py`
  - `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- slice result:
  - foreground pause, cancel, accepted-boundary drain, timeout-to-ambiguous,
    and replacement-dispatch gating now reconcile through real
    `agent.wait`/`sessions.abort` support truth
  - launch-time projection materialization stays inline with the real Gateway
    open path so the Phase 2 minimal lane remains readable on return
  - fenced dispatch closure now closes live node-session support rows and keeps
    previous-dispatch observability rereads materialized for replacement flows
- validator status:
  - required narrow `ruff check` batch passed on 2026-05-14 after parent-side
    import-order cleanup
  - required narrow `mypy` batch passed on 2026-05-14
  - required narrow pytest preservation batch passed on 2026-05-14 after the
    backend-handshake closeout
  - no broader Phase 4A closeout is claimed here

## Phase-local contract

- purpose: land the real runtime-owned OpenClaw Gateway worker path, exact
  Gateway subset, session/run binding, private node attachment, and continuity
  behavior without widening into Phase 4B watchdog/MCP or Phase 5 public noun
  ownership
- success criteria:
  - real `connect.challenge -> connect -> hello-ok -> agent -> agent.wait -> sessions.abort`
    runtime path exists
  - `gateway_session_key` and `gateway_run_id` carry real Gateway support
    truth
  - callback binding secret is no longer the Gateway `sessionKey`
  - continuity stays adapter-private and does not weaken fresh-session or
    fresh-run replacement dispatch
  - projections and operator/task-root rereads stay controller-owned and
    readable on return

## Preflight canon lock

- completed before code:
  - Phase 4 file-lock collateral now explicitly allows `apps/api/app/config.py`
    and `apps/api/app/main.py`
  - Phase 4B/Phase 5A MCP inventory seam is explicitly split in the interface
    docs so Phase 4A/4B do not have to guess operator-tool ownership

## Ordered work

### `P4A-WP1`

- add `apps/api/app/runtime/openclaw/**` as the dedicated adapter package
- vendor one pinned protocol snapshot and keep typed adapter models plus golden
  fixtures there
- extend config loading for `[openclaw]` and `[runtime]`
- replace fake dispatch acceptance with a real foreground `agent` launch that
  persists normalized accepted/provider support truth and rematerializes
  delivery/continuity/provider-event projections from committed rows

### `P4A-WP2`

- separate callback binding secret from Gateway session identity
- activate `NodeSessionModel` as the dispatch-bound execution-context support
  row
- integrate `agent.wait` and `sessions.abort` into the existing Phase 3
  control-state/drain model
- keep `previous_response_id` optional and adapter-private only

## Validation checkpoints

- after `P4A-WP1`:
  - config parsing tests green
  - golden fixture and startup compatibility tests green
  - dispatch-open integration proves real `gateway_session_key` and
    `gateway_run_id`
- after `P4A-WP2`:
  - wait/abort ambiguity tests green
  - callback legality and node-session binding tests green
  - Phase 2/3 preservation tests for projections, operator reads, and boundary
    drain stay green
- closeout:
  - live Gateway compatibility proof for `agent`, `agent.wait`, and
    `sessions.abort`
  - viable minimal and normal e2e lanes

## Current slice note

- scope: harden the gateway launch acceptance/error-state machine for the
  dispatch opening path only
- in scope for this edit:
  - distinguish pre-send launch failures from post-send launch ambiguity
  - clean up accepted remote runs when local acceptance persistence fails
  - prove both paths in `apps/api/tests/integration/phase4a/test_runtime_dispatch_gateway_integration.py`
- out of scope for this edit:
  - startup compatibility wiring
  - watchdog recovery execution
  - Phase 4B MCP/operator separation work

## Test budget and stop conditions

- each edit slice runs only one narrow owned-slice batch once
- do not run full repo `pytest` during edit slices
- stop and route to a canon fix if a required code surface falls outside owned
  or allowed collateral scope
- stop and escalate if live OpenClaw compatibility cannot be proven against the
  pinned `2026.4.x` family
- stop if any change would make projections or raw provider events into
  controller truth

## Parent Integration Update

- slice status: partially landed by parent integration after Wave 1
- touched surfaces in this slice:
  - `apps/api/app/runtime/openclaw/adapter.py`
  - `apps/api/app/runtime/openclaw/__init__.py`
  - `apps/api/app/runtime/openclaw/fixtures.py`
  - `apps/api/app/runtime/openclaw/request_builders.py`
  - `apps/api/app/main.py`
  - `apps/api/tests/integration/phase4a/test_openclaw_gateway_adapter.py`
- landed in this slice:
  - lifespan startup now runs the Gateway compatibility handshake and fails
    closed on missing `hello-ok.auth`, missing returned role/scopes, and
    missing required event discovery
  - the direct-loopback handshake now uses the installed Gateway backend path:
    `client.id="gateway-client"`, `client.mode="backend"`, and omitted
    `device`
  - `AUTH_TOKEN_MISMATCH` handling now stays bounded: the loopback backend path
    retries once with the host OpenClaw token when it differs from configured
    token; otherwise the adapter retries once with the cached device token only
    when the first attempt used a configured shared token and a cached token is
    available
  - outbound Gateway request-shape ownership now lives in explicit
    `app.runtime.openclaw.request_builders` helpers and the adapter reuses
    those typed builders instead of inline `model_validate({...})` assembly
  - the adapter now validates and records `hello-ok.policy.tickIntervalMs` and
    enforces truthful transport-policy limits for outbound request size and
    buffered pre-response event bytes
  - targeted tests now cover missing `hello-ok.auth`, missing `server`,
    missing `snapshot`, missing returned role/scopes, missing required event
    discovery, bounded auth retry, and payload or buffer policy violations
  - the live compatibility repro against the installed OpenClaw gateway now
    succeeds on `ws://127.0.0.1:18789` with protocol `3` and
    `operator.read`/`operator.write`
- intentionally not closed by this slice:
  - dispatch persistence or launch sequencing changes outside the owned Gateway
    adapter surfaces
  - explicit live `agent` / `agent.wait` / `sessions.abort` proof beyond the
    compatibility handshake
  - Phase 4A evidence or review artifact closeout

## Delegated slice briefs

### phase4a-openclaw-protocol-config-and-launch

- do-not-edit surfaces:
  - `apps/api/app/runtime/control/dispatch/**`
  - `apps/api/app/runtime/projection/**`
  - `apps/api/app/runtime/effects/worker.py`
  - `docs/**`
- required reads:
  - all Phase 4A mandatory docs listed in the header block
  - relevant config/tests for `Settings`, prompt transport, and Gateway subset
- required validators:
  - narrow `ruff check` on owned surfaces
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_config.py apps/api/tests/integration/phase4a/test_openclaw_gateway_adapter.py`
- expected outputs:
  - typed adapter package
  - `[openclaw]` and `[runtime]` settings parsing
  - protocol/gateway compatibility fixtures and tests
- dependencies:
  - preflight canon lock complete
- evidence to return:
  - changed file list
  - narrow validator/test command outputs
- parent-owned decisions:
  - runtime launch sequencing and dispatch integration
- stop conditions:
  - any need for dispatch/opening, startup wiring, or docs edits

### phase4a-dispatch-persistence-and-projections

- do-not-edit surfaces:
  - `apps/api/app/runtime/openclaw/**`
  - `apps/api/app/config.py`
  - `apps/api/app/main.py`
  - `docs/**`
- required reads:
  - all Phase 4A mandatory docs listed in the header block
  - new `app.runtime.openclaw` package
  - launch, dispatch, and projection code/tests
- required validators:
  - narrow `ruff check` on owned surfaces
  - `./.venv/bin/pytest -q apps/api/tests/integration/phase4a apps/api/tests/integration/phase2/bootstrap/test_dispatch.py apps/api/tests/integration/phase3/routes/observability_support.py apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- expected outputs:
  - real foreground `agent` launch
  - real `gateway_session_key` / `gateway_run_id`
  - accepted/provider-event normalization and projection updates
- dependencies:
  - `phase4a-openclaw-protocol-config-and-launch`
- evidence to return:
  - changed file list
  - narrow validator/test command outputs
- parent-owned decisions:
  - second-commit failure cleanup and callback/session truth split
- stop conditions:
  - any need for lifecycle-manager changes, docs edits, or Phase 5 nouns

### phase4a-wait-abort-continuity-and-node-session

- do-not-edit surfaces:
  - `apps/api/app/runtime/openclaw/**`
  - `apps/api/app/runtime/launch/**`
  - `apps/api/app/runtime/control/dispatch/opening.py`
  - `apps/api/app/config.py`
  - `apps/api/app/main.py`
  - `docs/**`
- required reads:
  - all Phase 4A mandatory docs listed in the header block
  - the merged Phase 4A adapter/dispatch changes
  - foreground lifecycle, flow control, and relevant phase3 control tests
- required validators:
  - narrow `ruff check` on owned surfaces
  - `./.venv/bin/pytest -q apps/api/tests/integration/phase4a apps/api/tests/integration/phase3/control/test_abort_cases.py apps/api/tests/integration/phase3/control/test_boundary_cases.py apps/api/tests/integration/phase3/routes/test_surface_contract.py`
- expected outputs:
  - real `agent.wait` / `sessions.abort` reconciliation in the foreground manager
  - timeout-to-ambiguous behavior
  - node-session lifecycle updates
- dependencies:
  - `phase4a-dispatch-persistence-and-projections`
- evidence to return:
  - changed file list
  - narrow validator/test command outputs
- parent-owned decisions:
  - broad review, orphan-run cleanup, and final Phase 4A integration
- stop conditions:
  - any need for watchdog package/startup work or docs edits

### phase4a-review

- do-not-edit surfaces:
  - all repo-tracked files
- required reads:
  - all Phase 4A mandatory docs listed in the header block
  - the merged Phase 4A adapter/dispatch/lifecycle changes
  - touched Phase 2/3 preservation tests
- required validators:
  - inspect delegated edit-slice proof and run only narrow spot-checks if needed
  - do not run full pytest or make test-api-db
- expected outputs:
  - independent findings and verdict
  - draft review artifact content for the matching Phase 4A review file
- dependencies:
  - `phase4a-openclaw-protocol-config-and-launch`
  - `phase4a-dispatch-persistence-and-projections`
  - `phase4a-wait-abort-continuity-and-node-session`
- evidence to return:
  - findings with exact file references
  - draft review artifact content
- parent-owned decisions:
  - final live Gateway proof and final Phase 4A closure status
- stop conditions:
  - stop if proving a finding requires full broad-suite validation or Phase 4B ownership

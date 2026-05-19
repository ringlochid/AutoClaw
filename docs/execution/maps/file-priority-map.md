# Implementation file lock map

Status: Target

Use this page as the canonical owned-surface map for redesign implementation.

Read it together with the current phase page before planning or editing.

## Rule

For each phase:

- `owned surfaces` are the primary files and directories the phase is expected to change
- `allowed collateral surfaces` may be changed only when the owned work cannot land cleanly without them
- `do not edit / defer surfaces` must stay untouched unless canon is patched first or the phase is re-scoped
- `required tests and validators` are the minimum evidence tied to those surfaces
- helpers imported across module boundaries count as shared surfaces for review
  and naming purposes; they must not remain underscore-private without an
  explicit phase-bounded review exception
- when a phase touches Python backend surfaces under `apps/api/**`, required
  proof includes the repo-native audit command `make pyright-api`
- when a Phase 0-3 cleanup slice touches Python-owned surfaces, required proof
  also includes `./.venv/bin/python -m scripts.docs.style_audit.cli
  --fail-on-findings` or an exact path-scoped equivalent
- when a layout-cleanup slice reorganizes `apps/**`, `apps/api/tests/**`, or
  `scripts/docs/**`, any remaining flat public-boundary exception must be named
  explicitly in the phase plan or review instead of inherited from stale tree
  shape

If a needed edit falls outside the owned or allowed collateral surfaces, stop and either:

1. patch canon first
2. re-scope the work package
3. move the change into the owning phase

When adjacent phases both touch the same high-level subsystem, the phase pages
must state the ownership split explicitly enough that one phase does not own the
same contract family in parallel with another.

Use this split for the OpenClaw, plugin, CLI, and onboarding families:

- Phase 4A owns the exact OpenClaw Gateway RPC subset, protocol pin, dispatch-scoped Gateway transport, the immediate controller-owned per-dispatch ingest write seam, session/run binding, parent/root same-session continuity semantics, and the worker/new-attempt fresh-session rules.
- Phase 4B owns watchdog trigger/readback freeze, operator-MCP inventory, static v1 node-MCP surface exposure, explicit node-tool argument bridge documentation, operator-safe automation parity, and frozen support-state readbacks including `provider-events.ndjson`, but only as consumers of already-committed truth.
- Phase 4.5 owns the session-rooted authority simplification, removal of the separate callback-binding authority model, unified node/callback validation, prompt-layer dispatch-context collateral, final watchdog recovery narrowing to lineage-preserving `redispatch_same_attempt | escalate`, and ballast deletion that follows the already-landed Phase 4A ingest seam and Phase 4B committed-truth model.
- Phase 5A owns frozen public CLI noun families, public ingest/API alignment,
  and the definition-registry/task-start extensions to `operator MCP`.
- Phase 5B owns install, onboarding, package/reset, release, and docs cutover teaching.
- Phase 0 may patch execution-router references, the implementation file lock
  map, and the affected phase-contract pages only when a canon-fix is required
  to make ownership boundaries, allowed collateral, or phase-scoped closeout
  authority truthful.

## Appendix-owner routing

Use the current phase page for authoritative appendix owners:

- `docs/redesign/interfaces/api-schema-appendix.md`
- `docs/redesign/workflows/workflow-schema-appendix.md`
- `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md`

## Execution record home

- approved phase plans and WBS artifacts live under `docs/execution/plans/`
- executed validator, test, gate, reset, and smoke proof lives under `docs/execution/evidence/`
- mandatory review outputs, closeout reviews, and explicit exceptions live under `docs/execution/reviews/`

## Phase-scoped execution artifact allowance

- shared record-home READMEs, templates, and any retained historical summary
  artifacts remain Phase 0-owned execution canon
- the selected phase may create or update only its own phase-scoped plan,
  evidence, and review artifacts under those homes as allowed collateral
- cross-phase or aggregate summary records remain historical/Phase 0 canon
  surfaces only while they still add unique replacement-routing value; prune
  them in a Phase 0 canon-fix slice once authoritative phase-scoped
  replacements and router pages make them redundant

## Authoritative artifact rule

- each approved plan, executed evidence artifact, and mandatory review used to close work must name exactly one selected phase and therefore one current phase page
- execution-record artifacts must use one exact top-of-file block immediately
  after `Status:` in this order: `selected phase:`, `current phase page:`,
  `selected work packages:`, `summary-only:`, and `delegated slices:`
- when delegated slices are listed, execution-record artifacts must append one
  contiguous delegated-slice block per slice in this order: `slice id:`,
  `slice type:`, `owned surfaces:`, and `touched surfaces:`
- `summary-only: no` is the authoritative phase-scoped sentinel
- `summary-only: yes` is the historical-summary sentinel
- cross-phase or aggregate historical summaries that do not map to one
  selected phase page must use `selected phase: none`,
  `current phase page: none`, and `selected work packages: none`
- historical summary artifacts must include truthful `## Authoritative replacements`
  links that point only to `summary-only: no` replacement artifacts
- cross-phase or aggregate records may exist only as historical summaries, do
  not satisfy mandatory-review, reset-gate, or phase-done closure
  requirements, and should be deleted once they no longer add unique
  replacement-routing value

## Phase 0

### Phase 0 owned surfaces

- `AGENTS.md`, `STYLE.md`
- `docs/README.md`
- `docs/execution/README.md`
- shared execution-record home surfaces: `docs/execution/plans/README.md`,
  `docs/execution/plans/phase-plan-template.md`,
  `docs/execution/evidence/README.md`,
  `docs/execution/evidence/phase-evidence-template.md`, and
  `docs/execution/reviews/README.md`
- any retained historical cross-phase or aggregate execution summary artifacts
  under `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/` that still carry unique replacement-routing value
- `docs/execution/gates/*`
- `docs/execution/phases/*`
- `docs/execution/how-to/*`
- `docs/execution/maps/*`
- execution router pages under `docs/redesign/*/README.md` when execution routing depends on them
- docs tooling and validation references under `scripts/docs/*`

### Phase 0 allowed collateral surfaces

- affected redesign owner docs under `docs/redesign/**` when an explicit
  canon-fix is required to reconcile conflicting live target owner docs with
  execution routing, current/target contrast truth, or the implementation file
  lock map
- `docs/redesign/prompt-layer/*` when execution prompt-family ownership changes require prompt-layer alignment
- `README.md` when root execution routing changes
- `docs/current/**` when Phase 0 canon repair must make shipped seed-authority,
  reseed-semantics, cancel-behavior contrast truth, stale path cleanup,
  route-map repair, or truthful current-behavior docs repair explicit without
  reinterpreting later product contracts

### Phase 0 do not edit / defer surfaces

- repo code under `apps/**`, `definitions/**`, `scripts/**`,
  `pyproject.toml`, and `Makefile`, except docs tooling under `scripts/docs/*`
- shipped current-behavior pages beyond Phase 0 stale-path cleanup, route-map
  repair, and truthful current-behavior docs repair

### Phase 0 required tests and validators

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate` when prompt surfaces change
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate` before validation when prompt inputs or generated prompt pages change
- `ruff check scripts/docs` when `scripts/docs/*` changes
- `mypy scripts/docs` when `scripts/docs/*` changes

## Phase 0.5

### Phase 0.5 owned surfaces

- repo code under `apps/**`
- repo tests under `apps/api/tests/**`
- repo definition content under `definitions/**`
- repo scripts under `scripts/**`, except docs tooling under `scripts/docs/*`
- `pyproject.toml`
- `Makefile`

### Phase 0.5 allowed collateral surfaces

- `apps/api/autoclaw/**`

### Phase 0.5 do not edit / defer surfaces

- `docs/**`
- target contract pages under `docs/redesign/**`
- prompt-layer owner or generated surfaces unless a separate Phase 0 canon fix explicitly owns them

### Phase 0.5 required tests and validators

- retained infra tests and smoke evidence for reset, package entrypoints, and health viability
- `ruff format`
- `ruff check`
- `pyright`
- `mypy`
- `pytest`

## Phase 1

### Phase 1 owned surfaces

- `apps/api/app/schemas/*`
- `apps/api/app/compiler/*`
- internal definition identity, revision, and lookup persistence needed for compiler or runtime revision pinning under `apps/api/app/db/*`, `apps/api/app/registry/*`, or `apps/api/app/services/*` when those surfaces do not widen into public ingest or route work
- `definitions/**/*`
- `docs/redesign/workflows/workflow-definition-schema.md`
- `docs/redesign/workflows/task-compose-schema.md`
- `docs/redesign/workflows/typed-dependency-selectors-and-produce-slots.md`
- `docs/redesign/workflows/mode-contract-and-legality-matrix.md`
- `docs/redesign/workflows/criteria-and-parent-verification.md`
- `docs/redesign/workflows/criteria-projection-and-consumption-example.md`
- `docs/redesign/workflows/compiler-contract-and-launch-materialization.md`
- `docs/redesign/workflows/provider-direction-and-provider-native-capabilities.md`
- `docs/redesign/workflows/role-and-policy-example-definitions.md`
- `docs/redesign/workflows/examples/*`
- `docs/redesign/workflows/workflow-schema-appendix.md`

### Phase 1 allowed collateral surfaces

- compiler-facing tests under `apps/api/tests/*`
- narrow runtime or registry lookup surfaces when schema/compiler alignment or revision-pinning truth requires them
- the exact Phase 1 current-contrast pages named on the phase page when
  truthful schema/compiler/registry contrast repair is required
- existing shipped init/upgrade/reset shell under `apps/api/app/cli.py` only when Phase 1-owned persistence truth must be reachable through the shipped path without widening public CLI nouns or package/install ownership
- package-contained seed mirrors under `apps/api/app/resources/definitions/**` and narrow `pyproject.toml` package-data entries only when Phase 1-owned internal registry truth must ship its baseline seed assets without widening broader package/install ownership
- `docs/redesign/interfaces/role-and-policy-definition-schema.md` when role or
  policy compatibility detail must stay aligned with Phase 1 validation
- `docs/redesign/interfaces/definition-registry-and-upload-contract.md` and `docs/redesign/interfaces/guarded-registry-and-runtime-writes.md` when internal registry persistence or lookup truth must be made explicit before public ingest routes land
- repo-root `.gitignore` only when Phase 1-owned `definitions/**/*` fixtures
  would otherwise remain excluded from tracked repo truth

### Phase 1 do not edit / defer surfaces

- runtime assignment, attempt, checkpoint, dispatch, closure, and replan persistence beyond narrow lookup compatibility needed to stop later phases from reading repo files as authority
- gateway, watchdog, operator, and plugin surfaces
- public ingest, public definition routes, new CLI noun families, package/install/reset/release surfaces, or broader CLI UX beyond the narrow shipped-path proof wiring explicitly allowed above

### Phase 1 required tests and validators

- schema validation unit tests
- definition identity or revision persistence tests
- registry-backed role or policy lookup and revision-pinning tests
- shipped-path schema install, upgrade, and reset proof for SQLite when definition persistence truth changes
- Postgres + Docker strong verification when definition persistence truth changes and the lane is viable
- compiler normalization and legality integration tests
- example or fixture validation for minimal, normal, and maximal authored workflows

## Phase 2

### Phase 2 owned surfaces

- app-owned shipped prompt assets under `apps/api/app/runtime/prompt/assets/**`
- prompt assembly and section-render package surfaces under
  `apps/api/app/runtime/prompt/**`
- manifest, dispatch, and attempt materialization package surfaces under
  `apps/api/app/runtime/projection/**`
- task-root path, localization, and write package surfaces under
  `apps/api/app/runtime/task_root/**`
- narrow Phase 2-owned bootstrap helpers under
  `apps/api/app/runtime/launch/bootstrap/**`
- `docs/redesign/prompt-layer/*`
- `docs/redesign/architecture/manifest-contract.md`
- `docs/redesign/architecture/worker-context-contract.md`
- `docs/redesign/architecture/task-root-layout-and-generated-files.md`
- `docs/redesign/architecture/artifact-ref-and-storage-contract.md`

### Phase 2 allowed collateral surfaces

- prompt-generated example surfaces under `docs/redesign/prompt-layer/generated/*`
- prompt resource appendix and workflow schema appendix
- the exact Phase 2 current-contrast pages named on the phase page when
  truthful contrast repair is required for prompt, manifest, or task-root
  behavior
- narrow `pyproject.toml` package-data entries only when Phase 2-owned prompt
  assets must ship through the existing package path without widening broader
  package/install ownership
- targeted prompt validation tooling under `scripts/docs/*` when prompt-layer
  owner or generated surfaces change
- API presenters or runtime read models only where the prompt/runtime contract cannot otherwise be represented
- prompt, manifest, bootstrap, and e2e proof tests under `apps/api/tests/**`
  when they are required to prove Phase 2-owned prompt/render/materialization
  truth
- the selected Phase 2 plan/evidence/review artifacts under
  `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/`

### Phase 2 do not edit / defer surfaces

- parent/root review and structural replan semantics
- watchdog, operator, plugin, and support-state surfaces
- launch/open/abort foreground control-state handshake, replacement-dispatch
  inactivity proof, assignment/attempt/checkpoint currentness truth, and
  closure precondition truth, which remain Phase 3-owned
- public ingest, new CLI noun families, package/install/reset/release
  surfaces, or broader CLI UX beyond the narrow prompt-asset package-data
  allowance above

### Phase 2 required tests and validators

- prompt/render unit tests
- manifest projection and bootstrap integration tests
- minimal e2e lane when viable
- prompt-catalog generate/validate when prompt-layer owner or generated surfaces change

## Phase 3

### Phase 3 owned surfaces

- runtime control, assignment, attempt, checkpoint, closure, review, and
  replan services under `apps/api/app/runtime/*`
- runtime models under `apps/api/app/db/*`
- `apps/api/app/schemas/runtime/__init__.py`
- runtime schemas and presenters under `apps/api/app/schemas/*` and
  `apps/api/app/api/*`
- the foreground dispatch control-state handshake, including `launching`,
  `live`, `abort_requested`, `ambiguous`, drain-window deadlines, and the
  proof that a prior run is inactive before replacement dispatch opens
- runtime/review/replan owner docs under `docs/redesign/architecture/*` and `docs/redesign/workflows/*`

### Phase 3 allowed collateral surfaces

- worker-context, artifact, and API appendix owners when review, closure, or replan payloads need exact updates
- `docs/current/architecture/runtime-control-plane.md` and
  `docs/current/interfaces/api-trust-lanes.md` when truthful current-contrast
  repair is required for runtime control-state, operator or callback lane, or
  compatibility readback wording
- existing shipped init/upgrade/reset shell under `apps/api/app/cli.py` only when Phase 3-owned runtime persistence truth must be reachable through the shipped path without widening public CLI nouns or package/install ownership
- narrow task-scoped `/operator/tasks/{task_id}/snapshot`,
  `/operator/tasks/{task_id}/trace`, and `/observability/tasks/{task_id}/*`
  read shells, plus the exact presenter or read-model wiring they need, when
  Phase 3-owned runtime closure or readback truth must surface through
  compatibility reads without widening into watchdog recovery, standard
  external operator-safe MCP/plugin parity, or frozen support-state semantics
- runtime, schema, route, and e2e proof tests under `apps/api/tests/**` when
  they are required to prove Phase 3-owned control-state, persistence,
  closure, review, or replan truth
- the selected Phase 3 plan/evidence/review artifacts under
  `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/`

### Phase 3 do not edit / defer surfaces

- gateway/session/continuity implementation beyond narrow compatibility fixes
- watchdog recovery, standard external operator-safe MCP/plugin parity, and
  frozen support-state semantics beyond the narrow task-scoped
  `/operator/...` snapshot/trace and `/observability/...` read shells
  explicitly allowed above
- public ingest, new CLI noun families, package/install/reset/release surfaces, or broader CLI UX beyond the narrow shipped-path proof wiring explicitly allowed above
- Phase 2 prompt/render/materialization helpers except for narrow compatibility
  fixes required to land runtime truth cleanly

### Phase 3 required tests and validators

- runtime transition unit tests
- review, closure, and replan integration tests
- shipped-path schema install, upgrade, and reset proof for SQLite when runtime persistence truth changes
- Postgres + Docker strong verification when runtime persistence truth changes and the lane is viable
- normal e2e lane when viable

## Phase 4A

### Phase 4A owned surfaces

- OpenClaw gateway, bridge-normalization, dispatch-scoped ingest, session, and continuity services under `apps/api/app/runtime/*`
- `docs/redesign/architecture/openclaw-gateway-rpc-subset.md`
- `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md`
- `docs/redesign/architecture/openclaw-session-lifecycle.md`
- `docs/redesign/architecture/openclaw-continuity-and-send-modes.md`

### Phase 4A allowed collateral surfaces

- runtime presenters and API appendix surfaces for session and dispatch readbacks
- prompt resource appendix where session/continuation behavior affects worker delivery
- `apps/api/app/config.py` and `apps/api/app/main.py` when the runtime-owned
  Gateway adapter needs canonical OpenClaw/runtime config loading or lifespan
  startup wiring
- `docs/redesign/architecture/README.md` when the exact Gateway subset page
  must become the search-first owner for handshake or machine-control
  questions
- `docs/redesign/architecture/provider-worker-and-operator-boundary.md` when
  node attachment or callback-authorization wording must align with the Phase
  4A gateway subset contract
- narrow runtime DB/runtime-model surfaces when the immediate controller-owned ingest commit, session/run persistence, session/readback truth, or parent/root same-session redispatch persistence must land without widening into watchdog recovery or external MCP or package ownership
- the selected Phase 4A plan/evidence/review artifacts under
  `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/`

### Phase 4A do not edit / defer surfaces

- external operator-safe MCP surface exposure, package/profile attachment verification, watchdog consumption of committed truth, and support-state readback freezing, including `delivery-state.json`, `continuity-state.json`, `watchdog-state.json`, and `provider-events.ndjson`
- public ingest/API/CLI packaging surfaces

### Phase 4A required tests and validators

- session, continuity, worker-lane, and immediate-ingest integration tests
- golden handshake or machine-control fixture verification
- startup compatibility-check proof for protocol version, required methods, and
  required scopes
- live Gateway compatibility proof for `agent`, `agent.wait`, and
  `sessions.abort`
- viable minimal and normal e2e lanes

## Phase 4B

### Phase 4B owned surfaces

- watchdog and monitor services under `apps/api/app/runtime/*`
- the repo-local plugin or parity-wrapper source tree under
  `apps/api/autoclaw/openclaw/**` created during Phase 4B from a target-only
  rebuild boundary
- `docs/redesign/interfaces/mcp-plugin-and-cli-boundary.md`
- `docs/redesign/interfaces/plugin-tool-reference.md`
- `docs/redesign/interfaces/human-and-operator-control-surface.md`
- `docs/redesign/interfaces/api-surface-and-trust-lane-map.md`
- `docs/redesign/interfaces/operator-definition-and-role-boundary.md`
- `docs/redesign/architecture/runtime-monitoring-and-watchdog-automation.md`
- `docs/redesign/architecture/runtime-observability-and-boundary-log.md`
- `docs/redesign/architecture/watchdog-and-recovery-contract.md`

### Phase 4B allowed collateral surfaces

- runtime database/support-state docs and API appendix owner pages
- narrow OpenClaw dispatch read models needed for watchdog or operator evidence after the Phase 4A ingest seam commits them
- the already-legalized shared Phase 3 runtime write and node-operation seams under `apps/api/app/runtime/effects/writes.py` and `apps/api/app/runtime/control/node_operations.py` when Phase 4B parity work must consume those shared boundaries without reopening broader Phase 3 ownership or the Phase 4A first-ingest seam
- `apps/api/app/config.py` and `apps/api/app/main.py` when watchdog or MCP
  wrapper wiring needs canonical runtime config loading or lifespan startup
  wiring
- narrow package metadata surfaces such as `pyproject.toml`,
  `apps/api/requirements.txt`, and `apps/api/requirements-dev.txt` when the
  repo-local OpenClaw wrapper needs one explicit MCP-server dependency and the
  slice does not widen into install/reset/release ownership
- the narrow shared current-definition catalog read surface under
  `apps/api/app/registry/definition_catalog.py` plus the exact definition read
  schemas it needs when dispatch-bound structural edits surface the
  current-only `role` / `policy` lookup lane without widening into
  revision-history/upload/task-start ownership
- `docs/redesign/interfaces/api-surface-and-trust-lane-map.md` when Phase 4B
  must lock MCP surface attachment or task-scoped observability-tool wording
  without widening public noun-family ownership
- `docs/redesign/interfaces/README.md` and `docs/redesign/interfaces/INDEX.md`
  when the new Phase 4B owner page must become the search-first front door for
  MCP surface questions
- `docs/redesign/architecture/provider-worker-and-operator-boundary.md` and
  `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md` when
  Phase 4B must align the trust split or OpenClaw attachment wording with the
  new MCP boundary owner page
- `docs/redesign/architecture/openclaw-gateway-rpc-subset.md` only when the
  Phase 4B proof requirements must reference the already-frozen Phase 4A
  Gateway subset without widening Phase 4B into gateway payload ownership
- the narrow shared operator wrapper files `apps/api/autoclaw/openclaw/common.py`,
  `apps/api/autoclaw/openclaw/operator_server.py`,
  `apps/api/autoclaw/openclaw/__init__.py`, and the split implementation
  package `apps/api/autoclaw/openclaw/operator_mcp/**` when the Phase 4B
  operator/node inventory proof must coexist with later Phase 5A operator
  parity in the same wrapper tree without claiming Phase 5A
  definition/task-start ownership
- the selected Phase 4B plan/evidence/review artifacts under
  `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/`
- `docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md`
  and `docs/execution/maps/file-priority-map.md` when the closeout chain needs
  exact Phase 4B ownership or allowed-collateral wording refreshed to match the
  landed MCP boundary, support-state, or watchdog proof lanes

### Phase 4B do not edit / defer surfaces

- gateway/session core semantics, the dispatch-scoped Gateway reader, the immediate controller-owned ingest write seam, and session-authority simplification except follow-on fixes discovered through watchdog work
- definition discovery, guarded upload, and task-start parity on `operator MCP`
  because those remain Phase 5A-owned public noun extensions
- public ingest/API/CLI and packaging/release surfaces

### Phase 4B required tests and validators

- watchdog/operator/plugin integration tests against committed truth
- support-state schema or example verification for `delivery-state.json`,
  `continuity-state.json`, `watchdog-state.json`, and
  `provider-events.ndjson`
- profile or session separation proof showing `operator MCP` and `node MCP`
  never appear as one mixed runtime-effective tool inventory
- viable minimal, normal, and maximal e2e lanes

## Phase 4.5

### Phase 4.5 owned surfaces

- session-authority collapse, callback and node validation unification, redispatch continuity, prompt cleanup, projection cleanup, and final watchdog narrowing or ballast-deletion implementation under `apps/api/app/runtime/*`
- runtime DB/model and schema surfaces under `apps/api/app/db/*` and `apps/api/app/schemas/*` when they own authority, continuity, or removed-field truth
- static v1 node-MCP wrapper surfaces under `apps/api/autoclaw/openclaw/**`
- touched regression, schema-contract, prompt, and e2e proof surfaces under `apps/api/tests/integration/phase3/**`, `apps/api/tests/integration/phase4a/**`, `apps/api/tests/integration/phase4b/**`, `apps/api/tests/integration/runtime_schema_contract/**`, `apps/api/tests/e2e/**`, and `apps/api/tests/unit/runtime_prompt_rendering/**`
- `docs/redesign/architecture/runtime-records-and-lifecycle.md`
- `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
- `docs/redesign/architecture/runtime-database-and-object-contract.md`
- `docs/redesign/architecture/openclaw-session-lifecycle.md`
- `docs/redesign/architecture/openclaw-continuity-and-send-modes.md`
- `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md`
- `docs/redesign/interfaces/mcp-plugin-and-cli-boundary.md`
- `docs/redesign/interfaces/plugin-tool-reference.md`
- `docs/redesign/interfaces/api-surface-and-trust-lane-map.md`
- `docs/redesign/interfaces/api-schema-appendix.md`
- `docs/redesign/architecture/provider-worker-and-operator-boundary.md`
- `docs/redesign/architecture/watchdog-and-recovery-contract.md`
- `docs/redesign/architecture/watchdog-and-provider-recovery.md`
- `docs/redesign/prompt-layer/contract.md`
- `docs/redesign/prompt-layer/source-and-sections.md`
- `docs/redesign/prompt-layer/render-and-persistence.md`
- `docs/redesign/prompt-layer/generated/*`
- `docs/redesign/prompt-layer/prompt-catalog.yaml`
- `docs/execution/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md`

### Phase 4.5 allowed collateral surfaces

- prompt-layer owner docs, generated prompt docs, and prompt-catalog inputs when `full_prompt`-only truth or dispatch-local `task_id` and `session_key` tool context must stay aligned without widening into broader docs-tooling ownership
- the exact Phase 4.5 current-contrast pages named on the phase page when deleted readback or prompt-compatibility debt must remain truthful as shipped contrast only
- narrow observability/readback docs when support-state wording must stop teaching callback-binding authority or fresh-session-per-dispatch target truth without reopening the Phase 4B committed-truth freeze
- `docs/redesign/README.md`, `docs/redesign/interfaces/README.md`, and `docs/redesign/interfaces/INDEX.md` when the search-first routing pages must stop teaching session-bound or hidden-binding target truth
- `apps/api/app/config.py` and `apps/api/app/main.py` when runtime-owned session/continuity wiring or config loading must change
- the selected Phase 4.5 plan, evidence, and review artifacts under `docs/execution/plans/`, `docs/execution/evidence/`, and `docs/execution/reviews/`
- the final strict closeout review slice may own only `docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`

### Phase 4.5 do not edit / defer surfaces

- public ingest/API/CLI noun-family work that remains Phase 5A-owned
- packaging/release/install/reset surfaces that remain Phase 5B-owned
- unrelated registry, frontend, or plugin work that does not participate in the selected Phase 4.5 proof lanes
- the Phase 4A dispatch-scoped Gateway reader and immediate controller-owned ingest write seam except for narrow ballast-removal follow-ons that do not redefine their ownership
- support-state field-set freezing beyond fields that still drive or directly explain behavior; non-behavioral support-state, readback, prompt-compatibility, schema, and test debt is Phase 4.5 deletion material, not protected ballast

### Phase 4.5 required tests and validators

- unified runtime authority rejection and redispatch integration tests
- explicit-arg callback/node-MCP validation tests
- parent/root same-session redispatch tests
- prompt hygiene and dispatch-local node-tool-context tests
- watchdog same-attempt redispatch versus escalation tests
- support/readback omission and runtime schema-contract tests after removed-field cleanup
- viable minimal, normal, and maximal e2e lanes
- shipped-path SQLite smoke/reset proof when runtime or persistence truth changes
- Postgres + Docker strong verification when runtime or persistence truth changes
- real OpenClaw host proof before closeout

## Phase 5A

### Phase 5A owned surfaces

- definition ingest and upload services under `apps/api/app/registry/*` and
  `apps/api/app/services/*`
- public API route and presenter surfaces under `apps/api/app/api/*`
- root CLI entrypoints under `apps/api/app/cli.py`
- `docs/redesign/interfaces/definition-registry-and-upload-contract.md`
- `docs/redesign/interfaces/definition-ingest-and-upload-contract.md`
- `docs/redesign/interfaces/cli-surface-and-operator-workflows.md`
- `docs/redesign/interfaces/api-surface-and-trust-lane-map.md`
- `docs/redesign/interfaces/api-schema-appendix.md`

### Phase 5A allowed collateral surfaces

- compiler or schema surfaces when public ingest payloads require exact alignment
- the concrete `operator MCP` definition/task-start parity wrapper under
  `apps/api/autoclaw/openclaw/operator_server.py`, its narrow shared helper
  module `apps/api/autoclaw/openclaw/common.py`, and the split implementation
  package `apps/api/autoclaw/openclaw/operator_mcp/**` when Phase 5A extends
  the same public/operator noun family without widening the Phase 4B trust
  boundary
- narrow Phase 4B MCP test surfaces only when later-phase operator inventory
  proof must move out of a previously Phase 4B-owned test file without
  widening trust-boundary semantics
- onboarding examples and required tutorials that demonstrate the public CLI/API nouns
- required current-contrast pages named by the Phase 5A page when those pages
  must stop teaching stale ingest, task-start, or file-upload framing

### Phase 5A do not edit / defer surfaces

- packaging, install/reset, release, and docs archive cutover surfaces
- gateway/watchdog/plugin contract pages except doc fixes needed for consistent public nouns
- the Phase 4B-owned MCP boundary page and the Phase 4B-owned MCP attachment
  wording on `docs/redesign/interfaces/api-surface-and-trust-lane-map.md`
  except narrow public-noun consistency fixes

### Phase 5A required tests and validators

- ingest/API/CLI unit tests
- public-surface integration tests
- all viable e2e lanes

## Phase 5B

### Phase 5B owned surfaces

- `pyproject.toml`
- `Makefile`
- `scripts/*`
- `docs/redesign/interfaces/testing-and-release-checklist.md`
- `docs/redesign/interfaces/release-and-install-strategy.md`
- `docs/redesign/interfaces/distribution-and-database-support-matrix.md`
- `docs/redesign/how-to/install-and-onboard.md`
- `docs/redesign/how-to/use-postgres.md`
- `docs/redesign/how-to/run-local-sqlite.md`
- `docs/redesign/how-to/publish-a-release.md`
- `docs/redesign/tutorials/onboard-locally.md`
- `docs/redesign/tutorials/end-to-end-redesign-walkthrough.md`
- install, release, onboarding, and cutover docs that teach those canonical surfaces
- root/router docs that must point to the final canonical surfaces
- archive cleanup under `docs/archive/*`

### Phase 5B allowed collateral surfaces

- CLI docs and examples when package or reset behavior changes their invocation story
- current docs router pages when cutover needs them to point cleanly back to canon

### Phase 5B do not edit / defer surfaces

- core runtime, compiler, gateway, watchdog, plugin, and public API semantics except doc corrections required for cutover

### Phase 5B required tests and validators

- package, install, and reset smoke checks
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- repo link and router audit
- all viable e2e lanes when packaging or reset changes can invalidate prior evidence

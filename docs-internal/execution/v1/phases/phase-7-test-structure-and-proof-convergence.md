# Phase 7 proof pattern, leak cleanup, and test structure convergence

Status: Reference

This phase now starts with the proof and teaching debt that remained after Phase 6: it inventories and removes execution-phase or internal-doc leak language from shipped code, converges runtime and watchdog wait patterns used by proof helpers, and removes broad shared timing defaults that make the suite slow by default. Once those seams are clean, it converges the test tree toward feature and boundary owners, removes phase-history as the primary test axis, cleans up cross-lane imports and path-segment heuristics, and keeps the command matrix stable while making proof easier to audit.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary design pages

- [Testing and release checklist](../../../design/v1/interfaces/testing-and-release-checklist.md)
- [Runtime lifecycle overview](../../../design/v1/architecture/runtime-lifecycle-overview.md)
- [Parent/root release and closure](../../../design/v1/workflows/parent-root-release-and-closure.md)
- [CLI, API, and package shape](../../../design/v1/interfaces/cli-api-and-package-shape.md)

## Required supporting design reads

- [Minimal workflow reference](../../../design/v1/workflows/examples/minimal.md)
- [Normal workflow reference](../../../design/v1/workflows/examples/normal.md)
- [Maximal workflow reference](../../../design/v1/workflows/examples/maximal.md)
- [Provider, worker, and operator boundary](../../../design/v1/architecture/provider-worker-and-operator-boundary.md)
- [MCP, plugin, and CLI boundary](../../../design/v1/interfaces/mcp-plugin-and-cli-boundary.md)
- [Run the design target on local SQLite](../../../design/v1/how-to/run-local-sqlite.md)
- [Use Postgres in the design target](../../../design/v1/how-to/use-postgres.md)

## Required standards reads

- [Test structure standard](../../../../.agents/standards/structure/test-structure.md)
- [Repo layout standard](../../../../.agents/standards/structure/repo-layout.md)
- [Source layout standard](../../../../.agents/standards/structure/source-layout.md)
- [Integration boundary standard](../../../../.agents/standards/structure/integration-boundaries.md)
- [Naming standard](../../../../.agents/standards/code/naming.md)

## Required current contrast reads

- [Run the current Docker and Postgres verification lane](../../../current/v1/operations/run-docker-postgres-verification.md)
- [Verify current install and runtime](../../../current/v1/operations/verify-current-install-and-runtime.md)
- [Current architecture](../../../current/v1/architecture/current-architecture.md)
- [API surface and route map](../../../current/v1/interfaces/api-surface-and-route-map.md)

## Required examples and diagrams

- the progressive workflow-lane matrix in [Progressive e2e workflow lanes](progressive-e2e-workflow-lanes.md)
- the minimal, normal, and maximal workflow examples named above

## Implementation surfaces

- owned surfaces: `apps/api/tests/**`, `scripts/testing/**`, `Makefile` when grouped runners or proof commands need alignment without renaming the public command matrix, maintainer or execution docs that describe the proof lanes, and `apps/api/src/autoclaw/**` when removing execution-roadmap or internal-doc leak language from shipped operator, CLI, HTTP, runtime, persistence, or integration surfaces, or converging proof-seam wait ownership without intentional product-behavior change
- allowed collateral surfaces: `docs/**`, `docs-internal/current/v1/**`, `docs-internal/execution/v1/**`, and `scripts/docs/**` when proof-lane routing, docs-freeze rules, or source-side teaching cleanup must stay aligned with the landed wait or leak-cleanup work; narrow proof tests under `apps/api/tests/**` when source-side leak cleanup changes locked assertions; and the selected Phase 7 plan, evidence, and review artifacts under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`

## Do not edit / defer surfaces

- source-tree relayout and package-authority work that remains Phase 6-owned
- command-surface renames for the repo-wide test matrix; if the public command matrix itself must change, stop and patch canon first
- externally visible API, CLI, MCP, or persistence contract changes beyond neutral wording cleanup, neutral metadata renames, or proof-seam wait convergence
- intentional runtime, API, CLI, or product behavior changes beyond narrow proof-seam cleanup

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagent slices
- subagents are useful here for source-side leak cleanup, shared helper or timing cleanup, tree migration, grouped-runner alignment, or review-only proof-lane inspection
- the parent agent owns final leak classification, wait-pattern decisions, runner coverage equivalence, and the proof call that the reorganized suite still covers the same behavior
- review-only subagents should start only after full `P7-WP3` and again at final closeout

## Wave integration loop

1. freeze the illegal-versus-allowed phase and internal-doc terms before changing source strings or persisted defaults
2. converge shared wait patterns and broad timing defaults before broad tree migration
3. prefer predicate-driven or wakeup-driven proof helpers over stacked `range + wait + drive + sleep` loops
4. land source-side leak cleanup before updating tests that intentionally lock the old strings
5. migrate one helper family, proof lane, or feature family at a time rather than renaming the entire suite in one pass
6. run the affected lane after each integrated move
7. run the full backend matrix only after leak cleanup, wait-pattern cleanup, and lane boundaries stabilize

## Phase purpose

Make proof surfaces describe current product behavior instead of repo execution history, converge test waiting on one explicit pattern, and then make the test tree reflect product and boundary ownership instead of redesign history while preserving or strengthening proof quality.

## Success criteria

- shipped operator, CLI, HTTP, runtime, persistence, and integration surfaces do not expose internal execution-phase chronology or internal-doc teaching unless the field is explicitly historical or test-only
- shared test contexts do not widen `dispatch_drain_timeout_seconds` broadly by default; long-drain semantics opt in per explicit proof case
- runtime and watchdog proof helpers converge on one documented pattern instead of stacked `range + wait + drive + sleep` loops
- any remaining direct sleep or polling in tests has an exact boundary reason and stays narrow
- phase-numbered test directories no longer act as the primary owner surface
- no cross-lane imports remain between unit, integration, and e2e trees for ordinary support code
- grouped runners preserve the full proof coverage of the commands they replace
- the repo-native test command matrix stays stable and green

## Deliverables

- source-side leak inventory and cleanup
- converged wait-pattern and timing-default rules
- feature-owned test tree
- helper and fixture convergence
- runner and proof-lane alignment

## Milestones

- leak inventory and kill-list frozen
- wait-pattern target and timing-default rules locked
- source-side leak cleanup complete
- helper extraction and wait cleanup complete
- lane-boundary cleanup complete
- grouped runners and proof docs aligned

## Ordered work packages

### `P7-WP0`

- objective: inventory all execution-phase and internal-doc leak language still present in shipped code, tests, and proof-teaching surfaces, and freeze the legal-versus-illegal term set before source cleanup begins
- owned surfaces: Phase 7 docs, plan artifacts, source and test search inventory, and narrow proof assertions only when the inventory must mark a term as intentional historical or test-only data
- dependencies: `Phase 6`
- test-first requirement: exact repo searches proving the current leak set before any rename wave
- documentation update requirement: the Phase 7 page, file lock map, and selected plan must agree about legal historical/test-only terms versus illegal shipped teaching
- subagent allowed: yes
- closeout evidence: frozen leak inventory that distinguishes shipped-source leaks from legitimate historical or test-only data

### `P7-WP1`

- objective: define and land the steady-state wait and timing pattern for proof helpers before broader tree migration
- owned surfaces: `apps/api/tests/helpers/**`, shared integration or e2e support helpers, `apps/api/src/autoclaw/runtime/post_commit/**`, `apps/api/src/autoclaw/runtime/watchdog/**`, and narrow interface or integration helpers when wait ownership must centralize
- dependencies: `P7-WP0`
- test-first requirement: focused failing or gap-revealing proof around the affected helper or wait contract
- documentation update requirement: the test-structure and Phase 7 docs must state when to use `wait_for_runtime_effects(...)`, `drive_runtime_until(...)`, `drive_watchdog_until(...)`, and any allowed narrow polling
- subagent allowed: yes
- closeout evidence: shared helper stacks no longer widen drain defaults broadly and no longer rely on redundant `range + wait + drive + sleep` loops

### `P7-WP2`

- objective: remove execution-phase and internal-doc language from shipped code and persisted default metadata where that language is not legitimate historical or test-only data
- owned surfaces: shipped operator, CLI, HTTP, runtime, persistence, definitions, and integration surfaces under `apps/api/src/autoclaw/**`, plus the exact tests that lock those strings
- dependencies: `P7-WP0`, `P7-WP1`
- test-first requirement: search inventory plus focused assertions for the renamed strings or metadata values
- documentation update requirement: maintainer or execution docs must describe the product-facing rule without reintroducing roadmap language as the source of truth
- subagent allowed: yes
- closeout evidence: no illegal execution-phase or internal-doc leak strings remain in shipped source surfaces

### `P7-WP3`

- objective: finish shared helper cleanup, remove broad timing ballast, and converge lane-local proof support on the documented wait pattern
- owned surfaces: `apps/api/tests/helpers/**`, lane-local support modules, shared runtime or watchdog wait helpers, and narrow affected proof tests
- dependencies: `P7-WP1`, `P7-WP2`
- test-first requirement: affected-lane smoke runs and focused helper or fixture proof
- documentation update requirement: support-only helper ownership and the narrow long-drain opt-in rule stay explicit
- subagent allowed: yes
- closeout evidence: broad shared `30s` drain overrides are gone or explicitly isolated to the small set of tests that prove long-drain behavior

### `P7-WP4`

- objective: replace phase-history test ownership with feature, boundary, or product owners beneath the existing top-level lanes, and remove cross-lane imports
- owned surfaces: `apps/api/tests/unit/**`, `apps/api/tests/integration/**`, `apps/api/tests/e2e/**`, and matching maintainer or execution docs
- dependencies: `P7-WP1`, `P7-WP2`, `P7-WP3`
- test-first requirement: gap-revealing lane snapshots or selection lists before moving families
- documentation update requirement: proof-lane docs update in the same phase
- subagent allowed: yes
- closeout evidence: phase-numbered directories no longer act as the primary owner map and cross-lane helper imports are removed

### `P7-WP5`

- objective: align grouped runners, maintainer docs, and proof evidence with the new owner map and wait pattern while preserving the existing command matrix
- owned surfaces: `scripts/testing/**`, `Makefile`, maintainer docs, current docs, execution docs, and final proof-lane inventory
- dependencies: `P7-WP1`, `P7-WP2`, `P7-WP3`, `P7-WP4`
- test-first requirement: before-and-after suite inventory proving grouped-runner coverage equivalence
- documentation update requirement: the test command matrix, wait-pattern rule, and proof-lane docs remain exact
- subagent allowed: yes
- closeout evidence: grouped runners and maintainer docs match the reorganized suite without changing the public command matrix

## Mandatory checklist

- [ ] top-level test lanes remain `unit`, `integration`, and `e2e`
- [ ] no shipped source surface leaks internal execution-phase chronology or internal-doc teaching unless the term is explicitly historical or test-only
- [ ] broad shared timing defaults do not reset the fast template baseline without an explicit test-local proof reason
- [ ] `wait_for_runtime_effects(...)` is not used as an outer retry loop when a predicate-driven runtime or watchdog helper is the right owner
- [ ] remaining direct sleeps or polling loops are narrow, justified, and boundary-specific
- [ ] phase-numbered directories are removed or reduced to temporary bridges only
- [ ] no unit-to-integration or e2e-to-integration imports remain for ordinary helper use
- [ ] shared helpers are support-only and named explicitly
- [ ] `conftest.py` does not use phase-directory path parsing as the long-term owner model
- [ ] grouped runners preserve the same proof coverage and readable progress
- [ ] any subagent slice stayed inside leak cleanup, wait cleanup, tree migration, runner, or docs-proof ownership

## Required tests

- `make check-api`
- `make pyright-api`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
- `make test-api`
- `make test-api-integration-local`
- `make test-api-db`
- all viable `make test-api-e2e-*` lanes
- any lane-specific smoke runs used while migrating the affected families
- `ruff check scripts/docs` and `mypy scripts/docs` when `scripts/docs/**` changes
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when maintainer, current, execution, or standards docs change

## Required docs and examples

- maintainer testing docs
- execution docs that describe the proof-lane matrix
- the workflow examples and lane matrix named above when touched docs depend on them

## Candidate delegated slices

- leak-inventory and source-string cleanup slice
- runtime and watchdog wait-pattern cleanup slice
- shared test-helper and timing cleanup slice
- tree-migration slice
- runner and maintainer-docs slice

## Exit evidence

- the illegal phase and internal-doc leak set is eliminated from shipped source surfaces
- wait and timing helpers use the documented steady-state pattern
- the test tree reflects feature or boundary owners instead of redesign-era phases
- the full repo-native backend test matrix stays green
- proof routing is easier to audit and no longer depends on historical phase naming or helper-local timing folklore

## Reset criteria

- apply the reset gate when grouped runners, DB lanes, package-install proof commands, or persisted default metadata change in a way that can invalidate prior proof expectations

## Kill-list terms

- phase chronology in shipped source strings or default metadata
- internal-doc teaching in product-facing or operator-facing instructions
- broad shared timeout escalation
- stacked `range + wait + drive + sleep` helper loops
- phase-numbered test trees as steady-state owners
- cross-lane helper imports
- path-segment test control planes
- grouped runners with hidden coverage loss

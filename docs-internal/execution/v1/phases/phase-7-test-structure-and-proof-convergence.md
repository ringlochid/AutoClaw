# Phase 7 test structure and proof convergence

Status: Reference

This phase lands the repo-wide standards refactor for tests and proof lanes after source ownership is clearer: it converges the test tree toward feature and boundary owners, removes phase-history as the primary test axis, cleans up cross-lane imports and path-segment heuristics, and keeps the command matrix stable while making proof easier to audit.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary design pages

- [Testing and release checklist](../../../design/v1/interfaces/testing-and-release-checklist.md)
- [Runtime lifecycle overview](../../../design/v1/architecture/runtime-lifecycle-overview.md)
- [Parent/root release and closure](../../../design/v1/workflows/parent-root-release-and-closure.md)

## Required supporting design reads

- [Minimal workflow reference](../../../design/v1/workflows/examples/minimal.md)
- [Normal workflow reference](../../../design/v1/workflows/examples/normal.md)
- [Maximal workflow reference](../../../design/v1/workflows/examples/maximal.md)
- [Run the design target on local SQLite](../../../design/v1/how-to/run-local-sqlite.md)
- [Use Postgres in the design target](../../../design/v1/how-to/use-postgres.md)

## Required standards reads

- [Test structure standard](../../../../.agents/standards/structure/test-structure.md)
- [Repo layout standard](../../../../.agents/standards/structure/repo-layout.md)
- [Source layout standard](../../../../.agents/standards/structure/source-layout.md)
- [Integration boundary standard](../../../../.agents/standards/structure/integration-boundaries.md)

## Required current contrast reads

- [Run the current Docker and Postgres verification lane](../../../current/v1/operations/run-docker-postgres-verification.md)
- [Verify current install and runtime](../../../current/v1/operations/verify-current-install-and-runtime.md)
- [Current architecture](../../../current/v1/architecture/current-architecture.md)

## Required examples and diagrams

- the progressive workflow-lane matrix in [Progressive e2e workflow lanes](progressive-e2e-workflow-lanes.md)
- the minimal, normal, and maximal workflow examples named above

## Implementation surfaces

- owned surfaces: `apps/api/tests/**`, `scripts/testing/**`, `Makefile` when grouped runners or proof commands need alignment without renaming the public command matrix, and maintainer or execution docs that describe the proof lanes
- allowed collateral surfaces: `apps/api/app/**`, `apps/api/autoclaw/**`, and `apps/api/src/autoclaw/**` only when a shared helper must be promoted to a public non-underscored source surface or a stable fixture seam must move out of an accidental private source helper without changing behavior; `docs/reference/maintainers/**`, `docs-internal/current/v1/operations/**`, and `docs-internal/execution/v1/**` when test-lane routing or proof instructions must be updated; and the selected Phase 7 plan, evidence, and review artifacts under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`

## Do not edit / defer surfaces

- source-tree relayout and package-authority work that remains Phase 6-owned
- command-surface renames for the repo-wide test matrix; if command expectations themselves must change, stop and route the canon patch before landing that change
- intentional runtime, API, CLI, or product behavior changes beyond narrow test-seam cleanup

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for unit-tree migration, integration-tree migration, e2e helper cleanup, or review-only proof-lane inspection
- the parent agent owns final lane-boundary decisions, runner coverage equivalence, and the proof call that the reorganized suite still covers the same behavior

## Wave integration loop

1. freeze the Phase 6 source-owner paths before moving the matching test owners
2. migrate one proof lane or feature family at a time rather than renaming the entire suite in one pass
3. integrate helper and fixture extraction before collapsing the old phase-owned directories
4. run the affected lane after each integrated move
5. run the full backend matrix only after the reorganized lane boundaries stabilize

## Phase purpose

Make the test tree reflect product and boundary ownership instead of redesign history while preserving or strengthening proof quality.

## Success criteria

- phase-numbered test directories no longer act as the primary owner surface
- no cross-lane imports remain between unit, integration, and e2e trees
- shared helpers live under explicit helper owners and stay support-only
- path-segment heuristics in `conftest.py` are replaced by clearer markers or fixtures
- grouped runners preserve the full proof coverage of the commands they replace
- the repo-native test command matrix stays stable and green

## Deliverables

- feature-owned test tree
- helper and fixture convergence
- runner and proof-lane alignment

## Milestones

- test owner map frozen
- helper extraction complete
- lane-boundary cleanup complete
- oversized test files split
- grouped runners and proof docs aligned

## Ordered work packages

### `P7-WP1`

- objective: replace phase-history test ownership with feature, boundary, or product owners beneath the existing top-level lanes
- owned surfaces: `apps/api/tests/unit/**`, `apps/api/tests/integration/**`, `apps/api/tests/e2e/**`, and matching maintainer or execution docs
- dependencies: `Phase 6`
- test-first requirement: gap-revealing lane snapshots or selection lists before moving families
- documentation update requirement: proof-lane docs update in the same phase
- subagent allowed: yes
- closeout evidence: phase-numbered directories no longer act as the primary owner map

### `P7-WP2`

- objective: extract shared helpers and fixtures into explicit helper owners and remove cross-lane imports
- owned surfaces: `apps/api/tests/helpers/**`, lane-local fixtures, and test support docs
- dependencies: `P7-WP1`
- test-first requirement: helper or fixture usage search plus affected-lane smoke runs
- documentation update requirement: helper ownership and support-only status stay explicit
- subagent allowed: yes
- closeout evidence: unit, integration, and e2e lanes no longer import each other for ordinary support code

### `P7-WP3`

- objective: replace path-segment heuristics and accidental lane coupling with explicit fixtures or markers
- owned surfaces: `apps/api/tests/conftest.py`, lane fixtures, runner support, and execution docs
- dependencies: `P7-WP1`, `P7-WP2`
- test-first requirement: failing or gap-revealing tests around the affected fixtures or marker behavior
- documentation update requirement: proof instructions and runner behavior remain exact
- subagent allowed: yes
- closeout evidence: lane setup no longer depends on phase-directory path parsing as the main control plane

### `P7-WP4`

- objective: split oversized test files by feature or contract owner without reducing coverage clarity
- owned surfaces: oversized test files and their immediate helper families
- dependencies: `P7-WP1`, `P7-WP2`, `P7-WP3`
- test-first requirement: assertion or coverage-preservation review before extraction
- documentation update requirement: test file naming stays aligned with the proved behavior
- subagent allowed: yes
- closeout evidence: readers can find proof by feature or boundary owner rather than by one giant catch-all test file

### `P7-WP5`

- objective: align grouped runners, maintainers docs, and proof evidence with the new test owner map while preserving the existing command matrix
- owned surfaces: `scripts/testing/**`, `Makefile`, maintainer docs, and execution docs
- dependencies: `P7-WP1`, `P7-WP2`, `P7-WP3`, `P7-WP4`
- test-first requirement: before and after suite inventory proving grouped-runner coverage equivalence
- documentation update requirement: the test command matrix and proof-lane docs remain exact
- subagent allowed: yes
- closeout evidence: grouped runners and maintainer docs match the reorganized suite without changing the public command matrix

## Mandatory checklist

- [ ] top-level test lanes remain `unit`, `integration`, and `e2e`
- [ ] phase-numbered directories are removed or reduced to temporary bridges only
- [ ] no unit-to-integration or e2e-to-integration imports remain for ordinary helper use
- [ ] shared helpers are support-only and named explicitly
- [ ] `conftest.py` does not use phase-directory path parsing as the long-term owner model
- [ ] oversized test files are split by behavior, feature, or contract owner
- [ ] grouped runners preserve the same proof coverage and readable progress
- [ ] any subagents slice stayed inside lane migration, helper extraction, runner,
      or docs-proof ownership

## Required tests

- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
- `make test-api`
- `make test-api-integration-local`
- `make test-api-db`
- all viable `make test-api-e2e-*` lanes
- any lane-specific smoke runs used while migrating the affected families
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when maintainer or execution docs change

## Required docs and examples

- maintainer testing docs
- execution docs that describe the proof-lane matrix
- the workflow examples and lane matrix named above when touched docs depend on them

## Candidate delegated slices

- unit-tree migration slice
- integration-tree migration slice
- e2e helper and marker cleanup slice
- runner and maintainer-docs slice

## Exit evidence

- the test tree reflects feature or boundary owners instead of redesign-era phases
- the full repo-native backend test matrix stays green
- proof routing is easier to audit and no longer depends on historical phase naming

## Reset criteria

- apply the reset gate when grouped runners, DB lanes, or package-install proof commands change in a way that can invalidate prior proof expectations

## Kill-list terms

- phase-numbered test trees as steady-state owners
- cross-lane helper imports
- path-segment test control planes
- giant catch-all proof files
- grouped runners with hidden coverage loss

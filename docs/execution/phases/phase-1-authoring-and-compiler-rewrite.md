# Phase 1 authoring and compiler rewrite

Status: Target

This phase lands the tree-only authoring model and the compiler rewrite that makes it executable.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Phase entry rule

Phase 0 is the baseline prerequisite for this phase.

Phase 0.5 is conditional routing guidance, not a blanket closed prerequisite:

- route to Phase 0.5 first when stale repo shape, reset baseline ambiguity,
  stale tests, or plugin-boundary drift still dominate the selected blocker
- stay in Phase 1 when the blocker is Phase 1-owned authoring, compiler, or
  internal definition-truth work and Phase 0.5 reset conditions are not the
  actual blocker
- if Phase 1 work uncovers a stale-shape or reset blocker, stop and route back
  to the earliest blocking phase instead of patching forward inside Phase 1

## Primary redesign pages

- [Workflow definition schema](../../redesign/workflows/workflow-definition-schema.md)
- [Task-compose schema](../../redesign/workflows/task-compose-schema.md)
- [Typed dependency selectors and produce slots](../../redesign/workflows/typed-dependency-selectors-and-produce-slots.md)
- [Mode contract and legality matrix](../../redesign/workflows/mode-contract-and-legality-matrix.md)
- [Criteria and parent verification](../../redesign/workflows/criteria-and-parent-verification.md)
- [Criteria projection and consumption example](../../redesign/workflows/criteria-projection-and-consumption-example.md)
- [Provider direction and provider-native capabilities](../../redesign/workflows/provider-direction-and-provider-native-capabilities.md)
- [Compiler contract and launch materialization](../../redesign/workflows/compiler-contract-and-launch-materialization.md)
- [Role and policy example definitions](../../redesign/workflows/role-and-policy-example-definitions.md)
- [Definition registry and upload contract](../../redesign/interfaces/definition-registry-and-upload-contract.md)
- [Guarded registry and runtime writes](../../redesign/interfaces/guarded-registry-and-runtime-writes.md)
- [Minimal workflow reference](../../redesign/workflows/examples/minimal.md)
- [Normal workflow reference](../../redesign/workflows/examples/normal.md)
- [Maximal workflow reference](../../redesign/workflows/examples/maximal.md)

## Required supporting redesign reads

- [Workflow front door](../../redesign/workflows/README.md)
- [Glossary and boundaries](../../redesign/architecture/glossary-and-boundaries.md)
- [ADR-0002 deterministic compiler and immutable compiled plans](../../redesign/decisions/ADR-0002-deterministic-compiler-and-immutable-compiled-plans.md)
- [ADR-0003 parent-owned execution tree and boundary advancement](../../redesign/decisions/ADR-0003-parent-owned-execution-tree-and-boundary-advancement.md)
- [Write a nested workflow](../../redesign/how-to/write-a-nested-workflow.md)
- [Create a definition and run a task](../../redesign/tutorials/create-a-definition-and-run-a-task.md)

## Required current contrast reads

- [Definition and task-compose YAML contract](../../current/interfaces/definition-and-task-compose-yaml-contract.md)
- [Definitions compiler and launch](../../current/interfaces/definitions-compiler-and-launch.md)
- [Definition precedence and skill-version defaults](../../current/interfaces/definition-precedence-and-skill-version-defaults.md)
- [Definition registry and publish lifecycle](../../current/interfaces/definition-registry-and-publish-lifecycle.md)

## Required examples and diagrams

- [Minimal workflow reference](../../redesign/workflows/examples/minimal.md)
- [Normal workflow reference](../../redesign/workflows/examples/normal.md)
- [Maximal workflow reference](../../redesign/workflows/examples/maximal.md)
- the worked diagrams and flow examples in [Compiler contract and launch materialization](../../redesign/workflows/compiler-contract-and-launch-materialization.md)
- the worked criteria example in [Criteria projection and consumption example](../../redesign/workflows/criteria-projection-and-consumption-example.md)

## Exhaustive appendix owners

- [Workflow schema appendix](../../redesign/workflows/workflow-schema-appendix.md)
- [Role and policy definition schema](../../redesign/interfaces/role-and-policy-definition-schema.md)
- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md) when internal registry row or revision readback detail must stay aligned with later public surfaces

## Implementation surfaces

- owned surfaces: `apps/api/app/schemas/*`, `apps/api/app/compiler/*`,
  internal definition identity, revision, and lookup persistence under
  `apps/api/app/db/*`, `apps/api/app/registry/*`, or `apps/api/app/services/*`
  when that work stays internal and does not widen into public ingest or route
  families, `definitions/*`, workflow schema owner docs, workflow legality and
  criteria docs, workflow role/policy example docs, workflow examples, and the
  workflow schema appendix
- allowed collateral surfaces: compiler-facing tests, narrow registry parsing
  or persistence surfaces when schema/compiler alignment requires them,
  the exact Phase 1 current-contrast pages named above when truthful
  schema/compiler/registry contrast repair is required,
  existing shipped init/upgrade/reset shell under `apps/api/app/cli.py` only
  when Phase 1-owned persistence truth must be reachable through the shipped
  path without widening public CLI nouns or package/install ownership,
  package-contained seed mirrors under `apps/api/app/resources/definitions/**`
  and narrow `pyproject.toml` package-data entries only when Phase 1-owned
  internal registry truth must ship its baseline seed assets without widening
  broader package/install ownership,
  `docs/redesign/interfaces/definition-registry-and-upload-contract.md` and
  `docs/redesign/interfaces/guarded-registry-and-runtime-writes.md` when
  internal registry truth must be made explicit before public ingest lands, and
  the repo-root `.gitignore` only when Phase 1-owned `definitions/*` fixtures
  would otherwise remain excluded from tracked repo truth

## Do not edit / defer surfaces

- runtime assignment, attempt, checkpoint, dispatch, closure, and replan
  persistence beyond narrow lookup compatibility needed to stop later phases
  from reading repo files as authority
- gateway, watchdog, operator, and plugin surfaces
- public ingest, public definition routes, new CLI noun families,
  package/install/reset/release surfaces, or broader CLI UX beyond the narrow
  shipped-path proof wiring explicitly allowed above

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for schema-only, compiler-only, or examples-and-fixtures slices
- each subagents slice must read the owned docs, tests, and code needed for that slice before editing and must return exact test evidence

## Wave integration loop

1. lock the schema, compiler, or example work package against the phase page and file lock map
2. decide `no subagents` or brief the bounded subagents slices
3. integrate the returned code and docs changes into one coherent tree-only authoring contract
4. run schema/compiler tests and example checks
5. review findings and patch before starting another wave

## Phase purpose

Make the authored workflow and compiler surfaces decision-complete for the tree-only target model.

## Success criteria

- tree-only workflow authoring is canonical in docs and code
- controller-owned definition identity, revision, and currentness truth exists
  before later phases pin or validate workflow, role, or policy revisions
- typed dependency selectors through `consumes.artifacts` and
  `consumes.criteria` are the hard dependency surface
- stale authored-edge, dotted-id parenthood, and generic authored `skill_refs` semantics are removed from target behavior

## Deliverables

- aligned schema and compiler behavior
- internal registry-backed definition resolution basis
- aligned workflow examples and fixtures
- removal of stale target authoring semantics

## Milestones

- internal registry truth aligned
- schema contracts aligned
- compiler behavior aligned
- examples and fixtures aligned

## Ordered work packages

### `P1-WP1`

- objective: land controller-owned internal definition identity, revision, and
  currentness truth needed for compiler and later runtime revision pinning
- owned surfaces: internal registry persistence and lookup surfaces plus any
  appendix or owner docs needed to make the internal truth explicit
- dependencies: Phase 0 complete; Phase 0.5 complete first only when the
  selected blocker still falls under stale-shape, reset-baseline, stale-test,
  or plugin-boundary cleanup
- test-first requirement: failing or gap-revealing definition persistence or
  lookup tests
- documentation update requirement: registry truth and phase-boundary ownership stay
  explicit without widening into public ingest
- subagent allowed: yes
- closeout evidence: later phases no longer need repo files as definition authority

### `P1-WP2`

- objective: align authored workflow schema and validator expectations with the
  tree-only model and the internal registry truth landed in `P1-WP1`
- owned surfaces: workflow schema docs, appendix owner, schema layer
- dependencies: `P1-WP1`
- test-first requirement: failing or gap-revealing schema validation tests
- documentation update requirement: schema docs and examples updated together
- subagent allowed: yes
- closeout evidence: current schema docs and validation behavior agree

### `P1-WP3`

- objective: align compiler normalization and compile-time legality with the
  tree-only model and DB-backed revision pinning
- owned surfaces: compiler code and compiler-facing tests
- dependencies: `P1-WP1`, `P1-WP2`
- test-first requirement: failing or gap-revealing compiler tests
- documentation update requirement: compiler contract examples remain aligned
- subagent allowed: yes
- closeout evidence: compile failures and derived graph behavior match canon

### `P1-WP4`

- objective: remove stale target authoring semantics from examples, fixtures,
  and acceptance paths
- owned surfaces: workflow examples, fixtures, regression tests
- dependencies: `P1-WP2`, `P1-WP3`
- test-first requirement: regression tests that stale generic `skill_refs` are rejected or isolated
- documentation update requirement: minimal, normal, and maximal YAML stay copy-safe
- subagent allowed: yes
- closeout evidence: examples and fixtures teach only live target semantics

## Mandatory checklist

- [ ] the authored schema, compiler behavior, and examples all teach the same tree-only model
- [ ] if stale repo shape, reset baseline ambiguity, stale tests, or
      plugin-boundary drift are still the real blocker, the work routes back
      to Phase 0.5 instead of patching forward inside Phase 1
- [ ] compiler and later runtime-facing resolution read controller-owned
      definition truth instead of repo files once `P1-WP1` lands
- [ ] shipped init, upgrade, and reset proof for definition persistence uses
      the existing shipped path rather than direct helper invocation or
      test-only schema setup when Phase 1 changes persistence truth
- [ ] typed dependency selectors through `consumes.artifacts` and
      `consumes.criteria` are the hard dependency surface in both docs and code
- [ ] removed authored-edge, dotted-id, and generic `skill_refs` semantics are rejected or isolated intentionally
- [ ] any subagents slice stayed inside its owned schema, compiler, or example surfaces

## Required tests

- unit tests for schema validation and normalization
- unit tests for internal definition identity or revision persistence and lookup
- integration tests for compile failures and derived graph behavior
- integration tests that compiler resolution pins current workflow, role, and
  policy revisions from controller-owned truth
- shipped-path schema install, upgrade, and reset proof for SQLite when
  definition persistence truth changes
- Postgres + Docker strong verification when definition persistence truth
  changes and the lane is viable
- regression tests that current-style generic `skill_refs` are rejected or isolated as legacy-only input
- example or fixture checks for minimal, normal, and maximal workflow YAML

## Required docs and examples

- workflow schema docs
- workflow schema appendix
- minimal, normal, and maximal examples

## Candidate delegated slices

- schema-only slice
- compiler-only slice
- examples/fixtures slice

## Exit evidence

- compiler behavior matches canonical schema docs
- compiler and later runtime-facing revision pinning use controller-owned
  definition truth rather than repo files
- shipped init, upgrade, and reset paths create and reseed controller-owned
  definition truth without test-only setup when Phase 1 changes persistence
  truth
- examples and compiler invariants agree
- stale flagship flat-workflow logic is no longer a live core path

## Reset criteria

- apply the reset gate if definition persistence or compiled-plan storage truth changes

## Kill-list terms

- authored `edges` as canonical workflow authoring
- dotted-id parent inference as core semantics
- generic authored `skill_refs` as target schema
- obsolete flat flagship workflow teaching model

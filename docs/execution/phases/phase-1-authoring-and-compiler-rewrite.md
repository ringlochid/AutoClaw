# Phase 1 authoring and compiler rewrite

Status: Target

This phase lands the tree-only authoring model and the compiler rewrite that makes it executable.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

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

## Required examples and diagrams

- [Minimal workflow reference](../../redesign/workflows/examples/minimal.md)
- [Normal workflow reference](../../redesign/workflows/examples/normal.md)
- [Maximal workflow reference](../../redesign/workflows/examples/maximal.md)
- the worked diagrams and flow examples in [Compiler contract and launch materialization](../../redesign/workflows/compiler-contract-and-launch-materialization.md)
- the worked criteria example in [Criteria projection and consumption example](../../redesign/workflows/criteria-projection-and-consumption-example.md)

## Exhaustive appendix owners

- [Workflow schema appendix](../../redesign/workflows/workflow-schema-appendix.md)
- [Role and policy definition schema](../../redesign/interfaces/role-and-policy-definition-schema.md)

## Implementation surfaces

- owned surfaces: `apps/api/app/schemas/*`, `apps/api/app/compiler/*`,
  `definitions/*`, workflow schema owner docs, workflow legality and criteria
  docs, workflow role/policy example docs, workflow examples, and the workflow
  schema appendix
- allowed collateral surfaces: compiler-facing tests, narrow registry parsing
  or persistence surfaces when schema/compiler alignment requires them, and the
  repo-root `.gitignore` only when Phase 1-owned `definitions/*` fixtures would
  otherwise remain excluded from tracked repo truth

## Do not edit / defer surfaces

- runtime persistence and controller-loop behavior
- gateway, watchdog, operator, and plugin surfaces
- package, install, reset, and release surfaces

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
- typed dependency selectors through `consumes.artifacts` and
  `consumes.criteria` are the hard dependency surface
- stale authored-edge, dotted-id parenthood, and generic authored `skill_refs` semantics are removed from target behavior

## Deliverables

- aligned schema and compiler behavior
- aligned workflow examples and fixtures
- removal of stale target authoring semantics

## Milestones

- schema contracts aligned
- compiler behavior aligned
- examples and fixtures aligned

## Ordered work packages

### `P1-WP1`

- objective: align authored workflow schema and validator expectations
- owned surfaces: workflow schema docs, appendix owner, schema layer
- dependencies: Phase 0 and 0.5 complete
- test-first requirement: failing or gap-revealing schema validation tests
- docs/update requirement: schema docs and examples updated together
- subagent allowed: yes
- closeout evidence: current schema docs and validation behavior agree

### `P1-WP2`

- objective: align compiler normalization and compile-time legality with the tree-only model
- owned surfaces: compiler code and compiler-facing tests
- dependencies: `P1-WP1`
- test-first requirement: failing or gap-revealing compiler tests
- docs/update requirement: compiler contract examples remain aligned
- subagent allowed: yes
- closeout evidence: compile failures and derived graph behavior match canon

### `P1-WP3`

- objective: remove stale target authoring semantics from examples, fixtures, and acceptance paths
- owned surfaces: workflow examples, fixtures, regression tests
- dependencies: `P1-WP1`, `P1-WP2`
- test-first requirement: regression tests that stale generic `skill_refs` are rejected or isolated
- docs/update requirement: minimal, normal, and maximal YAML stay copy-safe
- subagent allowed: yes
- closeout evidence: examples and fixtures teach only live target semantics

## Mandatory checklist

- [ ] the authored schema, compiler behavior, and examples all teach the same tree-only model
- [ ] typed dependency selectors through `consumes.artifacts` and
      `consumes.criteria` are the hard dependency surface in both docs and code
- [ ] removed authored-edge, dotted-id, and generic `skill_refs` semantics are rejected or isolated intentionally
- [ ] any subagents slice stayed inside its owned schema, compiler, or example surfaces

## Required tests

- unit tests for schema validation and normalization
- integration tests for compile failures and derived graph behavior
- regression tests that current-style generic `skill_refs` are rejected or isolated as legacy-only input
- example or fixture checks for minimal, normal, and maximal workflow YAML

## Required docs/examples

- workflow schema docs
- workflow schema appendix
- minimal, normal, and maximal examples

## Candidate delegated slices

- schema-only slice
- compiler-only slice
- examples/fixtures slice

## Exit evidence

- compiler behavior matches canonical schema docs
- examples and compiler invariants agree
- stale flagship flat-workflow logic is no longer a live core path

## Reset criteria

- apply the reset gate if definition persistence or compiled-plan storage truth changes

## Kill-list terms

- authored `edges` as canonical workflow authoring
- dotted-id parent inference as core semantics
- generic authored `skill_refs` as target schema
- obsolete flat flagship workflow teaching model

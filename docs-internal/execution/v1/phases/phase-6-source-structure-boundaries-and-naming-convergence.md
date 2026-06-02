# Phase 6 source standards convergence and package migration

Status: Reference

This phase lands the repo-wide standards refactor for shipped source code after the product behavior is already working: it converges structure, readability style, naming, package authority, and compatibility-shim usage to the repo standards without intentionally changing user-visible behavior. The work covers both file or path names and the names and code shape inside those files.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary design pages

- [Design overview](../../../design/v1/architecture/design-overview.md)
- [Glossary and boundaries](../../../design/v1/architecture/glossary-and-boundaries.md)
- [CLI, API, and package shape](../../../design/v1/interfaces/cli-api-and-package-shape.md)
- [Runtime lifecycle overview](../../../design/v1/architecture/runtime-lifecycle-overview.md)

## Required supporting design reads

- [Design architecture front door](../../../design/v1/architecture/README.md)
- [Interfaces front door](../../../design/v1/interfaces/README.md)
- [Provider, worker, and operator boundary](../../../design/v1/architecture/provider-worker-and-operator-boundary.md)
- [MCP, plugin, and CLI boundary](../../../design/v1/interfaces/mcp-plugin-and-cli-boundary.md)
- [Runtime records and lifecycle](../../../design/v1/architecture/runtime-records-and-lifecycle.md)

## Required standards reads

- [Repo layout standard](../../../../.agents/standards/structure/repo-layout.md)
- [Source layout standard](../../../../.agents/standards/structure/source-layout.md)
- [Integration boundary standard](../../../../.agents/standards/structure/integration-boundaries.md)
- [Naming standard](../../../../.agents/standards/code/naming.md)
- [Readability and refactor standard](../../../../.agents/standards/code/readability-refactor.md)

## Required current contrast reads

- [Current architecture](../../../current/v1/architecture/current-architecture.md)
- [API surface and route map](../../../current/v1/interfaces/api-surface-and-route-map.md)
- [CLI surface and config precedence](../../../current/v1/interfaces/cli-surface-and-config-precedence.md)
- [OpenClaw and bridge plugin](../../../current/v1/architecture/openclaw-and-bridge-plugin.md)

## Required examples and diagrams

- the runtime model diagram in [Design overview](../../../design/v1/architecture/design-overview.md)
- the current baseline diagram in [Current architecture](../../../current/v1/architecture/current-architecture.md)

## Locked execution decisions

- this phase owns three equal standards axes: structure, readability style, and naming
- the phase includes the full backend package move toward `apps/api/src/autoclaw/**`
- every wave uses a hard import and interface gate before any pytest
- the phase extends the repo-native audit tooling before the main refactor waves
- iteration uses focused pytest selection only; the full applicable backend matrix runs once at Phase 6 closeout

## Implementation surfaces

- owned surfaces: shipped backend source under `apps/api/app/**` and `apps/api/autoclaw/**`; the target source root `apps/api/src/autoclaw/**` as it is introduced by this phase; package and entrypoint surfaces such as `pyproject.toml`, `apps/api/app/*.py`, and `apps/api/autoclaw/*.py`; repo-native audit tooling under `scripts/docs/style_audit/**`; the audit-tool proof surface `apps/api/tests/unit/test_style_audit.py`; and the design, current, and execution docs needed to keep the refactor route, gate order, and ownership truth explicit
- allowed collateral surfaces: targeted proof tests under `apps/api/tests/**` when source movement, package migration, or function extraction requires adjacent proof repair without taking ownership of the test-tree relayout; `Makefile` and narrow `scripts/**` surfaces when package or import-path changes require command-truth alignment without reopening broader packaging or release ownership; and the selected Phase 6 plan, evidence, and review artifacts under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`

## Do not edit / defer surfaces

- broad test-tree ownership convergence, phase-directory removal, cross-lane import cleanup, and grouped-runner relayout, which remain Phase 7-owned
- intentional public-behavior, runtime-contract, or API-contract changes that are not required to preserve behavior during the structural refactor
- dormant frontend buildout under `apps/console/**`

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for audit-tooling expansion, package-authority cleanup, CLI decomposition, runtime domain-first relayout, or review-only standards inspection
- the parent agent owns final package-authority decisions, runtime-boundary interpretation, focused-proof selection, and the pass or fail call when structural cleanup risks behavior drift

## Wave integration loop

1. freeze the active package and command shells from Phase 5.5 before moving source
2. land the audit and rename-map wave before broader source mutation begins
3. choose one bounded source-owner family per wave rather than mixing package, CLI, runtime, and naming work together
4. run the hard import and interface gate before any pytest on that wave
5. run only focused pytest selectors for the touched wave while iterating
6. integrate one behavior-preserving source wave at a time before starting another
7. run the full applicable backend matrix once at Phase 6 code freeze

## Concrete app-owned waves

- Wave A: package and entrypoints
    - `apps/api/app/*.py`
    - `apps/api/autoclaw/*.py`
    - `pyproject.toml`
- Wave B: CLI and terminal
    - `apps/api/app/cli/**`
    - `apps/api/app/cli_commands/**`
    - `apps/api/app/terminal/**`
- Wave C: runtime and persistence
    - `apps/api/app/runtime/**`
    - `apps/api/app/db/**`
    - adjacent `apps/api/app/api/**` only where transport thinness or ownership depends on the move
- Wave D: contracts, schemas, registry, and wrappers
    - `apps/api/app/schemas/**`
    - `apps/api/app/registry/**`
    - `apps/api/autoclaw/openclaw/**`
- Wave E: final package move
    - `apps/api/src/autoclaw/**`
    - residual shims
    - final entrypoint and packaging cleanup

## Audit expansion before the main refactor waves

Extend the repo-native audit tooling with a small, high-signal set of checks. These checks are part of the implementation, not optional planning notes.

- import-direction audit
    - fail when migrated `autoclaw` source still routes through deprecated `app.*` imports outside approved shims
    - fail when both `app` and `autoclaw` are still treated as first-class owners in migrated areas
- wrapper-budget audit
    - build on the existing import-wrapper logic
    - fail closed on new wrapper modules outside the approved shim list
- public naming audit
    - run only on exported, public, or shared surfaces
    - flag weak verbs such as `handle`, `process`, `run`, `do`, `apply`, and `check`
    - flag booleans on public or shared surfaces that are not fact-shaped with
      `is_`, `has_`, `should_`, or `can_`
- module-shape audit
    - check top-down module order on owned source modules:
        - imports
        - constants, types, or contracts
        - public entrypoints
        - shared helpers
        - private helpers

## Phase purpose

Make the shipped source tree comply with the repo structure, readability, and naming standards while also completing the canonical backend package migration, so the later test refactor phase does not need to compensate for ambiguous source ownership.

## Success criteria

- one backend package authority and migration direction is explicit and landed
- transport surfaces stay thin and source ownership is obvious from the path
- runtime layout trends domain-first rather than mechanism-first
- touched files and directories have one dominant responsibility and names that match that responsibility
- touched oversized files and oversized functions are split or carry explicit, phase-bounded review exceptions
- no cross-module underscore-private helper imports remain in touched source surfaces
- compatibility wrappers are reduced to explicit temporary shims only
- naming families use one canonical term per concept across code and touched docs

## Deliverables

- source audit and rename map
- package authority convergence and final backend package migration
- CLI and terminal decomposition
- runtime domain-first relayout
- readability cleanup
- naming and compatibility-shim cleanup
- expanded audit tooling for source-standards enforcement

## Milestones

- audit and rename map frozen
- package authority frozen
- CLI source split complete
- runtime domain owners clarified
- naming cleanup complete
- final package move complete
- approved compatibility shims reduced

## Ordered work packages

### `P6-WP0`

- objective: produce the authoritative source-owner, rename, and audit-expansion map before broad source mutation begins
- owned surfaces: `scripts/docs/style_audit/**`, `apps/api/tests/unit/test_style_audit.py`, source-owner docs, and the Phase 6 plan artifact
- dependencies: `Phase 5.5`
- test-first requirement: gap-revealing audit-tool unit tests for the new checks
- documentation update requirement: gate order, audit ownership, and rename-map truth stay explicit
- subagent allowed: yes
- closeout evidence: the source-owner and rename map is decision-complete and the new audits fail on the intended stale shapes

### `P6-WP1`

- objective: freeze canonical package authority, stop new `app` growth, and narrow wrappers to explicit temporary shims
- owned surfaces: package metadata, entrypoints, import wrappers, and package-routing docs
- dependencies: `P6-WP0`
- test-first requirement: package-entrypoint and import-path smoke coverage
- documentation update requirement: package authority and shim status stay explicit
- subagent allowed: yes
- closeout evidence: one canonical package direction is explicit and no new parallel owner tree is created

### `P6-WP2`

- objective: move files into the correct owner packages and collapse repeated family stems into real responsibility-named owners
- owned surfaces: owned source packages, file-level routing docs, and targeted proof tests
- dependencies: `P6-WP1`
- test-first requirement: focused proof selectors for each moved owner family
- documentation update requirement: file and directory ownership stays obvious in touched docs
- subagent allowed: yes
- closeout evidence: file placement and directory ownership match the standards and generic buckets are reduced

### `P6-WP3`

- objective: apply readability-refactor cleanup to modules and functions so the code reads top-down with visible side effects and responsibility-shaped helpers
- owned surfaces: `apps/api/app/cli/**`, `apps/api/app/cli_commands/**`, `apps/api/app/terminal/**`, `apps/api/app/runtime/**`, and adjacent source-owner docs
- dependencies: `P6-WP2`
- test-first requirement: focused pytest selectors around each extracted or reordered source family
- documentation update requirement: touched docs reflect the landed owner paths and dominant responsibilities
- subagent allowed: yes
- closeout evidence: readers can follow one source owner or lifecycle without recovering the flow from nested branches or helper soup

### `P6-WP4`

- objective: converge file names, module names, exported names, booleans, contract types, and helper families onto canonical domain terms
- owned surfaces: shared contracts, schemas, registries, wrappers, file names, and source-owner docs
- dependencies: `P6-WP2`, `P6-WP3`
- test-first requirement: focused proof where renamed public or shared surfaces replace old synonyms
- documentation update requirement: touched docs use the same canonical terms as code
- subagent allowed: yes
- closeout evidence: touched source families no longer carry synonym drift, weak public names, or mismatched file responsibilities

### `P6-WP5`

- objective: complete the `apps/api/src/autoclaw/**` move, update packaging and entrypoints, and reduce remaining shims to the narrow minimum
- owned surfaces: `apps/api/src/autoclaw/**`, remaining shims, package exports, entrypoints, package metadata, and final Phase 6 docs
- dependencies: `P6-WP1`, `P6-WP2`, `P6-WP3`, `P6-WP4`
- test-first requirement: focused package-entrypoint and import-path smoke coverage for the final move
- documentation update requirement: shim status and remaining migration exceptions are written explicitly
- subagent allowed: yes
- closeout evidence: the canonical backend package move is complete and only deliberate temporary shims remain

## Mandatory checklist

- [ ] one canonical backend package direction is explicit and no new parallel
      first-class owner tree is introduced
- [ ] every touched file has one dominant responsibility
- [ ] every touched file name matches that responsibility
- [ ] transport surfaces remain thin
- [ ] touched mixed-responsibility files are split when the current slice already
      crosses those concern groups
- [ ] touched files over 600 lines do not keep growing without an exact review exception
- [ ] touched functions over 80 non-comment lines are extracted or carry an exact review exception
- [ ] every touched exported symbol is descriptive out of context
- [ ] every touched boolean on a public or shared surface is fact-shaped
- [ ] every touched side-effecting function uses an effect-bearing verb
- [ ] cross-module underscore-private helper imports are removed or converted into named public shared surfaces
- [ ] touched code reads top-down and outside-in
- [ ] formatter output was accepted and readability issues were solved by refactoring code shape
- [ ] no pytest ran for a wave until the import and interface gate passed
- [ ] full backend matrix execution is deferred until the end-of-phase checkpoint
- [ ] any subagents slice stayed inside audit, package, file-owner, readability, or naming ownership

## Required tests

Apply this gate order for every Phase 6 wave:

1. import and interface gate
    - touched-scope `scripts.docs.style_audit`, using `--scan-root <path>` when the wave is narrower than the full default audit roots
    - import-direction audit
    - wrapper-budget audit
    - package and import smoke
    - no pytest before this gate is clean on the touched scope
2. structure and readability gate
    - no new generic buckets
    - no new sibling-prefix sprawl
    - touched large files and functions either extracted or explicitly excepted
    - no cross-module underscore-private helper imports in touched source
3. focused proof only while iterating
    - run only the smallest affected pytest selectors for the touched wave
    - if a focused test does not exist, create or extract one before widening the run
    - every wave plan must name its focused proof selectors before implementation begins
4. wave-local broader proof only when forced by the touched surface
    - if a wave reaches a DB-backed or end-to-end boundary, still prefer the narrowest viable selector in that lane
    - do not run the full lane as routine iteration proof
5. end-of-phase full proof only once
    - `ruff format`
    - `ruff check`
    - `mypy`
    - `make pyright-api`
    - `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
    - `ruff check scripts/docs` and `mypy scripts/docs` when `scripts/docs/style_audit/**` changed
    - the full applicable backend test matrix for touched source surfaces
    - all viable e2e lanes required by the touched shipped surfaces

## Required docs and examples

- touched design, current, and execution routing docs that describe moved source owners
- touched maintainer docs when command or package paths change
- the examples and diagrams named above when ownership wording depends on them

## Candidate delegated slices

- audit-expansion and rename-map slice
- package-authority slice
- file-owner cleanup slice
- CLI and runtime readability slice
- naming and shim-minimization slice

## Exit evidence

- source ownership matches the refactor standards closely enough that the test refactor phase no longer has to compensate for ambiguous package or module shape
- the canonical backend package move is complete
- source quality gates pass
- remaining compatibility shims or structural exceptions are exact, bounded, and reviewed

## Reset criteria

- apply the reset gate when package, install, reset, or DB-lane truth changes as part of source convergence

## Kill-list terms

- parallel backend owner trees
- mechanism-first runtime sprawl
- growing oversized source files without extraction
- generic module buckets
- private cross-module helper imports
- synonym drift across source and docs
- broad pytest or full-matrix runs used as routine iteration proof

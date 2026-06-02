# Phase 6 source structure, boundaries, and naming convergence

Status: Reference

This phase lands the repo-wide standards refactor for shipped source code after the product behavior is already working: it converges package authority, source layout, module and function boundaries, naming, and compatibility-shim usage to the repo standards without intentionally changing user-visible behavior.

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

## Implementation surfaces

- owned surfaces: shipped backend source under `apps/api/app/**` and `apps/api/autoclaw/**`; package and entrypoint surfaces such as `pyproject.toml`, `apps/api/app/*.py`, and `apps/api/autoclaw/*.py`; and the design, current, and execution docs needed to keep the refactor route and ownership truth explicit
- allowed collateral surfaces: targeted proof tests under `apps/api/tests/**` when source movement or function extraction requires adjacent proof repair without taking ownership of the test-tree relayout; `Makefile` and narrow `scripts/**` surfaces when package or import-path changes require command truth alignment without reopening broader packaging or release ownership; and the selected Phase 6 plan, evidence, and review artifacts under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`

## Do not edit / defer surfaces

- test-tree ownership convergence, phase-directory removal, cross-lane import cleanup, and grouped-runner relayout, which remain Phase 7-owned
- intentional public-behavior, runtime-contract, or API-contract changes that are not required to preserve behavior during the structural refactor
- dormant frontend buildout under `apps/console/**`

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for package-authority cleanup, CLI decomposition, runtime domain-first relayout, or review-only standards inspection
- the parent agent owns final package-authority decisions, runtime-boundary interpretation, and the pass/fail call when structural cleanup risks behavior drift

## Wave integration loop

1. freeze the active package and command shells from Phase 5.5 before moving source
2. choose one bounded source owner family per wave, such as package authority, CLI, runtime, or schema and contract cleanup
3. integrate one behavior-preserving source wave at a time before starting another
4. run source quality gates and targeted proof after each integrated wave
5. run the full applicable backend matrix only at stable checkpoints and at code freeze

## Phase purpose

Make the shipped source tree comply with the repo structure, naming, and boundary standards without asking the later test refactor phase to compensate for ambiguous source ownership.

## Success criteria

- one backend package authority and migration direction is explicit
- transport surfaces stay thin and source ownership is obvious from the path
- runtime layout trends domain-first rather than mechanism-first
- touched oversized files and oversized functions are split or carry explicit, phase-bounded review exceptions
- no cross-module underscore-private helper imports remain in touched source surfaces
- compatibility wrappers are reduced to explicit temporary shims only
- naming families use one canonical term per concept across code and touched docs

## Deliverables

- package authority convergence
- CLI and terminal decomposition
- runtime domain-first relayout
- naming and compatibility-shim cleanup

## Milestones

- package authority frozen
- CLI source split complete
- runtime domain owners clarified
- naming cleanup complete
- approved compatibility shims reduced

## Ordered work packages

### `P6-WP1`

- objective: freeze backend package authority, inventory compatibility shims, and make the source-root migration direction explicit
- owned surfaces: package metadata, entrypoints, import wrappers, and package-routing docs
- dependencies: `Phase 5.5`
- test-first requirement: package-entrypoint and import-path smoke coverage
- documentation update requirement: package authority and shim status stay explicit
- subagent allowed: yes
- closeout evidence: one canonical package direction is explicit and no new parallel owner tree is created

### `P6-WP2`

- objective: decompose CLI and terminal owners into noun-family modules with thin entrypoints
- owned surfaces: `apps/api/app/cli/**`, `apps/api/app/cli_commands/**`, `apps/api/app/terminal/**`, and adjacent docs
- dependencies: `P6-WP1`
- test-first requirement: gap-revealing CLI parser, command, and output tests
- documentation update requirement: CLI source ownership stays obvious in touched docs
- subagent allowed: yes
- closeout evidence: CLI command families are split by owned responsibility and oversized command files are reduced

### `P6-WP3`

- objective: relayout runtime source toward domain-first owners while preserving current behavior
- owned surfaces: `apps/api/app/runtime/**`, `apps/api/app/db/**`, `apps/api/app/api/**`, and adjacent architecture or current-contrast docs
- dependencies: `P6-WP1`
- test-first requirement: targeted runtime regression tests around every moved domain family
- documentation update requirement: touched boundary docs stay aligned with the landed owner paths
- subagent allowed: yes
- closeout evidence: readers can follow one runtime lifecycle without hopping across ambiguous mechanism buckets

### `P6-WP4`

- objective: converge naming, contract placement, and shared-helper boundaries across source owners
- owned surfaces: shared contracts, schemas, registries, wrappers, and source-owner docs
- dependencies: `P6-WP2`, `P6-WP3`
- test-first requirement: gap-revealing tests where extracted public helpers replace private cross-module imports
- documentation update requirement: touched docs use the same canonical terms as code
- subagent allowed: yes
- closeout evidence: touched source families no longer carry synonym drift, generic buckets, or private cross-module imports

### `P6-WP5`

- objective: reduce approved compatibility shims to the narrow minimum and prepare the source tree for the later test-owner convergence
- owned surfaces: remaining shims, package exports, import-only wrappers, and final Phase 6 docs
- dependencies: `P6-WP1`, `P6-WP2`, `P6-WP3`, `P6-WP4`
- test-first requirement: package-entrypoint and public import smoke coverage
- documentation update requirement: shim status and remaining migration exceptions are written explicitly
- subagent allowed: yes
- closeout evidence: only deliberate temporary shims remain and their removal conditions are explicit

## Mandatory checklist

- [ ] one canonical package direction is explicit and no new parallel first-class
      backend owner is introduced
- [ ] transport surfaces remain thin
- [ ] touched mixed-responsibility files are split when the current slice already
      crosses those concern groups
- [ ] touched files over 600 lines do not keep growing without an exact review exception
- [ ] touched functions over 80 non-comment lines are extracted or carry an exact review exception
- [ ] cross-module underscore-private helper imports are removed or converted into named public shared surfaces
- [ ] naming families use one stable term per concept in touched code and docs
- [ ] any subagents slice stayed inside package, CLI, runtime, or naming ownership

## Required tests

- `ruff format`
- `ruff check`
- `mypy`
- `make pyright-api`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
- exact repo search for retained underscore-private shared helpers in touched source families
- the full applicable backend test matrix for touched source surfaces
- all viable e2e lanes when touched source refactors reach shipped end-to-end behavior

## Required docs and examples

- touched design, current, and execution routing docs that describe moved source owners
- touched maintainer docs when command or package paths change
- the examples and diagrams named above when ownership wording depends on them

## Candidate delegated slices

- package-authority slice
- CLI decomposition slice
- runtime domain-owner slice
- naming and shared-helper cleanup slice

## Exit evidence

- source ownership matches the refactor standards closely enough that the test refactor phase no longer has to compensate for ambiguous package or module shape
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

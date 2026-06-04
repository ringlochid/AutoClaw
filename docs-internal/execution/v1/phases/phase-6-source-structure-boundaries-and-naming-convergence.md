# Phase 6 full source standards convergence and package migration

Status: Reference

This phase lands the repo-wide standards refactor for shipped backend source code after the product behavior is already working. Phase 6 is source-only: it covers every shipped backend source owner family under `apps/api/app/**` and `apps/api/autoclaw/**`, plus the canonical `apps/api/src/autoclaw/**` target as it is introduced. Tests remain proof consumers and adjacent repair collateral only; test-tree ownership, fixture convergence, and runner relayout stay Phase 7-owned.

Structure, readability, naming, package authority, and compatibility-shim cleanup are not separate closure tracks here. A completed Phase 6 source-owner family must satisfy those standards together before that family is considered done. Hotspot-only cleanup is not closure authority for this phase.

Phase 6 also owns convergence to one coherent top-level taxonomy inside `apps/api/src/autoclaw/**`. A final source root that still mixes sibling transport trees, domain owners, and generic substrate buckets is not closure authority for this phase.

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

- this phase is source-only except for proof and docs collateral explicitly allowed below
- this phase owns structure, readability style, naming, compatibility-shim cleanup, and canonical package migration together for completed source-owner families
- every source-owner family wave uses a hard import and interface gate, then `make format-api` and `make check-api`, before any pytest
- every completed source-owner family must pass full touched-family `style_audit --scan-root <path> --fail-on-findings`; import-interface-only proof is necessary but not sufficient
- no source-owner family closes while module-shape, public-naming, import-direction, wrapper-budget, or family-stem debt still remains inside that same completed family, unless an exact Phase 6 review exception records why
- the phase includes the full backend package move toward `apps/api/src/autoclaw/**`
- the phase includes the final root-taxonomy cleanup inside `apps/api/src/autoclaw/**`
- a final `src/autoclaw` tree that still mixes sibling transport roots such as `api/**`, `cli/**`, or wrapper-facing transport trees with domain owners such as `runtime/**`, `compiler/**`, or `registry/**`, plus generic substrate roots such as `db/**` or `schemas/**`, is not Phase 6 closeout authority
- the preferred steady-state root families are `interfaces/http/**`, `interfaces/cli/**`, `interfaces/mcp/**`, `definitions/**` with `definitions/contracts/**`, `runtime/**` with `runtime/contracts/**`, `integrations/**`, `persistence/**`, and `platform/**`
- iteration uses focused pytest selection only; the full applicable backend matrix runs once at Phase 6 closeout
- broad test-tree ownership convergence stays Phase 7-owned even when Phase 6 must repair adjacent proof imports or monkeypatch targets

## Implementation surfaces

- owned surfaces: shipped backend source under `apps/api/app/**` and `apps/api/autoclaw/**`; the target source root `apps/api/src/autoclaw/**` as it is introduced by this phase; package and entrypoint surfaces such as `pyproject.toml`, `apps/api/app/*.py`, and `apps/api/autoclaw/*.py`; repo-native audit tooling under `scripts/docs/style_audit/**`; the audit-tool proof surface `apps/api/tests/unit/test_style_audit.py`; and the design, current, and execution docs needed to keep the refactor route, gate order, and ownership truth explicit
- allowed collateral surfaces: targeted proof tests under `apps/api/tests/**` when source movement, package migration, or function extraction requires adjacent proof repair without taking ownership of the test-tree relayout; `Makefile` and narrow `scripts/**` surfaces when package or import-path changes require command-truth alignment without reopening broader packaging or release ownership; `scripts/docs/docs_freeze/**` and `docs/reference/**` when package-owner or path-owner changes require docs-freeze path-validation truth and public reference owner paths to stay aligned; and the selected Phase 6 plan, evidence, and review artifacts under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`

## Do not edit / defer surfaces

- broad test-tree ownership convergence, phase-directory removal, cross-lane import cleanup, and grouped-runner relayout, which remain Phase 7-owned
- intentional public-behavior, runtime-contract, or API-contract changes that are not required to preserve behavior during the structural refactor
- dormant frontend buildout under `apps/console/**`

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- no edit subagents are required by default for this phase; parent-owned owner-family execution is preferred unless a later wave plan explicitly carves out a bounded slice
- fresh `review-only` slices are appropriate after a completed owner-family wave when independent standards inspection matters
- the parent agent owns final package-authority decisions, source-boundary interpretation, focused-proof selection, and the pass or fail call when structural cleanup risks behavior drift

## Wave integration loop

1. freeze the active package and command shells from Phase 5.5 before moving source
2. keep the `P6-WP0` source-audit baseline authoritative before broader source mutation begins
3. choose one bounded source-owner family per wave rather than mixing package, transport, platform, runtime, and naming cleanup together
4. run the hard import and interface gate before any pytest on that wave
5. run `make format-api`
6. run `make check-api`
7. run the full touched-family `style_audit --scan-root <path> --fail-on-findings` before calling the owner-family wave complete
8. run only focused pytest selectors for the touched wave while iterating
9. integrate one behavior-preserving source wave at a time before starting another
10. run the full applicable backend matrix once at Phase 6 code freeze

## Concrete source-owner waves

- Wave A: package authority and bridge surfaces
    - `apps/api/src/autoclaw/**`
    - `apps/api/app/*.py`
    - `apps/api/autoclaw/*.py`
    - `pyproject.toml`
- Wave B: transport and public-facing owner surfaces
    - `apps/api/app/api/**`
    - `apps/api/app/cli/**`
    - `apps/api/app/main.py`
    - `apps/api/app/cli_support.py`
    - public wrapper and MCP-facing entrypoint shells under `apps/api/autoclaw/**`, excluding non-shim OpenClaw internals deferred to `P6-WP4`
- Wave C: platform and shared owner surfaces
    - `apps/api/app/config.py`
    - `apps/api/app/paths.py`
    - `apps/api/app/file_entrypoints.py`
    - `apps/api/app/core/**`
    - `apps/api/app/service_managers/**`
    - `apps/api/app/services/**`
    - `apps/api/app/resources/**`
- Wave D: compiler, persistence, registry, and contract owners
    - `apps/api/app/compiler/**`
    - `apps/api/app/db/**`
    - `apps/api/app/registry/**`
    - `apps/api/app/schemas/**`
- Wave E: runtime and OpenClaw internals
    - `apps/api/app/runtime/**`
    - non-shim `apps/api/autoclaw/openclaw/**`
    - adjacent `apps/api/app/api/**` only where transport thinness or ownership depends on the move
- Wave F: final package move and shim collapse
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

Make the shipped backend source tree comply with the repo structure, readability, and naming standards while also completing the canonical backend package migration, so the later test refactor phase does not need to compensate for ambiguous source ownership.

## Success criteria

- one backend package authority and migration direction is explicit and landed
- completed transport surfaces stay thin and source ownership is obvious from the path
- one coherent root taxonomy is explicit inside `apps/api/src/autoclaw/**`
- completed source-owner families pass full touched-family `style_audit --scan-root <path> --fail-on-findings`
- completed source-owner families do not retain unresolved module-shape, import-direction, or public-naming debt without an exact Phase 6 review exception
- runtime and OpenClaw source layout trend domain-first rather than mechanism-first
- completed source-owner families have one dominant responsibility and names that match that responsibility
- no cross-module underscore-private helper imports remain in completed source-owner families
- compatibility wrappers are reduced to explicit temporary shims only
- naming families use one canonical term per concept across code and touched docs
- the canonical backend package move to `apps/api/src/autoclaw/**` is complete

## Deliverables

- source-only audit and owner map
- package authority convergence and final backend package migration
- transport and public-surface owner cleanup
- platform, compiler, persistence, and contract owner cleanup
- runtime and OpenClaw source convergence
- naming and compatibility-shim cleanup
- expanded audit tooling for source-standards enforcement

## Milestones

- source-only audit and owner map frozen
- package authority frozen
- transport owners clarified
- platform and contract owners clarified
- runtime and OpenClaw owners clarified
- naming cleanup complete
- final package move complete
- approved compatibility shims reduced

## Ordered work packages

### `P6-WP0`

- objective: produce the authoritative source-only owner, rename, and audit-expansion map before broad source mutation begins, and legalize the exact opening gate-unblock edits needed to start the source waves cleanly
- owned surfaces: `scripts/docs/style_audit/**`, `apps/api/tests/unit/test_style_audit.py`, source-owner docs, the Phase 6 plan artifact, and the exact opening gate-unblock surfaces `apps/api/app/cli/__init__.py` and `apps/api/app/cli/commands/server_config.py`
- dependencies: `Phase 5.5`
- test-first requirement: gap-revealing audit-tool unit tests for the new checks
- documentation update requirement: gate order, audit ownership, and source-only rename-map truth stay explicit
- subagent allowed: yes
- closeout evidence: the source-only owner and rename map is decision-complete, the new audits fail on the intended stale shapes, and the opening repo-native gate blockers are either repaired or explicitly recorded as Phase 6 source debt

### `P6-WP1`

- objective: freeze canonical package authority, introduce `apps/api/src/autoclaw/**` as the first-class package root, stop new `app` growth, and narrow wrappers to explicit temporary shims across package and bridge surfaces
- owned surfaces: package metadata, entrypoints, import wrappers, repo-native import shells, package-routing docs, and the public package shell under `apps/api/src/autoclaw/**`
- dependencies: `P6-WP0`
- test-first requirement: package-entrypoint and import-path smoke coverage
- documentation update requirement: package authority and shim status stay explicit
- subagent allowed: yes
- closeout evidence: one canonical package direction is explicit and no new parallel owner tree is created

### `P6-WP2`

- objective: converge public transport and wrapper shells so HTTP, CLI, app startup, and MCP-facing entry surfaces run through one obvious `src/autoclaw/interfaces/**` owner path while deeper non-transport cleanup stays with later bounded packages
- owned surfaces: `apps/api/app/api/**`, `apps/api/app/cli/**`, `apps/api/app/main.py`, `apps/api/app/cli_support.py`, public wrapper and MCP-facing entrypoint shells under `apps/api/autoclaw/**`, excluding non-shim OpenClaw internals deferred to `P6-WP4`, and matching source-owner docs
- dependencies: `P6-WP1`
- test-first requirement: focused proof selectors for each moved transport or public-surface family
- documentation update requirement: file and directory ownership stays obvious in touched docs
- subagent allowed: yes
- closeout evidence: public transport and wrapper shells run through `apps/api/src/autoclaw/interfaces/**`, touched transport surfaces pass their source-quality gates, `interfaces/http/routers/**` remains route-only, and any retained legacy `app/**` transport entrypoints are explicit temporary compatibility shims

### `P6-WP3`

- objective: converge platform, definition-domain, persistence, contract, and shared-owner source families, including readability and naming cleanup inside those families rather than leaving hotspot residue for later waves
- owned surfaces: `apps/api/app/config.py`, `apps/api/app/paths.py`, `apps/api/app/file_entrypoints.py`, `apps/api/app/core/**`, `apps/api/app/service_managers/**`, `apps/api/app/services/**`, `apps/api/app/resources/**`, `apps/api/app/compiler/**`, `apps/api/app/db/**`, `apps/api/app/registry/**`, `apps/api/app/schemas/**`, and matching source-owner docs
- dependencies: `P6-WP1`
- test-first requirement: focused proof selectors for each completed platform, compiler, persistence, or contract family
- documentation update requirement: touched docs reflect the landed owner paths and dominant responsibilities
- subagent allowed: yes
- closeout evidence: completed non-runtime source-owner families pass their full touched-family source-quality gates, definition-domain owners converge toward `definitions/**` with `definitions/contracts/**`, persistence owners converge toward `persistence/**`, runtime contracts converge toward `runtime/contracts/**`, and no avoidable shared-owner ambiguity remains
- required bounded package sequence:
    - package `P6-WP3A`: `config.py`, `paths.py`, `file_entrypoints.py`, and `core/**`
    - package `P6-WP3B`: `service_managers/**`, `resources/**`, and the disposition of the generic `services/**` bucket
    - package `P6-WP3C`: compiler, definition-facing registry, and definition-facing schema owners
    - package `P6-WP3D`: DB owners, runtime contract absorption, and the removal or justified relocation of `runtime/contract_models/**`

### `P6-WP4`

- objective: converge the full runtime and OpenClaw source owners, not just isolated hotspots, until those families meet the same source-quality bar as the earlier waves
- owned surfaces: `apps/api/app/runtime/**`, non-shim `apps/api/autoclaw/openclaw/**`, and adjacent `apps/api/app/api/**` only where transport thinness or ownership depends on the move
- dependencies: `P6-WP2`, `P6-WP3`
- test-first requirement: focused proof selectors around each completed runtime or OpenClaw owner family
- documentation update requirement: touched docs reflect the landed owner paths and dominant responsibilities
- subagent allowed: yes
- closeout evidence: runtime and OpenClaw source-owner families pass their full touched-family source-quality gates, reusable provider substrate converges under `integrations/openclaw/**`, runtime usage converges under `runtime/openclaw/**`, runtime-owned contracts stay under `runtime/contracts/**`, and hotspot-only cleanup no longer acts as closure authority
- required bounded package sequence:
    - package `P6-WP4A`: prompt, task-root, and projection materialization owners
    - package `P6-WP4B`: launch, assignment, boundary, checkpoint, flow, and release control owners
    - package `P6-WP4C`: dispatch, watchdog, replan, runtime OpenClaw usage, and reusable OpenClaw integration substrate

### `P6-WP5`

- objective: complete naming convergence, finish the `apps/api/src/autoclaw/**` move, converge the root to one coherent top-level taxonomy, and reduce remaining shims to the narrow minimum so the phase closes on one canonical backend package
- owned surfaces: `apps/api/src/autoclaw/**`, remaining shims, package exports, entrypoints, package metadata, and final Phase 6 docs
- dependencies: `P6-WP1`, `P6-WP2`, `P6-WP3`, `P6-WP4`
- test-first requirement: focused package-entrypoint and import-path smoke coverage for the final move plus focused proof for renamed public or shared surfaces
- documentation update requirement: shim status and remaining migration exceptions are written explicitly
- subagent allowed: yes
- closeout evidence: the canonical backend package move is complete, source-owner families are naming-clean, the final root taxonomy is coherent, and only deliberate temporary shims remain
- required bounded package sequence:
    - package `P6-WP5A`: package-authority flip across import shells, package metadata, Docker/dev shells, grouped runners, and subprocess/package-entrypoint proof
    - package `P6-WP5B`: residual shim collapse, final naming cleanup, and remaining oversized-function or manual-review backlog that scripts alone do not close

## Mandatory checklist

- [ ] Phase 6 stayed source-only except for allowed proof and docs collateral
- [ ] one canonical backend package direction is explicit and no new parallel first-class owner tree is introduced
- [ ] the final `apps/api/src/autoclaw/**` root uses one coherent top-level taxonomy rather than a mix of sibling transport, domain, and substrate buckets
- [ ] every completed source-owner family has one dominant responsibility
- [ ] every completed source-owner family passes its full touched-family `style_audit --scan-root <path> --fail-on-findings`
- [ ] completed transport surfaces remain thin
- [ ] completed HTTP route packages contain route owners only; support contracts, presenters, or translators are not parked under route-only packages
- [ ] completed HTTP route owners do not retain DB transaction control or runtime effect-runner coordination
- [ ] completed mixed-responsibility families are split when the current wave already crosses those concern groups
- [ ] completed source-owner families do not retain unresolved module-shape or public-naming debt without an exact review exception
- [ ] completed source-owner families do not retain cross-module underscore-private shared helpers without an exact review exception
- [ ] every completed exported symbol is descriptive out of context
- [ ] every completed public or shared boolean is fact-shaped
- [ ] every completed side-effecting function uses an effect-bearing verb
- [ ] no pytest ran for a wave until the import and interface gate, `make format-api`, and `make check-api` passed
- [ ] full backend matrix execution is deferred until the end-of-phase checkpoint
- [ ] no test-tree relayout or proof-lane convergence work was used as Phase 6 closure authority
- [ ] any subagents slice stayed inside audit, package, file-owner, readability, naming, or review-only ownership

## Required tests

Apply this gate order for every Phase 6 wave:

1. import and interface gate
    - touched-scope `scripts.docs.style_audit`, using `--scan-root <path>` and `--gate import-interface --fail-on-findings` when the wave is narrower than the full default audit roots
    - import-direction audit
    - wrapper-budget audit
    - package and import smoke
    - no pytest before this gate is clean on the touched scope
2. repo-native code-health gate before pytest
    - `make format-api`
    - `make check-api`
    - run these immediately after the import and interface gate because they are cheap and should fail fast before any pytest expansion
    - no pytest before both commands pass on the current worktree
3. structure, readability, and naming gate
    - touched-family `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root <path> --fail-on-findings`
    - no new generic buckets
    - no new sibling-prefix sprawl
    - completed large files and functions either extracted or explicitly excepted
    - no cross-module underscore-private helper imports in completed source-owner families
4. focused proof only while iterating
    - run only the smallest affected pytest selectors for the touched wave
    - if a focused test does not exist, create or extract one before widening the run
    - every wave plan must name its focused proof selectors before implementation begins
5. wave-local broader proof only when forced by the touched surface
    - if a wave reaches a DB-backed or end-to-end boundary, still prefer the narrowest viable selector in that lane
    - do not run the full lane as routine iteration proof
6. end-of-phase full proof only once
    - `ruff format`
    - `ruff check`
    - `mypy`
    - `make format-api`
    - `make check-api`
    - `make pyright-api`
    - `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
    - `ruff check scripts/docs` and `mypy scripts/docs` when `scripts/docs/style_audit/**` changed
    - `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when `docs-internal/execution/v1/**`, `docs-internal/current/v1/**`, `docs/reference/**`, or `scripts/docs/docs_freeze/**` changed as Phase 6 collateral
    - the full applicable backend test matrix for touched source surfaces
    - all viable e2e lanes required by the touched shipped surfaces

## Required docs and examples

- touched design, current, and execution routing docs that describe moved source owners
- touched maintainer docs when command or package paths change
- the examples and diagrams named above when ownership wording depends on them

## Candidate delegated slices

- audit-expansion and source-owner-map slice
- package-authority slice
- transport-owner cleanup slice
- platform and contract-owner cleanup slice
- runtime and OpenClaw owner cleanup slice
- review-only standards inspection slice

## Exit evidence

- source ownership matches the refactor standards closely enough that the test refactor phase no longer has to compensate for ambiguous package or module shape
- the canonical backend package move is complete
- source quality gates pass
- remaining compatibility shims or structural exceptions are exact, bounded, and reviewed

## Reset criteria

- apply the reset gate when package, install, reset, or DB-lane truth changes as part of source convergence

## Kill-list terms

- parallel backend owner trees
- partial hotspot packets used as Phase 6 closure authority
- mechanism-first runtime sprawl
- growing oversized source files without extraction
- generic module buckets
- private cross-module helper imports
- synonym drift across source and docs
- broad pytest or full-matrix runs used as routine iteration proof

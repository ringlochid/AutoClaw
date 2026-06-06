# Phase 6 full source standards convergence and package migration

Status: Reference

This phase lands the repo-wide standards refactor for the shipped backend source after the product behavior is already working. Phase 6 is source-only: it now covers the live canonical tree under `apps/api/src/autoclaw/**`, plus the narrow package, runner, audit-tool, and docs collateral needed to finish the taxonomy rewrite cleanly. Tests remain proof consumers and adjacent repair collateral only; broad test-tree ownership, proof-helper timing cleanup, source-side proof-teaching leak cleanup, fixture convergence, and runner relayout stay Phase 7-owned.

Structure, readability, naming, package authority, and compatibility cleanup are not separate closure tracks here. A completed Phase 6 source-owner family must satisfy those standards together before that family is considered done. Hotspot-only cleanup is not closure authority for this phase.

Phase 6 also owns convergence to one coherent top-level taxonomy inside `apps/api/src/autoclaw/**`. A final source root that still mixes sibling transport trees, domain owners, and generic substrate buckets is not closure authority for this phase.

Historical `P6-WP0` through `P6-WP2` artifacts are summary-only background now. Authoritative reopened execution starts from the current `src/autoclaw/**` tree and the refined steady-state taxonomy.

## Reopened source findings freeze

- controller-truth mutator cleanup, shipped source wait ownership, continuity authority, boundary cleanup, and neutral shipped-metadata naming exposed by the merged reopen findings stay Phase 6-owned whenever the fix lives in shipped source
- proof-helper amplification, timeout-lane isolation, grouped-runner alignment, and test-tree ownership remain Phase 7-owned even when the same source families have adjacent proof debt
- an audit-green source tree is not Phase 6 closeout authority if the merged reopen findings still identify unresolved shipped-source debt outside the current audit heuristics

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
- this phase owns structure, readability style, naming, compatibility cleanup, and canonical package migration together for completed source-owner families
- every source-owner family wave uses a hard import and interface gate, then `make format-api` and `make check-api`, before any pytest
- every completed source-owner family must pass full touched-family `style_audit --scan-root <path> --fail-on-findings`; import-interface-only proof is necessary but not sufficient
- no source-owner family closes while module-shape, public-naming, import-direction, wrapper-budget, family-stem, or structural debt still remains inside that same completed family, unless an exact Phase 6 review exception records why
- the final `src/autoclaw` root must converge to one coherent taxonomy with grouped `interfaces/**`, `definitions/**`, `runtime/**`, `integrations/**`, `persistence/**`, and `platform/**` owners, plus domain-owned contract lanes under `definitions/contracts/**` and `runtime/contracts/**`
- inside `interfaces/http/**`, `contracts/**` is the explicit owner for HTTP-only transport contracts, presenters, and support models; `routers/**` remains route-only
- merged reopen findings that surface controller-truth drift, shipped wait-owner layering, continuity authority drift, boundary ownership drift, or neutral shipped-metadata debt remain Phase 6 closure blockers until the source owner is cleaned up or an exact Phase 6 exception records why not
- no shipped compatibility shells, path-extension tricks, import bridges, or test-only compat lanes may remain at closeout
- iteration uses focused pytest selection only; the full applicable backend matrix runs once at Phase 6 closeout
- broad test-tree ownership convergence stays Phase 7-owned even when Phase 6 must repair adjacent proof imports or monkeypatch targets

## Implementation surfaces

- owned surfaces: shipped backend source under `apps/api/src/autoclaw/**`; package metadata and shipped entrypoint surfaces such as `pyproject.toml`, `apps/api/src/autoclaw/main.py`, `apps/api/src/autoclaw/__main__.py`, and the canonical CLI entrypoint; repo-native audit tooling under `scripts/docs/style_audit/**`; the audit-tool proof surface `apps/api/tests/unit/style_audit/**`; and the design, current, and execution docs needed to keep the refactor route, gate order, and ownership truth explicit
- allowed collateral surfaces: targeted proof tests under `apps/api/tests/**` when source movement, package migration, or function extraction requires adjacent proof repair without taking ownership of the test-tree relayout; `Makefile`, `apps/api/Dockerfile`, `apps/api/pyrightconfig.json`, and narrow `scripts/**` surfaces when package or import-path changes require command-truth alignment without reopening broader packaging or release ownership; `docs/**`, `docs-internal/current/**`, and `scripts/docs/docs_freeze/**` when package-owner or path-owner changes require docs-freeze path-validation truth and public or current reference owner paths to stay aligned; and the selected Phase 6 plan, evidence, and review artifacts under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`

## Do not edit / defer surfaces

- broad test-tree ownership convergence, phase-directory removal, cross-lane import cleanup, proof-helper timing convergence, source-side proof-teaching leak cleanup, and grouped-runner relayout, which remain Phase 7-owned
- intentional public-behavior, runtime-contract, or API-contract changes that are not required to preserve behavior during the structural refactor
- dormant frontend buildout under `apps/console/**`

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagent slices
- use one active worker at a time for code packages in this phase
- worker slices must read the phase page, lock map, the approved package plan, the smallest relevant design/current docs, and the named standards before editing
- worker slices must be told explicitly: no new subagents, no Codex CLI review, stop if the work escapes the owned slice
- no review-only slice before full `WP3`
- fresh `review-only` slices are appropriate only after full `WP3`, full `WP4`, and full `WP5`
- the parent/controller limits itself to trivial glue work: scope checks, docs-only collateral, validator orchestration, and go/no-go decisions between waves
- the parent agent owns final package-authority decisions, source-boundary interpretation, focused-proof selection, and the pass or fail call when structural cleanup risks behavior drift

## Wave integration loop

1. start from the current `apps/api/src/autoclaw/**` tree and treat earlier Phase 6 pre-closeout artifacts as historical context only
2. choose one bounded source-owner family per wave rather than mixing interfaces, definitions, persistence, runtime, and package-finalization cleanup together
3. run the hard import and interface gate before any pytest on that wave
4. run `make format-api`
5. run `make check-api`
6. run the full touched-family `style_audit --scan-root <path> --fail-on-findings` before calling the owner-family wave complete
7. run only focused pytest selectors for the touched wave while iterating
8. integrate one behavior-preserving source wave at a time before starting another
9. run a fresh review-only subagent only after full `WP3`, full `WP4`, and full `WP5`
10. run the full applicable backend matrix once at Phase 6 code freeze

## Phase purpose

Make the shipped backend source tree comply with the repo structure, readability, and naming standards while also completing the canonical backend taxonomy convergence, so the later test refactor phase does not need to compensate for ambiguous source ownership or leftover compatibility debt.

## Success criteria

- one backend package authority is explicit and landed
- the final `apps/api/src/autoclaw/**` root uses one coherent taxonomy instead of a mix of sibling transport, domain, and substrate buckets
- completed transport surfaces stay thin and source ownership is obvious from the path
- completed HTTP route packages contain route owners only; support contracts, presenters, or translators live under `interfaces/http/contracts/**`
- completed HTTP route owners do not retain DB transaction control or runtime effect-runner coordination
- completed source-owner families pass full touched-family `style_audit --scan-root <path> --fail-on-findings`
- completed source-owner families do not retain unresolved module-shape, import-direction, public-naming, or family-stem debt without an exact Phase 6 review exception
- reopened source findings do not leave controller-truth mutator drift, duplicate shipped wait ownership, or neutral phase-label metadata defaults in shipped source without an exact Phase 6 review exception
- runtime and OpenClaw source layout trend domain-first rather than mechanism-first
- completed source-owner families have one dominant responsibility and names that match that responsibility
- no cross-module underscore-private helper imports remain in completed source-owner families
- the shipped `src/autoclaw/**` tree is self-contained and no shipped compatibility shells, placeholders, shims, import bridges, or test-only compat lanes remain
- naming families use one canonical term per concept across code and touched docs

## Deliverables

- source-owner convergence across the live `src/autoclaw/**` tree
- package authority convergence and final backend package finalization
- interface owner cleanup
- platform, definition-domain, persistence, and contract owner cleanup
- runtime and OpenClaw source convergence
- naming and compatibility-debt cleanup
- expanded audit tooling for source-standards enforcement

## Ordered work packages

### `P6-WP3`

- objective: converge interfaces, definition-domain owners, persistence, contracts, platform, and root package owners around the current `src/autoclaw/**` tree before runtime closeout begins
- owned surfaces: `apps/api/src/autoclaw/{api,cli,compiler,db,registry,schemas,platform}/**`, root package modules, matching proof tests, and matching source-owner docs
- dependencies: Phase 0 canon reset
- test-first requirement: focused proof selectors for each completed platform, compiler, persistence, or contract family
- documentation update requirement: touched docs reflect the landed owner paths and dominant responsibilities
- subagent allowed: yes
- closeout evidence: completed non-runtime source families pass their full touched-family source-quality gates, public HTTP, CLI, and MCP owners converge under `interfaces/**`, definition owners converge under `definitions/**` with `definitions/contracts/**`, persistence converges under `persistence/**`, runtime contracts converge under `runtime/contracts/**`, shipped interface or persistence boundaries no longer hand-roll reusable visibility or transport-contract ownership, and no avoidable shared-owner or compatibility ambiguity remains
- required bounded package sequence:
    - package `P6-WP3A`: HTTP interface convergence
    - package `P6-WP3B`: CLI and MCP interface convergence
    - package `P6-WP3C`: definitions, persistence, and contract convergence
    - package `P6-WP3D`: platform, root, and non-runtime debt cleanup

### `P6-WP4`

- objective: converge the full runtime around direct domain owners, remove mechanism-first top-level buckets, and delete the standalone `runtime/openclaw/**` usage owner
- owned surfaces: `apps/api/src/autoclaw/runtime/**` and adjacent `apps/api/src/autoclaw/integrations/openclaw/**`
- dependencies: `P6-WP3`
- test-first requirement: focused proof selectors around each completed runtime or OpenClaw owner family
- documentation update requirement: touched docs reflect the landed owner paths and dominant responsibilities
- subagent allowed: yes
- closeout evidence: runtime and OpenClaw source-owner families pass their full touched-family source-quality gates, reusable provider substrate converges under `integrations/openclaw/**`, runtime-owned contracts stay under `runtime/contracts/**`, controller-truth mutators and continuity authority live behind canonical runtime owners, shipped wait ownership no longer layers duplicate reconcile or poll loops by default, and mechanism-first roots `runtime/effects/**`, `runtime/control/**`, and standalone `runtime/openclaw/**` no longer survive as top-level owner buckets
- required bounded package sequence:
    - package `P6-WP4A`: runtime foundations
    - package `P6-WP4B`: runtime domain-owner convergence
    - package `P6-WP4C`: dispatch, watchdog, replan, and OpenClaw runtime usage

### `P6-WP5`

- objective: finalize package authority, delete remaining compatibility ballast, and prove one self-contained canonical package rooted in `apps/api/src/autoclaw/**`
- owned surfaces: `apps/api/src/autoclaw/**`, package exports, entrypoints, package metadata, final audit-tool allowlists, remaining compatibility tests, and final Phase 6 docs
- dependencies: `P6-WP3`, `P6-WP4`
- test-first requirement: focused package-entrypoint and import-path smoke coverage for the final move plus focused proof for renamed public or shared surfaces
- documentation update requirement: compatibility-debt status and remaining migration exceptions are written explicitly
- subagent allowed: yes
- closeout evidence: the canonical backend package move is complete, source-owner families are naming-clean, the final root taxonomy is coherent, the shipped tree is self-contained, no shipped compatibility shells, placeholders, shims, or test-only compat lanes remain, neutral shipped metadata no longer persists redesign-era phase labels by default, and only product-canonical wrapper concepts survive
- required bounded package sequence:
    - package `P6-WP5A`: package authority and metadata finalization
    - package `P6-WP5B`: final debt purge and phase closeout

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
- [ ] no shipped compatibility shells, import bridges, or test-only compat lanes remain at phase closeout

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
    - `./.venv/bin/python -m scripts.docs.style_audit.cli --scan-root apps/api/src/autoclaw --fail-on-findings`
    - `ruff check scripts/docs` and `mypy scripts/docs` when `scripts/docs/style_audit/**` changed
    - `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when `docs-internal/execution/v1/**`, `docs-internal/current/v1/**`, `docs/reference/**`, or `scripts/docs/docs_freeze/**` changed as Phase 6 collateral
    - the full applicable backend test matrix for touched source surfaces
    - all viable e2e lanes required by the touched shipped surfaces

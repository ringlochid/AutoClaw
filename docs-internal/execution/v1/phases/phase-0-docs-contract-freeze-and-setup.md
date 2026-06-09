# Phase 0 docs, contract freeze, and setup

Status: Reference

This phase hardens the docs root, root instruction surfaces, execution-pack authority split, phase-boundary routing, landing-coverage maps, and validation tooling that later phases rely on, and it freezes the one-process local-tool-first execution stance for Phase 0-3.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary design pages

- [Design docs](../../../design/v1/README.md)
- [Prompt layer and dispatch contract](../../../design/v1/prompt-layer/contract.md)
- [Prompt source and assembly contract](../../../design/v1/prompt-layer/source-and-sections.md)
- [Prompt machine contract](../../../design/v1/prompt-layer/machine-contract.md)
- [Phase and gate overview](overview.md)

## Required supporting design reads

- [Design architecture front door](../../../design/v1/architecture/README.md)
- [Design workflows front door](../../../design/v1/workflows/README.md)
- [Design interfaces front door](../../../design/v1/interfaces/README.md)
- [Prompt-layer front door](../../../design/v1/prompt-layer/README.md)
- [Durable decisions](../../../adr/README.md) when router wording or phase-boundary guidance must preserve accepted invariants
- [How-to guides](../../../design/v1/how-to/README.md) and [Tutorials](../../../design/v1/tutorials/README.md) when execution routing or landing coverage must include target-facing usage material

## Required current contrast reads

- [Definition precedence and skill-version defaults](../../../current/v1/interfaces/definition-precedence-and-skill-version-defaults.md)
- [Definitions compiler and launch](../../../current/v1/interfaces/definitions-compiler-and-launch.md)
- [Definition registry and publish lifecycle](../../../current/v1/interfaces/definition-registry-and-publish-lifecycle.md)
- [Runtime control plane](../../../current/v1/architecture/runtime-control-plane.md)
- [API trust lanes](../../../current/v1/interfaces/api-trust-lanes.md) and [Current parent, retry, and operator control](../../../current/v1/architecture/parent-retry-and-operator-control.md) when stale deleted-test references or current-lane wording need truthful cleanup without reinterpreting later product contracts
- [Current architecture](../../../current/v1/architecture/current-architecture.md)
- [OpenClaw dispatch and session contract](../../../current/v1/architecture/openclaw-dispatch-and-session-contract.md)
- [Watchdog and runtime monitoring](../../../current/v1/architecture/watchdog-and-runtime-monitoring.md) when truthful watchdog/support-state contrast repair is required
- [Current implementation docs](../../../current/v1/README.md) and [Current architecture front door](../../../current/v1/architecture/README.md) when root/router truth must reinforce design-first authority without reinterpreting later product contracts
- [Current workflow-manifest projection](../../../current/v1/architecture/manifest-projection-and-acknowledgement.md), [Current OpenClaw and bridge-plugin baseline](../../../current/v1/architecture/openclaw-and-bridge-plugin.md), [Current runtime read models and operator surfaces](../../../current/v1/architecture/runtime-read-models-and-operator-surfaces.md), [Current definition ingest, task start, and task-root binding](../../../current/v1/interfaces/current-definition-bootstrap-and-task-upload.md), [CLI surface and config precedence](../../../current/v1/interfaces/cli-surface-and-config-precedence.md), and [Inspect approval-related and watchdog state in the current system](../../../current/v1/operations/inspect-approvals-and-watchdog.md) when routed current-behavior pages need truthful stale-wording cleanup and route-map repair without reinterpreting later product contracts
- [Run the current Docker and Postgres verification lane](../../../current/v1/operations/run-docker-postgres-verification.md) when a bounded runtime-normalization command-surface addendum must keep the stronger current DB-backed lane truthful without reopening Phase 5B install, onboarding, release, or docs-cutover teaching
- use the named current pages above first for seed-authority, reseed-semantics, cancel-behavior, and stale-path contrast repair
- broader `docs-internal/current/v1/**` reads are allowed only when truthful stale-path cleanup, route-map repair, or current-behavior docs repair is required to keep the canonical docs authority tree self-consistent

## Required examples and diagrams

- [Prompt composition example](../../../design/v1/prompt-layer/composition-example.md)
- [Rendered prompt examples](../../../design/v1/prompt-layer/generated/rendered-examples.md)
- any prompt-layer mermaid diagrams that phase-owned router or validator changes would otherwise drift from

## Implementation surfaces

- owned surfaces: `../../../../AGENTS.md`, `../../../../STYLE.md`, `../../../../docs/README.md`, `../../../docs-internal/execution/v1/**/*`, prompt-asset routing, prompt-catalog execution surfaces, and docs generation or validation tooling
- allowed collateral surfaces: root `README.md`, design router pages, prompt-layer owner pages when execution prompt-family authority depends on them, `docs-internal/current/v1/**` when stale-path cleanup, route-map repair, or truthful current-behavior docs repair must be made explicit without reinterpreting later product contracts, and one later same-program command-surface addendum over `Makefile`, `../../../../docker-compose.yml`, narrow runner orchestration under `../../../scripts/**`, and matching current/execution docs only when that addendum is explicitly approved to keep repo-native verification or DB-lane command truth aligned without reopening Phase 5B install, onboarding, release, or docs-cutover ownership

## Do not edit / defer surfaces

- app/runtime product code under `apps/**` and `definitions/**`
- non-docs `scripts/**`, `Makefile`, `docker-compose.yml`, and other repo command surfaces except for the explicitly approved later same-program command-surface addendum described above
- current-behavior owner pages beyond Phase 0 stale-path cleanup, route-map repair, and truthful current-behavior docs repair

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- in this phase, subagents are optional and should stay limited to router normalization, prompt-family rewrite, or validator cleanup
- every subagents brief must name owned surfaces, required reads, tests or validators, required evidence, and parent-owned decisions

## Wave integration loop

1. lock the current work package against the phase page and implementation file lock map
2. decide `no subagents` or brief bounded subagents slices
3. integrate the returned docs changes against the locked surfaces
4. run the relevant docs validators and prompt validators
5. review findings and patch before starting another wave or claiming the work package complete

## Phase purpose

Make the repo instruction surface, execution pack, and docs validation flow safe enough to drive a rewrite-first implementation without split authority and without hidden MQ or distributed-safe design pressure in Phase 0-3 canon.

## Success criteria

- `AGENTS.md` is canonical
- `STYLE.md` is canonical for code standards
- execution prompts are limited to pre-review, phase planning, and post-review
- Phase 0 canon states that Phase 0-3 optimize for a one-process local tool and treat MQ or distributed-safe compatibility as a non-goal note
- docs generation and validation paths are deterministic
- the execution pack treats app-owned prompt assets as the shipped prompt source and prompt docs or generated pages as mirrors of that source
- repo-local phase plans, executed proof, and review outputs have canonical homes under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`
- authoritative plan, evidence, and review artifacts name exactly one selected phase
- authoritative Phase 0 plan, evidence, and review artifacts use `selected work packages:` and list only `P0-WP1`, `P0-WP2`, and/or `P0-WP3`
- cross-phase closeout or program records are either deleted when redundant or kept only as `summary-only: yes` historical summaries with unique replacement-routing value; they are never phase-closure authority
- when the runtime-normalization reopen program is active, the authoritative Phase 0 reopen chain is `phase-0-runtime-normalization-reopen-canon-fix.*`, the matching master router is `phase-0-to-4.5-runtime-normalization-reopen-program.*`, and the older phase45 reopen/master chains are historical background only
- when the same runtime-normalization program needs repo-native command-truth repair before fresh reopened code-bearing closeout resumes, Phase 0 canon explicitly allows one later bounded addendum over `Makefile`, `docker-compose.yml`, narrow runner orchestration under `scripts/**`, and matching current/execution docs without reclassifying that work as Phase 5B package, install, onboarding, release, or docs-cutover ownership
- canon states that helpers imported across modules must use public non-underscored names and that underscore-prefixed helpers stay module-local
- Phase 0 canon extends responsibility-oriented package layout across `apps/**`, `apps/api/tests/**`, and `scripts/docs/**`, bans repeated sibling family prefixes once a family reaches three or more files, and keeps only explicit public-boundary exceptions flat
- Phase 0 canon bans long-lived compatibility wrappers, import-only shim modules, star-import test collectors, and placeholder-only tracked trees in started products
- Phase 0 canon may reopen `docs-internal/current/v1/**` for stale-path cleanup, route-map repair, and truthful current-behavior docs repair only; it must not use that allowance to reinterpret later product contracts
- execution routing sends exact inline-versus-after-return timing, case-sequence behavior, and sync/async ownership to Phase 2 or Phase 3 owner docs instead of teaching low-level effect-kind rules in shared Phase 0 canon
- phase ownership and proof-gate routing are explicit and non-overlapping
- Phase 0 canon names `make pyright-api` as the repo-native audit proof for touched Python backend surfaces and keeps `scripts/docs/*` lint and typing proof separate
- Phase 0 canon names `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings` as the structural debt audit proof for Phase 0-3 Python cleanup slices

## Deliverables

- canonical root instruction surfaces
- canonical coding-standard surface
- structural-debt cleanup canon for shared helper naming, repo-wide package layout, family-prefix cleanup, shim removal, placeholder-tree removal, function ordering, and backend Python audit proof
- local-tool-first canon for Phase 0-3 root and execution routing
- normalized execution-pack prompt families and routing
- canonical phase-boundary, read-coverage, and design-to-code landing maps
- deterministic docs validation references

## Milestones

- authority surfaces aligned
- structural-debt cleanup rules aligned
- execution router aligned
- phase ownership and coverage map aligned
- validators pass

## Ordered work packages

### `P0-WP1`

- objective: create the canonical root instruction and coding-standard surfaces, including the Phase 0-3 local-tool-first stance
- owned surfaces: root `AGENTS.md`, `STYLE.md`
- dependencies: none
- test-first requirement: docs routing/consistency checks when present
- documentation update requirement: root docs routers must point to the new canon
- subagent allowed: yes
- closeout evidence: root authority files exist and no longer conflict

### `P0-WP2`

- objective: rewrite execution prompts, router pages, and phase-boundary rules around pre-review, phase plan, post-review, single-phase closeout authority, and explicit Phase 2 or Phase 3 timing ownership
- owned surfaces: `docs-internal/execution/v1/README.md`, `docs-internal/execution/v1/gates/*`, execution how-to pages
- dependencies: `P0-WP1`
- test-first requirement: prompt-catalog validation if prompt-source routing, prompt docs mirrors, or prompt-generation surfaces change
- documentation update requirement: phase and gate overview, gates index, and how-to pages
- subagent allowed: yes
- closeout evidence: prompt-family docs are consistent and corrupted text is removed

### `P0-WP3`

- objective: normalize validation tooling, design-to-code landing coverage, root/readme routing, the explicit Phase 0 current-doc unlock list, and any later same-program command-surface addendum route needed to keep repo-native verification commands truthful before Phase 5B
- owned surfaces: docs routers, execution maps, and docs tooling references
- dependencies: `P0-WP1`, `P0-WP2`
- test-first requirement: docs validation/generation checks
- documentation update requirement: root and design routers updated
- subagent allowed: yes
- closeout evidence: validators pass and routing points to canonical surfaces

## Mandatory checklist

- [ ] the current phase page plus the implementation file lock map are sufficient to route the docs work
- [ ] execution routing points to canonical surfaces instead of duplicated authorities
- [ ] prompt-family wording is limited to pre-review, phase plan, and post-review
- [ ] Phase 0 canon states that Phase 0-3 optimize for one-process
      local-tool-first execution and treats MQ or distributed-safe
      compatibility as a non-goal note
- [ ] execution canon does not imply that design docs are the shipped prompt
      source when Phase 2 owns app-packaged prompt assets
- [ ] exact inline-versus-after-return timing, case-sequence behavior, and
      sync/async ownership are routed to Phase 2 or Phase 3 owner docs rather
      than shared Phase 0 effect-kind prose
- [ ] each authoritative plan, evidence, and review artifact names exactly one
      selected phase
- [ ] each authoritative Phase 0 plan, evidence, and review artifact uses
      `selected work packages:` and lists only `P0-WP1`, `P0-WP2`, and/or
      `P0-WP3`
- [ ] shared helpers imported across modules are documented as public/shared
      surfaces rather than underscore-private locals
- [ ] Phase 0 canon extends package-layout cleanup across `apps/**`,
      `apps/api/tests/**`, and `scripts/docs/**`, keeps only explicit
      public-boundary exceptions flat, and bans repeated sibling family
      prefixes once a family reaches three or more files
- [ ] Phase 0 canon bans long-lived compatibility wrappers, import-only shim
      modules, star-import test collectors, and placeholder-only tracked trees
      in started products
- [ ] Phase 0 canon names `make pyright-api` as required audit proof for
      touched Python backend surfaces and keeps `scripts/docs/*` proof explicit
- [ ] Phase 0 canon names `./.venv/bin/python
      -m scripts.docs.style_audit.cli --fail-on-findings` as the
      structural debt audit proof for Phase 0-3 Python cleanup slices
- [ ] the first four named current-contrast pages above remain limited to
      seed-authority, reseed-semantics, and cancel-behavior contrast repair
- [ ] `current-architecture.md` and
      `openclaw-dispatch-and-session-contract.md` are used only for stale path
      cleanup unless canon is patched again
- [ ] aggregate records are deleted when redundant, or otherwise kept only as
      `summary-only: yes` historical summaries with unique replacement-routing
      value, never phase closure authority
- [ ] the runtime-normalization reopen program explicitly legalizes one later bounded command-surface addendum over `Makefile`, `docker-compose.yml`, narrow runner orchestration under `scripts/**`, and matching current/execution docs without claiming broader Phase 5B ownership
- [ ] every phase page names required supporting design reads, required current-contrast reads, and required examples or diagrams
- [ ] overlapping phase ownership is removed from the execution pack and lock map
- [ ] docs validation and prompt validation commands are explicit and reproducible
- [ ] any subagents slice stayed inside bounded docs ownership

## Required tests

- docs routing acceptance checks
- prompt asset or prompt-family id routing checks
- prompt-catalog completeness checks
- generated-page freshness or validation checks
- design-to-code landing-map completeness checks
- `make pyright-api` when touched backend Python surfaces under `apps/api/**` change
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings` when the selected slice is enforcing Phase 0-3 structural debt cleanup
- the repaired repo-native verification or DB lane itself when a bounded Phase 0 command-surface addendum changes `Makefile`, `docker-compose.yml`, or runner orchestration
- `ruff check scripts/docs`
- `mypy scripts/docs`

## Required docs and examples

- root docs routers
- execution pack routers
- prompt-family pages
- execution maps, including design-to-code landing coverage

## Candidate delegated slices

- root authority surface normalization only
- execution prompt-family rewrite only
- docs router and validation reference cleanup only

## Exit evidence

Record the approved plan under [Plans home](../plans/README.md), the executed validator or test proof under [Evidence home](../evidence/README.md), and any closeout review or exception record under [Reviews home](../reviews/README.md).

- exact root and execution files changed
- the artifact header used `selected work packages:` and listed only `P0-WP1`, `P0-WP2`, and/or `P0-WP3`
- root and execution canon now state that Phase 0-3 are one-process local-tool-first and treat MQ or distributed-safe compatibility as a non-goal note
- any current-doc unlock relied only on the first four named current-contrast pages above for contrast repair and on `current-architecture.md` plus `openclaw-dispatch-and-session-contract.md` for stale path cleanup only
- any later same-program command-surface addendum remained limited to `Makefile`, `docker-compose.yml`, narrow runner orchestration under `scripts/**`, and matching current/execution docs for repo-native command truth only, without claiming broader Phase 5B ownership
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli` passed
- `make pyright-api` is named as the repo-native audit command for touched backend Python surfaces, and separate `scripts/docs/*` proof stays explicit
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate` passed when prompt surfaces changed
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings` passed when the selected slice enforced Phase 0-3 structural debt cleanup
- scoped Python lint and typing checks passed for touched `scripts/docs/*`

## Reset criteria

- not normally applicable unless generated-truth locations or public docs entrypoints change materially

## Kill-list terms

- subrepo docs described as primary truth
- prompt wording duplicated across multiple authorities
- execution routing that still relies on pseudo-path references
- phase ownership that overlaps on the same future code surfaces
- target examples, diagrams, or proof gates left outside the execution-plan read path

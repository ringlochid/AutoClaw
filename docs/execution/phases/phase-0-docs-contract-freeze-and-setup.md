# Phase 0 docs, contract freeze, and setup

Status: Target

This phase hardens the docs root, root instruction surfaces, execution-pack
authority split, phase-boundary routing, landing-coverage maps, and validation
tooling that later phases rely on.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Redesign docs](../../redesign/README.md)
- [Prompt layer and dispatch contract](../../redesign/prompt-layer/contract.md)
- [Prompt source and assembly contract](../../redesign/prompt-layer/source-and-sections.md)
- [Prompt machine contract](../../redesign/prompt-layer/machine-contract.md)
- [Phase and gate overview](overview.md)

## Required supporting redesign reads

- [Redesign architecture front door](../../redesign/architecture/README.md)
- [Redesign workflows front door](../../redesign/workflows/README.md)
- [Redesign interfaces front door](../../redesign/interfaces/README.md)
- [Prompt-layer front door](../../redesign/prompt-layer/README.md)
- [Durable decisions](../../redesign/decisions/README.md) when router wording or
  phase-boundary guidance must preserve accepted invariants
- [How-to guides](../../redesign/how-to/README.md) and
  [Tutorials](../../redesign/tutorials/README.md) when execution routing or
  landing coverage must include target-facing usage material

## Required current contrast reads

- [Definition precedence and skill-version defaults](../../current/interfaces/definition-precedence-and-skill-version-defaults.md)
- [Definitions compiler and launch](../../current/interfaces/definitions-compiler-and-launch.md)
- [Definition registry and publish lifecycle](../../current/interfaces/definition-registry-and-publish-lifecycle.md)
- [Runtime control plane](../../current/architecture/runtime-control-plane.md)
- [Current architecture](../../current/architecture/current-architecture.md)
- [OpenClaw dispatch and session contract](../../current/architecture/openclaw-dispatch-and-session-contract.md)
- use the first four current pages above only for the explicit Phase 0
  seed-authority, reseed-semantics, and cancel-behavior contrast repair
- use the two additional architecture pages above only for stale path cleanup
- all other current docs stay deferred unless canon is patched first

## Required examples and diagrams

- [Prompt composition example](../../redesign/prompt-layer/composition-example.md)
- [Rendered prompt examples](../../redesign/prompt-layer/generated/rendered-examples.md)
- any prompt-layer mermaid diagrams that phase-owned router or validator changes
  would otherwise drift from

## Implementation surfaces

- owned surfaces: `../../../AGENTS.md`, `../../../STYLE.md`,
  `../../../docs/README.md`, `../../../docs/execution/**/*`, prompt-asset
  routing, prompt-catalog execution surfaces, and docs generation or
  validation tooling
- allowed collateral surfaces: root `README.md`, redesign router pages,
  prompt-layer owner pages when execution prompt-family authority depends on
  them, the first four named current-contrast pages above when
  seed-authority, reseed-semantics, or cancel-behavior contrast truth must be
  repaired, and the two additional architecture pages above when stale path
  cleanup must be made explicit

## Do not edit / defer surfaces

- the code
- current-behavior owner pages beyond the six named current-doc unlocks above
  and router or front-door corrections

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

Make the repo instruction surface, execution pack, and docs validation flow safe enough to drive a rewrite-first implementation without split authority.

## Success criteria

- `AGENTS.md` is canonical
- `STYLE.md` is canonical for code standards
- execution prompts are limited to pre-review, phase planning, and post-review
- docs generation and validation paths are deterministic
- the execution pack treats app-owned prompt assets as the shipped prompt source
  and prompt docs or generated pages as mirrors of that source
- repo-local phase plans, executed proof, and review outputs have canonical
  homes under `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/`
- authoritative plan, evidence, and review artifacts name exactly one selected
  phase
- authoritative Phase 0 plan, evidence, and review artifacts use
  `selected work packages:` and list only `P0-WP1`, `P0-WP2`, and/or `P0-WP3`
- cross-phase closeout records such as `phase-0-3-closeout*` are routed as
  historical summaries only, not phase-closure authority
- the first four named current-contrast pages are explicit Phase 0 unlocks for
  shipped seed-authority, reseed-semantics, and cancel-behavior contrast repair
- `current-architecture.md` and
  `openclaw-dispatch-and-session-contract.md` are additional Phase 0 unlocks
  for stale path cleanup only
- phase ownership and proof-gate routing are explicit and non-overlapping

## Deliverables

- canonical root instruction surfaces
- canonical coding-standard surface
- normalized execution-pack prompt families and routing
- canonical phase-boundary, read-coverage, and redesign-to-code landing maps
- deterministic docs validation references

## Milestones

- authority surfaces aligned
- execution router aligned
- phase ownership and coverage map aligned
- validators pass

## Ordered work packages

### `P0-WP1`

- objective: create the canonical root instruction and coding-standard surfaces
- owned surfaces: root `AGENTS.md`, `STYLE.md`
- dependencies: none
- test-first requirement: docs routing/consistency checks when present
- docs/update requirement: root docs routers must point to the new canon
- subagent allowed: yes
- closeout evidence: root authority files exist and no longer conflict

### `P0-WP2`

- objective: rewrite execution prompts, router pages, and phase-boundary rules
  around pre-review, phase plan, post-review, and single-phase closeout
  authority
- owned surfaces: `docs/execution/README.md`, `docs/execution/gates/*`, execution how-to pages
- dependencies: `P0-WP1`
- test-first requirement: prompt-catalog validation if prompt-source routing,
  prompt docs mirrors, or prompt-generation surfaces change
- docs/update requirement: phase and gate overview, gates index, and how-to pages
- subagent allowed: yes
- closeout evidence: prompt-family docs are consistent and corrupted text is removed

### `P0-WP3`

- objective: normalize validation tooling, redesign-to-code landing coverage,
  root/readme routing, and the explicit Phase 0 current-doc unlock list
- owned surfaces: docs routers, execution maps, and docs tooling references
- dependencies: `P0-WP1`, `P0-WP2`
- test-first requirement: docs validation/generation checks
- docs/update requirement: root and redesign routers updated
- subagent allowed: yes
- closeout evidence: validators pass and routing points to canonical surfaces

## Mandatory checklist

- [ ] the current phase page plus the implementation file lock map are sufficient to route the docs work
- [ ] execution routing points to canonical surfaces instead of duplicated authorities
- [ ] prompt-family wording is limited to pre-review, phase plan, and post-review
- [ ] execution canon does not imply that redesign docs are the shipped prompt
      source when Phase 2 owns app-packaged prompt assets
- [ ] each authoritative plan, evidence, and review artifact names exactly one
      selected phase
- [ ] each authoritative Phase 0 plan, evidence, and review artifact uses
      `selected work packages:` and lists only `P0-WP1`, `P0-WP2`, and/or
      `P0-WP3`
- [ ] the first four named current-contrast pages above remain limited to
      seed-authority, reseed-semantics, and cancel-behavior contrast repair
- [ ] `current-architecture.md` and
      `openclaw-dispatch-and-session-contract.md` are used only for stale path
      cleanup unless canon is patched again
- [ ] aggregate records such as `phase-0-3-closeout*` are treated as
      historical summary only, not phase closure authority
- [ ] every phase page names required supporting redesign reads, required current-contrast reads, and required examples or diagrams
- [ ] overlapping phase ownership is removed from the execution pack and lock map
- [ ] docs validation and prompt validation commands are explicit and reproducible
- [ ] any subagents slice stayed inside bounded docs ownership

## Required tests

- docs routing acceptance checks
- prompt asset or prompt-family id routing checks
- prompt-catalog completeness checks
- generated-page freshness or validation checks
- redesign-to-code landing-map completeness checks
- `ruff check scripts/docs`
- `mypy scripts/docs`

## Required docs/examples

- root docs routers
- execution pack routers
- prompt-family pages
- execution maps, including redesign-to-code landing coverage

## Candidate delegated slices

- root authority surface normalization only
- execution prompt-family rewrite only
- docs router and validation reference cleanup only

## Exit evidence

Record the approved plan under [../plans/README.md](../plans/README.md), the
executed validator or test proof under [../evidence/README.md](../evidence/README.md),
and any closeout review or exception record under
[../reviews/README.md](../reviews/README.md).

- exact root and execution files changed
- the artifact header used `selected work packages:` and listed only
  `P0-WP1`, `P0-WP2`, and/or `P0-WP3`
- any current-doc unlock relied only on the first four named current-contrast
  pages above for contrast repair and on `current-architecture.md` plus
  `openclaw-dispatch-and-session-contract.md` for stale path cleanup only
- `python scripts/docs/docs_freeze_validate.py` passed
- `python scripts/docs/prompt_catalog_tools.py validate` passed when prompt surfaces changed
- scoped Python lint and typing checks passed for touched `scripts/docs/*`

## Reset criteria

- not normally applicable unless generated-truth locations or public docs entrypoints change materially

## Kill-list terms

- subrepo docs described as primary truth
- prompt wording duplicated across multiple authorities
- execution routing that still relies on pseudo-path references
- phase ownership that overlaps on the same future code surfaces
- target examples, diagrams, or proof gates left outside the execution-plan read path

# Phase 0 docs, contract freeze, and setup

Status: Target

This phase hardens the docs root, root instruction surfaces, execution-pack authority split, and validation tooling that later phases rely on.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Redesign docs](../../redesign/README.md)
- [Prompt layer and dispatch contract](../../redesign/prompt-layer/contract.md)
- [Prompt source and assembly contract](../../redesign/prompt-layer/source-and-sections.md)
- [Prompt machine contract](../../redesign/prompt-layer/machine-contract.md)
- [Phase and gate overview](overview.md)

## Implementation surfaces

- owned surfaces: `../../../AGENTS.md`, `../../../STYLE.md`,
  `../../../docs/README.md`, `../../../docs/execution/**/*`, prompt-pack and
  prompt-catalog execution surfaces, and docs generation or validation tooling
- allowed collateral surfaces: root `README.md`, redesign router pages, and prompt-layer owner pages when execution prompt-family authority depends on them

## Do not edit / defer surfaces

- the code
- current-behavior owner pages beyond router or front-door corrections

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

## Deliverables

- canonical root instruction surfaces
- canonical coding-standard surface
- normalized execution-pack prompt families and routing
- deterministic docs validation references

## Milestones

- authority surfaces aligned
- execution router aligned
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

- objective: rewrite execution prompts and router pages around pre-review, phase plan, and post-review
- owned surfaces: `docs/execution/README.md`, `docs/execution/gates/*`, execution how-to pages
- dependencies: `P0-WP1`
- test-first requirement: prompt-catalog validation if prompt-pack surfaces change
- docs/update requirement: phase and gate overview, gates index, and how-to pages
- subagent allowed: yes
- closeout evidence: prompt-family docs are consistent and corrupted text is removed

### `P0-WP3`

- objective: normalize validation tooling and root/readme routing
- owned surfaces: docs routers and docs tooling references
- dependencies: `P0-WP1`, `P0-WP2`
- test-first requirement: docs validation/generation checks
- docs/update requirement: root and redesign routers updated
- subagent allowed: yes
- closeout evidence: validators pass and routing points to canonical surfaces

## Mandatory checklist

- [ ] the current phase page plus the implementation file lock map are sufficient to route the docs work
- [ ] execution routing points to canonical surfaces instead of duplicated authorities
- [ ] prompt-family wording is limited to pre-review, phase plan, and post-review
- [ ] docs validation and prompt validation commands are explicit and reproducible
- [ ] any subagents slice stayed inside bounded docs ownership

## Required tests

- docs routing acceptance checks
- prompt-pack id resolution checks
- prompt-catalog completeness checks
- generated-page freshness or validation checks

## Required docs/examples

- root docs routers
- execution pack routers
- prompt-family pages

## Candidate delegated slices

- root authority surface normalization only
- execution prompt-family rewrite only
- docs router and validation reference cleanup only

## Exit evidence

- exact root and execution files changed
- `python scripts/docs/docs_freeze_validate.py` passed
- `python scripts/docs/prompt_catalog_tools.py validate` passed when prompt surfaces changed

## Reset criteria

- not normally applicable unless generated-truth locations or public docs entrypoints change materially

## Kill-list terms

- subrepo docs described as primary truth
- prompt wording duplicated across multiple authorities
- execution routing that still relies on pseudo-path references

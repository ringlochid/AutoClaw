# Phase 5A definition ingest, API, and CLI

Status: Target

This phase lands definition ingest, public API surfaces, and the canonical root CLI contract.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Definition registry and upload contract](../../redesign/interfaces/definition-registry-and-upload-contract.md)
- [Definition ingest and upload contract](../../redesign/interfaces/definition-ingest-and-upload-contract.md)
- [CLI surface and operator workflows](../../redesign/interfaces/cli-surface-and-operator-workflows.md)
- [API surface and trust-lane map](../../redesign/interfaces/api-surface-and-trust-lane-map.md)
- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)

## Implementation surfaces

- owned surfaces: definition ingest and guarded upload services under
  `apps/api/app/registry/*` and `apps/api/app/services/*`, API routes and
  presenters under `apps/api/app/api/*`, root CLI entrypoints under
  `apps/api/app/cli.py`, and the ingest/API/CLI owner docs
- allowed collateral surfaces: compiler or schema surfaces when public ingest payloads require exact alignment, and onboarding examples that demonstrate the public nouns

## Do not edit / defer surfaces

- packaging, install/reset, release, and docs archive cutover surfaces
- gateway/watchdog/plugin contract pages except doc fixes needed for consistent public nouns

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for ingest/API, CLI contract, or public-docs example slices
- the parent agent owns final public noun-family decisions, ingest contract interpretation, and CLI/API consistency

## Wave integration loop

1. lock the current ingest/API/CLI work package against the phase page and file lock map
2. decide `no subagents` or brief the bounded subagents slices
3. integrate the returned service, route, presenter, CLI, and docs changes
4. run ingest/API/CLI tests and all viable e2e lanes
5. review findings and patch before another wave

## Phase purpose

Finish the public ingest, API, and CLI surfaces so the redesign’s public nouns are explicit, test-backed, and teachable from canonical docs.

## Success criteria

- definition ingest and public noun families match canon
- the canonical root CLI contract is explicit and test-backed
- stale public vocabulary is removed from canonical docs and routes
- canonical root CLI includes `autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]`
- canonical root CLI includes zero-arg `autoclaw definitions import [--overwrite reject|allow_new_revision]` for shallow current-working-directory scan only

## Deliverables

- ingest alignment
- public API alignment
- root CLI alignment

## Milestones

- ingest nouns aligned
- API surface aligned
- CLI contract aligned

## Ordered work packages

### `P5A-WP1`

- objective: align definition ingest services and public HTTP noun families
- owned surfaces: ingest services, API routes, presenters, ingest docs
- dependencies: earlier runtime and compiler phases complete
- test-first requirement: failing or gap-revealing ingest/API tests
- docs/update requirement: public noun families stay explicit
- subagent allowed: yes
- closeout evidence: canonical route families match docs

### `P5A-WP2`

- objective: align the root CLI contract with canonical ingest and public nouns
- owned surfaces: CLI entrypoints, CLI docs, onboarding examples
- dependencies: `P5A-WP1`
- test-first requirement: CLI contract tests and smoke checks
- docs/update requirement: CLI examples and public nouns update together
- subagent allowed: yes
- closeout evidence: root CLI behavior is explicit and test-backed

## Mandatory checklist

- [ ] ingest, API, and root CLI docs teach the same public noun families
- [ ] the canonical `autoclaw definitions import ...` contract is explicit in docs and code
- [ ] stale public vocabulary is removed from canonical routes and examples
- [ ] any subagents slice stayed inside its ingest/API, CLI, or public-docs ownership

## Required tests

- unit tests for ingest, API, and CLI contract behavior
- integration tests for guarded upload, import, runtime control, and public surfaces
- all currently-viable minimal, normal, and maximal e2e lanes

## Required docs/examples

- ingest docs
- CLI/API examples
- onboarding examples for public nouns

## Candidate delegated slices

- ingest/API slice
- CLI contract slice
- public-docs example slice

## Exit evidence

- public surfaces match the canonical docs
- the root CLI contract is explicit and test-backed
- stale public vocabulary is removed from canonical routes and docs

## Reset criteria

- apply the reset gate if public API/CLI truth, ingest persistence, or route families change in a breaking way

## Kill-list terms

- stale public CLI or API nouns
- ingest contract inferred from old route shapes
- public docs that still require old packs to interpret the new nouns

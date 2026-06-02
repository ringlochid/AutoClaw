# Phase 5.5 repo hygiene and active-surface freeze

Status: Reference

This phase lands the post-5B repo hygiene pass before the larger refactor program begins: it deletes or repairs stale compose, env-example, service-template, placeholder, and local-artifact surfaces, freezes which infra and package shells remain active, and removes dead ballast so Phase 6 and Phase 7 can focus on source and test structure instead of rediscovering stale operational residue.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary design pages

- [Release and install strategy](../../../design/v1/interfaces/release-and-install-strategy.md)
- [CLI, API, and package shape](../../../design/v1/interfaces/cli-api-and-package-shape.md)
- [Testing and release checklist](../../../design/v1/interfaces/testing-and-release-checklist.md)
- [Distribution and database support matrix](../../../design/v1/interfaces/distribution-and-database-support-matrix.md)

## Required supporting design reads

- [CLI surface and operator workflows](../../../design/v1/interfaces/cli-surface-and-operator-workflows.md)
- [Install and onboard](../../../design/v1/how-to/install-and-onboard.md)
- [Run the design target on local SQLite](../../../design/v1/how-to/run-local-sqlite.md)
- [Use Postgres in the design target](../../../design/v1/how-to/use-postgres.md)
- [Publish a release](../../../design/v1/how-to/publish-a-release.md)

## Required standards reads

- [Repo layout standard](../../../../.agents/standards/structure/repo-layout.md)
- [Source layout standard](../../../../.agents/standards/structure/source-layout.md)
- [Docs structure guide](../../../../.agents/standards/docs/docs-structure.md)

## Required current contrast reads

- [Packaging CLI and install](../../../current/v1/interfaces/packaging-cli-and-install.md)
- [CLI surface and config precedence](../../../current/v1/interfaces/cli-surface-and-config-precedence.md)
- [Install and start local](../../../current/v1/operations/install-and-start-local.md)
- [Verify current install and runtime](../../../current/v1/operations/verify-current-install-and-runtime.md)
- [Run the current Docker and Postgres verification lane](../../../current/v1/operations/run-docker-postgres-verification.md)

## Required examples and diagrams

- the release architecture mermaid diagram in [Release and install strategy](../../../design/v1/interfaces/release-and-install-strategy.md)
- the current Docker and Postgres verification examples in [Run the current Docker and Postgres verification lane](../../../current/v1/operations/run-docker-postgres-verification.md)

## Implementation surfaces

- owned surfaces: root command and infra shells such as `docker-compose.yml`, `apps/api/Dockerfile`, `.env.example`, `.gitignore`, and `infra/**`; stale compose or service-template shells selected for deletion when they still exist; the packaged service-template owner under `apps/api/app/resources/systemd/autoclaw.service`; dormant placeholder product shells such as `apps/console/**`; and maintainer or current-contrast docs that describe those active command, package, or verification surfaces
- allowed collateral surfaces: `Makefile`, `scripts/**`, `pyproject.toml`, `apps/api/requirements.txt`, and `apps/api/requirements-dev.txt` when one kept package, compose, or cleanup shell must stay executable; `docs/reference/**`, `docs-internal/current/v1/**`, and `docs-internal/execution/v1/**` when routing or verification guidance must stop teaching deleted shells; and the selected Phase 5.5 plan, evidence, and review artifacts under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`

## Do not edit / defer surfaces

- source-tree relayout under `apps/api/app/**` or `apps/api/autoclaw/**`, which remains Phase 6-owned
- test-tree relayout under `apps/api/tests/**`, which remains Phase 7-owned
- public API, runtime, compiler, gateway, watchdog, or plugin behavior changes beyond narrow command-surface repair required to keep an active shell truthful

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for command-shell inventory, env-example cleanup, dormant-surface triage, or docs-routing cleanup
- the parent agent owns the final keep/delete decisions for active package, compose, service-template, and placeholder-product shells

## Wave integration loop

1. inventory the current command, infra, env-example, and placeholder shells against the active package and verification story
2. decide `no subagents` or brief bounded inventory or cleanup slices
3. delete or repair stale shells before renaming or polishing adjacent docs
4. integrate the returned shell, template, and docs updates
5. run command-surface smoke checks and docs validation before another wave

## Phase purpose

Establish one clean operational baseline for the standards-convergence program by deleting stale ambient surfaces, repairing any kept command or package shells, and making the remaining active infra surfaces explicit.

## Success criteria

- stale compose, env-example, service-template, and dormant placeholder shells are deleted or made truthful
- every kept package, compose, service-template, and verification surface has one obvious owner
- dead env-example keys and ignored legacy settings are removed from examples
- local-artifact cleanup is explicit and does not rely on manual workstation drift
- Phase 6 and Phase 7 start from a frozen active-shell map rather than a mixed keep-or-delete backlog

## Deliverables

- active command and infra shell freeze
- env-example and service-template cleanup
- dormant surface triage and local-artifact cleanup

## Milestones

- stale shell inventory complete
- active shell set frozen
- env-example cleanup complete
- dormant surface triage complete

## Ordered work packages

### `P5.5-WP1`

- objective: delete or repair stale compose, Docker, package, and verification shells
- owned surfaces: compose, Dockerfile, package shell, and verification docs
- dependencies: `Phase 5B`
- test-first requirement: command-surface smoke checks for every kept shell
- documentation update requirement: maintainer and current-contrast docs update in the same phase
- subagent allowed: yes
- closeout evidence: no kept shell teaches a deleted or stale command path

### `P5.5-WP2`

- objective: remove dead env-example keys and settle one owner for service-template truth
- owned surfaces: `.env.example`, service templates, and install or maintainer docs
- dependencies: `P5.5-WP1`
- test-first requirement: package or install shell smoke when a kept template changes
- documentation update requirement: env and service-template docs stay exact
- subagent allowed: yes
- closeout evidence: example config and service-template surfaces match current code

### `P5.5-WP3`

- objective: triage dormant placeholder product shells and add explicit local-artifact cleanup
- owned surfaces: dormant placeholder trees, local cleanup scripts or targets, and maintainer docs
- dependencies: `P5.5-WP1`
- test-first requirement: local cleanup command or script proves safe dry-run or exact target scope
- documentation update requirement: dormant or placeholder status is explicit where the surface remains tracked
- subagent allowed: yes
- closeout evidence: dormant placeholders and local-artifact cleanup no longer create active-surface ambiguity

## Mandatory checklist

- [ ] every kept compose or Docker shell is executable and truthful
- [ ] deleted shells are removed rather than left as shadow guidance
- [ ] dead env-example keys such as ignored legacy OpenClaw account settings are removed
- [ ] one service-template owner remains explicit
- [ ] dormant placeholder app shells are deleted or clearly marked as non-active
- [ ] local cleanup does not rely on tracked `dist/`, `node_modules/`, or cache residue
- [ ] any subagents slice stayed inside command-shell, env-example, dormant-surface,
      or docs-routing ownership

## Required tests

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when execution or current docs change
- `docker compose config` for every kept compose file
- package, install, or reset smoke checks when kept service-template or package shells change
- `make test-api-db` when the Docker or Postgres verification shell changes
- the repaired local cleanup command or script itself when Phase 5.5 adds one

## Required docs and examples

- maintainer verification docs
- install or release docs when a kept shell changes their instructions
- execution and current-contrast docs that describe the kept command surfaces

## Candidate delegated slices

- command-shell inventory slice
- env-example and service-template slice
- dormant-surface and cleanup-command slice

## Exit evidence

- the active command and infra shell set is explicit
- stale shell families no longer survive as tracked shadow guidance
- kept env-example, compose, Docker, and service-template surfaces match current code
- local-artifact cleanup is explicit and safe enough for the repo-wide refactor program

## Reset criteria

- apply the reset gate when Phase 5.5 changes package, install, reset, or DB-lane truth

## Kill-list terms

- stale compose shells
- dead env-example keys
- duplicate service-template owners
- dormant placeholders treated as active product truth
- local workstation residue relied on as repo behavior

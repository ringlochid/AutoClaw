# Phase 5A definition ingest, API, and CLI

Status: Target

This phase owns definition ingest, public API surfaces, and the later root CLI contract. The current shipped subset in this repo may close `P5A-WP1` while deferring the root CLI noun family to `P5A-WP2`.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Definition registry and upload contract](../../redesign/interfaces/definition-registry-and-upload-contract.md)
- [Definition ingest and upload contract](../../redesign/interfaces/definition-ingest-and-upload-contract.md)
- [CLI surface and operator workflows](../../redesign/interfaces/cli-surface-and-operator-workflows.md)
- [API surface and trust-lane map](../../redesign/interfaces/api-surface-and-trust-lane-map.md)
- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)

## Required supporting redesign reads

- [Interfaces front door](../../redesign/interfaces/README.md)
- [Interface index](../../redesign/interfaces/INDEX.md)
- [MCP, plugin, and CLI boundary](../../redesign/interfaces/mcp-plugin-and-cli-boundary.md)
- [CLI, API, and package shape](../../redesign/interfaces/cli-api-and-package-shape.md)
- [Guarded registry and runtime writes](../../redesign/interfaces/guarded-registry-and-runtime-writes.md)
- [Operator definition and role boundary](../../redesign/interfaces/operator-definition-and-role-boundary.md)
- [Write a nested workflow](../../redesign/how-to/write-a-nested-workflow.md)
- [Create a definition and run a task](../../redesign/tutorials/create-a-definition-and-run-a-task.md)
- [Run a bugfix flow](../../redesign/tutorials/run-a-bugfix-flow.md)

## Required current contrast reads

- [API surface and route map](../../current/interfaces/api-surface-and-route-map.md)
- [API trust lanes](../../current/interfaces/api-trust-lanes.md)
- [CLI surface and config precedence](../../current/interfaces/cli-surface-and-config-precedence.md)
- [Current registry bootstrap ingest and task file upload](../../current/interfaces/current-definition-bootstrap-and-task-upload.md)
- [Definition registry and publish lifecycle](../../current/interfaces/definition-registry-and-publish-lifecycle.md)

## Required examples and diagrams

- [API machine catalog](../../redesign/interfaces/api-machine-catalog.yaml)
- the target CLI examples in [CLI surface and operator workflows](../../redesign/interfaces/cli-surface-and-operator-workflows.md)
- the file-entry examples in [Definition ingest and upload contract](../../redesign/interfaces/definition-ingest-and-upload-contract.md)

## Exhaustive appendix owners

- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)

## Implementation surfaces

- owned surfaces: definition ingest and guarded upload services under `apps/api/app/registry/*` and `apps/api/app/services/*`, API routes and presenters under `apps/api/app/api/*`, later root CLI entrypoints under `apps/api/app/cli.py` when `P5A-WP2` is selected, and the ingest/API/CLI owner docs
- allowed collateral surfaces: compiler or schema surfaces when public ingest payloads require exact alignment, the concrete `operator MCP` definition/task-start parity wrapper under `apps/api/autoclaw/openclaw/operator_server.py`, its narrow shared helper module `apps/api/autoclaw/openclaw/common.py`, and the split implementation package `apps/api/autoclaw/openclaw/operator_mcp/**` when this phase extends the same public/operator noun family, onboarding examples and required tutorials that demonstrate the public nouns, the required current-contrast pages named above when they must be patched to stop teaching stale ingest or task-start framing, and narrow Phase 4B MCP test surfaces only when later-phase operator inventory proof must move out of a previously Phase 4B-owned test file without widening trust-boundary semantics

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

Finish the public ingest, API, and later CLI surfaces so the redesign's public nouns are explicit, test-backed, and teachable from canonical docs, including the OpenClaw lifecycle and tool-surface vocabulary.

## Success criteria

- definition ingest and public noun families match canon
- the selected work package's CLI/API contract is explicit and test-backed
- the OpenClaw lifecycle is explicit as `check`, `setup`, `onboard`, `configure`, and `doctor`, with `bootstrap` removed as the primary public noun
- the CLI docs lock `--json` as output-shape only, `--non-interactive` as the automation switch, rich styling as TTY-only, and the OpenClaw lobster-palette, section-and-panel visual grammar as the copied CLI style
- the CLI and docs keep two canonical MCP tool surfaces and treat `plugin` as adapter or wrapper terminology only
- stale public vocabulary is removed from canonical docs and routes
- when `P5A-WP2` is selected, the root CLI target includes `autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]`
- when `P5A-WP2` is selected, the root CLI target includes zero-arg `autoclaw definitions import [--overwrite reject|allow_new_revision]` for shallow current-working-directory scan only

## Deliverables

- ingest alignment
- public API alignment
- later root CLI alignment

## Milestones

- ingest nouns aligned
- API surface aligned
- CLI contract aligned when `P5A-WP2` is selected

## Ordered work packages

### `P5A-WP1`

- objective: align definition ingest services and public HTTP noun families
- owned surfaces: ingest services, API routes, presenters, ingest docs
- dependencies: earlier runtime and compiler phases complete
- test-first requirement: failing or gap-revealing ingest/API tests
- documentation update requirement: public noun families stay explicit
- subagent allowed: yes
- closeout evidence: canonical route families match docs

### `P5A-WP2`

- objective: align the root CLI contract with canonical ingest, public nouns, and the frozen OpenClaw lifecycle and output rules
- owned surfaces: CLI entrypoints, CLI docs, onboarding examples
- dependencies: `P5A-WP1`
- test-first requirement: CLI contract tests and smoke checks
- documentation update requirement: CLI examples and public nouns update together
- subagent allowed: yes
- closeout evidence: root CLI behavior, OpenClaw lifecycle verbs, and interaction or output rules are explicit and test-backed

## Mandatory checklist

- [ ] the selected work package teaches the same public noun families across its owned docs
- [ ] if `P5A-WP2` is selected, the `autoclaw definitions import ...` target contract is explicit in docs and code
- [ ] `autoclaw openclaw check|setup|onboard|configure|doctor` are locked with the approved roles and `bootstrap` is not used as the primary public noun
- [ ] CLI docs lock `--json`, `--non-interactive`, TTY-only styling, and the warning-first onboarding tone plus the copied high-contrast panel-and-section style at a high level
- [ ] stale public vocabulary is removed from canonical routes and examples
- [ ] any subagents slice stayed inside its ingest/API, CLI, or public-docs ownership

## Required tests

- unit tests for ingest, API, and any selected CLI contract behavior
- integration tests for guarded upload, import, runtime control, and public surfaces
- all currently-viable minimal, normal, and maximal e2e lanes
- SQLite local smoke when the landed public surfaces depend on runtime persistence
- Postgres + Docker strong verification when the landed public surfaces depend on runtime persistence or migrations

## Required docs and examples

- ingest docs
- API examples and, when `P5A-WP2` is selected, CLI examples
- onboarding examples for public nouns
- required examples and diagrams named above

## Candidate delegated slices

- ingest/API slice
- CLI contract slice
- public-docs example slice

## Exit evidence

- public surfaces match the canonical docs
- the selected work package's CLI/API contract is explicit and test-backed
- the OpenClaw lifecycle, MCP tool-surface framing, and CLI output rules match the canonical docs
- stale public vocabulary is removed from canonical routes and docs
- DB-backed public-surface proof lanes are recorded or explicitly blocked with an exact phase-bounded reason

## Reset criteria

- apply the reset gate if public API/CLI truth, ingest persistence, or route families change in a breaking way

## Kill-list terms

- stale public CLI or API nouns
- ingest contract inferred from old route shapes
- `bootstrap` reused as the primary public onboarding noun
- `--json` or `--non-interactive` overloaded into side-effect semantics
- public docs that still require old packs to interpret the new nouns

# AutoClaw coding agent contract

Status: Reference

This is the canonical root instruction surface for coding agents in this repo. Keep this file and `STYLE.md` short, stable, and authoritative. Put extended, example-heavy standards in [`.agents/standards/`](.agents/standards/README.md). If those standards disagree with this file or `STYLE.md`, the root files win.

## Product purpose

AutoClaw is a controlled agent runtime for multi-step work that must stay auditable, replayable, and operationally recoverable.

We are building it so:

- controller-owned runtime truth stays separate from provider behavior
- explicit routing and boundaries beat hidden conversational continuity
- parent, worker, operator, and support lanes stay distinct products
- prompts, plans, artifacts, reviews, and observability stay explicit enough to validate and recover

## Design philosophy

- document target truth before trusting old code shape
- prefer rewrite-first when the current structure hides the target model
- keep recovery, routing, and ownership rules teachable
- treat docs, prompts, examples, and gates as implementation inputs
- keep support observability subordinate to controller truth

## Principles

- do not assume agents know the product concepts, nouns, or rules unless the prompt or docs restate them
- do not assume hidden transcript memory is sufficient for correctness
- do not assume cross-system context sharing is robust, cheap, or lossless
- do not assume filesystem state is canonical runtime truth unless canon says so
- do not assume repo-local YAML or packaged definition files stay canonical after a controller-owned definition registry exists
- do not assume validation preview is equivalent to publish-, start-, commit-, or runtime-time legality
- treat Phase 0-3 as one-process local-tool-first until canon explicitly reopens MQ or distributed-safe compatibility
- do not assume retries are safe to replay across queued or distributed delivery
- do not assume support-state files are authoritative controller truth
- do not assume old compatibility layers deserve to survive
- do not assume provider terminal success implies assignment success
- do not assume missing contract details can be reconstructed safely from nearby code shape
- keep exact inline-versus-after-return timing and sync/async ownership with the owning Phase 2 or Phase 3 docs

## Authority split

- `AGENTS.md` owns shared repo policy, routing, verification expectations, and delegation rules
- `STYLE.md` owns measurable coding standards and refactor triggers
- `.agents/standards/*` owns long-form structural, readability, test, docs, and boundary guidance
- [code/naming.md](.agents/standards/code/naming.md) owns long-form symbol, module, and package naming guidance
- [structure/source-layout.md](.agents/standards/structure/source-layout.md) owns long-form monorepo, package-root, domain-first runtime, transport-thinness, and test-layout guidance
- public product docs, public reference/internals docs, and internal canon docs should remain distinct methodology layers
- `docs-internal/design/**` is the long-term home for target design truth
- `docs-internal/current/**` is the long-term home for shipped-behavior contrast
- `docs-internal/execution/**` owns execution routing, phase contracts, gates, and execution records
- the current phase page owns the phase-local delivery contract
- design appendix owners own exhaustive API, schema, prompt, and payload detail

## Instruction layering

- read this file first
- read `STYLE.md` second
- read `docs-internal/execution/v1/README.md`, `docs-internal/execution/v1/phases/overview.md`, the current phase page, and `docs-internal/execution/v1/maps/file-priority-map.md` before implementation work
- use `.agents/standards/*` for extended cleanup and layout guidance after the root surfaces
- if a closer subtree `AGENTS.md` is added later, treat it as local routing for that subtree, not a silent replacement for root canon

## Docs layout rule

The current docs layout is:

- public docs under `docs/**`
- target design truth under `docs-internal/design/v1/**`
- shipped-behavior contrast under `docs-internal/current/v1/**`
- execution routing, phases, gates, and records under `docs-internal/execution/v1/**`
- durable accepted decisions under `docs-internal/adr/**`
- historical material under `docs-internal/archive/**`

Rules:

- prefer `design/` rather than `redesign/` in all live canon naming
- keep public docs versionless by default
- keep internal version eras explicit with directories such as `v1/`, `v2/`, and `vnext/`
- do not recreate live `docs-internal/design/v1/**`, `docs-internal/current/v1/**`, `docs-internal/execution/v1/**`, or `docs-internal/archive/**` trees

## Source of truth rule

- `docs-internal/design/v1/**` is the current target product and implementation source of truth
- `docs-internal/current/v1/**` is the current shipped-behavior contrast lane
- when target design truth and shipped contrast disagree about target behavior, target design truth wins
- code and tests can expose drift, but they do not overrule target design truth unless canon is silent and is being patched

## Mandatory read order

Read these in order before non-trivial implementation:

1. `STYLE.md`
2. `docs-internal/execution/v1/README.md`
3. `docs-internal/execution/v1/phases/overview.md`
4. the selected current phase page in `docs-internal/execution/v1/phases/`
5. `docs-internal/execution/v1/maps/file-priority-map.md`
6. the primary design pages named by the phase page
7. the required supporting design pages, current-contrast pages, examples, and diagrams named by the phase page
8. the relevant gate pages in `docs-internal/execution/v1/gates/`
9. the smallest relevant subset of `.agents/standards/*`

## Implementation fast path

1. Identify the next blocking design delta and select the owning phase.
2. Run the pre-implementation review flow from `docs-internal/execution/v1/README.md`.
3. If stale repo shape still dominates the target-facing behavior, route to Phase 0.5 before patching forward.
4. Use the current phase page as the sole phase-local contract.
5. Use `docs-internal/execution/v1/maps/file-priority-map.md` as the owned-surface map.
6. Read the required design, current-contrast, example, and diagram pages named by the phase page.
7. Add or update tests early.
8. Implement only the approved work package or bounded slice.
9. Run post-implementation review, gates, reset when applicable, and phase-done checks before claiming completion.
10. If the blocker depends on exact case-sequence timing or sync/async ownership, route it back to the owning Phase 2 or Phase 3 docs instead of inventing new shared canon.

## Answer-source hierarchy

Use this order when a design or implementation question comes up:

1. `docs-internal/design/v1/**`
2. named design appendix owners
3. `docs-internal/current/v1/**`
4. repo code and tests
5. `docs-internal/archive/**`, only when canonical docs are still silent

Rules:

- do not ask the user for answers already covered by design or current docs
- when design and current disagree about target behavior, design wins
- use current only for migration truth or shipped-behavior contrast
- if canonical docs are silent, record the exact gap and patch canon before treating the answer as settled

## Shared implementation stance

- treat target design implementation as override-first
- remove stale core logic instead of leaving parallel truth paths alive
- keep current truth and target truth separate
- keep boundaries explicit and low-surprise
- keep domain concepts typed and named directly
- persist canonical controller relationships as DB-enforced truth when canon names them as authoritative
- when a helper becomes shared across modules, promote it to a public shared surface instead of leaving it underscore-private
- when touched code drifts into structural cleanup, use `STYLE.md` plus [structure/repo-layout.md](.agents/standards/structure/repo-layout.md), [code/readability-refactor.md](.agents/standards/code/readability-refactor.md), and [code/naming.md](.agents/standards/code/naming.md)

## Extended standards router

Use [`.agents/standards/`](.agents/standards/README.md) when the root contract is not enough but the question is still a repo-wide structure, style, docs, test, or boundary issue. Read only the smallest relevant subset.

- [README.md](.agents/standards/README.md) — index, precedence, and use order for the standards tree. Go here first when you are not sure which deeper guide owns the issue.
- [standards-writing.md](.agents/standards/standards-writing.md) — how the standards stack itself should be structured, named, and maintained. Go here when editing `AGENTS.md`, `STYLE.md`, or any file under `.agents/standards/**`.
- [code/readability-refactor.md](.agents/standards/code/readability-refactor.md) — long-form guidance for extraction, control-flow cleanup, helper shaping, whitespace phases, and readability-first refactors. Go here when a slice needs more than formatter output or crosses readability/refactor thresholds.
- [code/naming.md](.agents/standards/code/naming.md) — naming rules for symbols, files, packages, schemas, routes, and CLI/API surfaces. Go here when naming or renaming anything shared, user-visible, or structurally important.
- [structure/repo-layout.md](.agents/standards/structure/repo-layout.md) — repo tree, package splitting, family-stem cleanup, and ownership-by-path guidance. Go here when moving files, splitting directories, or cleaning flat-tree sprawl.
- [structure/source-layout.md](.agents/standards/structure/source-layout.md) — monorepo root ownership, canonical backend package direction, transport thinness, and steady-state source layout. Go here when deciding long-term package roots, transport layering, or source-tree convergence.
- [structure/test-structure.md](.agents/standards/structure/test-structure.md) — proof-lane ownership and where unit, integration, and e2e tests belong. Go here when adding tests, reorganizing test trees, or deciding what evidence is acceptable for a touched slice.
- [structure/integration-boundaries.md](.agents/standards/structure/integration-boundaries.md) — seam ownership between API, services, runtime, registry, DB, CLI, OpenClaw, and support-state surfaces. Go here when a change crosses subsystem boundaries or risks putting logic in the wrong layer.
- [Docs structure guide](.agents/standards/docs/docs-structure.md) — public-versus-internal docs placement, page types, versioning, and docs information architecture. Go here when adding, moving, splitting, or reclassifying docs.

## Testing, proof, and commands

Use real shipped lanes for shipped behavior. Do not treat mocks or ad-hoc setup as equivalent proof when the touched slice owns persistence, runtime truth, CLI behavior, or end-to-end semantics.

Rules:

- add or update tests before claiming a behavior change is done
- where practical, start with a failing or gap-revealing test
- keep exact phase-scoped runs, gate results, and blockers in the matching evidence or review artifacts
- use real DB paths and shipped setup for integration, reset, schema, install, upgrade, and public-surface proof; unit lanes remain unit-scoped
- do not use mocks to stand in for shipped persistence, shipped runtime truth, or shipped public-surface behavior
- keep exact phase-scoped plan, evidence, and review artifacts under `docs-internal/execution/v1/plans/`, `docs-internal/execution/v1/evidence/`, and `docs-internal/execution/v1/reviews/`
- if a command, validator, or lane is skipped, record the exact scope reason or blocker in review
- if test-command expectations change, update this file and the owning command surface such as `Makefile` together

### Test command matrix

- `make check-api` runs lint, mypy, and pyright only; it is not a test command
- `make test-api` runs `apps/api/tests/unit`
- `make test-api-integration-local` runs the repo-native SQLite and runtime-template integration groups
- `make test-api-db` runs the Docker/Postgres-backed integration groups only
- `make test-api-e2e-minimal`, `make test-api-e2e-normal`, and `make test-api-e2e-maximal` are the progressive e2e lanes
- grouped runners must preserve the full coverage of the target they replace and expose readable progress

### Applicability

For touched backend behavior under `apps/api/**`, run every applicable lane before claiming completion:

- `make test-api`
- `make test-api-db`
- `make test-api-integration-local` when the touched slice owns local integration behavior
- the relevant e2e lane when the touched slice reaches parent-first runtime flows, support-state truth, public CLI/API semantics, or other shipped end-to-end behavior

Prefer focused pytest selection while iterating, but do not claim completion until the applicable command matrix for the touched surface is green.

## Repo-native quality gates

For touched Python backend surfaces:

- `ruff format`
- `ruff check`
- `mypy`
- `make pyright-api`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
- the full applicable backend test command matrix
- exact repo search for retained underscore-private shared helpers, plus explicit review justification for any retained exception

For touched prompt assets, prompt-catalog inputs, or generated prompt pages:

- `python -m scripts.docs.prompt_catalog.cli validate`
- `python -m scripts.docs.prompt_catalog.cli generate` first when inputs or generated pages changed
- `ruff check scripts/docs` and `mypy scripts/docs` when the slice touched `scripts/docs/*`

For touched TypeScript, frontend, or plugin surfaces:

- repo-native typecheck
- repo-native build
- repo-native tests when present

For touched docs:

- keep line wrapping and paragraph breaks intentional
- fix broken line-splitting instead of carrying it forward
- update the owning current, design, execution, standards, public product, or public reference surface instead of dropping truth into an unrelated page
- do not collapse public docs and internal canon into one undifferentiated tree; follow [Docs structure guide](.agents/standards/docs/docs-structure.md)
- keep new steady-state path planning aligned with `docs/**` for public docs and `docs-internal/**` for internal canon

## Delegation model

- the parent agent is the router and integrator
- the parent agent owns contract interpretation, critical-path design decisions, integration, final validation, and closeout
- check tool and runtime constraints before spawning subagents
- do not assume forked subagent-of-subagent flows are available, necessary, or appropriate; prefer parent-owned fanout unless the runtime explicitly supports the deeper fork and the plan truly needs it
- use subagents only for bounded slices with explicit owned surfaces
- every plan must say `no subagents` or define the delegated slices
- every delegated slice must be tagged `edit` or `review-only`
- every delegated slice must name the selected phase, owned surfaces, do-not-edit surfaces, required reads, expected outputs, required tests or validators, dependencies, evidence to return, parent-owned decisions, and stop conditions
- subagents must read the docs, tests, code, examples, and diagrams needed for their owned slice before editing
- keep parallel subagent edit surfaces separated
- make every subagent aware of the real user task, the approved plan, and the relevant WBS/work package rather than giving it a context-free patch brief
- when a second pass or independent check matters, use a review-only subagent explicitly
- while a delegation wave is running, the parent waits instead of making proactive repo-tracked edits
- after each delegation wave, the parent agent must verify scope, revert out-of-scope edits, integrate, validate, review, and patch before starting another wave
- for larger docs or codebase tasks, prefer multiple bounded slices over one overloaded child, but keep concurrency intentionally low and ownership explicit
- post-implementation review must verify that delegation respected ownership boundaries
- review-only slices must not edit files; if they do, the parent must stop the slice and revert those edits before integration

### Subagent brief standard

- every subagent brief must name the slice type (`edit` or `review-only`)
- every subagent brief must name the selected phase and the approved work package or bounded slice it serves
- every subagent brief must name owned surfaces and explicit do-not-edit surfaces
- every subagent brief must name the required docs, code, tests, examples, and diagrams the slice must read before editing
- every subagent brief must name expected outputs, required tests or validators, dependencies, evidence to return, parent-owned decisions, and stop conditions
- every subagent brief must tell the slice to stop and report back if the work needs surfaces outside owned or allowed collateral scope

### Wave safety standard

- while a subagent wave is running, the parent agent must not edit repo-tracked files proactively
- the parent agent must wait for the full wave before integrating or patching
- after the wave returns, the parent agent must compare each returned diff against the briefed owned surfaces and slice type before integrating
- the parent agent must revert any out-of-scope edits and any edits produced by review-only slices before integration
- the parent agent must run integration, validation, review, and patch after each wave before starting another wave

### Phase barrier rule

- a subagent may not advance work into a different phase, a later work package, or an unrelated lane on its own
- if landing a slice would require the next phase, a different owning work package, a canon patch, or surfaces outside the approved slice, the subagent must stop and return the blocker or handoff instead of continuing

## Review and closeout rule

Do not claim work complete until:

- the selected phase contract, file-lock map, and approved plan all still agree with the landed diff
- code, docs, tests, and evidence are present together
- the mandatory review gate passes
- the reset gate passes when the touched phase owns DB schema, runtime record contract, package/install path, or public CLI/API truth
- docs-only progress is not being used where code or tests were required
- inspected-only evidence is not standing in for executed proof when executed tests were required and viable
- no locked-surface drift remains without an explicit re-scope or canon update
- no install, upgrade, or reset proof depends on test-only schema creation, direct helper invocation, or other non-shipped setup
- no later-phase behavior still reads authority from repo files after canon assigns that authority to controller-owned DB truth
- the relevant phase kill-list terms have been searched before completion
- the final diff is clean against `AGENTS.md`, `STYLE.md`, and the relevant `.agents/standards/*` guidance
- any skipped lane, retained debt, or exception is written down with an exact owner and reason
- touched Python-owned surfaces do not retain unaccessed private helpers, duplicated logic, redundant branches, or underscore-private shared helpers without exact review justification

## OpenAI docs rule

When touching OpenAI, Codex, or API behavior and repo canon is silent or stale, use official OpenAI docs as the primary external source. Treat external blogs, issue threads, or examples as secondary support only.

## If the docs are silent

If design, current, execution, and the relevant standards are still silent:

1. verify the current code and tests
2. use primary framework docs for the exact technology involved
3. record the canon gap
4. patch the owning canonical surface before calling the answer settled

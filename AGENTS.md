# AutoClaw coding agent contract

Status: Reference

This is the canonical root instruction surface for coding agents in this repo.
Keep this file and `STYLE.md` short, stable, and authoritative. Put extended,
example-heavy standards in [`.agents/standards/`](.agents/standards/README.md). If those standards disagree
with this file or `STYLE.md`, the root files win.

## Product purpose

AutoClaw is a controlled agent runtime for multi-step work that must stay
auditable, replayable, and operationally recoverable.

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

- do not assume hidden transcript memory is sufficient for correctness
- do not assume filesystem state is canonical runtime truth unless canon says so
- treat Phase 0-3 as one-process local-tool-first until canon explicitly reopens MQ or distributed-safe compatibility
- do not assume support-state files are authoritative controller truth
- do not assume old compatibility layers deserve to survive
- do not assume provider terminal success implies assignment success
- do not assume current code can safely fill in missing contract details
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
- read `docs/execution/README.md`, `docs/execution/phases/overview.md`, the current phase page, and `docs/execution/maps/file-priority-map.md` before implementation work
- use `.agents/standards/*` for extended cleanup and layout guidance after the root surfaces
- if a closer subtree `AGENTS.md` is added later, treat it as local routing for that subtree, not a silent replacement for root canon

## Transitional docs rule

The repo is still migrating from the legacy internal-canon layout:

- `docs/redesign/**`
- `docs/current/**`
- `docs/execution/**`
- `docs/archive/**`

Until the migration completes:

- treat `docs/redesign/**` as the current target-design owner
- treat `docs/current/**` as the current shipped-contrast owner
- treat `docs/execution/**` as the current execution owner
- plan all new docs structure work so the steady-state end state becomes:
  - public docs under `docs/**`
  - internal canon under `docs-internal/design/**`,
    `docs-internal/current/**`, `docs-internal/execution/**`,
    `docs-internal/archive/**`, and `docs-internal/adr/**`
- prefer `design/` rather than `redesign/` in all new steady-state naming and planning
- make internal version eras explicit with directories such as `v1/`, `v2/`, and `vnext/`

## Source of truth rule

- `docs/redesign/**` is the current transitional source of target product and implementation truth
- `docs-internal/design/**` is the intended steady-state home for that target truth
- `docs/current/**` is the current transitional shipped-behavior contrast lane
- `docs-internal/current/**` is the intended steady-state home for that contrast
- when target design truth and shipped contrast disagree about target behavior, target design truth wins
- code and tests can expose drift, but they do not overrule target design truth unless canon is silent and is being patched

## Mandatory read order

Read these in order before non-trivial implementation:

1. `STYLE.md`
2. `docs/execution/README.md`
3. `docs/execution/phases/overview.md`
4. the selected current phase page in `docs/execution/phases/`
5. `docs/execution/maps/file-priority-map.md`
6. the primary design pages named by the phase page
7. the required supporting design pages, current-contrast pages, examples, and diagrams named by the phase page
8. the relevant gate pages in `docs/execution/gates/`
9. the smallest relevant subset of `.agents/standards/*`

## Implementation fast path

1. Identify the next blocking design delta and select the owning phase.
2. Run the pre-implementation review flow from `docs/execution/README.md`.
3. If stale repo shape still dominates the target-facing behavior, route to Phase 0.5 before patching forward.
4. Use the current phase page as the sole phase-local contract.
5. Use `docs/execution/maps/file-priority-map.md` as the owned-surface map.
6. Read the required design, current-contrast, example, and diagram pages named by the phase page.
7. Add or update tests early.
8. Implement only the approved work package or bounded slice.
9. Run post-implementation review, gates, reset when applicable, and phase-done checks before claiming completion.
10. If the blocker depends on exact case-sequence timing or sync/async ownership, route it back to the owning Phase 2 or Phase 3 docs instead of inventing new shared canon.

## Answer-source hierarchy

Use this order when a design or implementation question comes up:

1. `docs/redesign/**` now, and `docs-internal/design/**` after migration
2. named design appendix owners
3. `docs/current/**` now, and `docs-internal/current/**` after migration
4. repo code and tests
5. `docs/archive/**` now, and `docs-internal/archive/**` after migration, only when canonical docs are still silent

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

## Extended standards

Use these files for long-form guidance that should not bloat the root contract:

- [README.md](.agents/standards/README.md)
- [standards-writing.md](.agents/standards/standards-writing.md)
- [structure/repo-layout.md](.agents/standards/structure/repo-layout.md)
- [code/readability-refactor.md](.agents/standards/code/readability-refactor.md)
- [code/naming.md](.agents/standards/code/naming.md)
- [structure/source-layout.md](.agents/standards/structure/source-layout.md)
- [structure/test-structure.md](.agents/standards/structure/test-structure.md)
- [docs/docs-structure.md](.agents/standards/docs/docs-structure.md)
- [structure/integration-boundaries.md](.agents/standards/structure/integration-boundaries.md)

## Testing, proof, and commands

Use real shipped lanes for shipped behavior. Do not treat mocks or ad-hoc setup as equivalent proof when the touched slice owns persistence, runtime truth, CLI behavior, or end-to-end semantics.

Rules:

- add or update tests before claiming a behavior change is done
- where practical, start with a failing or gap-revealing test
- keep exact phase-scoped plan, evidence, and review artifacts under `docs/execution/plans/`, `docs/execution/evidence/`, and `docs/execution/reviews/` during the current transition, and move them under `docs-internal/execution/<version>/` when the internal-doc migration lands
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
- do not collapse public docs and internal canon into one undifferentiated tree; follow [docs/docs-structure.md](.agents/standards/docs/docs-structure.md)
- keep new steady-state path planning aligned with `docs/**` for public docs and `docs-internal/**` for internal canon

## Delegation model

- the parent agent owns contract interpretation, integration, final validation, and closeout
- use subagents only for bounded slices with explicit owned surfaces
- every plan must say `no subagents` or define the delegated slices
- every delegated slice must be tagged `edit` or `review-only`
- every brief must name the selected phase, owned surfaces, do-not-edit surfaces, required reads, required tests, expected outputs, dependencies, and stop conditions
- review-only slices must not edit files
- after a delegation wave, the parent agent must verify scope, revert out-of-scope edits, integrate, validate, review, and patch before starting another wave
- a subagent may not advance work into a different phase or unrelated work package on its own

## Review and closeout rule

Do not claim work complete until:

- the selected phase contract, file-lock map, and approved plan all still agree with the landed diff
- code, docs, tests, and evidence are present together
- the final diff is clean against `AGENTS.md`, `STYLE.md`, and the relevant `.agents/standards/*` guidance
- any skipped lane, retained debt, or exception is written down with an exact owner and reason

## OpenAI docs rule

When touching OpenAI, Codex, or API behavior and repo canon is silent or stale, use official OpenAI docs as the primary external source. Treat external blogs, issue threads, or examples as secondary support only.

## If the docs are silent

If design, current, execution, and the relevant standards are still silent:

1. verify the current code and tests
2. use primary framework docs for the exact technology involved
3. record the canon gap
4. patch the owning canonical surface before calling the answer settled

# AutoClaw coding agent contract

Status: Reference

This file is the canonical root instruction surface for Codex and other coding agents working in this repo.

## Product purpose

AutoClaw is a controlled agent runtime for multi-step work that must stay auditable, replayable, and operationally recoverable.

We are building it so:

- controller-owned runtime truth stays separate from provider behavior
- explicit routing and boundaries beat hidden conversational continuity
- parent, worker, operator, and support lanes are distinct products, not one blended loop
- replan, review, checkpoint, artifact, filesystem, definition, compiler, and observability concerns stay explicit enough to validate, recover, and evolve safely

## Design philosophy

- product truth is explicit, controller-owned, and documented before code
- runtime control is a product surface, not an implementation accident
- routing, boundary, and recovery rules must be teachable without relying on agent intuition
- rewrite-first is preferred when old code shape hides or contradicts the target model
- docs, prompts, and examples are implementation inputs, not optional narrative garnish
- support observability exists to explain controller truth, not replace it

## Principles

- do not assume agents know the product concepts, nouns, or rules unless the prompt or docs restate them
- do not assume cross-system context sharing is robust, cheap, or lossless
- do not assume filesystem state is canonical runtime truth unless canon says so
- do not assume validation preview is equivalent to publish-, start-, commit-, or runtime-time legality
- do not assume retries are message-queue safe
- do not assume support-state files are authoritative controller truth
- do not assume compatibility surfaces should survive just because code already exists
- do not assume provider terminal success implies assignment success
- do not assume hidden transcript memory is sufficient for runtime correctness
- do not assume a missing contract detail can be reconstructed safely from nearby code shape

## Authority split

- `AGENTS.md` owns shared coding-agent policy, product-purpose framing, delegation policy, and the implementation quickstart
- `STYLE.md` owns measurable coding standards and refactor triggers
- `STYLE_GUIDE.md` owns docs/style rules only
- `docs/execution/` owns execution routing, phase contracts, the implementation file lock map, gates, checklists, and reusable prompt families
- phase pages own phase-local delivery contracts
- redesign appendix owners own exhaustive API, schema, prompt, and payload detail

## Mandatory read order

Read this file first.

Then read, in order:

1. [STYLE.md](STYLE.md)
2. [Execution pack](docs/execution/README.md)
3. [Phase and gate overview](docs/execution/phases/overview.md)
4. the current phase page in `docs/execution/phases/`
5. [Implementation file lock map](docs/execution/maps/file-priority-map.md)
6. the primary redesign pages named by that phase page
7. any appendix owners named by that phase page when API, schema, prompt, or payload detail matters
8. the relevant gates in `docs/execution/gates/`

## Implementation fast path

When you are implementing:

1. identify the active phase in `docs/execution/phases/overview.md`
2. run the pre-implementation review flow from `docs/execution/README.md`
3. if stale repo shape still dominates target-facing behavior, start with Phase 0.5 before Phase 1
4. use the current phase page as the sole phase-local delivery contract
5. use `docs/execution/maps/file-priority-map.md` as the canonical implementation file lock map
6. use the current phase page plus the implementation file lock map plus the approved phase plan as the immediate execution brief
7. add or update tests early
8. implement only the current work package or bounded slice
9. run post-implementation review, gates, reset when applicable, and phase-done checks before claiming completion

## Answer-source hierarchy

When a design or implementation question comes up, use this order:

1. `docs/redesign/`
2. named redesign appendix owners when exhaustive API, schema, prompt, or payload detail matters
3. `docs/current/`
4. repo code and tests
5. `docs/archive/` or older source packs only when canonical docs are still silent

Rules:

- do not ask the user if `docs/redesign/` or `docs/current/` already answer the question
- when a phase page names appendix owners, use them before reconstructing detail from neighboring pages
- use `docs/current/` only for migration truth or current behavior contrast
- inspect code and tests when implementation reality matters or canonical docs still leave an ambiguity
- if canonical docs are silent, record the exact gap and update canon before treating the answer as settled

## Shared implementation stance

- treat redesign implementation as override-first
- prefer the canonical redesign contract over old code shape
- remove stale core logic instead of leaving it alive in parallel
- keep current truth and target truth separate
- keep boundaries explicit and low-surprise
- keep domain concepts typed and named directly

## Shared TDD and evidence rule

- when a phase changes behavior, add or update tests before claiming the behavior is implemented
- where practical, start with a failing or gap-revealing test
- if failing-first is not practical, record the exact reason and still land the tests before phase closeout
- do not bolt tests on after undocumented behavior drift and treat that as equivalent evidence
- keep exact test runs, gate results, and blockers with phase evidence
- once a minimal, normal, or maximal e2e lane becomes viable, later phases must keep it green

## Repo-native quality gates

For touched Python backend surfaces:

- `ruff format`
- `ruff check`
- `pyright`
- `mypy`
- `pytest`

For touched TypeScript, frontend, or plugin surfaces:

- repo-native `tsc` or `typecheck`
- repo-native build script
- repo-native test script when present

No phase touching those surfaces is complete while relevant gates are failing without an explicit, phase-bounded blocker recorded in review.

## Delegation model

- Codex is the router and integrator
- use subagents for bounded work packages with explicit owned surfaces
- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- keep critical-path design decisions and contract interpretation with the parent agent
- every delegated slice must name owned surfaces, required reads, expected outputs, required tests, dependencies, and evidence to return
- subagents should read the docs, tests, and code needed for their owned slice before editing
- after each subagents wave, the parent agent must integrate the results, run QA and validation, review findings, and patch before starting another wave
- post-implementation review must verify that delegation respected ownership boundaries

## Review and closeout rule

- every phase must pass the mandatory review gate
- every phase touching DB schema, runtime record contract, package/install path, or public CLI/API surface must pass the reset gate
- no phase is done on docs-only progress when code/tests were required
- no phase is done on inspected-only evidence when executed tests were required and viable
- no phase is done when implementation crossed locked surfaces without an explicit re-scope or canon update
- search phase kill-list terms before claiming completion

## OpenAI docs rule

Always use the OpenAI developer documentation MCP server if you need to work with the OpenAI API, ChatGPT Apps SDK, Codex, or OpenAI prompt/model guidance without me having to explicitly ask.

## If the docs are silent

If canonical docs are silent on a required implementation decision:

1. confirm the gap after reading redesign and current pages
2. inspect code and tests
3. use archive/source packs only as fallback evidence
4. write down the exact gap
5. update canonical docs before treating the answer as settled

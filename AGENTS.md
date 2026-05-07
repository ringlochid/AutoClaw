# AutoClaw coding agent contract

Status: Reference

This file is the canonical root instruction surface for Codex and other coding agents working in this repo.
Treat this file, `STYLE.md`, and `docs/execution/` as frozen
implementation-control canon after Phase 0. Change them later only through
explicit canon fixes.

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
- do not assume repo-local YAML or packaged definition files stay canonical after a controller-owned definition registry exists
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
- `docs/execution/` owns execution routing, phase contracts, the implementation file lock map, gates, checklists, and reusable prompt families
- docs authoring rules stay local to their owning canonical surfaces; do not create a competing repo-wide docs-style authority
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
7. the required supporting redesign reads, required current-contrast pages, and required examples or diagrams named by that phase page
8. any appendix owners named by that phase page when API, schema, prompt, or payload detail matters
9. the relevant gates in `docs/execution/gates/`

## Implementation fast path

When you are implementing:

1. identify the active phase in `docs/execution/phases/overview.md`
2. run the pre-implementation review flow from `docs/execution/README.md`
3. if stale repo shape still dominates target-facing behavior, start with Phase 0.5 before Phase 1
4. if a later-phase surface depends on missing earlier-phase truth, route back to the earliest blocking phase instead of patching forward from the later phase
5. use the current phase page as the sole phase-local delivery contract
6. use `docs/execution/maps/file-priority-map.md` as the canonical implementation file lock map
7. read the required supporting redesign reads, required current-contrast pages, and required examples or diagrams named by that phase page
8. use the current phase page plus the implementation file lock map plus the approved phase plan recorded under `docs/execution/plans/` as the immediate execution brief
9. add or update tests early
10. implement only the current work package or bounded slice
11. run post-implementation review, gates, reset when applicable, and phase-done checks before claiming completion
12. compare with git difference for code review, better use a subagents for code review and patch the problems before claim done. every delivery should have a confident review before be claimed.

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
- treat DB-backed definition truth as a prerequisite for any phase that pins or validates workflow, role, or policy revisions
- remove stale core logic instead of leaving it alive in parallel
- remove unaccessed private helpers, redundant branches, and duplicated logic in
  touched owned surfaces unless canon explicitly reserves them for a later phase
- keep current truth and target truth separate
- keep boundaries explicit and low-surprise
- keep domain concepts typed and named directly
- persist canonical controller relationships as DB-enforced truth when canon names them as authoritative currentness or lineage owners
- during ORM modernization, bring owned mapped edges and their primary read paths up to the current `STYLE.md` SQLAlchemy rules when you touch them, but do not widen a work package solely to normalize untouched legacy mappings

## Package layout rule

- prefer responsibility-oriented subpackages over flat prefix-based module piles once one concern grows into several related files or starts crossing the refactor thresholds in `STYLE.md`
- in `apps/api/app/runtime`, group implementation under named responsibility packages such as `launch/`, `prompt/`, `projection/`, `control/`, and `replan/`; keep only stable high-fan-in boundary modules flat, for example `contracts.py`, `ids.py`, and other explicitly justified exceptions
- do not add new generic runtime buckets such as `support`, `resources`, or `lookup` when the real responsibility can be named directly at the package level
- in `apps/api/app/schemas`, keep authored definition contracts and validation under `schemas/definitions/` and keep runtime/operator/observability contracts under `schemas/runtime/`; do not let one schema module mix unrelated route families once the split is already clear
- in `apps/api/app/db/models`, keep runtime model implementation under `db/models/runtime/` and keep registry model implementation separate; once a file already lives under `models/`, do not preserve `_models` suffix naming in the canonical implementation path
- keep `app.db.models.__init__`, `app.db.__init__`, and other outward-facing barrels stable when they are part of metadata/bootstrap truth, but point them at the grouped implementation packages internally
- compatibility shims for moved modules must stay thin re-export layers only, must not accumulate logic, and must be removed or explicitly reviewed in a bounded follow-up instead of becoming a second long-term authority

## Shared TDD and evidence rule

- use docker/cli with the real db fro test, don't use mock.
- when a phase changes behavior, add or update tests before claiming the behavior is implemented
- where practical, start with a failing or gap-revealing test
- if failing-first is not practical, record the exact reason and still land the tests before phase closeout
- do not bolt tests on after undocumented behavior drift and treat that as equivalent evidence
- keep exact test runs, gate results, and blockers with phase evidence
- keep repo-local execution records under `docs/execution/plans/` for approved phase plans, `docs/execution/evidence/` for executed validator or test proof, and `docs/execution/reviews/` for mandatory review outputs or explicit exceptions
- once a minimal, normal, or maximal e2e lane becomes viable, later phases must keep it green
- do not treat tests that manually install missing shipped schema or synthesize missing setup paths as acceptable proof for install, upgrade, reset, or public runtime behavior
- the docker plus db task may take 15 minutes now, which is pretty slow.

## Repo-native quality gates

For touched Python backend surfaces:

- `ruff format`
- `ruff check`
- `pyright`
- `mypy`
- `pytest`
- unused-code audit proof using pyright or editor diagnostics when available
  plus exact repo search for each flagged private symbol retained or removed

For touched TypeScript, frontend, or plugin surfaces:

- repo-native `tsc` or `typecheck`
- repo-native build script
- repo-native test script when present

No phase touching those surfaces is complete while relevant gates are failing without an explicit, phase-bounded blocker recorded in review.

## Delegation model

- Codex is the router and integrator
- use subagents for bounded work packages with explicit owned surfaces
- every subagents slice must be explicitly tagged as `edit` or `review-only`
- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- keep critical-path design decisions and contract interpretation with the parent agent
- every delegated slice must name owned surfaces, required reads, expected outputs, required tests, dependencies, and evidence to return
- subagents should read the docs, tests, and code needed for their owned slice before editing
- after each subagents wave, the parent agent must integrate the results, run QA and validation, review findings, and patch before starting another wave
- principle for subagents
    - context matters, the subagents should read more than need and read carefully with instructions
    - the user's task matters, all subagents should be awared of real plan
    - WBS and workpackage matters
    - all subagents should have separated edit surface when running in parallel
    - when subagents are working, wait instead of doing anything proactively
    - you are the conductor, not the worker, be patient for the subagents, they typically take 20 minutes to finish a task
    - subagents should be also used for code review
    - the final validation and final patch work should be done by parent
    - assumption: for larger docs/codebase, more subagents are needed
- post-implementation review must verify that delegation respected ownership boundaries
- review-only slices must not edit files; if they do, the parent must stop the slice and revert those edits before integration

### Subagent brief standard

- every subagents brief must name the slice type (`edit` or `review-only`)
- every subagents brief must name the selected phase and the approved work package or bounded slice it serves
- every subagents brief must name owned surfaces and explicit do-not-edit surfaces
- every subagents brief must name the required docs, code, tests, examples, and diagrams the slice must read before editing
- every subagents brief must name expected outputs, required tests or validators, dependencies, evidence to return, parent-owned decisions, and stop conditions
- every subagents brief must tell the slice to stop and report back if the work needs surfaces outside owned or allowed collateral scope

### Wave safety standard

- while a subagents wave is running, the parent agent must not edit repo-tracked files proactively
- the parent agent must wait for the full wave before integrating or patching
- after the wave returns, the parent agent must compare each returned diff against the briefed owned surfaces and slice type before integrating
- the parent agent must revert any out-of-scope edits and any edits produced by review-only slices before integration
- the parent agent must run integration, validation, review, and patch after each wave before starting another wave

### Phase barrier rule

- a subagent may not advance work into a different phase, a later work package, or an unrelated lane on its own
- if landing a slice would require the next phase, a different owning work package, or a canon patch outside the approved slice, the subagent must stop and return the blocker or handoff instead of continuing

## Review and closeout rule

- every phase must pass the mandatory review gate
- every phase touching DB schema, runtime record contract, package/install path, or public CLI/API surface must pass the reset gate
- no phase is done on docs-only progress when code/tests were required
- no phase is done on inspected-only evidence when executed tests were required and viable
- no phase is done when implementation crossed locked surfaces without an explicit re-scope or canon update
- no phase is done if fresh install, upgrade, or reset proof still depends on test-only schema creation, direct helper invocation, or other non-shipped setup
- no phase is done if later-phase behavior still reads authority from repo files after canon assigns that authority to controller-owned DB truth
- search phase kill-list terms before claiming completion
- no phase is done if touched Python-owned surfaces still keep flagged unaccessed
  private helpers, duplicated logic, or redundant branches without an exact
  framework or contract justification recorded in review

## OpenAI docs rule

Always use the OpenAI developer documentation MCP server if you need to work with the OpenAI API, ChatGPT Apps SDK, Codex, or OpenAI prompt/model guidance without me having to explicitly ask.

## If the docs are silent

If canonical docs are silent on a required implementation decision:

1. confirm the gap after reading redesign and current pages
2. inspect code and tests
3. use archive/source packs only as fallback evidence
4. write down the exact gap
5. update canonical docs before treating the answer as settled

# Mandatory phase review

Status: Reference

Every redesign phase must pass this review before it can be marked done.

- [ ] landed code matches the phase contract and does not drift from canonical redesign docs
- [ ] landed work matches the approved phase plan deliverables and work packages
- [ ] the approved phase plan is recorded under `docs/execution/plans/`
- [ ] the approved plan, executed evidence, and mandatory review used for closure each name exactly one selected phase
- [ ] the mandatory phase review records that selected phase and the current phase page explicitly
- [ ] the mandatory phase review links the approved plan and executed evidence for that same selected phase
- [ ] the approved plan, executed evidence, and mandatory review use one exact top-of-file execution-record block immediately after `Status:` with `selected phase:`, `current phase page:`, `selected work packages:`, `summary-only:`, and `delegated slices:` in that order
- [ ] delegated-slice records use `delegated slices: none` or the exact labels `slice id:`, `slice type:`, `owned surfaces:`, and `touched surfaces:`
- [ ] the top-level execution-record block is treated as authoritative; any later `## Slice identity` narrative is descriptive only
- [ ] the current phase page still acts as the phase-local contract owner
- [ ] landed work stayed within the implementation file lock map, or any re-scope or canon patch was explicit
- [ ] any checklist explicitly required by the current phase page was completed
- [ ] docs and examples for the phase were updated with the landed behavior
- [ ] when shipped prompt-source ownership changed, app-owned prompt assets, prompt docs mirrors, generated examples, validators, and any narrow package-data wiring changed together
- [ ] required supporting redesign reads named by the phase page were reread when live target semantics, durable decisions, onboarding, recovery, or tutorial coverage mattered
- [ ] required current-contrast pages named by the phase page were reread when migration truth or shipped behavior mattered
- [ ] required examples and diagrams named by the phase page were reviewed against the landed behavior
- [ ] named appendix owners were updated when exhaustive API/schema/prompt detail changed
- [ ] any earlier-phase prerequisite truth that this phase depends on was actually landed instead of silently reconstructed from repo files or old code shape
- [ ] test-first behavior changes were handled correctly, or an exact exception was recorded
- [ ] tests are meaningful for the phase rather than only preserving old behavior
- [ ] relevant repo-native quality gates from `../../../AGENTS.md` passed for the touched surfaces
- [ ] when Phase 0 touched `scripts/docs/*`, `ruff check scripts/docs` and `mypy scripts/docs` both passed
- [ ] touched code is clean enough in function/file responsibility and naming
- [ ] unit tests cover the changed core logic
- [ ] integration tests cover changed runtime, DB, route, provider, or CLI behavior where applicable
- [ ] currently-viable e2e lanes were exercised and reviewed
- [ ] required SQLite, Postgres+Docker, package, or reset verification lanes were exercised and reviewed when the phase page or reset gate required them
- [ ] install, upgrade, or reset proof does not rely on test-only schema creation or synthetic setup outside the shipped path
- [ ] required exit evidence for the phase was captured
- [ ] executed validator, test, gate, reset, and smoke proof is recorded under `docs/execution/evidence/`
- [ ] mandatory review outputs and any explicit exceptions are recorded under `docs/execution/reviews/`
- [ ] the mandatory phase review records delegated-slice compliance
- [ ] the mandatory phase review records the proof lanes relied on for phase closure
- [ ] the mandatory phase review records stale-logic search proof for the phase
- [ ] the mandatory phase review records kill-list proof for the phase
- [ ] the mandatory phase review records docs answer-sourcing proof for the landed decisions
- [ ] the mandatory phase review records any phase-bounded `STYLE.md` exceptions, or an explicit `none`
- [ ] aggregate cross-phase summaries or closeout artifacts were not used as substitute closure evidence and remain summary-only
- [ ] any historical cross-phase or aggregate artifact referenced in the review is marked `summary-only: yes`
- [ ] any cross-phase or aggregate historical artifact referenced in the review uses the `selected phase: none`, `current phase page: none`, and `selected work packages: none` sentinel grammar
- [ ] any historical summary artifact referenced in the review carries truthful `## Authoritative replacements` links that point only to `summary-only: no` replacement artifacts
- [ ] prose disclaimers such as "historical summary only" were not treated as a substitute for `summary-only: yes`
- [ ] delegated slices, if any, used explicit slice type plus owned-surface, do-not-edit, required-read, required-test, dependency, and evidence-return briefs; respected those boundaries; and review-only slices returned no edits
- [ ] each subagents wave, if any, kept the parent out of active repo-tracked-file edits until the wave completed, then ran ownership review, any required revert, integration, validation, review, and patch before another wave
- [ ] stale core logic is not still alive in parallel
- [ ] no obvious under-engineered shortcut replaced a required rewrite
- [ ] reusable execution prompts or checklists touched by the phase still reference the phase page and implementation file lock map instead of downgrading them to suggestions or re-mirroring stale phase-local detail
- [ ] remaining gaps, if any, are exact and phase-bounded rather than vague TODOs

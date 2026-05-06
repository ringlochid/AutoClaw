# Phase done gate

Status: Reference

Use this gate for every redesign phase.

- [ ] the phase goal matches the current phase page
- [ ] the approved phase plan is recorded under `docs/execution/plans/`
- [ ] the mandatory phase review artifact records exactly one selected phase and one current phase page
- [ ] the mandatory phase review artifact links the approved plan and executed evidence for that same selected phase
- [ ] the approved plan, executed evidence, and mandatory review use the exact parseable labels `selected phase:`, `current phase page:`, `selected work packages:`, and `summary-only:`
- [ ] delegated-slice records use `delegated slices: none` or the exact labels `slice id:`, `slice type:`, `owned surfaces:`, and `touched surfaces:`
- [ ] the top-level parseable label block remained the authoritative record grammar; any later `## Slice identity` narrative stayed descriptive only
- [ ] the current phase page remained the sole phase-local contract
- [ ] the landed work stayed within the implementation file lock map, or any re-scope or canon patch was explicit
- [ ] the ordered work packages, milestones, and deliverables for the phase are complete
- [ ] any checklist explicitly required by the current phase page was completed
- [ ] primary redesign contract pages for the phase were updated when needed
- [ ] required supporting redesign reads named by the phase page were used when live target semantics, durable decisions, onboarding, recovery, or tutorial coverage mattered
- [ ] required current-contrast pages named by the phase page were used when migration truth or shipped behavior mattered
- [ ] required examples and diagrams named by the phase page were read and updated when the landed behavior changed them
- [ ] named appendix owners were updated when exhaustive API/schema/prompt detail changed
- [ ] primary code surfaces for the phase were updated enough to land the new design
- [ ] required unit tests were added or updated
- [ ] required integration tests were added or updated
- [ ] every currently-viable e2e workflow lane for this phase passed, or the phase page explicitly says the lane is not yet viable
- [ ] every required SQLite, Postgres+Docker, package, or reset verification lane named by the phase page or reset gate passed, or an exact blocker was recorded
- [ ] behavior-changing work followed the shared TDD rule in `../../../AGENTS.md`, or an exact exception was recorded
- [ ] docs and examples affected by the phase were updated
- [ ] the code quality gate passed for the touched language surfaces
- [ ] when Phase 0 touched `scripts/docs/*`, `ruff check scripts/docs` and `mypy scripts/docs` both passed
- [ ] the mandatory phase review passed
- [ ] the reset gate passed when the phase changed DB/schema/package/public-surface truth
- [ ] the mandatory phase review records delegated-slice compliance and the proof lanes relied on for closure
- [ ] stale-logic search proof for the phase is recorded in the mandatory phase review
- [ ] kill-list proof is recorded in the mandatory phase review and shows no live core logic remains under the phase kill-list terms
- [ ] docs answer-sourcing proof is recorded in the mandatory phase review
- [ ] phase-bounded `STYLE.md` exceptions are recorded in the mandatory phase review, or it states `none`
- [ ] cross-phase closeout artifacts, if referenced, remain summary-only and were not used as phase closure authority
- [ ] any historical cross-phase or aggregate artifact referenced for context is marked `summary-only: yes`
- [ ] prose disclaimers such as "historical summary only" were not treated as a substitute for `summary-only: yes`
- [ ] reusable prompts, gates, or checklists touched for the phase still point back to the current phase page and implementation file lock map instead of silently redefining or downgrading them
- [ ] subagents, if used, stayed bounded by explicit slice type and owned surfaces; review-only slices returned no edits; and each wave ran parent wait, ownership review, any required revert, integration, validation, review, and patch
- [ ] the phase is not marked done on inspected-only evidence when executed tests were required
- [ ] the required exit evidence and review artifacts were recorded
- [ ] executed validator, test, gate, reset, and smoke proof is recorded under `docs/execution/evidence/`
- [ ] mandatory review outputs and explicit exceptions are recorded under `docs/execution/reviews/`

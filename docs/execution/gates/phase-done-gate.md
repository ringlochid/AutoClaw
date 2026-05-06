# Phase done gate

Status: Reference

Use this gate for every redesign phase.

- [ ] the phase goal matches the current phase page
- [ ] the approved phase plan is recorded under `docs/execution/plans/`
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
- [ ] stale-logic search for the phase was run
- [ ] no kill-list terms for the phase remain as live core logic
- [ ] the implementation followed the docs answer-sourcing checklist
- [ ] reusable prompts, gates, or checklists touched for the phase still point back to the current phase page instead of silently redefining it
- [ ] subagents, if used, stayed bounded and each wave ran integration, validation, review, and patch
- [ ] the phase is not marked done on inspected-only evidence when executed tests were required
- [ ] the required exit evidence and review artifacts were recorded
- [ ] executed validator, test, gate, reset, and smoke proof is recorded under `docs/execution/evidence/`
- [ ] mandatory review outputs and explicit exceptions are recorded under `docs/execution/reviews/`

# Phase done gate

Status: Reference

Use this gate for every redesign phase.

- [ ] the phase goal matches the current phase page
- [ ] the current phase page remained the sole phase-local contract
- [ ] the landed work stayed within the implementation file lock map, or any re-scope or canon patch was explicit
- [ ] the ordered work packages, milestones, and deliverables for the phase are complete
- [ ] any checklist explicitly required by the current phase page was completed
- [ ] primary redesign contract pages for the phase were updated when needed
- [ ] named appendix owners were updated when exhaustive API/schema/prompt detail changed
- [ ] primary code surfaces for the phase were updated enough to land the new design
- [ ] required unit tests were added or updated
- [ ] required integration tests were added or updated
- [ ] every currently-viable e2e workflow lane for this phase passed, or the phase page explicitly says the lane is not yet viable
- [ ] behavior-changing work followed the shared TDD rule in `../../../AGENTS.md`, or an exact exception was recorded
- [ ] docs and examples affected by the phase were updated
- [ ] the code quality gate passed for the touched language surfaces
- [ ] the mandatory phase review passed
- [ ] the reset gate passed when the phase changed DB/schema/package/public-surface truth
- [ ] stale-logic search for the phase was run
- [ ] no kill-list terms for the phase remain as live core logic
- [ ] the implementation followed the docs answer-sourcing checklist
- [ ] reusable prompts, gates, or checklists touched for the phase still point back to the current phase page instead of silently redefining it
- [ ] subagents, if used, stayed bounded and each wave ran integration, validation, review, and patch
- [ ] the phase is not marked done on inspected-only evidence when executed tests were required
- [ ] the required exit evidence and review artifacts were recorded

# Mandatory phase review

Status: Reference

Every redesign phase must pass this review before it can be marked done.

- [ ] landed code matches the phase contract and does not drift from canonical redesign docs
- [ ] landed work matches the approved phase plan deliverables and work packages
- [ ] the approved phase plan is recorded under `docs/execution/plans/`
- [ ] the approved plan, executed evidence, and mandatory review used for closure each name exactly one selected phase
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
- [ ] aggregate cross-phase summaries were not used as substitute closure evidence
- [ ] delegated slices, if any, used explicit slice type plus owned-surface, do-not-edit, required-read, required-test, dependency, and evidence-return briefs; respected those boundaries; and review-only slices returned no edits
- [ ] each subagents wave, if any, kept the parent out of active repo-tracked-file edits until the wave completed, then ran ownership review, any required revert, integration, validation, review, and patch before another wave
- [ ] stale core logic is not still alive in parallel
- [ ] no obvious under-engineered shortcut replaced a required rewrite
- [ ] reusable execution prompts or checklists touched by the phase still reference the phase page and implementation file lock map instead of downgrading them to suggestions or re-mirroring stale phase-local detail
- [ ] remaining gaps, if any, are exact and phase-bounded rather than vague TODOs

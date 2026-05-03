# Mandatory phase review

Status: Reference

Every redesign phase must pass this review before it can be marked done.

- [ ] landed code matches the phase contract and does not drift from canonical redesign docs
- [ ] landed work matches the approved phase plan deliverables and work packages
- [ ] the current phase page still acts as the phase-local contract owner
- [ ] landed work stayed within the implementation file lock map, or any re-scope or canon patch was explicit
- [ ] any checklist explicitly required by the current phase page was completed
- [ ] docs and examples for the phase were updated with the landed behavior
- [ ] named appendix owners were updated when exhaustive API/schema/prompt detail changed
- [ ] test-first behavior changes were handled correctly, or an exact exception was recorded
- [ ] tests are meaningful for the phase rather than only preserving old behavior
- [ ] relevant repo-native quality gates from `../../../AGENTS.md` passed for the touched surfaces
- [ ] touched code is clean enough in function/file responsibility and naming
- [ ] unit tests cover the changed core logic
- [ ] integration tests cover changed runtime, DB, route, provider, or CLI behavior where applicable
- [ ] currently-viable e2e lanes were exercised and reviewed
- [ ] required exit evidence for the phase was captured
- [ ] delegated slices, if any, respected their owned surfaces and returned the required evidence
- [ ] each subagents wave, if any, ran integration, validation, review, and patch before another wave
- [ ] stale core logic is not still alive in parallel
- [ ] no obvious under-engineered shortcut replaced a required rewrite
- [ ] reusable execution prompts or checklists touched by the phase still reference the phase page rather than re-mirroring stale phase-local detail
- [ ] remaining gaps, if any, are exact and phase-bounded rather than vague TODOs

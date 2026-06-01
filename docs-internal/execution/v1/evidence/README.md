# Execution Evidence

Status: Reference

This folder is the canonical repo-local home for executed validator, test, gate, reset, and smoke evidence tied to execution-pack work.

Use this folder for:

- command logs and result summaries
- validator and test outcomes
- gate, reset, SQLite, Postgres, package, and smoke proof
- exact blockers or failures that stop closeout

Rules:

- evidence here supports the selected phase plan; it does not replace gate decisions or the phase page
- keep exact commands, pass or fail outcomes, and blockers explicit
- link each evidence artifact back to its plan under `../plans/` and any review output under `../reviews/`
- keep the top-level parseable label block exact and at line start
- use `## Artifacts changed` for the phase-scoped changed-surface inventory so validator coverage and human review stay aligned
- use `## Residual blockers` to record exact remaining blockers, or `none`, so the section label matches the authoritative closeout evidence surfaces

Start with [phase-evidence-template.md](phase-evidence-template.md).

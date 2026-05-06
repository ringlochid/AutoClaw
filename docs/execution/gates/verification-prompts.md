# Verification prompts

Status: Reference

Use these prompts for post-implementation review before claiming any phase is complete. Shared execution policy lives in [AGENTS.md](../../../AGENTS.md). Coding standards live in [STYLE.md](../../../STYLE.md).

## Post-implementation review prompt

```text
Run the post-implementation review for the current redesign phase.

Do not expand scope. Verify the landed work only against the approved phase plan and the canonical docs.

Tasks:
1. Re-read AGENTS.md, STYLE.md, the approved phase plan from `docs/execution/plans/`, the current phase page, the implementation file lock map, and the primary redesign reference pages.
2. Re-read the required supporting redesign reads, required current-contrast pages, required examples, and required diagrams named by the current phase page.
3. Re-read any appendix owners named by the current phase page when exact API/schema/prompt/payload detail matters.
4. Confirm the current phase page still matches the intended delivery contract.
5. Confirm that the approved plan and any evidence or review artifact being used for closure each name exactly one selected phase, and treat any aggregate cross-phase summary as reference-only.
6. Confirm the landed work stayed within the locked implementation surfaces, or that any phase-bounded re-scope or canon patch was recorded explicitly.
7. List the primary code surfaces, docs, prompts, gates, and examples that should have changed.
8. Confirm whether they changed enough to land the new design.
9. Confirm whether the shared TDD rule was followed for behavior changes, or whether an exact exception was recorded.
10. List the repo-native quality gates that should have run for the touched surfaces.
11. Confirm whether they ran and whether they passed. When Phase 0 touched `scripts/docs/*`, this explicitly includes `ruff check scripts/docs` and `mypy scripts/docs`.
12. List the unit, integration, currently-viable e2e, and any required SQLite, Postgres+Docker, package, or reset verification lanes that should exist.
13. Confirm whether they exist and whether they pass.
14. Confirm whether the required deliverables, milestones, work packages, required supporting redesign reads, required current-contrast reads, required examples/diagrams, and exit evidence from the approved phase plan were satisfied and recorded under phase-scoped artifacts in `docs/execution/evidence/`.
15. Run the code quality gate and mandatory phase review.
16. Run the reset gate if DB/schema/package/public-surface truth changed.
17. Search for stale logic and phase kill-list terms that should have been removed.
18. Confirm that any phase-local required checklist was completed.
19. Review delegation results:
    - were delegated work packages bounded correctly?
    - did returned evidence match the requested ownership and tests?
    - did any delegated slice silently change non-owned surfaces?
    - did each subagents wave run integration, validation, review, and patch before another wave?
20. Review agentic behavior:
    - did the work stay on the selected current phase?
    - did tool or route choices match the current docs?
    - did any docs gap get patched before code assumed new truth?
21. If anything is incomplete, do not claim done. Produce an exact remaining-work list.
```

## Mandatory phase review prompt

```text
Run the mandatory phase review for the current phase.

Check:
- does the landed work match the phase contract and approved phase plan?
- do the approved plan, executed evidence, and mandatory review used for closure each name exactly one selected phase?
- did the current phase page remain the phase-local authority?
- did the landed work stay within the locked implementation surfaces?
- were docs, prompts, gates, and examples updated where required?
- were required supporting redesign reads, required current-contrast pages, and required examples/diagrams from the current phase page actually used?
- were named appendix owners updated when exhaustive detail changed?
- was every required checklist completed?
- were tests added or updated early enough to satisfy the shared TDD rule?
- are the tests sufficient and meaningful for the phase?
- were required SQLite, Postgres+Docker, package, or reset verification lanes run when the phase page or reset gate required them?
- did the touched language surfaces pass the repo-native quality gates?
- are the touched files and functions clean in naming, responsibility, and measurable thresholds from STYLE.md?
- does stale core logic still survive in parallel?
- did the implementation take under-engineered shortcuts or avoid a required refactor?
- did delegation respect ownership boundaries and return the required evidence?
- did each subagents wave run integration, validation, review, and patch before another wave?
- were aggregate cross-phase summaries kept as reference-only rather than treated as closure evidence?

Return:
- pass or fail
- exact findings
- remaining fixes before the phase can close
```

# Verification prompts

Status: Reference

Use these prompts for post-implementation review before claiming any phase is complete. Shared execution policy lives in [AGENTS.md](../../../AGENTS.md). Coding standards live in [STYLE.md](../../../STYLE.md).

## Post-implementation review prompt

```text
Run the post-implementation review for the current redesign phase.

Do not expand scope. Verify the landed work only against the approved phase plan and the canonical docs.

Tasks:
1. Re-read AGENTS.md, STYLE.md, the approved phase plan, the current phase page, the implementation file lock map, and the primary redesign reference pages.
2. Re-read any appendix owners named by the current phase page when exact API/schema/prompt/payload detail matters.
3. Confirm the current phase page still matches the intended delivery contract.
4. Confirm the landed work stayed within the locked implementation surfaces, or that any phase-bounded re-scope or canon patch was recorded explicitly.
5. List the primary code surfaces, docs, prompts, gates, and examples that should have changed.
6. Confirm whether they changed enough to land the new design.
7. Confirm whether the shared TDD rule was followed for behavior changes, or whether an exact exception was recorded.
8. List the repo-native quality gates that should have run for the touched surfaces.
9. Confirm whether they ran and whether they passed.
10. List the unit, integration, and currently-viable e2e tests that should exist.
11. Confirm whether they exist and whether they pass.
12. Confirm whether the required deliverables, milestones, work packages, and exit evidence from the approved phase plan were satisfied.
13. Run the code quality gate and mandatory phase review.
14. Run the reset gate if DB/schema/package/public-surface truth changed.
15. Search for stale logic and phase kill-list terms that should have been removed.
16. Confirm that any phase-local required checklist was completed.
17. Review delegation results:
    - were delegated work packages bounded correctly?
    - did returned evidence match the requested ownership and tests?
    - did any delegated slice silently change non-owned surfaces?
    - did each subagents wave run integration, validation, review, and patch before another wave?
18. Review agentic behavior:
    - did the work stay on the active phase?
    - did tool or route choices match the current docs?
    - did any docs gap get patched before code assumed new truth?
19. If anything is incomplete, do not claim done. Produce an exact remaining-work list.
```

## Mandatory phase review prompt

```text
Run the mandatory phase review for the current phase.

Check:
- does the landed work match the phase contract and approved phase plan?
- did the current phase page remain the phase-local authority?
- did the landed work stay within the locked implementation surfaces?
- were docs, prompts, gates, and examples updated where required?
- were named appendix owners updated when exhaustive detail changed?
- was every required checklist completed?
- were tests added or updated early enough to satisfy the shared TDD rule?
- are the tests sufficient and meaningful for the phase?
- did the touched language surfaces pass the repo-native quality gates?
- are the touched files and functions clean in naming, responsibility, and measurable thresholds from STYLE.md?
- does stale core logic still survive in parallel?
- did the implementation take under-engineered shortcuts or avoid a required refactor?
- did delegation respect ownership boundaries and return the required evidence?
- did each subagents wave run integration, validation, review, and patch before another wave?

Return:
- pass or fail
- exact findings
- remaining fixes before the phase can close
```

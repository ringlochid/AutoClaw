# Write tests for a phase

Status: Reference

This page defines the phase-local testing workflow. Shared TDD and quality-gate policy lives in [AGENTS.md](../../../../AGENTS.md). Measurable coding standards live in [STYLE.md](../../../../STYLE.md).

## Procedure

1. Identify the current work package, its dependencies, and its success criteria.
2. Identify the behavior and contract boundaries that are changing.
3. Add or update unit and integration tests early.
4. Where practical, make the first relevant test run fail or expose the gap before implementing.
5. Implement until the relevant tests for the current work package go green.
6. Run every currently-viable minimal, normal, and maximal e2e lane required by the current phase.
7. Run any required SQLite, Postgres+Docker, package, or reset verification lane named by the current phase page or reset gate.
8. Update examples, diagrams, and docs required by the same work package.
9. Record whether evidence is inspected-only or executed-test-backed.
10. Use the mandatory review, code quality, and reset gates as applicable.

## Progressive e2e rule

- minimal lane enters once prompt, runtime, and bootstrap flow are viable
- normal lane enters once parent, review, and closure flow are viable
- maximal lane enters once multi-subtree, review, and replan flow are viable

For the exact lane matrix, see [Progressive e2e workflow lanes](../phases/progressive-e2e-workflow-lanes.md).

## Persistence and package rule

E2E workflow lanes are not the only required proof.

If the current phase changes runtime persistence, DB/schema truth, package-install truth, or public API/CLI truth:

- run the SQLite smoke lane when viable
- run the Postgres + Docker strong lane when viable
- run package or reset smoke when the phase page or reset gate requires it
- record the exact blocker if one of those lanes is not yet viable

## Surface rule

Tests are not a substitute for repo-native quality gates or post-implementation review.

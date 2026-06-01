# AutoClaw extended standards

Status: Reference

This directory holds long-form agent guidance that supports `AGENTS.md` and
`STYLE.md` without turning the root files into books.

## Precedence

- `AGENTS.md` wins on repo policy, routing, verification, and delegation
- `STYLE.md` wins on measurable coding standards and refactor triggers
- the current phase page and `docs/execution/maps/file-priority-map.md` win on owned surfaces and phase-local delivery rules
- files in this directory explain how to apply those rules in larger structural or cleanup work

## Use order

Read only the smallest relevant subset:

1. `AGENTS.md`
2. `STYLE.md`
3. the execution pack and current phase page
4. the relevant file in this directory

If a future subtree `AGENTS.md` exists near the code you are touching, read it after the root files and before applying the matching standard.

## Files

- `repo-layout.md`: responsibility-oriented tree shape, package extraction, naming, and file-family cleanup
- `readability-refactor.md`: rewrite-versus-patch decisions, touched-surface cleanup expectations, and exception discipline
- `test-structure.md`: lane ownership, test placement, and proof quality
- `docs-structure.md`: three-layer docs methodology, public versus internal separation, and versioned internal-canon rules
- `integration-boundaries.md`: backend, runtime, CLI, gateway, operator, and support-state boundary rules

## Update rule

Update these files when the root rules stay stable but the repo needs better examples, sharper cleanup guidance, or a clearer operating playbook.

If a change alters measurable repo-wide policy, update `AGENTS.md` or `STYLE.md` instead of hiding the rule here.

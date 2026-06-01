# AutoClaw extended standards

Status: Reference

This directory holds long-form agent guidance that supports
[`AGENTS.md`](../../AGENTS.md) and [`STYLE.md`](../../STYLE.md) without turning
those root files into books.

## Precedence

- [`AGENTS.md`](../../AGENTS.md) wins on repo policy, routing, verification,
  and delegation
- [`STYLE.md`](../../STYLE.md) wins on measurable coding standards and refactor
  triggers
- the current phase page and
  [`docs/execution/maps/file-priority-map.md`](../../docs/execution/maps/file-priority-map.md)
  win on owned surfaces and phase-local delivery rules
- files in this directory explain how to apply those rules in larger
  structural or cleanup work

## Use order

Read only the smallest relevant subset:

1. [`AGENTS.md`](../../AGENTS.md)
2. [`STYLE.md`](../../STYLE.md)
3. the execution pack and current phase page
4. the relevant file in this directory

If a future subtree `AGENTS.md` exists near the code you are touching, read it
after the root files and before applying the matching standard.

## Structure

- [`standards-writing.md`](./standards-writing.md): how the standards stack
  itself should be structured and maintained
- [`code/`](./code/): code-writing and symbol-level standards
- [`structure/`](./structure/): repo, source, integration, and test layout
  standards
- [`docs/`](./docs/): docs information architecture standards

## File map

### Code
- [`code/readability-refactor.md`](./code/readability-refactor.md)
- [`code/naming.md`](./code/naming.md)

### Structure
- [`structure/repo-layout.md`](./structure/repo-layout.md)
- [`structure/source-layout.md`](./structure/source-layout.md)
- [`structure/test-structure.md`](./structure/test-structure.md)
- [`structure/integration-boundaries.md`](./structure/integration-boundaries.md)

### Docs
- [`docs/docs-structure.md`](./docs/docs-structure.md)

## Update rule

Update these files when the root rules stay stable but the repo needs better
examples, sharper cleanup guidance, or a clearer operating playbook.

If a change alters measurable repo-wide policy, update
[`AGENTS.md`](../../AGENTS.md) or [`STYLE.md`](../../STYLE.md) instead of
hiding the rule here.

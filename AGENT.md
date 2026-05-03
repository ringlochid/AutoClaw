# AutoClaw agent quickstart

Status: Reference

`AGENTS.md` is the canonical root instruction surface for this repo. This file is a compatibility bridge only.

Use `AGENTS.md` for the shared coding-agent policy, read order, answer-source hierarchy, delegation rules, and review/closeout rules.

## Implementation fast path

1. Read `AGENTS.md` first.
2. Read `STYLE.md`.
3. Read `docs/execution/README.md` and `docs/execution/phases/overview.md`.
4. Select the current phase from `docs/execution/phases/overview.md`.
5. Read the current phase page and treat it as the sole phase-local contract.
6. Read `docs/execution/maps/file-priority-map.md`.
7. Read the primary redesign owner pages named by the phase page.
8. if exact API/schema/prompt detail matters, read the named appendix owners.
9. Run the execution-pack review, planning, and verification flow before claiming completion.

# AutoClaw

AutoClaw is a long-running adaptive workflow framework built on top of OpenClaw.

## Current repo purpose

This repo holds the **AutoClaw framework layer**:
- definition registry seeds for roles / policies / workflows
- deterministic compiler scaffolding
- runtime/control-plane scaffolding
- operator console scaffolding

It does **not** own OpenClaw's skill package source by default.

## Ownership boundary

- **OpenClaw owns** actual skill packages (`SKILL.md`, scripts, references, execution behavior).
- **AutoClaw owns** workflow/role/policy definitions, skill bindings/refs, compile/runtime state, and operator UX.

## Repo shape

- `definitions/` — user-editable seed definitions
- `apps/api/` — registry + compiler + runtime backend
- `apps/console/` — operator dashboard
- `examples/` — example workflows / plan patches / demo data
- `docs/` — architecture and decisions

## Roadmap

- `ROADMAP.md` — canonical front-door roadmap
- `docs/roadmap/current.md` — current working phase
- `docs/roadmap/` — detailed phase documents and backlog

## First implementation target

Build only the minimum kernel first:
1. definition registry
2. deterministic compiler v0
3. parent + main-loop-child runtime
4. checkpoints / approvals / basic retries
5. simple operator status view

# Authoring, Compiler, and Runtime

## Authoring surfaces

Users should be able to change these without engine changes:

- **roles** — who a node is
- **policies** — retry / approval / watchdog / escalation rules
- **workflows** — reusable graph / subtree templates and pack composition
- **skill bindings** — references to OpenClaw-managed skills

AutoClaw should treat those as source definitions, not as live runtime truth.

## Skill ownership boundary

OpenClaw owns actual skill packages:
- `SKILL.md`
- nested scripts
- references / assets
- skill execution behavior

AutoClaw owns:
- skill references / compatibility metadata
- version pinning
- binding of roles/workflows/policies to skills

## Planner vs compiler vs runtime

Use a strict split:

- **planner** proposes or patches the next shape of work
- **compiler** deterministically validates, normalizes, and lowers accepted definitions or patches into IR
- **runtime** instantiates and executes the compiled plan revision

The runtime must not interpret raw authoring definitions directly.

## Compile boundary vs dispatch boundary

Compile when executable structure changes:
- run start
- published definition change used for a new run
- accepted plan patch

Do not full-compile before every leaf action.

Before each real step, do only cheap dispatch validation:
- dependencies satisfied?
- approval state valid?
- node runnable under current plan revision?
- not paused / blocked / cancelled?

## Four levels of planning output

1. **private reasoning** — scratch thinking inside the parent session; not compiled
2. **dispatch decision** — choose the next step inside the current plan; usually not recompiled
3. **plan patch proposal** — candidate executable change; must be validated
4. **compiled plan revision** — accepted executable truth for the next phase of the run

## Safe recompile boundaries

A new plan revision should be adopted only at safe boundaries:
- after a typed checkpoint
- after approval resolution
- after explicit blocked state
- after watchdog intervention at a safe stop point

Never replace executable plan structure mid-tool-call.

## Determinism rule

Planning may be hybrid.
Compilation must be deterministic once inputs are pinned.

That gives us:
- reproducibility
- plan hashing
- debuggable diffs
- safer rollback and audit

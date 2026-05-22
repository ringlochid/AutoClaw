# AutoClaw docs

Status: Reference

This is the canonical docs root and front-door router for AutoClaw. `AGENTS.md`, `STYLE.md`, and `docs/execution/` are implementation-control surfaces that freeze after Phase 0.

Use it to choose the right truth surface before reading implementation repos or archive material. When target product or implementation truth matters, start with `redesign/`. Use `current/` only for shipped-behavior contrast and migration checks.

## Search-first routing

If you are asking:

- "How does closure work?" -> start at [Target redesign contract](redesign/README.md), then go to [Runtime boundary and controller loop](redesign/architecture/runtime-boundary-and-controller-loop-contract.md)
- "How do parent/root release and closure work?" -> start at [Target redesign contract](redesign/README.md), then go to [Runtime boundary and controller loop](redesign/architecture/runtime-boundary-and-controller-loop-contract.md) and [Parent/root release and closure](redesign/workflows/parent-root-release-and-closure.md)
- "Where is the task-compose schema?" -> go to [Task compose schema](redesign/workflows/task-compose-schema.md)
- "What is the operator boundary or target operator plugin contract?" -> go to [Operator definition and role boundary](redesign/interfaces/operator-definition-and-role-boundary.md) and [Plugin tool reference](redesign/interfaces/plugin-tool-reference.md)
- "What happened to removed approval-era or skill-write surfaces?" -> go to [Current schema, route, and plugin migration appendix](execution/maps/current-schema-route-and-plugin-migration-appendix.md), [Plugin tool reference](redesign/interfaces/plugin-tool-reference.md), and [Runtime database and object contract](redesign/architecture/runtime-database-and-object-contract.md)
- "What is operator trace?" -> go to [Plugin tool reference](redesign/interfaces/plugin-tool-reference.md) and [Runtime observability and boundary log](redesign/architecture/runtime-observability-and-boundary-log.md)
- "What does the current bridge plugin expose today?" -> go to [Use the current OpenClaw bridge plugin](current/operations/use-the-openclaw-bridge-plugin.md)
- "Where are exact dispatch prompt examples?" -> go to [Generated prompt reference](redesign/prompt-layer/generated/README.md)
- "What does the current implementation actually do?" -> go to [Current implementation truth](current/README.md)
- "How do I land the redesign in repo code?" -> go to [Execution pack](execution/README.md)

## Start here

- [Target redesign contract](redesign/README.md)
- [Execution pack](execution/README.md)
- [Current implementation truth](current/README.md)
- [Product narrative](product/README.md)
- [Archive provenance](archive/README.md)
- [Root agent guidance](../AGENTS.md)
- [Coding standards](../STYLE.md)

## Source of truth rule

- `redesign/` is the target product and implementation source of truth
- `current/` is shipped implementation truth and contrast only
- `execution/` defines how to land redesign canon in code and docs
- code and tests may confirm shipped behavior or expose drift, but they do not replace redesign canon unless canon is silent and is being patched

## Keywords

- canonical docs map
- current truth
- redesign truth
- execution pack
- operator plugin
- operator trace
- removed approval-era surfaces
- skill writes
- task-compose schema
- generated prompt examples

## Prompt layer

- Target prompt truth starts at [redesign/prompt-layer/README.md](redesign/prompt-layer/README.md).
- Current prompt truth starts at [current/interfaces/prompt-layer-and-worker-delivery.md](current/interfaces/prompt-layer-and-worker-delivery.md).
- Current OpenClaw/session/watchdog implementation truth starts under [current/architecture/README.md](current/architecture/README.md).
- Target external-operator and parent-owned watchdog behavior starts under [redesign/architecture/README.md](redesign/architecture/README.md).

## Surface ownership

- `product/` explains the product, operators, and workflow stories.
- `redesign/` defines the target contract only.
- `current/` describes the shipped implementation only.
- `execution/` defines how to land the redesign in code and docs.
- `archive/` keeps provenance, source packs, and historical disposition notes.

## Front-door rule

Use this page to choose the right canonical truth surface.

If current and redesign disagree about target behavior, redesign is the authority and current stays contrast-only.

Do not use it as the place to learn detailed prompt contracts, exact generated dispatch examples, or historical design provenance.

## Not authoritative

- Subrepo `README.md` files are entrypoint stubs and local repo notes.
- historical subrepo docs are repo context only.

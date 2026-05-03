# Current implementation docs

Status: Current

Last verified: 2026-04-27

This tree owns shipped AutoClaw behavior only. Use it for code-aligned implementation truth, migration checks, and current operator guidance. It is not the redesign contract.

Current route nouns such as `/flows/*`, `/registry/*`, `/tasks/composes/start`, and deeper `/internal/*` bridge paths are shipped implementation truth only. They are not the redesign's canonical lane names.

## Canonical current owners

- [Current architecture](architecture/README.md)
- [Current interfaces](interfaces/README.md)
- [Current operations](operations/README.md)

## Search-first routing

If you are asking:

- "What routes exist today?" -> [API surface and route map](interfaces/api-surface-and-route-map.md)
- "What are the current operator and internal trust lanes?" -> [API trust lanes](interfaces/api-trust-lanes.md)
- "What does the CLI do today?" -> [CLI surface and config precedence](interfaces/cli-surface-and-config-precedence.md)
- "How does current OpenClaw dispatch work?" -> [OpenClaw dispatch and session contract](architecture/openclaw-dispatch-and-session-contract.md)
- "What is the current worker prompt-delivery shape?" -> [Prompt layer and worker delivery](interfaces/prompt-layer-and-worker-delivery.md)
- "Where are the exact current bridge prompt strings?" -> [Current exact OpenClaw bridge prompt strings](interfaces/current-openclaw-bridge-prompt-strings.md)
- "What raw operator query tools exist today?" -> [Current runtime read models and operator surfaces](architecture/runtime-read-models-and-operator-surfaces.md)
- "How do current definition ingest and task uploads split?" -> [Current registry bootstrap ingest and task file upload](interfaces/current-definition-bootstrap-and-task-upload.md)
- "How do I install or verify the current system?" -> [Current operations](operations/README.md)
- "What is the shipped task-compose or YAML contract?" -> [Definition and task-compose YAML contract](interfaces/definition-and-task-compose-yaml-contract.md)

## Surface map

- `architecture/` owns current runtime, boundary, continuity, and observability truth.
- `interfaces/` owns current API, CLI, registry, prompt-delivery, and YAML contracts.
- `operations/` owns current verification and operator workflows.

## Surface rule

Use this tree for shipped behavior only.

Do not use it as the target redesign contract, and do not use archive pages unless current and redesign owner pages are both silent.

## Evidence rule

Current pages must carry page-level `## Evidence` or `## Verification` sections unless they are pure routers.

Evidence may come from inspected code, inspected tests, or executed tests. `Last verified` alone is not enough for behavioral claims.

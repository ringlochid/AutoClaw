# Current implementation docs

Status: Current

Last verified: 2026-05-18

This tree owns shipped AutoClaw behavior only. Use it for code-aligned implementation truth, migration checks, and current operator guidance. It is not the redesign contract and does not compete with redesign canon.

Current route nouns such as `/runtime/*`, `/operator/*`, `/callback/*`, and `/observability/*` are shipped implementation truth only. They are not the redesign's canonical lane names.

## Canonical current owners

- [Current architecture](architecture/README.md)
- [Current interfaces](interfaces/README.md)
- [Current operations](operations/README.md)

## Search-first routing

If you are asking:

- "What routes exist today?" -> [API surface and route map](interfaces/api-surface-and-route-map.md)
- "What are the current trust lanes?" -> [API trust lanes](interfaces/api-trust-lanes.md)
- "What is the shipped prompt-delivery contract?" -> [Prompt layer and worker delivery](interfaces/prompt-layer-and-worker-delivery.md)
- "What happened to the old OpenClaw bridge strings?" -> [Current exact OpenClaw bridge prompt strings](interfaces/current-openclaw-bridge-prompt-strings.md)
- "What YAML contracts ship today?" -> [Definition and task-compose YAML contract](interfaces/definition-and-task-compose-yaml-contract.md)
- "How are current definitions compiled and launched?" -> [Definitions compiler and launch](interfaces/definitions-compiler-and-launch.md)
- "How do I run real minimal, normal, and maximal e2e workflow lanes?" -> [Run real e2e workflow lanes](operations/run-real-e2e-workflow-lanes.md)
- "Where does current definition truth live?" -> [Definition registry and publish lifecycle](interfaces/definition-registry-and-publish-lifecycle.md)
- "How does the current runtime control plane work?" -> [Runtime control plane](architecture/runtime-control-plane.md)
- "What runtime/operator read surfaces exist today?" -> [Current runtime read models and operator surfaces](architecture/runtime-read-models-and-operator-surfaces.md)
- "How does the current manifest projection work?" -> [Current workflow-manifest projection](architecture/manifest-projection-and-acknowledgement.md)
- "How are current task roots laid out?" -> [Task roots and materialized paths](architecture/task-roots-and-materialized-paths.md)
- "How do I run the stronger DB-backed verification lane?" -> [Run Docker Postgres verification](operations/run-docker-postgres-verification.md)

## Surface map

- `architecture/` owns current runtime, manifest, task-root, and read-model truth.
- `interfaces/` owns current API, prompt, registry, compiler, and YAML contracts.
- `operations/` owns current verification procedures.

## Surface rule

Use this tree for shipped behavior only.

Do not use it as the target redesign contract. When current and redesign differ about target behavior, redesign wins and current remains contrast-only. Do not treat older current pages that are not routed from the front doors above as reverified by this Phase 0 wave.

## Evidence rule

Current pages must carry page-level `## Evidence` or `## Verification` sections unless they are pure routers.

Evidence may come from inspected code, inspected tests, or executed tests. `Last verified` alone is not enough for behavioral claims.

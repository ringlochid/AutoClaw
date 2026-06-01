# Design interfaces

Status: Target

This folder owns the frozen external and adapter-facing contracts for:

- MCP surface boundaries and packaging/CLI terminology
- definition registry reads and guarded writes
- task start
- public operator runtime reads and flow control
- operator-safe and node-bound MCP tool surfaces
- CLI/package/install surfaces

`tool` is the canonical runtime term. `plugin` and `bundle` are packaging or parity-wrapper terminology only.

A retained secondary search router exists for legacy entry points. This `README.md` is the canonical interfaces front door.

## Start Here

Read in this order:

1. [mcp-plugin-and-cli-boundary.md](mcp-plugin-and-cli-boundary.md)
2. [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md)
3. [api-schema-appendix.md](api-schema-appendix.md)
4. [api-machine-catalog.yaml](api-machine-catalog.yaml)
5. [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md)
6. [role-and-policy-definition-schema.md](role-and-policy-definition-schema.md)
7. [plugin-tool-reference.md](plugin-tool-reference.md)

## Canonical Live Owners

- [mcp-plugin-and-cli-boundary.md](mcp-plugin-and-cli-boundary.md) the two-MCP model, plugin or bundle terminology limits, OpenClaw attachment boundary, the explicit-arg v1 node-MCP bridge, and CLI ownership split
- [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md) route families, trust lanes, and stale-write guards
- [api-schema-appendix.md](api-schema-appendix.md) named requests, responses, shared enums, and shared nested shapes
- [api-machine-catalog.yaml](api-machine-catalog.yaml) machine-readable route and MCP tool catalog, including exact caller-facing arguments and result carriers
- [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md) registry lifecycle, upload rules, and registry-read discovery for structural edits
- [role-and-policy-definition-schema.md](role-and-policy-definition-schema.md) authored role/policy shapes and validation rules
- [plugin-tool-reference.md](plugin-tool-reference.md) tool inventory split across `operator MCP` and `node MCP`

## Supporting Surfaces

- [human-and-operator-control-surface.md](human-and-operator-control-surface.md)
- [cli-surface-and-operator-workflows.md](cli-surface-and-operator-workflows.md)
- [cli-api-and-package-shape.md](cli-api-and-package-shape.md)
- [definition-ingest-and-upload-contract.md](definition-ingest-and-upload-contract.md)
- [release-and-install-strategy.md](release-and-install-strategy.md)
- [distribution-and-database-support-matrix.md](distribution-and-database-support-matrix.md)
- [testing-and-release-checklist.md](testing-and-release-checklist.md)

## Search-First Questions

- "Which routes are public and which are internal?" [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md)
- "Which MCP surfaces exist and how do plugin, bundle, and CLI terms split?" [mcp-plugin-and-cli-boundary.md](mcp-plugin-and-cli-boundary.md)
- "What are the exact request/response shapes?" [api-schema-appendix.md](api-schema-appendix.md)
- "What exact route arguments, tool arguments, filters, sorts, tool aliases, and result carriers may a model caller use?" [api-machine-catalog.yaml](api-machine-catalog.yaml)
- "How are roles and policies discovered and uploaded into current registry revisions?" [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md)
- "What tool inventory does each MCP surface expose?" [plugin-tool-reference.md](plugin-tool-reference.md)
- "What is the operator boundary?" [operator-definition-and-role-boundary.md](operator-definition-and-role-boundary.md)
- "What CLI/package/install behavior is in scope?" [cli-api-and-package-shape.md](cli-api-and-package-shape.md) and [release-and-install-strategy.md](release-and-install-strategy.md)
- "What does the root CLI actually expose day to day?" [cli-surface-and-operator-workflows.md](cli-surface-and-operator-workflows.md)

## Fast Route Examples

- "I want to understand how upload-triggered internal validation works for a workflow definition." Read [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md) first, then the exact request/response shape in [api-schema-appendix.md](api-schema-appendix.md).
- "I want to start a task from a local file." Read [definition-ingest-and-upload-contract.md](definition-ingest-and-upload-contract.md) for file-entry rules, then [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md) for `POST /tasks/start`.
- "I want to pause or continue a live flow." Read [human-and-operator-control-surface.md](human-and-operator-control-surface.md) for the authority boundary, then [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md) and [api-schema-appendix.md](api-schema-appendix.md).
- "I want the shortest root-command list before I read route details." Start with [cli-surface-and-operator-workflows.md](cli-surface-and-operator-workflows.md), then read [cli-api-and-package-shape.md](cli-api-and-package-shape.md) for the split between CLI, API, and adapter/package surfaces.
- "I want to know whether the external MCP surface may call `assign_child`." Read [mcp-plugin-and-cli-boundary.md](mcp-plugin-and-cli-boundary.md), [plugin-tool-reference.md](plugin-tool-reference.md), and [human-and-operator-control-surface.md](human-and-operator-control-surface.md). The answer is no: that is `node MCP`, not `operator MCP`; in v1 it uses explicit `session_key` + `task_id`.

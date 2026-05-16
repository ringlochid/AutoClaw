# Interfaces Index

Status: Owner index

Use this page when you know the question before you know the file.

## Canonical live owners

- [mcp-plugin-and-cli-boundary.md](mcp-plugin-and-cli-boundary.md)
- [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md)
- [api-schema-appendix.md](api-schema-appendix.md)
- [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md)
- [role-and-policy-definition-schema.md](role-and-policy-definition-schema.md)
- [plugin-tool-reference.md](plugin-tool-reference.md)

Compatibility rule: `tool` is the canonical runtime term. `plugin` and
`bundle` are packaging or parity-wrapper terms only.

## Routes, Lanes, And Guards

- "Which MCP surfaces exist and how do they relate to plugin, bundle, and CLI terms?" [mcp-plugin-and-cli-boundary.md](mcp-plugin-and-cli-boundary.md)
- "Which routes are public versus internal?" [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md)
- "Which stale-write guards are canonical?" [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md)
- "What are the exact route payloads?" [api-schema-appendix.md](api-schema-appendix.md)
- "What exact query params, sorts, and tool aliases may a model caller use?" [api-machine-catalog.yaml](api-machine-catalog.yaml)

## Definition Registry

- "How do definitions upload, validate internally, and become current revisions?" [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md)
- "What do role and policy definitions look like?" [role-and-policy-definition-schema.md](role-and-policy-definition-schema.md)
- "How do local files ingest into the registry or task start?" [definition-ingest-and-upload-contract.md](definition-ingest-and-upload-contract.md)

## Operator And Adapter Surfaces

- "What can a human/operator do?" [human-and-operator-control-surface.md](human-and-operator-control-surface.md)
- "What is the operator boundary?" [operator-definition-and-role-boundary.md](operator-definition-and-role-boundary.md)
- "What tool inventory does each MCP surface expose?" [plugin-tool-reference.md](plugin-tool-reference.md)

## Common Concrete Scenarios

- "I have a local workflow file and want to know the file-entry rules before upload." Use [definition-ingest-and-upload-contract.md](definition-ingest-and-upload-contract.md) for file-entry rules, then [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md) for upload and internal-validation lifecycle, and [api-schema-appendix.md](api-schema-appendix.md) for exact request and response shapes.
- "I have a running flow and want the current summary without touching node-level state." Use the operator lane described in [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md) and [human-and-operator-control-surface.md](human-and-operator-control-surface.md).
- "I need to know whether an automation client is allowed to use parent/root tools." Read [mcp-plugin-and-cli-boundary.md](mcp-plugin-and-cli-boundary.md), [plugin-tool-reference.md](plugin-tool-reference.md), and [operator-definition-and-role-boundary.md](operator-definition-and-role-boundary.md). Standard operator-safe automation is task-scoped only; session-bound parent/root tools belong to `node MCP`.
- "I need exact examples of compact surfaced refs or checkpoint/assignment payloads." Start with [api-schema-appendix.md](api-schema-appendix.md).

## CLI, Package, And Release

- "What does the CLI own?" [cli-surface-and-operator-workflows.md](cli-surface-and-operator-workflows.md)
- "How do CLI, API, and package boundaries split?" [cli-api-and-package-shape.md](cli-api-and-package-shape.md)
- "What is the install and release posture?" [release-and-install-strategy.md](release-and-install-strategy.md)
- "What is the frozen support matrix?" [distribution-and-database-support-matrix.md](distribution-and-database-support-matrix.md)
- "What release/testing evidence is required?" [testing-and-release-checklist.md](testing-and-release-checklist.md)

## Historical Search Terms

If you arrive searching for:

- callback-era worker surfaces
- `parent_gate`
- public child retry or reassignment control
- `scope_key`
- `instruction_text`
- plugin-first tool model
- shared mixed MCP catalog

start with:

- [mcp-plugin-and-cli-boundary.md](mcp-plugin-and-cli-boundary.md)
- [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md)
- [plugin-tool-reference.md](plugin-tool-reference.md)
- [role-and-policy-definition-schema.md](role-and-policy-definition-schema.md)

# Workflow node schema

Status: Target

This page defines the V2 portable authored schema for workflow-node fields.

## Core rule

Workflow nodes own portable authored execution intent.

They do not own:

- machine-local provider config
- host paths
- auth material
- adapter session ids
- transport details

Those stay in `config.toml`, runtime, or adapter-owned local state.

This page owns the portable node object even while the outer workflow-definition envelope may evolve.

## `WorkflowNodeInput`

V2 authored workflow nodes use a portable body such as:

```yaml
node_key: string
kind: root | parent | worker
title: string | optional
role_id: string
policy_id: string
provider_preference: openclaw | codex | claude | optional
description: string
instruction: string | optional
```

Field meaning:

- `node_key` is the stable logical node identity inside the workflow definition
- `kind` is the structural execution kind
- `title` is optional authored display metadata
- `role_id` points to the portable role definition the node should resolve at launch or adopt time
- `policy_id` points to the portable policy definition the node should resolve at launch or adopt time
- `provider_preference` is an optional portable logical preference for provider selection
- `description` is reusable node-purpose text and remains distinct from guidance layers
- `instruction` is optional node-local prompt guidance for how this node should execute its role

## Validation rules

Validation must enforce:

- `node_key`, `kind`, `role_id`, `policy_id`, and `description` are required
- `kind` accepts only `root`, `parent`, or `worker`
- `provider_preference`, when present, accepts only `openclaw`, `codex`, or `claude`
- `provider_preference` is optional and omission means runtime will resolve through the machine-local default provider
- `instruction`, when present, is non-empty prompt guidance authored on the node itself
- runtime and projection fields disambiguate this source as `node_instruction`, separate from `role_instruction`, `policy_instruction`, task instruction, and assignment instruction

## Separation rule

`provider_preference` is reusable authored intent only.

Rules:

- `provider_preference` belongs on workflow nodes, not role or policy definitions
- `provider_preference` is not a model string, socket path, auth ref, sandbox config, or transport block
- machine-local config decides how this host reaches `openclaw`, `codex`, or `claude`
- controller truth records requested and resolved provider provenance without turning local config into authored definition truth

## Non-goals

This page does not define:

- the full outer workflow-definition container shape
- machine-local provider setup
- provider fallback semantics
- provider-specific MCP tool names

## Related contracts

- [Role and policy definition schema](role-and-policy-definition-schema.md)
- [Provider preference and runtime config](provider-selection-and-runtime-config.md)
- [Provider-aware setup, configure, and doctor](provider-aware-setup-and-doctor.md)
- [Node and operator MCP surface contract](node-and-operator-mcp-surface-contract.md)

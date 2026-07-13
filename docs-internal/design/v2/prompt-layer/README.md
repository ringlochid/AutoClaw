# Prompt layer (v2)

Status: Target

This folder owns the V2 provider-neutral prompt package and worker operating policy.

## Core model

- controller truth renders one complete prompt per dispatch
- `instructions_text` and `input_text` remain separate persisted transport fields
- every worker rereads current context and maintains one `AttemptPlan`
- checkpoints remain narrow handoff and terminal evidence
- external waits end the current response without a workflow boundary
- parent/root orchestration remains unchanged
- provider configuration, events, and hidden conversation memory never become prompt truth

## Start here

1. [Prompt system v2](prompt-system-v2.md)
2. [Attempt plan and checkpoint contract](../architecture/attempt-plan-and-checkpoint-contract.md)
3. [Node and operator MCP surface](../interfaces/node-and-operator-mcp-surface-contract.md)
4. [V1 prompt-layer front door](../../v1/prompt-layer/README.md) for shipped baseline and migration contrast

## Ownership boundary

The prompt owner defines assembly, persistence, worker instructions, continuation context, and conformance requirements. Runtime owners define legality, plans, checkpoints, waits, files, and boundaries. Adapters translate the committed transport request without changing its semantic contract.

Exact current prompt assets remain shipped-behavior evidence until V2 implementation replaces them. V2 does not add separate prompt preview, diff, or regression products.

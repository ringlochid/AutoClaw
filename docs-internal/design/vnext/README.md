# Design docs (vnext)

Status: Target

This tree defines the future target design that succeeds `design/v1`.

Use it for future-design questions such as:

- how V2-era controller truth should work
- how human requests, long-running command runs, and realtime task event streams fit into the controller model
- how prompt upgrades extend the current prompt architecture
- how future adapters should map into AutoClaw without becoming truth owners
- how implementation work can split across worktrees and agents without redefining shared contracts

This tree is not shipped-behavior contrast and it is not an execution-program surface.

## Core direction

Vnext keeps these baseline rules from V1:

- controller-owned state remains the only runtime truth owner
- provider, adapter, prompt artifact, and support-file views stay downstream of controller truth
- control-plane access remains external and task-scoped
- portable authored definitions stay separate from machine-local provider config and auth or transport state
- prompt rendering remains a derived brief over controller-owned truth rather than a second truth lane

Vnext extends that baseline with:

- typed pending human requests instead of generic chat continuation
- controller-managed long-running command runs as explicit runtime boundaries
- replayable task event streams over persisted controller events
- optional node-level provider preference plus separate machine-local provider config
- the current prompt render-and-persist model preserved while prompt text stays provider-independent
- adapter mappings that are explicitly source-grounded and do not silently become controller truth
- a contract-first worktree split model for parallel feature implementation

## Start here

Read in this order:

1. [Controller contract and resumable execution](architecture/controller-contract-and-resumable-execution.md)
2. [Workflow node schema](interfaces/workflow-node-schema.md)
3. [Role and policy definition schema](interfaces/role-and-policy-definition-schema.md)
4. [Provider preference and runtime config](interfaces/provider-selection-and-runtime-config.md)
5. [Capability, security, and audit](interfaces/capability-security-and-audit.md)
6. [Human request and approval contract](interfaces/human-request-and-approval-contract.md)
7. [Command run and long-running boundary](architecture/command-run-and-long-running-boundary.md)
8. [Control API and task event stream](interfaces/control-api-and-task-event-stream.md)
9. [Control UI runtime and authoring surfaces](interfaces/control-ui-runtime-and-authoring-surfaces.md)
10. [Provider-aware setup, configure, and doctor](interfaces/provider-aware-setup-and-doctor.md)
11. [Provider support and compatibility](interfaces/provider-support-and-compatibility.md)
12. [Node and operator MCP surface contract](interfaces/node-and-operator-mcp-surface-contract.md)
13. [Definition authoring workbench](interfaces/definition-authoring-workbench.md)
14. [Definition authoring API and draft-set contract](interfaces/definition-authoring-api-and-draft-set-contract.md)
15. [Prompt system vnext](prompt-layer/prompt-system-vnext.md)
16. [Adapter contract](architecture/adapter-contract.md)
17. [Worktree and agent split contract](architecture/worktree-and-agent-split-contract.md)

## Search-first routing

If you are asking:

- "What stays authoritative when adapters, UI, prompts, and support files disagree?" -> [Controller contract and resumable execution](architecture/controller-contract-and-resumable-execution.md)
- "What portable fields belong on authored workflow nodes?" -> [Workflow node schema](interfaces/workflow-node-schema.md)
- "How should human direction, approval, input, or review requests work?" -> [Human request and approval contract](interfaces/human-request-and-approval-contract.md)
- "How should human-request and command-run capability allow/deny work, and where do capability readbacks live?" -> [Capability, security, and audit](interfaces/capability-security-and-audit.md) and [Prompt system vnext](prompt-layer/prompt-system-vnext.md)
- "How do long-running commands yield and later continue the same task from database state?" -> [Command run and long-running boundary](architecture/command-run-and-long-running-boundary.md)
- "How do normalized long-running command summaries differ from raw log files?" -> [Command run and long-running boundary](architecture/command-run-and-long-running-boundary.md)
- "How should the control UI stream, replay, and backfill task events?" -> [Control API and task event stream](interfaces/control-api-and-task-event-stream.md)
- "How should the runtime UI separate execution, requests, jobs, and authoring?" -> [Control UI runtime and authoring surfaces](interfaces/control-ui-runtime-and-authoring-surfaces.md)
- "How should definition drafts, validate/save/apply/import, optional task-compose preview, and stale protection work?" -> [Definition authoring API and draft-set contract](interfaces/definition-authoring-api-and-draft-set-contract.md) and [Definition authoring workbench](interfaces/definition-authoring-workbench.md)
- "How do node-level provider preference, default provider config, and fallback stay separate from portable definitions?" -> [Workflow node schema](interfaces/workflow-node-schema.md), [Provider preference and runtime config](interfaces/provider-selection-and-runtime-config.md), and [Role and policy definition schema](interfaces/role-and-policy-definition-schema.md)
- "How should onboard, configure, doctor, and `autoclaw openclaw|codex|claude` work once multiple providers exist?" -> [Provider-aware setup, configure, and doctor](interfaces/provider-aware-setup-and-doctor.md)
- "What exact support or compatibility rules should operators see for OpenClaw, Codex, or Claude?" -> [Provider support and compatibility](interfaces/provider-support-and-compatibility.md), [OpenClaw support and compatibility](interfaces/openclaw-support-and-compatibility.md), [Codex support and compatibility](interfaces/codex-support-and-compatibility.md), and [Claude support and compatibility](interfaces/claude-support-and-compatibility.md)
- "Do OpenClaw, Codex, and Claude need different `/node` or `/operator` MCP contracts?" -> [Node and operator MCP surface contract](interfaces/node-and-operator-mcp-surface-contract.md)
- "How does Vnext keep the current prompt layer while keeping provider choice out of prompt text?" -> [Prompt system vnext](prompt-layer/prompt-system-vnext.md)
- "How should Codex or Claude map into AutoClaw without redefining controller truth?" -> [Adapter contract](architecture/adapter-contract.md), [Codex app-server adapter](architecture/adapters/codex-app-server.md), and [Claude Agent SDK adapter](architecture/adapters/claude-agent-sdk.md)
- "How should implementation work be split across worktrees or agents?" -> [Worktree and agent split contract](architecture/worktree-and-agent-split-contract.md)

## Contrast routing

Use `design/v1` when you need the current target baseline that Vnext extends:

- [V1 design front door](../v1/README.md)
- [V1 runtime boundary and controller loop](../v1/architecture/runtime-boundary-and-controller-loop-contract.md)
- [V1 human and operator control surface](../v1/interfaces/human-and-operator-control-surface.md)
- [V1 prompt-layer front door](../v1/prompt-layer/README.md)
- [V1 OpenClaw worker and gateway contract](../v1/architecture/openclaw-worker-and-gateway-contract.md)

Those V1 pages remain the contrast baseline. Vnext pages own the future target where they exist.

## Scope note

This tree does not reopen platform-service support by default. If a future slice changes the target service contract for macOS or Windows, add that work explicitly. Otherwise treat platform parity as a current-versus-target implementation gap outside this tree.

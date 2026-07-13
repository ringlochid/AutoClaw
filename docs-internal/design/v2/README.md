# Design docs (v2)

Status: Target

This tree defines the V2 target design that succeeds `design/v1`.

Use it for V2 design questions such as:

- how MCP-backed controller mutations become the agent-runtime truth boundary
- how the local supervisor, one watchdog, and minimal provider control fit together
- how plans, checkpoints, human requests, command runs, and task events divide ownership
- how task-relative MCP reads replace provider-shaped runtime context assumptions
- how CLI and console surfaces expose controller truth without provider telemetry

This tree is not shipped-behavior contrast and it is not an execution-program surface.

## Core direction

V2 keeps these baseline rules from V1:

- controller-owned state remains the only runtime truth owner
- provider, adapter, prompt artifact, and support-file views stay downstream of controller truth
- control-plane access remains external and task-scoped
- portable authored definitions stay separate from machine-local provider config and auth or transport state
- prompt rendering remains a derived brief over controller-owned truth rather than a second truth lane

V2 extends that baseline with:

- one same-host `LocalRuntimeSupervisor` with centralized provider control and one watchdog
- semantic MCP-backed controller commits as the only agent progress signal
- attempt-owned worker plans plus checkpoints reserved for handoff and terminal evidence
- typed human requests and controller-managed command runs as external waits
- minimal `start` and `stop` provider adapters with opaque optional continuity hints
- task-relative MCP context, listing, and bounded text reads over a reduced task root
- replayable controller task events that remain chronology rather than current-state authority
- provider-neutral CLI and console readback for setup, retries, recovery, and waits

## Start here

Read in this order:

1. [Runtime lifecycle and watchdog](architecture/runtime-lifecycle-and-watchdog.md)
2. [Runtime records and control state](architecture/runtime-records-and-control-state.md)
3. [Attempt plan and checkpoint contract](architecture/attempt-plan-and-checkpoint-contract.md)
4. [Task root and file access](architecture/task-root-and-file-access.md)
5. [Controller contract and resumable execution](architecture/controller-contract-and-resumable-execution.md)
6. [Node and operator MCP surface contract](interfaces/node-and-operator-mcp-surface-contract.md)
7. [Node MCP schema appendix](interfaces/node-mcp-schema-appendix.md)
8. [Workflow node schema](interfaces/workflow-node-schema.md)
9. [Role and policy definition schema](interfaces/role-and-policy-definition-schema.md)
10. [Provider preference and runtime config](interfaces/provider-selection-and-runtime-config.md)
11. [Capability, security, and audit](interfaces/capability-security-and-audit.md)
12. [Human request and approval contract](interfaces/human-request-and-approval-contract.md)
13. [Command run and external wait](architecture/command-run-and-external-wait.md)
14. [Control API](interfaces/control-api.md)
15. [Task event stream](interfaces/task-event-stream.md)
16. [Console runtime surfaces](interfaces/console-runtime-surfaces.md)
17. [Provider CLI and doctor](interfaces/provider-cli-and-doctor.md)
18. [Provider support and compatibility](interfaces/provider-support-and-compatibility.md)
19. [Prompt layer](prompt-layer/README.md)
20. [Minimal provider adapter contract](architecture/adapter-contract.md)
21. [Definition authoring workbench](interfaces/definition-authoring-workbench.md)
22. [Definition authoring API and flat draft contract](interfaces/definition-authoring-api-and-flat-draft-contract.md)

## Search-first routing

If you are asking:

- "What stays authoritative when adapters, UI, prompts, and support files disagree?" -> [Controller contract and resumable execution](architecture/controller-contract-and-resumable-execution.md)
- "How does the local supervisor, one watchdog, and restart-before-escalation lane work?" -> [Runtime lifecycle and watchdog](architecture/runtime-lifecycle-and-watchdog.md)
- "Which runtime records survive the provider-neutral reset?" -> [Runtime records and control state](architecture/runtime-records-and-control-state.md)
- "How do worker plans differ from checkpoints?" -> [Attempt plan and checkpoint contract](architecture/attempt-plan-and-checkpoint-contract.md)
- "What task files can agents read through MCP?" -> [Task root and file access](architecture/task-root-and-file-access.md) and [Node MCP schema appendix](interfaces/node-mcp-schema-appendix.md)
- "What portable fields belong on authored workflow nodes?" -> [Workflow node schema](interfaces/workflow-node-schema.md)
- "How should human direction, approval, input, or review requests work?" -> [Human request and approval contract](interfaces/human-request-and-approval-contract.md)
- "How should human-request and command-run capability allow/deny work, and where do capability readbacks live?" -> [Capability, security, and audit](interfaces/capability-security-and-audit.md) and [Prompt system v2](prompt-layer/prompt-system-v2.md)
- "How do long-running commands yield and later continue the same task from database state?" -> [Command run and external wait](architecture/command-run-and-external-wait.md)
- "How do normalized long-running command summaries differ from raw log files?" -> [Command run and external wait](architecture/command-run-and-external-wait.md)
- "Which routes read and control current task state?" -> [Control API](interfaces/control-api.md)
- "How should the control UI stream, replay, and backfill task events?" -> [Task event stream](interfaces/task-event-stream.md)
- "How should the runtime UI present plans, provider control, recovery, and external waits?" -> [Console runtime surfaces](interfaces/console-runtime-surfaces.md) and [Console target](console/README.md)
- "How should definition drafts, validate/save/apply/import, optional task-compose preview, and stale protection work?" -> [Definition authoring API and flat draft contract](interfaces/definition-authoring-api-and-flat-draft-contract.md) and [Definition authoring workbench](interfaces/definition-authoring-workbench.md)
- "How do node-level provider preference, default provider config, and fallback stay separate from portable definitions?" -> [Workflow node schema](interfaces/workflow-node-schema.md), [Provider preference and runtime config](interfaces/provider-selection-and-runtime-config.md), and [Role and policy definition schema](interfaces/role-and-policy-definition-schema.md)
- "How should onboard, setup, login, status, and doctor work once multiple providers exist?" -> [Provider CLI and doctor](interfaces/provider-cli-and-doctor.md)
- "What exact support or compatibility rules should operators see for OpenClaw, Codex, or Claude?" -> [Provider support and compatibility](interfaces/provider-support-and-compatibility.md), [OpenClaw support and compatibility](interfaces/openclaw-support-and-compatibility.md), [Codex support and compatibility](interfaces/codex-support-and-compatibility.md), and [Claude support and compatibility](interfaces/claude-support-and-compatibility.md)
- "Do OpenClaw, Codex, and Claude need different `/node` or `/operator` MCP contracts?" -> [Node and operator MCP surface contract](interfaces/node-and-operator-mcp-surface-contract.md)
- "How does V2 keep the current prompt layer while keeping provider choice out of prompt text?" -> [Prompt system v2](prompt-layer/prompt-system-v2.md)
- "How should OpenClaw, Codex, or Claude map into AutoClaw without redefining controller truth?" -> [Minimal provider adapter contract](architecture/adapter-contract.md), [OpenClaw Gateway adapter](architecture/adapters/openclaw-gateway.md), [Codex app-server adapter](architecture/adapters/codex-app-server.md), and [Claude Agent SDK adapter](architecture/adapters/claude-agent-sdk.md)

## Contrast routing

Use `design/v1` when you need the current target baseline that V2 extends:

- [V1 design front door](../v1/README.md)
- [V1 runtime boundary and controller loop](../v1/architecture/runtime-boundary-and-controller-loop-contract.md)
- [V1 human and operator control surface](../v1/interfaces/human-and-operator-control-surface.md)
- [V1 prompt-layer front door](../v1/prompt-layer/README.md)
- [V1 OpenClaw worker and gateway contract](../v1/architecture/openclaw-worker-and-gateway-contract.md)

Those V1 pages remain the contrast baseline. V2 pages own the target contract where they exist.

## Scope note

This tree does not reopen platform-service support by default. If a future slice changes the target service contract for macOS or Windows, add that work explicitly. Otherwise treat platform parity as a current-versus-target implementation gap outside this tree.

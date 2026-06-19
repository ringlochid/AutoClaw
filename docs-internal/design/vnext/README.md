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
- portable authored definitions stay separate from machine-local deployment bindings
- prompt rendering remains a derived brief over controller-owned truth rather than a second truth lane

Vnext extends that baseline with:

- typed pending human requests instead of generic chat continuation
- controller-managed long-running command runs as explicit runtime boundaries
- replayable task event streams over persisted controller events
- richer portable role metadata plus separate deployment-binding maps
- prompt preview, diff, and regression surfaces as first-class design concerns
- adapter mappings that are explicitly source-grounded and do not silently become controller truth
- a contract-first worktree split model for parallel feature implementation

## Start here

Read in this order:

1. [Controller contract and resumable execution](architecture/controller-contract-and-resumable-execution.md)
2. [Capability, security, and audit](interfaces/capability-security-and-audit.md)
3. [Human request and approval contract](interfaces/human-request-and-approval-contract.md)
4. [Command run and long-running boundary](architecture/command-run-and-long-running-boundary.md)
5. [Control API and task event stream](interfaces/control-api-and-task-event-stream.md)
6. [Control UI runtime and authoring surfaces](interfaces/control-ui-runtime-and-authoring-surfaces.md)
7. [Role and policy definition schema](interfaces/role-and-policy-definition-schema.md)
8. [Deployment binding and runtime profile map](interfaces/deployment-binding-and-runtime-profile-map.md)
9. [Prompt system vnext](prompt-layer/prompt-system-vnext.md)
10. [Adapter contract](architecture/adapter-contract.md)
11. [Worktree and agent split contract](architecture/worktree-and-agent-split-contract.md)

## Search-first routing

If you are asking:

- "What stays authoritative when adapters, UI, prompts, and support files disagree?" -> [Controller contract and resumable execution](architecture/controller-contract-and-resumable-execution.md)
- "How should human direction, approval, input, or review requests work?" -> [Human request and approval contract](interfaces/human-request-and-approval-contract.md)
- "How should dispatch prompts make capability allow/deny explicit, and where do capability readbacks live?" -> [Capability, security, and audit](interfaces/capability-security-and-audit.md) and [Prompt system vnext](prompt-layer/prompt-system-vnext.md)
- "How do long-running commands yield and later continue the same task from database state?" -> [Command run and long-running boundary](architecture/command-run-and-long-running-boundary.md)
- "How do normalized long-running command summaries differ from raw log files?" -> [Command run and long-running boundary](architecture/command-run-and-long-running-boundary.md)
- "How should the control UI stream, replay, and backfill task events?" -> [Control API and task event stream](interfaces/control-api-and-task-event-stream.md)
- "How should the runtime UI separate execution, requests, jobs, and authoring?" -> [Control UI runtime and authoring surfaces](interfaces/control-ui-runtime-and-authoring-surfaces.md)
- "How do portable definitions stay separate from host paths and runtime profiles?" -> [Role and policy definition schema](interfaces/role-and-policy-definition-schema.md) and [Deployment binding and runtime profile map](interfaces/deployment-binding-and-runtime-profile-map.md)
- "How do prompt preview, diff, and regression extend the current prompt layer?" -> [Prompt system vnext](prompt-layer/prompt-system-vnext.md) and [Prompt regression suite](prompt-layer/prompt-regression-suite.md)
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

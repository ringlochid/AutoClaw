# Design docs (vnext)

Status: Target

This tree defines the future target design that succeeds `design/v1`.

Use it for future-design questions such as:

- how V2-era controller truth should work
- how human requests, async jobs, and realtime operator streams fit into the controller model
- how prompt upgrades extend the current prompt architecture
- how future adapters should map into AutoClaw without becoming truth owners

This tree is not shipped-behavior contrast and it is not an execution-program surface.

## Core direction

Vnext keeps these baseline rules from V1:

- controller-owned state remains the only runtime truth owner
- provider, adapter, prompt artifact, and support-file views stay downstream of controller truth
- operator-facing control remains external and task-scoped
- portable authored definitions stay separate from machine-local deployment bindings
- prompt rendering remains a derived brief over controller-owned truth rather than a second truth lane

Vnext extends that baseline with:

- typed pending human requests instead of generic chat continuation
- controller-managed async jobs as resumable runtime boundaries
- replayable operator event streams over persisted controller events
- richer portable role metadata plus separate deployment-binding maps
- prompt preview, diff, and regression surfaces as first-class design concerns
- adapter mappings that are explicitly source-grounded and do not silently become controller truth

## Start here

Read in this order:

1. [Controller contract and resumable execution](architecture/controller-contract-and-resumable-execution.md)
2. [Capability, security, and audit](interfaces/capability-security-and-audit.md)
3. [Human request and approval contract](interfaces/human-request-and-approval-contract.md)
4. [Async job and long-running boundary](architecture/async-job-and-long-running-boundary.md)
5. [Operator UI API and event stream](interfaces/operator-ui-api-and-event-stream.md)
6. [Role and policy definition schema](interfaces/role-and-policy-definition-schema.md)
7. [Deployment binding and runtime profile map](interfaces/deployment-binding-and-runtime-profile-map.md)
8. [Prompt system vnext](prompt-layer/prompt-system-vnext.md)
9. [Adapter contract](architecture/adapter-contract.md)

## Search-first routing

If you are asking:

- "What stays authoritative when adapters, UI, prompts, and support files disagree?" -> [Controller contract and resumable execution](architecture/controller-contract-and-resumable-execution.md)
- "How should human approval or typed operator input work?" -> [Human request and approval contract](interfaces/human-request-and-approval-contract.md)
- "How do long-running commands or jobs yield and wake the same task?" -> [Async job and long-running boundary](architecture/async-job-and-long-running-boundary.md)
- "How should the operator UI stream, replay, and backfill events?" -> [Operator UI API and event stream](interfaces/operator-ui-api-and-event-stream.md)
- "How do portable definitions stay separate from host paths and runtime profiles?" -> [Role and policy definition schema](interfaces/role-and-policy-definition-schema.md) and [Deployment binding and runtime profile map](interfaces/deployment-binding-and-runtime-profile-map.md)
- "How do prompt preview, diff, and regression extend the current prompt layer?" -> [Prompt system vnext](prompt-layer/prompt-system-vnext.md) and [Prompt regression suite](prompt-layer/prompt-regression-suite.md)
- "How should Codex or Claude map into AutoClaw without redefining controller truth?" -> [Adapter contract](architecture/adapter-contract.md), [Codex app-server adapter](architecture/adapters/codex-app-server.md), and [Claude Agent SDK adapter](architecture/adapters/claude-agent-sdk.md)

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

# Minimal provider adapter contract

Status: Target

This page defines the complete provider-facing control contract for the local V2 runtime.

## Core rule

MCP is the agent/runtime protocol. A provider adapter only starts and stops one provider turn and optionally preserves provider conversation continuity.

Provider output, lifecycle events, tool events, completion notifications, and connection state are never controller correctness signals. The controller learns useful progress, external waits, and completion only from committed AutoClaw MCP operations.

## Required interface

The required public interface is:

```python
async def start(
    prompt: PromptTransportRequest,
    session_hint: str | None = None,
) -> str | None:
    ...


async def stop(session_hint: str | None = None) -> None:
    ...
```

`PromptTransportRequest` preserves two distinct prompt lanes:

```python
@dataclass(frozen=True)
class PromptTransportRequest:
    instructions_text: str
    input_text: str
```

Adapters must preserve the split when the provider supports separate instruction and input lanes. A provider with only one message lane may flatten the two values into the canonical combined rendering.

The adapter is constructed with provider and dispatch launch state that does not belong in the two verbs:

- task workspace
- AutoClaw Node MCP URL and provider-native MCP attachment
- sandbox, permission, and non-interactive approval policy
- sparse AutoClaw provider overrides
- provider-native runtime and connection configuration

## Start semantics

`start()` means that the provider turn has been handed off and that its effective optional continuity hint is known. It does not mean that the agent has made progress or completed.

Rules:

- AutoClaw creates the dispatch and live `NodeSession` before calling `start()`.
- The adapter always sends both current prompt lanes, including when it resumes a provider conversation.
- The returned value is the effective provider session hint. AutoClaw replaces the stored hint when the adapter falls back to a fresh provider session.
- A provider without reusable conversation continuity returns `None`.
- The first committed semantic Node MCP operation, normally `update_plan`, proves useful agent progress.
- A launch acknowledgement, provider stream item, or provider terminal notification proves none of those facts.

If a provider cannot reliably refresh instructions while resuming, the adapter starts a fresh provider session with the full current prompt and returns the replacement hint. Controller context and checkpoint rereading keep correctness independent of provider memory.

## Stop semantics

`stop()` ends the current provider turn associated with the adapter's private active handle and optional continuity hint.

A successful return is the watchdog replacement boundary: the adapter-owned active execution can no longer continue the stopped turn. The adapter must wait for its provider-specific interrupt or abort acknowledgement and perform any private cleanup required to uphold that result. If the adapter can only request interruption but cannot establish that boundary within the operation timeout, it raises a control failure; the `AgentControlManager` retries it and eventually pauses recovery instead of launching a replacement beside an uncertain old turn.

The `AgentControlManager` is the only caller. It centralizes duplicate-call coalescing, retry, timeout, visibility, and cleanup so watchdog recovery, explicit cancellation, and lifespan shutdown do not grow separate stop paths.

Normal return boundaries and external waits do not call `stop()`:

- after a return boundary, the provider response ends naturally
- after opening a human request or command run, the provider response ends naturally while the controller-owned lineage waits
- watchdog recovery and explicit cancellation use the centralized stop path

This guarantee is intentionally limited to the adapter-owned execution being stopped. It does not introduce a generalized workspace, container, external-effect, or distributed fencing model.

## Identity separation

The runtime keeps these identities distinct:

| Identity | Owner | Meaning |
| --- | --- | --- |
| `NodeSession.session_key` | AutoClaw | Existing task and node recognition on Node MCP calls |
| provider session hint | Adapter/provider | Optional conversation continuity only |
| private active handle | Adapter/manager | Provider-specific process, run, turn, client, or connection needed to stop the active turn |

OpenClaw session keys, Codex thread ids, and Claude session ids may be persisted as the optional provider session hint. Provider run ids, Codex turn ids, live SDK clients, child processes, and connections remain private control details. None of them authorizes Node MCP access or replaces controller lineage.

## Private provider behavior

An adapter may privately:

- drain a provider SDK or subprocess stream so the provider can continue running
- retain an active SDK client, turn handle, child process, or connection needed by `stop()`
- reconnect to a provider control plane
- inspect provider-native messages for transport housekeeping or to obtain a session hint
- record bounded support diagnostics

It must not translate provider lifecycle, built-in tool, token, or completion events into watchdog progress, controller completion, or assignment success.

## Interactive wait rule

AutoClaw MCP is the only interactive wait lane. Adapters configure provider-native approval and question mechanisms to allow, deny, or fail according to machine policy without waiting for provider UI input. Prompts direct agents to use AutoClaw human-request and command-run tools when controller-owned external waiting is required.

An adapter must expose Node MCP to managed agents. It must never expose Operator MCP as part of worker launch readiness.

## Retry ownership

The lifespan-owned `AgentControlManager` applies the shared provider-operation policy to both verbs:

- six total calls by default
- waits of 1, 2, 4, 8, and 16 seconds between calls
- one bounded operation timeout per call, 15 seconds by default
- transient connection and availability failures are retryable
- authentication, configuration, and invalid-request failures fail immediately
- delayed retries return to the central queue rather than blocking another control command

Connection establishment and the requested provider operation share this one budget; an adapter must not nest another six-call connection loop inside each manager call. One dispatch stays on one resolved provider. The six-call budget never switches provider. Provider fallback is resolved before the dispatch is committed.

## Provider-page evidence rule

Every provider adapter page uses these sections in order:

1. `Confirmed external behavior`
2. `AutoClaw mapping`
3. `Open assumptions and non-goals`

Only primary-source-confirmed provider behavior belongs in the first section. AutoClaw translation belongs in the second. Uncertainty and deliberately deferred behavior belong in the third.

## Conformance requirements

Every adapter must pass the same controller-level cases:

- fresh start returns the effective optional session hint
- resumed start resends current instructions and input
- failed continuity falls back to a fresh session and returns a replacement hint
- Node MCP can read current context and commit plan, progress, wait, and boundary operations
- no provider event or terminal signal advances watchdog progress or closes a dispatch
- provider-native questions and approvals cannot create invisible waits
- repeated start or stop requests are centralized by `AgentControlManager`
- stop interrupts the active provider turn without making provider completion controller truth

Provider-specific pages add only the transport cases required by that provider.

## Related pages

- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [Runtime lifecycle and watchdog](runtime-lifecycle-and-watchdog.md)
- [Node and operator MCP surface contract](../interfaces/node-and-operator-mcp-surface-contract.md)
- [Provider selection and runtime config](../interfaces/provider-selection-and-runtime-config.md)
- [Codex app-server adapter](adapters/codex-app-server.md)
- [Claude Agent SDK adapter](adapters/claude-agent-sdk.md)
- [OpenClaw Gateway adapter](adapters/openclaw-gateway.md)

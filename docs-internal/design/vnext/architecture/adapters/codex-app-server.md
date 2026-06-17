# Codex app-server adapter

Status: Target

This page defines the Vnext target mapping for Codex app-server.

## Confirmed External Behavior

The confirmed external behavior for Codex app-server is:

- Codex app-server supports bidirectional JSON-RPC 2.0-style messaging, with `stdio`, Unix socket, and an experimental unsupported WebSocket transport: [Codex app-server protocol](https://developers.openai.com/codex/app-server)
- thread and turn are first-class server concepts. The server exposes operations such as `thread/start`, `thread/resume`, `thread/fork`, and emits notifications such as `thread/started`, `turn/started`, `turn/completed`, and `turn/diff/updated`: [Codex app-server message schema and events](https://developers.openai.com/codex/app-server)
- app-server includes approval flows for command execution and file changes, with explicit request and resolution messages in the event stream: [Codex app-server approvals](https://developers.openai.com/codex/app-server)
- Codex documentation describes app-server as the local JSON-RPC server used to embed Codex threads, turns, approvals, history, and streamed events in custom clients: [Codex glossary](https://developers.openai.com/codex/glossary)
- published SDK guidance says the Python SDK controls the local app-server over JSON-RPC: [Codex SDK](https://developers.openai.com/codex/sdk)

## AutoClaw Mapping

AutoClaw maps Codex app-server into the controller model as follows:

- one AutoClaw task lineage maps to one long-lived app-server thread
- one AutoClaw dispatch or explicit controller wake maps to one app-server turn inside that thread
- app-server notifications are normalized into controller-owned operator event records before they affect UI replay or audit
- app-server approval requests become AutoClaw typed pending human requests when a human decision is required; the approval prompt itself is not controller truth until the controller persists the pending request
- app-server file diffs, review outputs, or conversation history remain secondary read surfaces unless a later controller contract explicitly promotes a normalized derivative into controller truth
- local integration should prefer `stdio` or Unix socket transports; the experimental unsupported WebSocket transport must not become the assumed production transport in the target design

## Open Assumptions / Non-goals

- This page does not claim that every app-server notification family should become a first-class AutoClaw event family.
- This page does not make detached review threads or Codex-specific thread branching into controller-core truth.
- Exact launch-time transport choice, local auth packaging, and long-history retention policy remain implementation-slice decisions beneath this mapping.

## Related contracts

- [Adapter contract](../adapter-contract.md)
- [Controller contract and resumable execution](../controller-contract-and-resumable-execution.md)
- [Operator UI API and event stream](../../interfaces/operator-ui-api-and-event-stream.md)

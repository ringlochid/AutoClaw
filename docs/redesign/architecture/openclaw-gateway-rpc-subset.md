# OpenClaw Gateway RPC Subset

Status: Target

## Purpose

This page freezes the exact OpenClaw Gateway WebSocket RPC subset that AutoClaw
depends on in Phase 4A.

Use it to prevent two kinds of drift:

- implementers guessing Gateway request or response shapes from prose
- adapter code silently following upstream OpenClaw changes without a pinned
  schema snapshot and compatibility check

## Core Rule

AutoClaw v1 does not integrate against the whole OpenClaw Gateway surface.

It integrates against one pinned subset:

- handshake: `connect.challenge`, `connect`, `hello-ok`
- machine control: `agent`, `agent.wait`, `sessions.abort`
- the exact lifecycle and stream events needed to normalize provider delivery into controller-owned observability truth

Everything else is out of scope unless canon is patched first.

## Upstream Truth And Version Pin

- OpenClaw TypeBox schema and generated protocol artifacts are upstream truth.
- AutoClaw must not hand-maintain guessed JSON payloads as the primary adapter contract.
- AutoClaw v1 targets the OpenClaw `2026.5.x` release family and currently pins the subset through the typed local protocol models under `app/runtime/openclaw/` plus live compatibility proof against the installed `2026.5.12` gateway on this host.
- The exact `PROTOCOL_VERSION` integer must come from that pinned `2026.5.x` contract, not from prose examples copied from docs pages.
- If a vendored upstream snapshot lands later, update this page, the golden fixtures, and the compatibility tests in the same slice.

`hello-ok.features.methods` is feature discovery only. It is not schema truth.
`hello-ok.pluginSurfaceUrls` is an optional protocol-v4 transport field. The
AutoClaw adapter must accept it without promoting hosted plugin-surface URLs
into controller truth.

Configurable transport/runtime knobs are a different category:

- endpoint, auth, and request-timeout knobs live under `[openclaw]`
  in the canonical local `config.toml`
- drain, watchdog, and recovery cadence knobs live under `[runtime]`
- protocol version, required methods, required scopes, and required payload
  fields are canon and compatibility truth, not user-configurable settings

See [Install and onboard](../how-to/install-and-onboard.md) for the canonical
config owner page.

## Required Handshake Subset

### `connect.challenge`

AutoClaw must accept the pre-connect event:

```json
{
    "type": "event",
    "event": "connect.challenge",
    "payload": {
        "nonce": "...",
        "ts": 1737264000000
    }
}
```

Required consumed fields:

- `type`
- `event`
- `payload.nonce`
- `payload.ts`

### `connect`

AutoClaw must send one `connect` request as the first client frame:

```json
{
    "type": "req",
    "id": "...",
    "method": "connect",
    "params": {
        "minProtocol": 4,
        "maxProtocol": 4,
        "client": {
            "id": "gateway-client",
            "version": "...",
            "platform": "...",
            "mode": "backend"
        },
        "role": "operator",
        "scopes": ["operator.read", "operator.write"],
        "caps": [],
        "commands": [],
        "permissions": {},
        "auth": { "token": "..." },
        "locale": "en-US",
        "userAgent": "autoclaw-openclaw-backend/..."
    }
}
```

Required request rules:

- `minProtocol` and `maxProtocol` are both the vendored `PROTOCOL_VERSION`
- direct trusted-loopback Gateway handshakes use
  `client.id="gateway-client"` and `client.mode="backend"`
- `role` is `operator`
- minimum required scopes are `operator.read` and `operator.write`
- any broader scope request must be explicit and bounded by later canon
- `caps`, `commands`, and `permissions` stay empty for the AutoClaw Gateway
  adapter path
- auth material stays transport-private and never becomes prompt-visible worker
  context
- omit `device` entirely on the trusted-loopback backend path
- any non-loopback or CLI/device-auth path requires full signed device identity
  and is not a Phase 4A AutoClaw feature

### `hello-ok`

AutoClaw must accept only a successful `hello-ok` response:

```json
{
    "type": "res",
    "id": "...",
    "ok": true,
    "payload": {
        "type": "hello-ok",
        "protocol": 4,
        "server": {
            "version": "2026.5.12",
            "connId": "conn-123"
        },
        "snapshot": {},
        "pluginSurfaceUrls": {
            "canvas": "https://plugins.example.test/canvas"
        },
        "policy": {
            "tickIntervalMs": 15000,
            "maxPayload": 1048576,
            "maxBufferedBytes": 1048576
        },
        "auth": {
            "role": "operator",
            "scopes": ["operator.read", "operator.write"],
            "issuedAtMs": 1737264000000
        },
        "features": {
            "methods": ["agent", "agent.wait", "sessions.abort"],
            "events": ["agent", "response.delta", "response.completed"]
        }
    }
}
```

Required consumed fields:

- `type`
- `id`
- `ok`
- `payload.type`
- `payload.protocol`
- `payload.server.version`
- `payload.server.connId`
- `payload.snapshot`
- `payload.policy.tickIntervalMs`
- `payload.policy.maxPayload`
- `payload.policy.maxBufferedBytes`
- `payload.auth.role`
- `payload.auth.scopes`
- `payload.auth.issuedAtMs` when OpenClaw returns auth timing detail
- `payload.auth.deviceToken` when the adapter persists reconnectable device auth
- `payload.pluginSurfaceUrls` when OpenClaw advertises hosted plugin surfaces;
  accept the map and ignore unconsumed surfaces
- `payload.features.methods` only as a presence check for required methods
- `payload.features.events` only as a presence check for the required event family and any extra observed event names the adapter may later normalize; this field is discovery-only rather than a frozen raw run-stream contract

Protocol-v4 note:

- `pluginSurfaceUrls.canvas` replaces the deprecated `canvasHostUrl` alias in
  the live `2026.5.x` contract; the old alias is not part of the pinned
  subset

AutoClaw must fail closed when:

- `ok` is false
- `payload.type` is not `hello-ok`
- `payload.protocol` does not match the vendored `PROTOCOL_VERSION`
- returned role/scopes cannot legally support `agent`, `agent.wait`, and
  `sessions.abort`
- required methods are missing from discovered features when the server
  advertises them

Reconnect and auth rules:

- persist the primary `hello-ok.auth.deviceToken` after every successful
  connect when OpenClaw issues one
- the configured `[openclaw].gateway_token` remains the first shared-token
  source for trusted-loopback backend connects
- when reconnecting with a stored device token, reuse the stored approved scope
  set for that token instead of silently narrowing scope
- treat extra `hello-ok.auth.deviceTokens` entries as bounded bootstrap
  handoff tokens only
- persist bootstrap handoff tokens only when the connect used a trusted
  transport such as loopback or `wss://`
- on `AUTH_TOKEN_MISMATCH`, allow at most one bounded automatic retry path:
  direct loopback backend connects retry once with the locally resolved
  OpenClaw gateway token when it differs from the configured token; otherwise,
  a second attempt is allowed only when the first attempt used a configured
  shared token and a cached per-device token is available
- the local loopback token-resolution order is:
  `OPENCLAW_GATEWAY_TOKEN`, then `OPENCLAW_CONFIG_PATH`, then
  `~/.openclaw/openclaw.json` at `gateway.auth.token`
- if that retry fails, stop automatic reconnect loops and surface operator
  action guidance

## Required Machine-Control Subset

### `agent`

AutoClaw uses `agent` to start one Gateway run for one controller dispatch.

Runtime ownership rule:

- the actual OpenClaw dispatch call belongs to the runtime-owned adapter
  surfaces under `apps/api/app/runtime/*`
- CLI, package, setup, and wrapper surfaces may configure or verify this
  adapter path, but they do not own live `agent` dispatch semantics

Required request behavior:

- use the controller-selected agent-scoped `sessionKey` as the canonical session selector
- send one root `message` string plus `idempotencyKey`; do not send the older split root fields `account`, `instructions`, `input`, `meta`, or `previousResponseId`
- the shipped Phase 4A adapter collapses the regenerated prompt package into that one `message` string for the live Gateway path
- keep any delivery, provider, or model-tuning extensions adapter-private
- send a deterministic idempotency key when the upstream schema requires one
- side-effecting requests must supply the vendored upstream idempotency-key
  shape; do not invent an adapter-local substitute
- keep strict delivery behavior by default; do not enable best-effort delivery
  fallback unless canon explicitly reopens it

Required consumed response fields:

- `runId`
- `status`
- `acceptedAt`

AutoClaw must not infer assignment success from `agent` acceptance.

### `agent.wait`

AutoClaw uses `agent.wait` only as terminal confirmation for one live `runId`.

Required consumed response shape:

```json
{
    "runId": "...",
    "status": "ok|error|timeout",
    "startedAt": "...",
    "endedAt": "...",
    "error": {}
}
```

Rules:

- `runId` is the canonical wait correlation key
- adapter compatibility must accept current terminal metadata such as string `error`, `stopReason`, `livenessState`, `aborted`, and `yielded` without treating them as a transport-schema failure
- some live timeout responses may omit `startedAt` / `endedAt`; the adapter must still treat `status=timeout` as an ambiguous transport outcome
- only bare `status=timeout` with no terminal metadata is the live ambiguous wait outcome
- `status=timeout` with terminal metadata such as `endedAt`, `error`, `stopReason`, `livenessState`, `aborted`, or `yielded` is a terminal provider outcome that must reconcile as terminal failure rather than `transport_timeout`
- `status=timeout` is transport uncertainty, not assignment outcome
- `error` is support-only transport detail unless canon explicitly promotes it

### `sessions.abort`

AutoClaw uses `sessions.abort` as the canonical machine abort surface.

Required request rules:

- canonical AutoClaw call path sends `key=sessionKey` and `runId` when the
  current `runId` is known
- `runId`-only resolution is compatibility behavior, not the canonical
  AutoClaw adapter contract

Required consumed behavior:

- abort acceptance does not by itself prove the old run is terminal
- terminal confirmation still comes from `agent.wait` and/or the exact
  lifecycle event family this page freezes

## Required Event Subset

AutoClaw pins the upstream Gateway event envelope and one required event family. It does not freeze a guessed upstream raw run-event vocabulary here.

Pinned upstream truth:

- `connect.challenge` during handshake
- the generic Gateway event envelope `{type:"event", event, payload, seq?, stateVersion?}`
- presence of the `agent` event family in `hello-ok.features.events` when the server advertises event discovery

AutoClaw-owned normalization may consume additional observed raw event names only when they correlate to the active dispatch/run and can be mapped into controller-owned observability truth. Extra event names advertised by Gateway are discovery-only until that normalization contract accepts them.

Transport-policy rules:

- validate and record `hello-ok.policy.tickIntervalMs` rather than keeping a stale local heartbeat default after the handshake succeeds
- enforce `hello-ok.policy.maxPayload` and `hello-ok.policy.maxBufferedBytes` rather than stale local buffer or payload defaults after handshake
- treat payload or buffered-output violations as transport compatibility or delivery failures, not as assignment meaning
- normalize accepted raw progress and terminal signals into controller-owned observability enums rather than persisting raw OpenClaw event names as controller truth

### AutoClaw Event Consumption Table

| Raw material | Consumed by AutoClaw | Required meaning when consumed | Normalized output | Liveness relevance | Dedupe / correlation rule |
| --- | --- | --- | --- | --- | --- |
| `connect.challenge` event | yes | pre-connect handshake challenge | none | none | not part of run liveness |
| `hello-ok.features.events` entry `agent` | yes | required event-family presence check | none | none | discovery-only handshake check |
| Generic event envelope `type,event,payload,seq?,stateVersion?` | yes | raw carrier only; not semantic truth by itself | none directly | none directly | envelope is accepted before event-specific normalization |
| Raw event correlated to the active dispatch/run and showing first meaningful provider data | yes | provider stream proved initial live progress | `first_data` | yes | dedupe by `seq` when present; otherwise use bounded fallback heuristics and require dispatch/run correlation before accepting it |
| Raw event correlated to the active dispatch/run and showing subsequent provider output progress | yes | provider stream advanced after first meaningful data | `output_delta` | yes | same dedupe and correlation rule as above |
| Raw event correlated to the active dispatch/run and showing tool-side provider activity | yes | provider-side tool activity occurred on the active dispatch/run | `tool_event` | optional hint only | same dedupe and correlation rule as above |
| Raw event correlated to the active dispatch/run and showing provider terminal success | yes | provider transport ended normally for that run | `response_completed` | yes, terminal | same dedupe and correlation rule as above |
| Raw event correlated to the active dispatch/run and showing provider terminal failure | yes | provider transport ended with provider-reported failure for that run | `response_failed` | yes, terminal | same dedupe and correlation rule as above |
| Unrelated buffered event such as `presence`, `tick`, or other uncorrelated broadcast traffic | no for liveness | observability noise outside the active dispatch/run | none | none | ignore for liveness and do not let it update progress anchors |

## Trusted Execution Context Rule

One current controller dispatch maps to one trusted OpenClaw execution context:

- `task_id`
- `assignment_key`
- `attempt_id`
- `dispatch_id`
- `sessionKey`
- current live `runId`

Rules:

- `sessionKey` is the primary private binding key for `node MCP`
- `runId` is the live-run correlation key for `agent.wait` and
  `sessions.abort`
- `runId` is not the canonical callback authority identity
- callback authority comes from trusted session context resolved server-side,
  not prompt-visible tokens, env files, or caller-supplied dispatch ids
- canonical parent/root same-attempt redispatch keeps the same `sessionKey`,
  sends a fresh `idempotencyKey`, and accepts a fresh returned `runId`
- worker retry, new attempt, and fresh child assignment use a fresh
  `sessionKey`, a fresh `idempotencyKey`, and a fresh returned `runId`
- any retained `same_session_continue` transport detail is adapter-private only
  and must not replace the full-resend Gateway `agent` request contract

## Compatibility And Failure Rules

At adapter startup and reconnect time, AutoClaw must validate:

- negotiated protocol version
- returned role and scopes
- presence of `agent`, `agent.wait`, and `sessions.abort`
- presence of required event families
- policy limits the adapter must obey, including payload and buffering limits

Failure classes must stay explicit:

- protocol mismatch -> fail closed, compatibility error
- missing required method or event -> fail closed, compatibility error
- missing auth or scope in `hello-ok` -> fail closed, compatibility error
- payload or buffer policy violation -> fail closed, transport compatibility or
  delivery error
- `agent` acceptance without boundary truth -> transport success only
- `agent.wait timeout` -> ambiguous transport outcome, not assignment success

## Required Proof Artifacts

Phase 4 implementation must land all of these:

- one vendored OpenClaw protocol snapshot for the pinned upstream target
- typed adapter models derived from that snapshot
- golden fixtures for:
    - `connect.challenge`
    - `connect`
    - `hello-ok`
    - `agent` accepted response
    - `agent.wait` success, error, and timeout responses
    - `sessions.abort` request and confirmation path
    - normalized stream-event examples
- startup compatibility checks
- reconnect/auth-drift handling for persisted device tokens and one bounded token-mismatch retry
- a live compatibility lane against a real OpenClaw Gateway

Config writes or bootstrap config presence are not sufficient proof.

## Related Contracts

- [OpenClaw worker and gateway contract](openclaw-worker-and-gateway-contract.md)
- [OpenClaw session lifecycle](openclaw-session-lifecycle.md)
- [OpenClaw continuity and send modes](openclaw-continuity-and-send-modes.md)
- [Provider, worker, and operator boundary](provider-worker-and-operator-boundary.md)
- [Install and onboard](../how-to/install-and-onboard.md)
- [MCP, plugin, and CLI boundary](../interfaces/mcp-plugin-and-cli-boundary.md)

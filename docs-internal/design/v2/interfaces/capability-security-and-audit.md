# Capability, security, and audit

Status: Target

This page owns V2 managed-agent capability decisions, noninteractive provider policy, trust-surface separation, and controller audit provenance.

## Core rule

Controller-owned capability decides which special semantic node actions are legal. Provider permissions may narrow execution locally, but provider UI, events, or configuration never widen controller authority or become audit truth.

## Trust surfaces

AutoClaw exposes two distinct MCP trust surfaces:

- Node MCP is attached to managed worker, parent, and root executions. Its existing `task_id` plus `session_key` recognition resolves current node, dispatch, assignment, and attempt authority.
- Operator MCP is an external inspection and control surface. It uses operator authentication and task authorization and is never attached to a managed execution.

Managed agents require Node MCP only. Operator MCP availability is not provider readiness and operator credentials never appear in a managed-agent prompt or adapter configuration.

## Effective capability set

The controller computes one stable effective capability set before committing a dispatch:

```yaml
effective_capability_set:
    dispatch_id: string
    human_request:
        direction: allow | deny
        approval: allow | deny
        input: allow | deny
        review: allow | deny
    command_run: allow | deny
```

The decision may derive from:

- current role and policy definitions
- current task and workflow policy
- the dispatch's fixed `resolved_provider`
- local runtime configuration and adapter constraints

Rules:

- omitted capabilities and omitted human-request kinds resolve to `deny`
- provider fallback finishes before dispatch commit; one dispatch keeps one capability decision and one resolved provider
- a later dispatch recomputes from current controller truth
- adapter permission systems may enforce a stricter local result but may not silently allow a controller-denied action
- ordinary Node MCP access is a launch-readiness requirement, not an optional capability family
- pause, continue, cancel, human-request resolution, and command-run cancellation are operator controls authorized separately from node capability

The exact task tree has no `_runtime/.../capabilities.json` or `capabilities.md`. `get_current_context` returns effective capabilities and currently allowed actions from controller state. Prompt text and task files are not capability authority.

## Capability enforcement

The minimum node capability families are:

- `human_request.<direction|approval|input|review>`
- `command_run`

Capability validates after task and node-session recognition and before the semantic source row is created. A denial returns a shared structured failure:

```yaml
OperationFailure:
    ok: false
    code: capability_rejected
    summary: string
    retryable: false
    field_path: null
    suggested_next_step: string | null
```

The rejected capability name appears in the bounded `summary`; capability denial does not define a second failure carrier or add undeclared fields to the shared `OperationFailure` schema.

A rejected call:

- creates no human-request or command-run source row
- creates no waiting cause
- does not close the dispatch
- does not advance `last_progress_at`
- does not emit a standalone main-timeline event

The admitted failed invocation may still retain its normalized failure code in the internal `NodeMcpInvocation` audit record.

## Noninteractive provider policy

Provider-native question, approval, or permission mechanisms must never wait for input through a provider UI that AutoClaw does not consume.

Every managed adapter configures those mechanisms to one of these noninteractive outcomes:

- allow under the adapter's bounded machine policy
- deny and return a normal provider/tool failure
- fail launch when the provider cannot guarantee noninteractive behavior

The worker prompt teaches the agent to use AutoClaw `open_human_request` when it intentionally needs human direction, approval, input, or review. AutoClaw does not translate provider-native prompts after the fact, because doing so would reintroduce provider-event ingestion as runtime truth.

Provider-native sandbox and approval configuration is defense in depth. It does not replace Node MCP legality or human-request policy.

## Provider provenance

Every dispatch records controller-owned provider resolution:

```yaml
provider_resolution:
    requested_provider: openclaw | codex | claude
    resolved_provider: openclaw | codex | claude
```

Rules:

- the requested value comes from lawful task/operator preference or the runtime default
- fallback resolves before the dispatch commits
- the resolved value stays fixed for the dispatch
- later same-attempt dispatches may resolve differently from current policy
- API and event readbacks may expose requested and resolved provider plus provenance
- opaque provider session hints, credentials, provider payloads, and raw errors never appear on public readbacks

Provider provenance explains which adapter the controller selected. It is not provider lifecycle or semantic progress.

## Human-request provenance

Every terminal human request stores:

```yaml
human_request_provenance:
    request_id: string
    task_id: string
    resolved_by_actor_ref: string | null
    resolved_by_surface: control_api | control_ui | operator_mcp | controller
    resolution_kind: answered | timed_out | cancelled
    resolved_at: timestamp
    resolution_policy_basis: string
    resolution_note: string | null
```

The controller records provenance for answers, timeout, and cancellation. Provenance is immutable audit fact. It may be displayed by authorized control surfaces but never edited by a prompt or provider callback.

## Task authorization

Control reads and writes are authorized per task.

Rules:

- operator identity remains external authority, represented by a stable actor reference in audit rows and events
- adapter authentication proves only that AutoClaw may call that adapter
- provider login never authorizes controller writes
- operator MCP and HTTP controls use the same task currentness and authorization policy even when their transport authentication differs
- node mutations must pass session recognition, currentness, capability, and operation legality before commit

Credentials and raw authentication material are never controller runtime records, prompt fields, task events, or task files.

## Audit ownership

Controller source rows own current truth. The append-only task event stream owns bounded chronology over committed source changes.

Each task event retains:

```yaml
task_event_integrity:
    event_id: string
    event_hash: string
    prev_event_hash: string | null
```

The hash covers the canonical serialized controller event plus the prior hash. The concrete hash algorithm may evolve without changing the source-row truth model.

Provider output, native tool events, approval UI, token streams, disconnects, and terminal frames are never accepted as controller audit facts. Generic provider-control readback is controller state describing AutoClaw's own start or stop attempts, not normalized provider lifecycle.

Individual `NodeMcpInvocation` rows remain internal audit/progress evidence and do not generate one main-timeline event per call.

## Payload boundary

The minimum local-first contract does not add heuristic secret detection or structural masking to human-request and command-run content.

Instead, surfaces stay bounded by ownership:

- human-request list/detail may expose the authorized typed source and resolution
- human-request events do not inline full answer bodies or input payloads
- command-run list/detail may expose normalized command truth and log refs
- raw command logs remain behind the dedicated authorized log route
- task events carry bounded summaries, identifiers, state, and provenance
- provider payloads and credentials are never stored in these surfaces

Future principal-aware narrowing may strengthen this policy without making provider events authoritative.

## Required invariants

- managed executions receive Node MCP and never Operator MCP
- effective capability is stable for one dispatch and recomputed for the next
- task files and prompts never authorize capability
- provider-native interactive waits are disabled
- only AutoClaw MCP opens a managed-agent human wait
- provider authentication never authorizes controller mutation
- controller source rows and controller events remain the only audit truth

## Related contracts

- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Runtime records and control state](../architecture/runtime-records-and-control-state.md)
- [Node and operator MCP surface contract](node-and-operator-mcp-surface-contract.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Command run and external wait](../architecture/command-run-and-external-wait.md)
- [Control API](control-api.md)
- [Task event stream](task-event-stream.md)

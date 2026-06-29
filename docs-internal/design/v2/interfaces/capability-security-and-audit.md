# Capability, security, and audit

Status: Target

This page defines the V2 capability, security, and audit contract.

## Core rule

Capability, human-request permission, and audit are V2 core runtime concerns, not optional UX polish.

Human requests, long-running command runs, provider launch compatibility, and adapter integrations all depend on one controller-owned capability and audit model.

## Effective capability model

The controller must compute an effective capability set per current node execution.

That effective capability set may draw from:

- the current role and policy definitions
- controller-owned task or control policy
- resolved provider preference plus machine-local provider config
- adapter-specific constraints that are mapped into controller truth

The controller-owned effective capability set is the only authority for whether the current node may:

- open each kind of human request
- start a long-running command run for command work expected to exceed about two minutes

Adapter permissions, local tool permissions, and UI affordances may restrict further, but they must not silently widen the controller-owned capability set.

If the selected provider cannot use the required provider-neutral AutoClaw node and operator MCP surfaces, runtime must fail or fall back before dispatch acceptance. That is launch compatibility, not a per-dispatch capability deny.

The controller may serialize that effective set in a shape such as:

```yaml
effective_capability_set:
    execution_scope: dispatch | human_request_open | command_run_start
    human_request:
        direction: allow | deny
        approval: allow | deny
        input: allow | deny
        review: allow | deny
    command_run: allow | deny
```

Rules:

- effective `human_request` capability resolves per request kind, not as one vague yes or no bit
- omitted or denied `human_request` kinds resolve to `deny` in the effective capability set
- one dispatch should use one stable evaluated capability snapshot for prompt and readback surfaces
- later dispatches may recompute the set from fresher controller truth without treating old prompt text as authority

## Non-detector rule

The capability layer is not a provider tool detector.

It does not watch arbitrary model/provider tool calls and decide whether the user should approve them. AutoClaw's default automation posture remains explicit orchestration: a node requests human help when its instructions, workflow state, or model judgment say the task needs human direction, input, review, or approval.

Provider-specific approval or permission mechanisms may exist underneath particular adapters, but they are not capability-layer concepts.

Ordinary node MCP access is a launch-compatibility fact. It does not become a first-class capability family unless a later contract introduces a controller-owned lane that needs explicit allow or deny semantics.

## Minimum V2 capability families

V2 must model these capability families explicitly:

- `human_request`
- `command_run`

Rules:

- `human_request` uses explicit deny/allow policy and governs whether the current node may open a typed pending human request
- `command_run` governs whether the current node may start a controller-managed long-running command run for work expected to exceed about two minutes
- ordinary node MCP access is assumed once provider launch compatibility succeeds
- control-plane actions such as pause, continue, cancel, and resolve are governed by task authorization plus current task state rather than a node capability family

## Structured rejection rule

Illegal `human_request` or `command_run` attempts should be rejected immediately with a detailed structured error.

Minimum fields may look like:

```yaml
error:
    code: capability_rejected
    capability: human_request.review
    message: current worker policy does not allow review requests from this node
    next_legal_action: record_checkpoint_or_choose_another_allowed_boundary | optional
```

Rules:

- rejected special-lane calls do not create `pending_human_request`
- rejected special-lane calls do not create command-run records
- rejected special-lane calls do not emit standalone task-event noise in the minimum contract
- the error should be detailed enough that the node can adjust without reverse-engineering policy text from other surfaces

## Provider-resolution provenance

Accepted dispatches may persist minimal controller-owned provider-resolution provenance.

Minimum fields are:

```yaml
provider_resolution:
    requested_provider: openclaw | codex | claude
    resolved_provider: openclaw | codex | claude
```

Rules:

- `requested_provider` is the node-selected provider preference when present, otherwise the configured default provider
- `resolved_provider` is the provider that actually owns the accepted attempt
- fallback may happen only before dispatch acceptance
- once an attempt starts, provider identity for that attempt is pinned for audit and continuity
- fallback detail, adapter session ids, and model ids may stay in support-state or observability lanes until a later contract proves they need first-class surfaced status

## Capability snapshot and projection rule

The controller may materialize dispatch-local capability readbacks such as `_runtime/dispatch/<dispatch_id>/capabilities.json` or `_runtime/dispatch/<dispatch_id>/capabilities.md`.

Rules:

- those files are read models over controller-owned effective capability truth
- prompt sections may read from the same evaluated capability snapshot, but prompt text is not the source of truth
- if a materialized capability file lags, disappears, or disagrees with controller truth, controller truth and task events win

## Human request provenance

Every resolved human request must persist controller-owned provenance.

Minimum provenance fields are:

```yaml
human_request_provenance:
    request_id: string
    task_id: string
    resolved_by_actor_ref: string
    resolved_by_surface: control_api | control_ui | operator_mcp
    resolution_kind: answered | timed_out | cancelled
    resolved_at: timestamp
    policy_basis: string
    note: string | optional
```

Rules:

- the controller persists provenance even when the final result is rejection, timeout, or cancellation
- `resolved_by_actor_ref` is the controller's stable actor/principal reference for who or what resolved the request
- provenance is auditable fact, not prompt context by default
- future UI surfaces may display provenance, but they must not edit it

## No-redaction pre-UI rule

The minimum pre-UI lane does not plan structural redaction or heuristic secret detection on human-request or command-run surfaces.

Rules:

- human-request readbacks may carry controller-owned answer fields and provenance on their dedicated source rows
- task-event payloads for `human_request_*` stay bounded and do not inline full answered item bodies or structured response payloads
- command-run list/detail reads carry controller-owned command truth and log refs, but raw log bytes stay behind the dedicated log read
- the controller does not perform structural or heuristic masking over human answers, command strings, workdirs, or logs in this minimum contract
- task-event and readback surface splits in this lane are about controller ownership and replay shape, not secret suppression or payload reduction
- auth- or principal-aware narrowing may arrive later, but it is not part of the pre-UI capability/audit contract

## Event-log integrity

Controller-owned task events, human-request state changes, and command-run state changes must be append-only and tamper-evident.

Minimum integrity rule:

- each persisted event record carries `event_id`
- each persisted event record carries `event_hash`
- each persisted event record carries `prev_event_hash | null`
- the hash is computed over the controller's canonical serialized event payload plus the prior hash

The exact hash algorithm may evolve, but the design contract requires a verifiable append-only chain.

## Per-task auth rule

Control-plane reads and writes must be authorized per task.

Rules:

- operator identity remains external authority, not runtime DB truth
- task-scoped access is evaluated against controller-owned authorization inputs
- adapter-local auth success does not automatically authorize controller writes
- controller writes from adapter callbacks or adapter-normalized human requests must still pass task-lineage and capability checks

## Related contracts

- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [Workflow node schema](workflow-node-schema.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Command run and long-running boundary](../architecture/command-run-and-long-running-boundary.md)
- [Control API and task event stream](control-api-and-task-event-stream.md)
- [Node and operator MCP surface contract](node-and-operator-mcp-surface-contract.md)
- [Provider preference and runtime config](provider-selection-and-runtime-config.md)

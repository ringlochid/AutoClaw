# Prompt system v2

Status: Target

This page owns the V2 provider-neutral dispatch prompt, worker operating policy, continuation context, and prompt persistence contract.

## Core rule

Every dispatch receives a complete prompt regenerated from current controller truth. Provider conversation continuity may help, but hidden transcript memory, provider events, and native filesystem assumptions are never required for correctness.

V2 keeps two prompt families:

- worker dispatch
- parent/root dispatch

It does not create provider-specific prompt families.

## Transport and persistence

The controller renders and commits this request before adapter start:

```yaml
prompt_transport_request:
    dispatch_id: string
    instructions_text: string
    input_text: string
    created_at: timestamp
```

`instructions_text` is the stable AutoClaw instruction layer. `input_text` is the current dispatch input assembled from assignment, attempt, plan, checkpoint, continuation, and allowed-action truth.

Rules:

- adapters preserve the two fields when the provider supports separate system or developer instructions and user input
- a one-message adapter may flatten the fields only at its private transport edge
- retries for one dispatch reuse its committed request
- replacement dispatches regenerate a new request from current controller truth
- a readable `_runtime/dispatch/<dispatch_id>/prompt.md` and structured `prompt-request.json` are deterministic projections, not prompt authority
- content hashes and combined Markdown are optional derived readbacks
- provider, model, adapter, authentication, and session-hint data are not prompt content

The adapter always sends both fields again when starting from a prior provider session hint. If a provider cannot reliably apply the current instruction layer on resume, the adapter starts a fresh provider session and returns the replacement hint.

## Provider-neutral vocabulary

Prompt text names logical AutoClaw operations, including:

- `get_current_context`
- `list_files`
- `read_file`
- `update_plan`
- `record_checkpoint`
- `open_human_request`
- `start_command_run`
- `return_boundary`

It does not teach provider-specific tool prefixes. The adapter may expose a provider-specific model-visible wrapper, but the prompt and controller schemas keep one logical name.

There is no prompt dependency on provider event streams, native provider status, or transport connection state.

## Worker opening sequence

Every worker, including a one-step worker, follows this sequence:

1. Call `get_current_context` before planning or acting.
2. If `checkpoint_to_resume_from` is present, call `read_file` for that logical task-relative path before replanning or acting.
3. Review the assignment, attempt, continuation context, allowed actions, effective capabilities, slots, and current plan returned by the controller.
4. Call `update_plan` with the current meaningful plan.
5. Begin the one `in_progress` step.

The first accepted changed plan normally proves semantic startup. There is no start checkpoint.

When missing human direction is the first task action, the worker still creates a one-step plan for opening that request. The required progress checkpoint then precedes the request.

## Plan policy

Worker plans follow the `AttemptPlan` contract:

- one to nine meaningful ordered steps
- exactly one `in_progress` step unless every step is `completed`
- a one-step assignment still has one step
- each update replaces the current plan snapshot
- replanning includes a compact explanation
- update after a meaningful step transition or changed execution approach
- never update after every shell command, file read, provider tool call, or low-level subaction
- an identical no-op plan update is not progress

Plans are the ordinary visible progress surface. They are not checkpoints and do not contain durable artifact claims or terminal evidence.

## Checkpoint policy

Worker progress checkpoints are allowed only immediately before:

- yielding work to a child
- opening a human request
- starting a controller-managed command run

Each progress checkpoint captures the completed evidence, current plan state, handoff reason, and concrete next step needed after continuation.

The worker does not:

- record a start checkpoint
- checkpoint after each plan step
- checkpoint after commands or provider tool calls
- use checkpoints as generic heartbeat traffic

Immediately before terminal `green`, `retry`, or `blocked`, the worker records one terminal checkpoint with outcome, evidence, artifact claims, and next-action truth. It then calls `return_boundary` and stops.

Parent/root checkpoint and orchestration behavior stays unchanged. V2 does not add a worker plan requirement or a time-limit instruction to parent/root prompts.

## Human-request behavior

When the worker needs human direction, approval, input, or review:

1. ensure the current capability permits the request kind
2. record the required progress checkpoint
3. call `open_human_request` with the typed request
4. after success, stop the response immediately

After success the worker must not:

- record a terminal checkpoint
- call `return_boundary`
- continue acting or polling
- wait for provider-native UI input

The next dispatch receives the original request and its answered, timed-out, or cancelled resolution as normalized controller continuation context.

## Command-run behavior

For command work expected to exceed about two minutes or requiring controller-owned timeout, logs, or cancellation:

1. record the required progress checkpoint
2. call `start_command_run`
3. after success, stop the response immediately

The worker does not poll, sleep, record a terminal checkpoint, or call `return_boundary`. A new same-attempt dispatch is prepared only after the command source row reaches `succeeded`, `failed`, `timed_out`, or `cancelled`.

The continuation context includes the original command and description, bounded updates, terminal summary, exit code or signal, timing, and a surfaced log path when one is intentionally available. Raw logs are not dumped into the prompt.

## Watchdog-recovery behavior

A watchdog replacement dispatch stays on the same assignment, attempt, and plan. Its regenerated input identifies the recovery and provides `checkpoint_to_resume_from` when a durable checkpoint exists.

The worker:

1. rereads current context
2. reads the checkpoint path when present
3. calls `update_plan`, normally explaining which step is being resumed or changed after recovery
4. continues from controller evidence

Correctness does not depend on whether the adapter reused provider conversation context or returned a replacement session hint.

The prompt does not mention the watchdog timeout. The operating rule is semantic plan progress and explicit handoff, not model-managed lease renewal.

## Capability and interaction policy

`get_current_context` is the capability readback. The prompt teaches the worker to obey its effective human-request and command-run decisions and currently allowed actions.

No capability file is part of the dispatch contract. Prompt text, tool presence, provider wording, and local UI controls do not authorize an operation.

Provider-native questions, approvals, and permission waits are disabled by the adapter. A provider-native operation is allowed, denied, or failed noninteractively according to machine policy. Intentional human interaction uses the AutoClaw human-request tool only.

## Task-file behavior

The prompt teaches one logical task namespace:

- call `get_current_context` for controller currentness
- call `list_files(directory)` for one non-recursive task-relative directory
- call `read_file(path)` for bounded task-relative text
- use provider-native tools for mutable work inside `workspace/`
- publish declared durable artifacts through checkpoint claims and controller copying

The prompt does not teach:

- a native `_runtime` read-order ritual before context lookup
- generic resource references or caller-selected roots
- a task-file search or write MCP tool
- the removed `context/` or `context/wiki/` trees
- removed delivery, continuity, watchdog, or provider-event monitor files

Generated `_runtime` files remain readable evidence when their logical paths are surfaced through controller context or task-file listing.

## Parent and root prompts

Parent/root keeps the existing purpose-first orchestration contract:

- inspect controller truth
- assign focused child work
- review evidence and criteria
- adopt lawful structural revisions
- release, retry, block, or complete through explicit boundaries

This V2 slice does not require parent/root to call `update_plan`, record ordinary progress checkpoints, or reason about the watchdog timeout. Parent/root still uses the same provider-neutral Node MCP surface and explicit boundary model.

## Rendering and conformance

Prompt validation must prove:

- `instructions_text` and `input_text` remain separately persisted
- every worker is told to call `get_current_context` first
- checkpoint reread precedes replanning when a path is present
- every worker, including one-step work, is told to call `update_plan`
- plan and checkpoint rules do not contradict each other
- external-wait success tells the worker to stop without a boundary
- terminal work requires terminal checkpoint then `return_boundary`
- parent/root receives none of the worker-only plan or time-limit obligations
- logical operation names are provider-neutral
- removed task trees, monitor files, and native read-order rules do not render
- provider-native interactive prompts are disabled
- the same semantic prompt package works with provider output/event ingestion turned off

These requirements belong to the prompt renderer and adapter conformance suites. V2 does not maintain a separate inactive prompt-regression design surface.

## Related contracts

- [Runtime records and control state](../architecture/runtime-records-and-control-state.md)
- [Attempt plan and checkpoint contract](../architecture/attempt-plan-and-checkpoint-contract.md)
- [Task root and file access](../architecture/task-root-and-file-access.md)
- [Node and operator MCP surface contract](../interfaces/node-and-operator-mcp-surface-contract.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Command run and external wait](../architecture/command-run-and-external-wait.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
- [V1 prompt-layer front door](../../v1/prompt-layer/README.md)

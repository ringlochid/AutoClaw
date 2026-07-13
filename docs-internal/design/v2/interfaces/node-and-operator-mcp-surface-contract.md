# Node and operator MCP surface contract

Status: Target

This page defines the V2 provider-neutral MCP surface split and the semantic role of node MCP operations. Exact context, file, and plan schemas live in the [Node MCP schema appendix](node-mcp-schema-appendix.md).

## Core rule

AutoClaw has two logical MCP surfaces:

- `node` for a managed agent acting as the current worker, parent, or root
- `operator` for external task inspection and control

Committed, current semantic node MCP mutations are the agent-facing runtime truth. MCP transport state and provider observations are not.

## Lowest-common-denominator profile

The shared logical contract assumes only:

- MCP tools
- explicit JSON-schema inputs
- structured JSON results with a text fallback
- stateless streamable HTTP for the local AutoClaw server
- provider-neutral logical tool names

Correctness does not depend on MCP prompts, resources, ping, progress notifications, transport session continuity, provider tool events, provider output streams, or dynamic tool refresh.

Adapters may privately use provider-specific configuration to attach node MCP. They must not rename or fork the logical AutoClaw tool contract.

## Node surface

Node MCP is the required managed-agent surface. AutoClaw commits the current dispatch and live `NodeSession` before provider launch, and an adapter does not report readiness until the agent can reach the node server.

Managed Codex, Claude, and OpenClaw agents receive node MCP only. They never receive operator MCP as part of dispatch launch.

### Context and plan family

The shared context, file-read, and plan family is exactly:

```text
get_current_context()
list_files(directory=".")
read_file(path, start_line=1, max_lines=400)
update_plan(explanation?, steps)
```

These signatures omit the common recognition arguments for readability. Every node call explicitly includes:

```text
task_id
session_key
```

The server resolves those values against current controller truth before any read or mutation. Provider identity and provider session continuity are not MCP recognition fields.

`get_current_context` returns:

- the current assignment and attempt
- the current attempt plan
- effective capabilities and currently allowed actions
- consume and produce slots with logical task-relative paths
- normalized human-request, command-run, or watchdog-restart continuation context when present
- `checkpoint_to_resume_from` when a durable handoff must be reread

The [prompt system](../prompt-layer/prompt-system-v2.md) owns the rule that a worker reads `checkpoint_to_resume_from` before replanning. The MCP surface returns the selected controller truth and does not duplicate that prompt policy.

`list_files` is non-recursive. `read_file` is bounded and text-only. Both use the shared resolver owned by [Task root and file access](../architecture/task-root-and-file-access.md).

`update_plan` is worker-only. Each accepted changed request replaces the current plan snapshot with one to nine ordered steps. Exactly one step is `in_progress` unless every step is `completed`. Parent and root orchestration continue to use their existing tools and do not acquire worker plan requirements.

### Existing semantic families

The context and plan family extends, rather than replaces, the existing provider-neutral semantic families:

- current-only definition lookup for legal structural edits
- checkpoint publication through `record_checkpoint`
- terminal and yield boundaries through `return_boundary`
- human-request and command-run wait creation
- parent and root assignment and structural mutation

Their request and response payloads remain owned by their existing architecture and interface contracts. They use the same recognition, failure, invocation, and progress rules defined here.

### File boundary

Node MCP reads controller context and files from the whole logical task namespace. It does not write task files, search file contents, accept generic resource references, or select remote filesystem roots.

Provider-native tools edit `workspace/`. Declared durable artifacts are published through checkpoint claims and controller copying. This keeps one workspace mutation lane and one durable publication lane.

## Operator surface

Operator MCP remains an external control and inspection surface. It owns provider-neutral actions such as:

- definition registry reads, definition upload, and task start
- runtime reads and task control
- human-request inspection and resolution
- running command-run cancellation
- support and observability reads

Mutating definition draft authoring remains on the trusted HTTP `/authoring` workbench API, not operator MCP.

Operator MCP is not attached to managed provider executions and is not a provider adapter readiness requirement. Its authentication and authorization remain separate from node-session recognition.

## Semantic progress

After request shape and current task, node-session, dispatch, assignment, and attempt authority validate, the server records the admitted node call as a `NodeMcpInvocation` with:

- invocation identity
- current dispatch identity
- provider-neutral tool name
- `started`, `completed`, or `failed` status
- start and finish time
- whether the completed operation advanced semantic progress
- normalized failure code when failed

This record supports audit, watchdog timing, and diagnostics. It is not a public task-timeline event and does not store provider output or request payloads.

A changed `update_plan` call and other meaningful committed controller mutations advance the dispatch's `last_progress_at`. Read-only calls, rejected calls, failed calls, and identical plan updates do not. Invocation start alone never advances progress.

The detailed matrix is in the [Node MCP schema appendix](node-mcp-schema-appendix.md). Persistence and transaction ownership live in [Runtime records and control state](../architecture/runtime-records-and-control-state.md), and plan revision ownership lives in [Attempt plan and checkpoint](../architecture/attempt-plan-and-checkpoint-contract.md).

## Failure contract

Every node tool has a structured success schema plus the shared structured `OperationFailure` alternative. Validation, recognition, currentness, path, plan, and operation errors therefore remain provider-neutral.

Failures do not advance `last_progress_at`. A call admitted after authority validation and then failing during tool handling is recorded as a terminal `failed` invocation. Shape, recognition, and currentness failures that happen before invocation admission still return `OperationFailure`, but do not require a `NodeMcpInvocation` row.

## Transport is not runtime truth

These observations never change assignment, attempt, dispatch, plan, checkpoint, boundary, wait, or watchdog truth:

- MCP transport connect or disconnect
- MCP transport session identifiers
- MCP ping
- MCP protocol progress notifications
- provider-native tool events
- provider output, token, or terminal streams

Only a successful current semantic operation may commit controller state. The runtime watchdog uses the resulting `last_progress_at`, not transport traffic.

## No-split rule

Do not create provider-specific logical routes or tool vocabularies such as `/codex/node`, `/claude/node`, or `/openclaw/operator`.

If a hard incompatibility appears, split only the adapter's transport, configuration, or authentication wrapper. Preserve:

- provider-neutral logical tool names
- node versus operator trust separation
- controller-owned request, response, and failure semantics
- semantic progress rules

## Related contracts

- [Node MCP schema appendix](node-mcp-schema-appendix.md)
- [Task root and file access](../architecture/task-root-and-file-access.md)
- [Runtime records and control state](../architecture/runtime-records-and-control-state.md)
- [Attempt plan and checkpoint](../architecture/attempt-plan-and-checkpoint-contract.md)
- [Runtime lifecycle and watchdog](../architecture/runtime-lifecycle-and-watchdog.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Human request and approval](human-request-and-approval-contract.md)
- [Command run and external wait](../architecture/command-run-and-external-wait.md)
- [ADR-0008: task-relative MCP reads and reduced task root](../../../adr/ADR-0008-task-relative-mcp-reads-and-reduced-task-root.md)

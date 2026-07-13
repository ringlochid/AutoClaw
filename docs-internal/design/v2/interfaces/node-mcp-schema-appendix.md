# Node MCP schema appendix

Status: Target

This appendix owns the exact V2 request, response, validation, path, failure, and progress contract for `get_current_context`, `list_files`, `read_file`, and `update_plan`.

The schemas are provider-neutral. Model-visible prefixes added by a provider or MCP client are discovery details and never appear in these logical names or payloads.

## Shared conventions

### Recognition arguments

Every node request extends this shape:

```yaml
NodeRecognitionArguments:
  task_id: string
  session_key: string
```

Both strings are required and nonempty. Every concrete request and response schema below forbids properties it does not declare. The arguments remain explicit tool input fields over stateless streamable HTTP; they are not HTTP headers, provider session ids, bearer tokens, or values inferred from the transport connection.

Before executing a tool, AutoClaw resolves `session_key` to a live `NodeSession` and verifies that `task_id`, dispatch, assignment, attempt, node, and flow currentness all agree. Failure occurs before the requested read or mutation.

### Success and failure results

Each tool returns either its named success schema or the shared failure shape:

```yaml
OperationFailure:
  ok: false
  code: OperationFailureCode
  summary: string
  retryable: boolean
  field_path: string | null
  suggested_next_step: string | null
```

Additional properties are forbidden. MCP marks the failure result with `isError: true` and may repeat `summary` as text content. Success payloads do not add an `ok` discriminator.

All timestamps below are RFC 3339 UTC strings. All logical paths use `/` separators and are relative to the logical task namespace.

## Shared read types

```yaml
AssignmentContextRead:
  assignment_id: string
  node_key: string
  node_kind: worker | parent | root
  summary: string
  instruction:
    type: string
    nullable: true
  criteria:
    - slot: string
      path: string
      description: string

AttemptContextRead:
  attempt_id: string
  assignment_id: string
  retry_of_attempt_id: string | null

AttemptPlanStepRead:
  step: nonempty string
  status: pending | in_progress | completed

AttemptPlanRead:
  attempt_id: string
  revision: integer >= 1
  explanation: string | null
  steps: [AttemptPlanStepRead, ...] # 1..9
  updated_at: timestamp

SlotContextRead:
  slot: string
  kind: artifact | criteria | checkpoint | transient | workspace
  description: string
  path: string | null
  version: integer >= 1 | null

EffectiveCapabilitySet:
  dispatch_id: string
  human_request:
    direction: allow | deny
    approval: allow | deny
    input: allow | deny
    review: allow | deny
  command_run: allow | deny

HumanRequestContinuationRead:
  kind: human_request
  request: HumanRequestRead
  resolution: HumanRequestResolutionRead

CommandRunContinuationRead:
  kind: command_run
  run: CommandRunRecord

WatchdogRestartContinuationRead:
  kind: watchdog_restart
  previous_dispatch_id: string
  restart_number: integer >= 1
  summary: string

NormalizedContinuationRead:
  one_of:
    - HumanRequestContinuationRead
    - CommandRunContinuationRead
    - WatchdogRestartContinuationRead
```

`HumanRequestRead` is the complete original source record and `HumanRequestResolutionRead` is its typed terminal resolution, as owned by the human-request contract. `CommandRunRecord` is the terminal-result shape owned by the command-run contract. The wrappers above add only the provider-neutral continuation discriminator. `get_current_context` embeds exactly one continuation variant or `null`; it does not expose provider response text or provider lifecycle state.

For slot reads:

- `path` is the current logical task path when a body is materialized
- an unmaterialized produce requirement has `path: null`
- `version` is present only for a versioned artifact and is otherwise `null`
- slot order follows the current assignment's declared order

## `get_current_context`

### Request

```yaml
GetCurrentContextRequest:
  task_id: string
  session_key: string
```

### Success response

```yaml
GetCurrentContextResponse:
  assignment: AssignmentContextRead
  attempt: AttemptContextRead
  plan: AttemptPlanRead | null
  capabilities: EffectiveCapabilitySet
  allowed_actions: [string, ...]
  consume_slots: [SlotContextRead, ...]
  produce_slots: [SlotContextRead, ...]
  continuation: NormalizedContinuationRead | null
  checkpoint_to_resume_from: string | null
```

`EffectiveCapabilitySet` is the current controller-owned capability shape from the capability contract. `allowed_actions` contains provider-neutral node operation names legal for this dispatch; it never contains provider-prefixed tool ids.

`checkpoint_to_resume_from` is selected by the controller. When non-null, it must be a readable task-relative checkpoint path. The agent does not infer a checkpoint by scanning attempt directories or ordering history.

The response is a current read and is not paginated. It contains summaries and logical refs rather than file bodies; agents use `read_file` for a referenced body.

## `list_files`

### Request

```yaml
ListFilesRequest:
  task_id: string
  session_key: string
  directory: string = "."
```

`directory` must resolve to the logical task root or one readable directory.

### Success response

```yaml
FileEntryRead:
  name: string
  path: string
  kind: file | directory | symlink | other
  size_bytes: integer >= 0 | null

ListFilesResponse:
  directory: string
  entries: [FileEntryRead, ...]
```

Entries are sorted by Unicode code point of `name`. The listing is exactly one level and never recursive. `size_bytes` is the regular-file size and is `null` for directories, symlinks, and other file kinds.

The response has no cursor and no pagination in V2. If a configured directory entry ceiling would be exceeded, the entire call fails with `directory_limit_exceeded`; AutoClaw does not return an ambiguous partial listing. The ceiling is deployment configuration, not a frozen schema number.

## `read_file`

### Request

```yaml
ReadFileRequest:
  task_id: string
  session_key: string
  path: string
  start_line: integer >= 1 = 1
  max_lines: integer >= 1 = 400
```

The schema freezes a 400-line default and does not freeze a universal hard maximum. A deployment may configure a maximum requested line count or response byte count.

### Success response

```yaml
ReadFileResponse:
  path: string
  start_line: integer >= 1
  max_lines: integer >= 1
  content: string
  lines_returned: integer >= 0
  has_more: boolean
  next_start_line: integer >= 1 | null
```

The server accepts a regular file or a contained symlink resolving to a regular file. It decodes UTF-8 text and preserves the selected lines' original newline characters in `content`.

`lines_returned` is the count of selected logical lines. When more lines remain, `has_more` is true and `next_start_line` equals `start_line + lines_returned`; otherwise `next_start_line` is null. A `start_line` beyond end of file succeeds with empty `content`, zero returned lines, `has_more: false`, and no next line.

If a configured requested-line or response-byte ceiling would be exceeded, the call fails with `file_read_limit_exceeded`. It does not return content that quietly violates the requested line slice.

## `update_plan`

### Request

```yaml
UpdatePlanStep:
  step: nonempty string
  status: pending | in_progress | completed

UpdatePlanRequest:
  task_id: string
  session_key: string
  explanation: string | null = null
  steps: [UpdatePlanStep, ...] # 1..9
```

Validation rules:

- only a current worker dispatch may call the tool
- the ordered list contains one through nine steps
- exactly one step is `in_progress`, unless every step is `completed`
- zero active steps with any pending step is invalid
- two or more active steps are invalid
- `explanation` may be null for the first plan and must be nonempty when replanning materially changes the intended step sequence or meaning
- parent and root dispatches fail with `illegal_caller`

### Success response

```yaml
UpdatePlanResponse:
  changed: boolean
  plan: AttemptPlanRead
```

Each changed call replaces the whole current plan and increments its revision once. The controller emits one `plan_updated` task event and advances `last_progress_at` in the same accepted mutation.

A request whose validated `explanation` and ordered `(step, status)` values equal the persisted plan is a no-op. It returns `changed: false` with the unchanged plan and creates no revision, task event, or semantic progress.

## Path normalization and containment

`list_files` and `read_file` share this behavior:

1. accept `/` as the logical separator
2. reject empty paths except the listing default `.`
3. reject NUL bytes, POSIX absolute paths, Windows drive paths, UNC paths, backslash-rooted paths, and every `..` segment
4. normalize removable `.` segments
5. accept only `workspace`, `outputs`, `tmp`, or `_runtime` as the first segment
6. map the selected root through persisted task-root or workspace-binding truth
7. resolve symlinks and require the result to remain inside that selected physical root

The logical root listing `.` returns the four logical roots. It never lists their physical parents. A contained symlink is visible as `kind: symlink`; any later operation follows it only after repeating the containment check.

## File and path failures

The context and plan tools use existing common failure codes such as `invalid_request_shape`, `illegal_caller`, `illegal_state`, `stale_dispatch`, and `missing_resource`. The file contract adds these exact codes:

| Code | Meaning | Retryable |
| --- | --- | --- |
| `invalid_task_path` | malformed, absolute, NUL-containing, or parent-traversing logical path | no |
| `invalid_task_root` | first segment is not a V2 logical root, or the persisted selected-root mapping is unavailable | no |
| `path_escape` | symlink resolution leaves the selected mapped root | no |
| `not_a_directory` | `list_files` target exists but is not a directory | no |
| `not_a_file` | `read_file` target exists but is not a regular file or contained symlink to one | no |
| `binary_file` | target is not valid supported UTF-8 text or contains binary NUL data | no |
| `file_read_limit_exceeded` | configured requested-line or response-byte ceiling would be exceeded | no |
| `directory_limit_exceeded` | configured directory-entry ceiling would be exceeded | no |

A nonexistent path uses the existing `missing_resource` code. Unsupported special files use `not_a_file`. Failure `field_path` is `path`, `directory`, `start_line`, `max_lines`, or the exact invalid plan field when applicable.

Plan invariant violations use `invalid_request_shape` with `field_path: steps`. Recognition and currentness failures occur before path-existence details are returned, preventing stale or unauthorized callers from probing task files.

## Invocation and progress matrix

After request shape and current authority validate, every admitted node call creates one `NodeMcpInvocation`. The record enters `started`, then finishes as `completed` or `failed`. Only a successful semantic commit may set `advanced_progress: true`.

| Operation result | Invocation terminal state | Advances `last_progress_at` |
| --- | --- | --- |
| `get_current_context` success | `completed` | no |
| `list_files` success | `completed` | no |
| `read_file` success | `completed` | no |
| changed `update_plan` success | `completed` | yes |
| identical `update_plan` success | `completed` | no |
| meaningful checkpoint, boundary, external-wait, assignment, or structural mutation commit | `completed` | yes |
| legality, path, or mutation failure after invocation admission | `failed` | no |
| request-shape, recognition, or currentness failure before admission | no invocation row | no |

Invocation acceptance or `started` status alone never advances progress. Provider events, MCP ping, MCP progress notifications, and transport traffic do not create semantic progress.

## Transaction and event rules

- a changed plan revision, its `plan_updated` event, invocation completion, and `last_progress_at` update commit atomically
- a successful read commits only invocation completion metadata
- a call that fails after invocation admission commits normalized invocation failure metadata without the requested semantic mutation
- a shape, recognition, or currentness failure before admission returns the shared failure without creating an invocation row
- `NodeMcpInvocation` is not emitted as a public event for every call
- request payloads, file content, provider output, and session credentials are not copied into invocation metadata

Persistence details are owned by [Runtime records and control state](../architecture/runtime-records-and-control-state.md). Plan and checkpoint semantics are owned by [Attempt plan and checkpoint](../architecture/attempt-plan-and-checkpoint-contract.md).

## Related contracts

- [Node and operator MCP surface](node-and-operator-mcp-surface-contract.md)
- [Task root and file access](../architecture/task-root-and-file-access.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Human request and approval](human-request-and-approval-contract.md)
- [Command run and external wait](../architecture/command-run-and-external-wait.md)
- [ADR-0008: task-relative MCP reads and reduced task root](../../../adr/ADR-0008-task-relative-mcp-reads-and-reduced-task-root.md)

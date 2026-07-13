# Task root and file access

Status: Target

This page owns the V2 local task tree, logical path resolution, and the split between provider-native workspace editing, node MCP reads, and controller-owned artifact publication.

## Core rule

AutoClaw exposes one logical task namespace. Controller records own semantic truth. Files below the task namespace are mutable work, durable bodies, or deterministic projections; none can overrule the controller database.

V2 remains local-first and same-host. The file boundary is a code ownership boundary, not a separately deployed file service.

## Canonical task tree

The complete V2 task tree is:

```text
task/
  workspace/
  outputs/
    artifacts/
  tmp/
    transfers/
      localized/
  _runtime/
    criteria/
    workflow-manifest.json
    workflow-manifest.md
    attempts/
      <attempt_id>/
        assignment.json
        assignment.md
        latest-checkpoint.json
        latest-checkpoint.md
        artifact-index.json
        transient-index.json
    dispatch/
      <dispatch_id>/
        prompt.md
        prompt-request.json
```

No other top-level task directory is part of the V2 contract.

## Root ownership

| Logical root | Physical mapping | Owner and purpose |
| --- | --- | --- |
| `workspace/` | the persisted workspace binding | provider-native mutable work for the current task |
| `outputs/` | below the physical task root | controller-published durable output bodies and artifact pointers |
| `tmp/` | below the physical task root | controller-managed noncanonical transient and localized material |
| `_runtime/` | below the physical task root | controller-generated readable projections |

The persisted workspace binding may point outside the physical task-root directory. That does not widen the logical namespace: callers still select `workspace/...`, never an arbitrary physical root.

### `workspace/`

Managed Codex and Claude processes use the workspace binding as their working directory. OpenClaw receives the same effective task workspace through its adapter configuration.

Provider-native tools may read, create, edit, rename, and delete workspace files subject to provider sandbox and approval policy. Workspace contents are not controller truth and are not automatically durable publications.

### `outputs/artifacts/`

The artifact owner accepts declared checkpoint claims, validates them against the assignment's produce slots, copies the accepted workspace bodies, versions them, and updates controller-owned artifact records and current pointers.

Agents do not publish by writing directly into `outputs/artifacts/` through node MCP.

### `tmp/transfers/localized/`

External material that must become task-local is copied into `tmp/transfers/localized/` before the controller surfaces its logical path. Localized files are convenience inputs, not durable controller truth.

### `_runtime/`

`_runtime/` contains deterministic controller projections:

- explicit criteria projections
- the stable whole-workflow manifest
- current attempt assignment and latest-checkpoint projections
- attempt artifact and transient indexes
- dispatch prompt and structured prompt-request evidence

The controller writes these files. Agents may read them through the node MCP file tools but do not mutate them.

## Logical path contract

Node MCP file tools accept forward-slash logical paths. The public namespace contains only:

- `workspace`
- `outputs`
- `tmp`
- `_runtime`

The special path `.` means the logical task root and is accepted only where a directory is valid. Listing `.` returns entries from this logical namespace; it does not expose the physical parent directories that back the mappings.

### Shared resolver

All task-relative file tools use one resolver. It performs these steps in order:

1. validate the input as a nonempty logical path using `/` separators
2. reject POSIX absolute paths, Windows drive paths, UNC paths, backslash-rooted paths, NUL bytes, and any `..` segment
3. collapse `.` segments without changing the selected logical root
4. require the first segment to be one of the four logical roots, except for the listing-only `.` path
5. map that root through controller-owned task-root or workspace-binding truth
6. resolve the candidate and any symlinks
7. verify that the resolved path remains inside the selected physical root

The resolver rejects caller-selected physical roots. A symlink that resolves outside its selected mapped root is an escape even when its target happens to be below another valid task root.

Contained symlinks may be listed and read. Directory listing reports them as symlinks; a subsequent read or listing resolves them again and applies the same containment check.

## Node MCP read behavior

The task-file read family is:

```text
list_files(directory=".")
read_file(path, start_line=1, max_lines=400)
```

`list_files` reads one directory and is never recursive. It returns names, logical paths, entry kinds, and file sizes where available. It does not search contents or walk descendants.

`read_file` accepts regular text files only. It decodes UTF-8, returns a line-bounded slice, reports whether more lines remain, and never returns a partial success caused by an operational byte or entry ceiling. Binary, missing, invalid-root, escaped, wrong-kind, and over-limit cases return the explicit failures defined in the [Node MCP schema appendix](../interfaces/node-mcp-schema-appendix.md).

The schema default is 400 lines. V2 does not freeze a universal hard maximum. A deployment may configure response-byte, requested-line, or directory-entry ceilings; exceeding one returns the documented over-limit failure instead of silently truncating beyond the requested line boundary.

## Context read behavior

`get_current_context` is the primary worker reread. It returns controller-owned current assignment, attempt, plan, capability, slot, continuation, and checkpoint-path state directly rather than asking the provider to infer those facts from directory layout.

Generated files remain useful for readable evidence and detailed payloads. When `checkpoint_to_resume_from` is present, the worker prompt teaches the worker to call `read_file` for that path before replanning or acting. The [prompt system](../prompt-layer/prompt-system-v2.md) owns the exact teaching; this page owns only the readable path and file behavior.

## Mutation and publication lanes

The file model has three deliberately separate lanes:

| Need | Canonical lane |
| --- | --- |
| edit current work | provider-native tools inside `workspace/` |
| read controller context or any logical task file | node MCP context and file tools |
| publish a durable declared artifact | checkpoint claim plus controller copy/version |

Node MCP does not expose a task-file write tool, a content-search tool, generic resource refs, or a caller-selected root. Future remote execution may expose a remote command environment with its own standard file and search tools; it does not require V2 to invent a second local filesystem protocol now.

## Removal and reset

V2 removes these V1 task-root concepts in one reset-only change:

- `context/`
- `context/wiki/`
- task-memory search hints
- the dispatch delivery-state projection
- the dispatch continuity-state projection
- the dispatch watchdog-state projection
- the dispatch provider-event projection

Do not keep ignored schema fields, empty compatibility directories, or prompt fallbacks for those surfaces.

Database and task-root upgrade compatibility is not required. Stale local state fails with reset guidance. Reset must not recursively delete a formerly configured external context binding because the path may contain user-owned data outside AutoClaw's task root.

## Security and audit

- node MCP recognition remains `task_id` plus current `NodeSession` `session_key`
- file reads run only after current node-session, dispatch, assignment, attempt, and task authority validation
- logical paths and normalized failures may be audited; provider credentials and file contents are not added to invocation metadata
- managed agents receive node MCP only; operator MCP remains a separate external control surface
- filesystem transport state and provider events never establish runtime progress

## Related contracts

- [Node and operator MCP surface](../interfaces/node-and-operator-mcp-surface-contract.md)
- [Node MCP schema appendix](../interfaces/node-mcp-schema-appendix.md)
- [Runtime records and control state](runtime-records-and-control-state.md)
- [Attempt plan and checkpoint](attempt-plan-and-checkpoint-contract.md)
- [Runtime lifecycle and watchdog](runtime-lifecycle-and-watchdog.md)
- [ADR-0008: task-relative MCP reads and reduced task root](../../../adr/ADR-0008-task-relative-mcp-reads-and-reduced-task-root.md)

# Task root and file access

Status: Target

This page owns the V2 logical task tree, controller-generated request files, safe Node MCP reads, and separation between required request materialization and optional support projections.

## Authority rule

The controller database owns runtime currentness, legality, lineage, and metadata. Task files may be durable bodies or derived readable projections, but they never authorize a controller transition merely by existing.

The two committed dispatch request files are authoritative only for the exact bytes delivered to that dispatch. Their refs row in the database establishes which files belong to the dispatch.

## Logical task tree

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
        instructions.md
        input.md
```

`workspace/` is a logical root backed by the task's persisted workspace binding. It may resolve to a controller-owned copy or an explicitly bound external directory according to the task/workspace contract. Callers never provide or discover the physical root.

`outputs/`, `tmp/`, and `_runtime/` live beneath the physical task root. Their ownership and retention differ; all access still uses logical task-relative paths.

The target has no `context/` or `context/wiki/` family and no provider delivery, continuity, watchdog, or provider-event files under dispatch directories.

## Canonical dispatch request pair

Every dispatch directory contains exactly:

```text
instructions.md
input.md
```

`instructions.md` contains the exact resolved AutoClaw instruction bytes for the dispatch's role family and authored guidance. `input.md` contains the exact complete dynamic snapshot for the dispatch.

There is no combined `prompt.md`, `prompt-request.json`, resume append, provider transport envelope, content-hash file, or launch-time regenerated substitute.

## Publication order

The exact-source opener mints a prospective dispatch ID and renders both files outside the final database transaction. It stages and publishes them as a pair before attempting the D2+refs commit.

The final transaction revalidates the source/currentness and creates D2 plus its refs-only row. A committed refs row therefore never points to a half-published request.

If the transaction loses, the pair is unreferenced and may be removed by bounded cleanup. It cannot trigger provider work.

The provider starter reads only the committed refs. It never invokes the renderer, repairs a missing file, changes bytes, or selects another dispatch directory.

## Atomic file publication

The implementation must use a same-filesystem staging and replacement strategy for the pair. The exact primitive may be a staging directory followed by atomic renames, but these invariants are fixed:

- neither final path is referenced before both staged files are complete;
- file contents are flushed/closed before the final DB transaction;
- existing immutable request paths are never overwritten by a retry;
- a second candidate for the same dispatch identity is rejected; and
- orphan cleanup never deletes files referenced by a committed row.

The database transaction remains the authority handoff. Filesystem atomicity alone cannot make a dispatch current.

## Support and observability projections

Workflow manifests, assignment/checkpoint readbacks, artifact indexes, and other operator support files may be refreshed after their owning controller transaction by a separate `SupportProjectionOwner`.

Support projection rules:

- projection signals carry exact source/revision identity;
- projection handlers reread committed controller truth;
- failures are visible and retriable within the projection domain;
- a missing support file does not reopen, close, or block a dispatch; and
- provider start never waits for a support projection unless the file is one of the two canonical request files, in which case it is request materialization rather than support projection.

## Task-relative Node MCP reads

The provider-neutral logical read family is:

```text
get_current_context()
list_files(directory=".")
read_file(path, start_line=1, max_lines=400)
```

Managed schemas contain semantic arguments only. The managed binding supplies task/dispatch scope below the model-visible schema. The compatibility projection adds full `task_id` and `dispatch_id` arguments.

`get_current_context` reads controller records directly. It does not reconstruct currentness from files.

`list_files` is non-recursive and returns bounded entries with logical paths and basic type/size metadata. `read_file` returns bounded UTF-8 text and a stable truncation/continuation shape.

The MCP surface does not expose generic task-file writes or search in this phase.

## Logical-path resolver

One shared resolver maps allowed logical prefixes to physical roots and rejects:

- absolute paths;
- empty or ambiguous path segments where disallowed;
- `..` traversal;
- NUL and invalid encoding;
- paths outside declared logical roots;
- symlink resolution escaping the selected root;
- special devices, sockets, or non-regular files for text reads; and
- task/dispatch scope that fails fresh currentness validation.

Containment is checked after canonical resolution. String-prefix comparison alone is not sufficient.

Managed request-file validation uses the same resolver and additionally requires the exact committed dispatch directory and filenames.

## Workspace mutation

Provider-native tools remain the workspace editing lane. Their authority is the ambient AutoClaw service identity plus resolved provider policy, not Node MCP.

Node MCP does not offer general file writes, shell execution, or provider-native tool emulation. The controller `command_run` surface is a distinct external-wait concept.

Provider-native access, network, managed Node MCP, command runs, and human requests remain separate capability dimensions.

## Artifact publication

Workers publish declared artifacts through the checkpoint/boundary contract. The controller validates declared slots and copies/versions accepted bodies into `outputs/artifacts/`.

Artifact indexes are controller projections over accepted publication records. Writing a file directly into `outputs/artifacts/` cannot create an artifact record or satisfy a criterion.

Large bodies remain behind logical refs. Prompt snapshots, checkpoints, task events, and generic readbacks do not duplicate them.

## Transient localization

`tmp/transfers/localized/` holds controller-localized transient inputs needed for the task. Its index records provenance and logical refs. Transient bodies are not automatically durable artifacts and do not become workflow truth.

Cleanup follows the owning task retention policy and never traverses an externally bound workspace path.

## Request and support cleanup

Cleanup may remove:

- unreferenced candidate dispatch directories older than a safety horizon;
- staging directories left by interruption;
- expired transient localized bodies; and
- obsolete support projections that can be regenerated.

Cleanup must first prove that no committed request-ref, artifact, transient, checkpoint, or active task relationship references the path. It is maintenance work, not the dispatch correctness path.

## Secrets and sensitive data

Task files must not contain:

- managed MCP bearer credentials or digests;
- provider/API/Gateway credentials;
- raw environment secrets;
- provider thread/session handles;
- physical task roots;
- unbounded human answers or command logs in generic projections; or
- hidden model reasoning.

Prompts may contain canonical non-secret task/dispatch IDs and logical paths.

## Reset behavior

V2 reset removes obsolete generated context and provider-monitor projections and rebuilds controller-owned runtime files from supported source records where allowed.

Reset must never recursively delete an external workspace or formerly configured external context path. User-owned paths are outside the task-root deletion boundary.

## Required proof

- one committed dispatch has one pair and one refs row;
- a failed/losing transaction causes no provider call;
- retry rereads identical bytes without rendering;
- missing, unreadable, symlink-escaped, or wrong-dispatch refs cause zero provider I/O;
- support projection failure does not block or change controller state;
- logical reads reject traversal and symlink escape;
- provider-native workspace edits remain separate from Node MCP reads;
- artifact records cannot be forged by filesystem writes; and
- cleanup preserves every committed reference and external workspace.

## Related

- [Prompt system](../prompt-layer/prompt-system.md)
- [Runtime records and control state](runtime-records-and-control-state.md)
- [Runtime lifecycle and watchdog](runtime-lifecycle-and-watchdog.md)
- [Work plan and checkpoint contract](work-plan-and-checkpoint-contract.md)
- [Node MCP schema appendix](../interfaces/node-mcp-schema-appendix.md)

# Current definitions, compiler, and task start

Status: Current

Last verified: 2026-07-19

Published role, policy, and workflow revisions live in the controller database. Packaged YAML is seed and import input, not runtime authority after publication.

## Registry

Each definition revision is immutable and content-addressed. One current revision is selected for each kind and key. Reads, history, upload, CLI import, authoring publish, and task compilation all use this registry.

An identical upload is a no-op replay. Changed content creates a new revision when the caller allows it. Publishing never edits an old revision.

## Drafts

Definition drafts are editable files under the configured AutoClaw data directory. They are authoring state, not published runtime truth.

A draft records its create or update mode and, for an update, the published revision it started from. Validate reports schema, cross-reference, and stale-baseline problems. Publish rechecks current registry truth before creating the immutable revision.

## Compilation

Task preview and task start compile the selected current workflow. Compilation resolves every referenced role and policy, validates graph and node rules, resolves the strict provider route, and computes the effective capability ceiling.

The compiled launch snapshot pins exact workflow, role, and policy revisions. Later definition changes do not rewrite a running task.

Provider selection has no hidden fallback. An explicit node provider must be configured and available. An omitted provider uses the configured default; starting fails when no default exists.

Provider-native access defaults to full when omitted. Authored, task, and controller policy may only narrow it. Network access is a separate policy axis.

## Task start

The following surfaces share `start_task_from_definition`:

- `POST /tasks/start`
- operator MCP `start_task`
- `autoclaw task-compose start --file ...`

Task start validates task-root bindings, compiles and pins definitions, creates the task, flow, root assignment, root attempt, and durable flow-start source in one transaction, then commits.

After commit, it publishes independent runtime and support-projection wakeups and returns the task identity and manifest reference. It does not wait for the first provider start or provider output. The flow-start handler prepares the request pair and opens the root dispatch from committed truth.

## Evidence

- `apps/api/src/autoclaw/definitions/registry/`
- `apps/api/src/autoclaw/definitions/authoring/`
- `apps/api/src/autoclaw/definitions/compiler/`
- `apps/api/src/autoclaw/definitions/registry/task_start.py`
- `apps/api/src/autoclaw/runtime/launch/`
- `apps/api/tests/integration/definition_registry/`
- `apps/api/tests/e2e/workflows/test_registry_start_provider.py`

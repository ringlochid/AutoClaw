# Task start failures

Status: Reference

Last verified: 2026-06-28

Use this page when `autoclaw task-compose start --file ...` or `POST /tasks/start` fails before useful runtime work begins.

## Start with the launch input

Check:

- the task-compose file exists on the AutoClaw host
- `task.key`, `task.title`, `task.summary`, and `task.instruction` are present
- `workflow.key` names a current workflow definition in the registry
- `roots.workspace` and `roots.context` use supported binding modes

Supported root binding modes are:

- `ensure_task_default`
- `ensure_host_path`
- `use_existing_host`

## Workflow key is missing

Check current workflow definitions through the registry read surfaces:

```bash
curl -sS -H "X-AutoClaw-API-Key: <redacted>" \
  "http://127.0.0.1:18125/definitions/workflows"
```

Operator MCP can also use `search_definitions` and `get_definition`.

Read current definitions through the registry surfaces rather than reading repo files as live truth.

Fix:

- import the missing role, policy, or workflow definition
- use `--overwrite allow_new_revision` only when you intentionally want changed local content to become a new current revision
- run `autoclaw configure --section definitions` when packaged seed defaults need to be reseeded

## YAML shape is invalid

Use the shipped schema contract:

- role YAML owns reusable role behavior
- policy YAML owns budgets, guardrails, and capabilities
- workflow YAML owns the node tree, consumes, produces, and criteria
- task-compose owns one launch request and root bindings

Fix:

- remove stale fields such as `inputs`, `edges`, or `skill_refs`
- keep root node id as `root`
- ensure consumed artifact and criteria slots resolve to declared providers
- ensure role and policy ids exist in current registry truth

Reference: [Definition and task-compose YAML contract](../reference/api/definition-and-task-compose-yaml-contract.md).

## Doctor is healthy but task start still fails

Likely causes:

- task-compose selected an unavailable workflow key
- workflow validation fails against current role or policy registry truth
- a root binding points at a missing existing host path
- the API is healthy but not ready against the configured database

Check:

```bash
autoclaw doctor --json
curl http://127.0.0.1:18125/readyz
```

Then inspect the task-start error. Schema and registry errors are usually more precise than the top-level symptom.

## Related pages

- [Write a task-compose file](../guides/write-a-task-compose.md)
- [Write a role](../guides/write-a-role.md)
- [Write a policy](../guides/write-a-policy.md)
- [Write a workflow](../guides/write-a-workflow.md)
- [Definition registry and publish lifecycle](../reference/api/definition-registry-and-publish-lifecycle.md)

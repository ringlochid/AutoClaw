# Write a task-compose file

Use task-compose when you are ready to launch one concrete task from reusable AutoClaw definitions.

Task-compose is not where reusable behavior lives. Put durable behavior in roles, policies, and workflows. Put the concrete launch request, selected workflow, and any explicit root bindings in task-compose.

## Minimal shape

A task-compose file needs a task and a workflow. Roots are optional; omitted roots default to task-owned `workspace` and `context` paths.

```yaml
task:
    key: first-research-brief
    title: First research brief
    summary: Turn one topic into a polished source-grounded idea brief.
    instruction: >-
      Research local-first orchestration for delegated AI work and produce a concise idea brief with evidence, tradeoffs, and a recommended next step.
workflow:
    key: topic-research-brief
```

Use this shape for first-run work and isolated local experiments.

## Choose the workflow

Set `workflow.key` to the reusable workflow you want to launch.

Use [write a workflow](write-a-workflow.md) when the shipped examples do not match your automation. `workflow.key` can point at any seeded or uploaded workflow definition.

## Write the task summary

`task.summary` should summarize the concrete run.

Good:

```yaml
summary: Fix the invoice import date parsing regression in the local repo.
```

Too reusable:

```yaml
summary: Always research, implement, verify, review, and release carefully.
```

Reusable behavior belongs in definitions, not task-compose.

## Write the task instruction

Keep task instruction concrete and scoped:

- say what this run should accomplish
- name important constraints or deferrals
- name local context the reusable workflow cannot know
- avoid reusable role or policy behavior
- avoid secrets and private credentials

Good:

```yaml
instruction: >-
  Reproduce the reported invoice date parsing regression, fix the narrow cause, add regression proof, and do not change unrelated import behavior.
```

If the same instruction should apply to many tasks, move it into a role, policy, or workflow instead.

## Bind roots

Task-compose root bindings decide whether AutoClaw creates task-local paths or binds directly to existing host paths. If you omit `roots`, AutoClaw uses task-owned defaults.

### Default task-local binding

Use `ensure_task_default` when you want AutoClaw to create task-owned roots:

```yaml
roots:
    workspace:
        mode: ensure_task_default
    context:
        mode: ensure_task_default
```

This is the cleanest first-run lane because every task gets isolated roots.

### Explicit host-path binding

Use `ensure_host_path` when you want a specific host path and you are okay with AutoClaw creating it if needed:

```yaml
roots:
    workspace:
        mode: ensure_host_path
        host_path: /home/ubuntu/workspaces/autoclaw-task
    context:
        mode: ensure_task_default
```

### Existing host-path binding

Use `use_existing_host` when the path must already exist:

```yaml
roots:
    workspace:
        mode: use_existing_host
        host_path: /home/ubuntu/projects/real-repo
    context:
        mode: use_existing_host
        host_path: /home/ubuntu/projects/real-repo/docs
```

Use this for real project work where the task should operate against an existing repository or context material.

## Start the task

Run:

```bash
autoclaw task-compose start --file ./task-compose.yaml --json
```

## Checklist

Before launch, check:

- `workflow.key` names the intended reusable workflow
- task summary and instruction are concrete to this run
- secrets are not copied into task-compose
- omitted roots or explicit root bindings match the intended workspace and context
- reusable behavior is not duplicated from role, policy, or workflow docs

## Related pages

- [Design workflows and instructions](design-workflows-and-instructions.md)
- [Write layered instructions](write-layered-instructions.md)
- [Minimal task-compose reference](../reference/definitions/task-compose/minimal.md)
- [Bound workspace task-compose reference](../reference/definitions/task-compose/bound-workspace.md)
- [Copied e2e workspace task-compose reference](../reference/definitions/task-compose/copied-e2e-workspace.md)

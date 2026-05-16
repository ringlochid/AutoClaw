# Create a definition and run a task

Status: Target

This tutorial walks through the intended definition-to-task path under the redesign.

## Walkthrough

### 1. Author the workflow definition

Place the definition files you want to import in the current working directory.

```text
root_planning_lead.yaml
standard-root-planning.yaml
auth-refresh-bugfix.yaml
```

Start with one authored tree that uses only:

- `children`
- `consumes`
- `produces`
- `criteria`

Minimal example:

```yaml
kind: workflow
id: auth-refresh-bugfix
description: Fix the auth refresh regression and release only after review.
root:
  id: root
  role: root_planning_lead
  policy: standard-root-planning
  description: Coordinate the flow and decide final closure.
  children:
    - id: implementation_subtree
      role: planning_lead
      policy: standard-parent-planning
      description: Coordinate investigation, implementation, and review.
      children:
        - id: investigate_issue
          role: researcher
          description: Gather findings.
          produces:
            artifacts:
              - slot: findings_report
                description: Findings for downstream implementation.
        - id: implement_change
          role: engineer
          description: Implement the scoped fix.
          consumes:
            artifacts:
              - slot: findings_report
          produces:
            artifacts:
              - slot: change_patch
                description: Patch for the scoped fix.
```

Upload those local definition files through the shipped guarded definition surface. On the current repo state that means `POST /definitions` or the operator MCP parity tool `upload_definition(...)`.

### 2. What guarded definition upload does

Guarded definition upload is the canonical ingest front door for this walkthrough on the current shipped subset.

It uploads the accepted definitions:

- the workflow definition
- any referenced roles
- any referenced policies

The important check is not just YAML shape. Guarded upload also validates typed dependency legality, uniqueness rules, and role / policy compatibility. Task start validates again against current truth before runtime materialization commits.

### 3. Author task compose

```yaml
task:
  key: auth-refresh-hardening
  title: Harden auth refresh flow
  summary: Investigate and fix the auth refresh regression.
workflow:
  key: auth-refresh-bugfix
roots:
  workspace:
    mode: ensure_task_default
  context:
    mode: ensure_task_default
```

### 4. Start the task

Use the public `POST /tasks/start` surface or the operator MCP parity tool `start_task(...)`. Successful start creates the task root, materializes the initial runtime tree, and opens the first `dispatch`.

### 5. Read the deterministic runtime files

Inspect:

- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.md`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
- `outputs/artifacts/...` for current durable outputs and evidence
- optional `tmp/transfers/...` only when surfaced through `transient_refs`

### 6. Follow the runtime loop

Read the model in this order:

1. manifest = current workflow structure
2. assignment = current mission contract
3. latest checkpoint = what happened and what should happen next
4. artifacts = durable evidence or produced output

That is the current live model. Do not look for old handoff packets, result records, or gate bundles.

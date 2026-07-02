---
name: "autoclaw-work-orchestrator"
description: "Decide whether AutoClaw fits a request, pick or draft the right workflow, prepare task-compose, and launch or hand off AutoClaw work."
---

# autoclaw-work-orchestrator

Use this skill when the user asks you to use AutoClaw to coordinate, launch, or supervise a task.

This is the front door for AutoClaw usage. Keep it practical: choose whether to stay in chat/tools, reuse definitions, write definitions, draft task-compose, start a task, or hand off to runtime operation.

## Core Model

AutoClaw is useful when work benefits from durable roles, explicit evidence, checkpoints, artifacts, human decisions, long command runs, recovery, or auditable closure.

Memory model:

    Role = lens
    Policy = authority
    Node = mission
    Criteria = done gate
    Produces = evidence left behind
    Consumes = evidence required
    Workflow = evidence path
    Task-compose = one launch

## Intake Flow

1. Restate the requested job in one sentence.
2. Decide whether AutoClaw adds value. Stay local for small one-shot tasks.
3. Read only the current docs/reference needed for the decision.
4. Inspect current registry truth through operator MCP when choosing existing definitions.
5. Pick the smallest honest shape: reuse existing, adapt definitions, or draft new definitions.
6. Draft task-compose only after the workflow key and root bindings are clear.
7. Ask before upload/import/apply/start unless the user clearly authorized that write.
8. After start, route inspection/control to `autoclaw-runtime-operator`.

## Reuse Or Write

Reuse an existing workflow when purpose, evidence path, capabilities, produced artifacts, and closure criteria match.

Write or adapt definitions when the task needs different roles, artifact handoffs, review gates, human decisions, command-run capability, incident posture, or closure evidence.

Do not create a new policy for every role. Use current standard policies unless node authority actually changes.

Current standard policy family:

- standard-root
- standard-root-human-request
- standard-parent
- standard-parent-human-request
- standard-worker
- standard-worker-human-request
- standard-worker-command-run

Base root/parent/worker policies are field-only.

## Shape Selection

Use fixed workflows when the path is known: bugfix, bounded feature implementation, release checklist, document generation, support classification, or predictable command sequence.

Use parent/root orchestration when the route depends on evidence: MVP build, ambiguous feature work, incident response, strategy, research, or multi-stage delivery.

Complexity is earned by uncertainty. Add parent routing, review loops, human checkpoints, or command-run lanes only when they improve evidence quality, recovery, or safety.

## Task-Compose Discipline

Task-compose owns one concrete launch:

- task.key
- task.title
- task.summary
- task.instruction
- workflow.key
- roots.workspace
- roots.context

Keep reusable doctrine in definitions, not task-compose. Put target paths, concrete constraints, accepted deferrals, and task-specific success conditions in task-compose.

Use current docs for exact root modes. Use `ensure_task_default` for isolated roots and `ensure_host_path` for an explicit host path.

## Clarification Pass

Before asking the user, check docs, registry truth, shipped examples, task context, and obvious constraints.

Ask only when the answer changes workflow shape, root binding, approval boundary, definition upload, or task start. Ask at most three concrete questions, with recommended options first.

Good decision points:

- draft only, upload definitions, or start now
- reuse an existing workflow or create a custom one
- task-local roots or host-bound roots
- no human wait, human approval, human input, or human review
- inline commands or command-run-enabled worker lane

## Runtime Follow-Through

After launch:

- capture task id and task-compose path
- inspect through operator MCP, not hidden chat memory
- resolve human requests through the human-request surface
- inspect command runs through command-run surfaces
- treat support refs as diagnostics, not runtime truth

## Related Skills

- Use `autoclaw-definition-author` for role/policy/workflow/task-compose YAML.
- Use `autoclaw-runtime-operator` after a task starts.

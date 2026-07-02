# Start a task

This tutorial starts one local task with the shipped topic-research workflow. The first task is intentionally small: one root delegates one researcher, then AutoClaw records the assignment, checkpoint, and artifact evidence.

## Before you start

Make sure the local install and OpenClaw integration are healthy:

```bash
autoclaw onboard
autoclaw doctor
autoclaw openclaw check
```

The shipped onboarding path seeds the packaged definition fixtures, including the topic-research workflow used here.

## Create `task-compose.yaml`

Create this file in an empty working directory:

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

This task-compose file does three things:

- describes one task
- selects the `topic-research-brief` workflow
- relies on the default task-owned `workspace` and `context` roots

## Start the task

Run:

```bash
autoclaw task-compose start --file ./task-compose.yaml --json
```

The command reads one local file and starts the same task body that the public task-start API accepts.

## What success looks like

- the command returns a task id
- AutoClaw reports the generated task-root path
- `_runtime/workflow-manifest.md` exists under that path
- the first assignment surface is inspectable
- checkpoint and artifact surfaces become inspectable as the researcher works
- the final artifact includes a polished `research_brief.md`

## Next step

Use [inspect a task](inspect-a-task.md) to read the generated runtime surfaces and operator-facing outputs.

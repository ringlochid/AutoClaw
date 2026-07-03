# Start a task

This tutorial starts one local task with the shipped topic-research workflow. The first task is intentionally small: one root delegates one researcher, then AutoClaw records the assignment, checkpoint, and research artifact.

## Before you start

Make sure the local install and OpenClaw integration are healthy:

```bash
autoclaw onboard
autoclaw doctor
autoclaw openclaw check
```

The shipped onboarding path seeds the packaged definition fixtures, including the topic-research workflow used here.

Find the local console port:

```bash
autoclaw config show --json
```

Open `http://127.0.0.1:<server.port>/task-start`. The default port is `18125`.

## Start from the console

In Task Start:

- select `topic-research-brief`
- use a short task key, title, and summary
- enter the research topic in the task instruction
- start the task

Open the returned task detail page at:

```text
http://127.0.0.1:<server.port>/tasks/<task_id>
```

## Start from a task-compose file

Create `task-compose.yaml` in an empty working directory:

```yaml
task:
    key: first-research-brief
    title: First research brief
    summary: Turn one topic into one concise Markdown research brief.
    instruction: >-
      Research local-first orchestration for delegated AI work and produce one concise Markdown brief with evidence, tradeoffs, and a recommended next step.
workflow:
    key: topic-research-brief
```

This task-compose file does three things:

- describes one task
- selects the `topic-research-brief` workflow
- relies on the default task-owned `workspace` and `context` directories

## Launch the task-compose file

Run:

```bash
autoclaw task-compose start --file ./task-compose.yaml --json
```

This starts a task from the YAML file instead of the Task Start page.

## What success looks like

- AutoClaw returns a task id
- the task detail page shows the workflow graph and event stream
- the run advances through `root` and `research_topic`
- the final output is `workspace/research_brief.md`
- the `research_brief` artifact is published

## Next step

Use [inspect a task](inspect-a-task.md) to read task detail, data-dir paths, and diagnostic files.

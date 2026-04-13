# System Overview

## What AutoClaw is

AutoClaw is a framework for **long-running adaptive workflows** built on top of OpenClaw.

Users define workflow pieces.
AutoClaw compiles those definitions into a normalized executable plan.
The runtime executes that plan through parent supervision, child loops, checkpoints, approvals, and controlled replanning.

## What AutoClaw is not

AutoClaw is not a hard real-time controller.
It is not meant to replace a cheap high-throughput DAG runner for massive fixed batch graphs.

Best fit:
- coding / debugging / repair loops
- research / synthesis / reporting workflows
- long-running review / approval / compliance work
- staged idea-to-demo / MVP-building workflows

Weaker fit:
- hard real-time control
- giant static batch compute DAGs
- tiny one-shot tasks that do not need supervision

## Default runtime shape

The minimum required kernel is:

```text
source defs
-> compile / normalize
-> parent supervisor
-> main execution loop child
-> light review if needed
-> sync / report
```

This is the normal path.
Bigger trees are extensions, not the default assumption for every run.

## Escalation ladder

Expand only as needed:

1. add an approval gate if the next action is risky or irreversible
2. add one specialist reviewer if a clear risk domain appears
3. add a subtree if the task genuinely branches into separate concerns
4. add a committee only when one reviewer is not enough

## High-level layers

AutoClaw has five conceptual layers:

1. source definitions
2. compiler / normalizer
3. compiled plan
4. runtime instance
5. event / history / approval trail

## Product stance

AutoClaw should feel like a framework, not a hardcoded workflow app.
But the kernel must stay small enough that the framework remains understandable.

Early-phase rule:
prove one real default path well before trying to generalize everything.

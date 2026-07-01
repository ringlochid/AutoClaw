# Minimal task-compose guide example

Use this example when you want AutoClaw to use default task-owned roots and prove the smallest launch path.

This example teaches:

- omitted `roots` defaults to task-owned `workspace` and `context` paths
- the task body names the concrete launch while the workflow key picks the reusable workflow
- the wrapper reads one local file and submits the same backend task-start body as the canonical route

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

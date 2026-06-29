# AutoClaw Frontend Launch Plan

Status: reference pointer only.

`references/frontend` is an ignored project reference area. Keep reusable
AutoClaw definition drafts and task-compose launch drafts in Orin's workspace
curation area instead:

```text
/home/ubuntu/.openclaw/workspaces/orin/autoclaw/drafts/
```

Current frontend draft pack:

```text
/home/ubuntu/.openclaw/workspaces/orin/autoclaw/drafts/frontend-console-v2/README.md
/home/ubuntu/.openclaw/workspaces/orin/autoclaw/drafts/workflows/frontend_console_full_delivery.yaml
/home/ubuntu/.openclaw/workspaces/orin/autoclaw/drafts/task-compose/autoclaw_console_frontend_full_delivery/full-delivery.task-compose.yaml
```

Use the full-delivery compose when the goal is one AutoClaw task from audit and
contract docs through implementation, validation, review, and closure.

Use named standalone fallback composes from the same Orin draft pack only when a
slice genuinely needs to be split out. Do not use numeric `00..99` launch
ordering for this frontend program.

The task still binds:

- workspace: `/home/ubuntu/leo/projects/autoclaw`
- context/evidence: `/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/<purpose>`

The workflow should write comprehensive plans under `references/frontend` and
locked frontend contracts under `docs-internal/design/v2/console`.

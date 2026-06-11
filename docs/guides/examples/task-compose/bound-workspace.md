# Bound workspace task-compose guide example

Status: Reference

Use this example when a task should target a real host path instead of an AutoClaw-created task-local root.

This example teaches:

- `ensure_host_path` binds to an explicit host path and creates it if needed
- you can mix host-bound workspace roots with task-local context roots
- launch input is where host placement becomes concrete

For the exact YAML, use the [bound workspace task-compose reference example](../../../reference/definitions/task-compose/bound-workspace.md).

# Personas and core surfaces

Status: Reference

This page describes AutoClaw in product terms, not implementation-contract terms.

## Personas

- workflow author: defines reusable workflow, role, and policy inputs
- task launcher: starts concrete work from a task compose or equivalent start surface
- operator: inspects task runtime, pauses or continues whole-task execution, reads watchdog state, and reviews release health

## Core surfaces

- authoring surface: reusable workflow, role, policy, and task-compose inputs
- runtime surface: tasks, flows, attempts, manifests, artifacts, and observability readbacks
- operator surface: flow inspect, control, audit, review, and recovery
- worker surface: OpenClaw-backed delegated execution with continuity and watchdog rules

## Related reference

- [API reference](../reference/api/README.md)
- [CLI reference](../reference/cli/README.md)
- [Operator reference](../reference/operator/README.md)

# 01 — Phase 1: Kernel and Data Model

## Goal

Prove the minimum end-to-end AutoClaw kernel.

## In Scope

- initial registry/runtime SQLAlchemy models
- initial Alembic migration
- `task/run/attempt/flow` runtime chain
- one default workflow pack (`default-bugfix`)
- typed checkpoints and approval records
- minimal API to create and inspect runs

## Out of Scope

- advanced hierarchy
- complex policy DSL
- partial recompile adoption
- rich operator console
- broad workflow-pack library

## Deliverables

- working model set for registry + runtime core
- first migration
- definition import bootstrap
- minimal run creation path
- persisted checkpoint path

## Data Model Changes

Minimum target tables:

- `role_definitions`, `role_versions`
- `policy_definitions`, `policy_versions`
- `workflow_definitions`, `workflow_versions`
- `skill_registry`, `skill_versions`
- `tasks`, `runs`, `attempts`
- `compiled_plans`, `compiled_plan_nodes`, `compiled_plan_edges`
- `flow_nodes`, `node_checkpoints`, `approvals`

## API / Runtime Changes

- create task/run
- inspect run
- list checkpoints
- basic approval action placeholder

## Tests / Verification

- model import works
- migration applies cleanly
- health/ready endpoints work
- one run can be created from a published workflow
- one checkpoint can be recorded and read back

## Exit Criteria

Phase 1 is done when we can:

1. publish one workflow definition set
2. compile it into a normalized plan
3. create a run and instantiate a flow
4. record a checkpoint
5. inspect the run via API

## Deferred Follow-ups

- plan patch revisions
- watchdog states
- deep operator graph views

## Risks

- too much schema too early
- registry/runtime boundary blur
- route handlers taking on business logic

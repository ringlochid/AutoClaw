# Onboard locally

Status: Target

This tutorial walks through the intended local onboarding story.

## Walkthrough

1. Install the package and confirm the CLI is available.
2. Run `autoclaw doctor` to confirm local config, database wiring, and service dependencies.
3. Read the current owner docs in this order:
   - workflow definition schema
   - task compose schema
   - prompt contract
   - runtime boundary and controller loop contract
4. Import and upload one small workflow plus any referenced role/policy definitions.
5. Author one small task compose file for local launch.
6. Start the task with `autoclaw task-compose start --file <task_compose_path>`.
7. Open the generated task root and inspect:
   - `_runtime/workflow-manifest.md`
   - `_runtime/attempts/<attempt_id>/assignment.md`
   - `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
   - `_runtime/dispatch/<dispatch_id>/delivery-state.json`
   - `_runtime/dispatch/<dispatch_id>/continuity-state.json`
   - `_runtime/dispatch/<dispatch_id>/watchdog-state.json` Treat the three dispatch-local state files as observability projections only. They are useful for transport/recovery debugging, but they are not ordinary task truth.
8. Follow the first dispatch and verify that the system behaves through assignments, checkpoints, and durable artifacts rather than old handoff or gate-era surfaces.

For local definition authoring:

- use `autoclaw definitions import --file <definition_path>` for one explicit file
- or run `autoclaw definitions import` from the directory that holds the top-level definition YAML files you want to import
- DB-backed registry truth becomes authoritative after successful import

## Local onboarding goal

At the end of onboarding, a reader should be able to answer:

- where authored workflow structure lives
- where current runtime structure lives
- where the current assignment lives
- where the latest checkpoint lives
- where durable evidence lives
- which generated files are observability only

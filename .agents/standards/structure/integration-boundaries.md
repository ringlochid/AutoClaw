# Integration boundary standard

Status: Reference

Use this guide when a change touches seams between backend layers, OpenClaw integration, CLI surfaces, operator/plugin lanes, or support-state readbacks.

## Core boundary rules

- keep controller-owned truth separate from provider behavior and support readbacks
- keep public surfaces separate from internal implementation helpers
- keep phase ownership explicit when several subsystems meet at one seam
- do not move business rules into adapters, routes, or support-state readers just because that is where the data arrives

## Backend boundaries

- `api/**` owns HTTP parsing, dependency wiring, service calls, and HTTP translation only
- `services/**` owns orchestration, transaction-aware behavior, and domain flows
- `runtime/**` owns runtime records, manifests, task-root materialization, prompt assembly, and controller-loop behavior named by canon
- `compiler/**` owns authoring-model compilation and legality work
- `registry/**` owns definition lookup and revision truth
- `db/**` owns persistence models and DB access surfaces
- `schemas/**` owns explicit contract models
- `cli/**` and `cli_commands/**` own public CLI noun-family behavior, not backend business logic

## OpenClaw and support-state boundaries

- gateway/session continuity questions route to the Phase 4A owner docs
- watchdog, operator/plugin lanes, and support-state readbacks route to the Phase 4B owner docs
- session-authority simplification and same-session redispatch cleanup route to the Phase 4.5 owner docs
- public CLI/API ingest and definition-registry surfaces route to the Phase 5A owner docs
- install, onboarding, reset, package, and docs cutover route to the Phase 5B owner docs

## Support-state rules

- support-state files explain committed truth; they do not become committed truth
- do not read support snapshots as the authority when controller-owned DB/runtime records own that answer
- do not let diagnostics-only paths become the steady-state business path

## Adapter and boundary discipline

- keep adapters thin and named for the external system they bridge
- do not hide controller decisions inside transport or adapter helpers
- when an external integration forces dialect- or provider-specific behavior, isolate it behind a narrow persistence or adapter boundary
- when a seam crosses ownership, stop and confirm the phase-local owner before widening the edit

## Review checklist

- which layer owns the behavior that changed
- did the diff move logic toward the correct owner or away from it
- did a support or transport surface start acting like the system of record
- did the change widen into another phase or public surface without explicit approval

# Current worker prompt delivery and OpenClaw bridge envelope

Status: Current

Last verified: 2026-04-25

This page owns the current worker-delivery shape:

- rendered OpenClaw bridge text
- lineage-gated worker-bundle reads

This is the canonical current prompt-delivery contract page.

For the exact current bootstrap and execution bridge strings, see `current-openclaw-bridge-prompt-strings.md`.

For transport/session details that are specific to the OpenClaw bridge, see `../architecture/openclaw-dispatch-and-session-contract.md`.

## Ownership map

Current prompt-related ownership is:

| Concern                     | Current owner                                                                                                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| dispatch text renderer      | `autoclaw-main/apps/api/app/services/openclaw_bridge.py::_build_dispatch_input()`                                                                                               |
| dispatch selection and send | `autoclaw-main/apps/api/app/services/openclaw_bridge.py::prepare_flow_dispatch_to_openclaw()` and `dispatch_flow_to_openclaw()`                                                 |
| transport wrapper           | `autoclaw-main/apps/api/app/integrations/openclaw.py::OpenClawRequest` and `create_response()`                                                                                  |
| manifest source             | `autoclaw-main/apps/api/app/runtime/dispatcher.py::project_context_manifest()`                                                                                                  |
| worker-bundle source        | `autoclaw-main/apps/api/app/runtime/read_models.py::get_flow_worker_bundle_snapshot()` and `autoclaw-main/apps/api/app/api/presenters/runtime.py::to_flow_worker_bundle_read()` |
| compiler-fed prompt inputs  | `autoclaw-main/apps/api/app/compiler/resolve.py::_effective_description()` and `autoclaw-main/apps/api/app/compiler/normalize.py::normalize_resolved_workflow()`                |
| watchdog wording override   | `autoclaw-main/apps/api/app/runtime/watchdog.py::recover_flow_watchdog()`                                                                                                       |

This page owns the current prompt-source map and worker-delivery shape only. It does not define the redesign target prompt canon.

## Current shape

Current worker input is split into two pieces:

- a rendered OpenClaw dispatch text envelope
- structured runtime reads from the worker-bundle surface

Current AutoClaw does not yet have the redesign's explicit controller-owned prompt bundle contract.

## Dispatch text envelope

The dispatch text is built in `autoclaw-main/apps/api/app/services/openclaw_bridge.py`.

Current phases:

- bootstrap dispatch
- execution dispatch

Current wording overlays:

- optional `instruction_override` appended as `Operator guidance: ...`

Bootstrap dispatch includes:

- flow, node, attempt, and session identifiers
- projected manifest identifiers and payload
- the instruction to call `ack_context_manifest` first
- the exact lineage values the worker must reuse in later callbacks

Execution dispatch includes:

- a continuation instruction for the current node attempt
- the next suggested checkpoint sequence
- the latest acknowledged manifest payload
- strict instructions to keep using the latest acknowledged lineage values
- optional operator guidance when the controller or watchdog provides it

## Manifest-lineage rule

Current delegated execution is manifest-lineage-sensitive.

Bootstrap rule:

1. the worker acknowledges the projected manifest first
2. later callbacks and bundle reads must reuse the exact `node_session_key`, `manifest_id`, `manifest_hash`, and `ack_checkpoint_id` from the latest acknowledged manifest

This is why the current worker prompt repeatedly tells the worker not to reuse stale lineage values from older checkpoints or older manifests.

## Current OpenClaw request mapping

Current OpenClaw request payload shape allows:

- `input`
- `instructions`
- `previous_response_id`

Current bridge behavior is:

- delegated worker text is sent through `input`
- top-level `instructions` is not currently used by the bridge
- `previous_response_id` is not currently used by the bridge
- current prompt delivery is full-text resend, not compact continuation
- current runtime does not persist a prompt artifact or prompt hash per dispatch

## Worker-bundle pull

The worker uses the current controller-private worker-bundle route for structured runtime context:

- `/internal/flows/{flow_id}/worker-bundle`

Current worker-bundle access is not an open read. It is current/shipped lineage-gated behavior, not the redesign's target callback or observability lane model.

Current binding gate requires:

- `manifest_id`
- `manifest_hash`
- `node_session_key`

And `ack_checkpoint_id` matters for acknowledged execution binding.

The current worker bundle includes:

- flow inspect view
- task record
- compiled plan
- current node, attempt, session, and manifest
- task compose
- recent checkpoints
- approvals visible to the current attempt
- recent manifests
- visible context items
- recent audit events

This is the current structured side of the worker input.

## Minimal example

```text
dispatch text
  -> bootstrap instructions
  -> ack the manifest first
  -> keep exact lineage values

worker bundle
  -> current manifest
  -> current attempt
  -> requires manifest/session binding
  -> recent checkpoints
  -> visible context and audit events
```

## Expanded example

```text
bootstrap dispatch
  -> "AutoClaw bootstrap execution started."
  -> flow/node/attempt/session ids
  -> projected manifest payload
  -> first action must be ack_context_manifest

execution dispatch
  -> "Continue AutoClaw node execution."
  -> next checkpoint sequence
  -> latest acknowledged manifest payload
  -> exact manifest/session/checkpoint lineage reuse rule

worker bundle pull
  -> flow inspect
  -> task
  -> compiled plan
  -> current node/attempt/session/manifest
  -> manifest/session binding gate
  -> approvals
  -> visible context items
  -> recent audit events
```

## Current limits

- current worker-facing text has only two families: `bootstrap` and `execution`
- current wording overlay has only one explicit dynamic append: `instruction_override`
- current dispatch is OpenClaw-shaped
- current prompt delivery is not yet the redesign's canonical OpenClaw-first markdown prompt contract
- current worker input is not yet the redesign's explicit canonical-markdown prompt contract
- current runtime does not yet define a persisted prompt artifact for every dispatch
- current runtime does not yet define strict ordered markdown sections, fresh redispatch renders, or the target raw prompt-audit surface
- current worker-bundle access is lineage-gated rather than open by default

## Target contrast

The target redesign differs in three main ways:

- every dispatch gets a fresh canonical markdown prompt rather than ad hoc transport-shaped text
- the rendered prompt is persisted as an internal audit artifact with hash and lineage metadata
- the target prompt contract defines a stricter source precedence, excerpt policy, and bundle-access rule

## Evidence

- inspected code in `autoclaw-main/apps/api/app/services/openclaw_bridge.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/flows.py`
- inspected code in `autoclaw-main/apps/api/app/api/presenters/runtime.py`
- inspected code in `autoclaw-main/apps/api/app/schemas/runtime.py`
- inspected code in `autoclaw-main/apps/api/app/integrations/openclaw.py`

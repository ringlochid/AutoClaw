# Current OpenClaw and bridge-plugin baseline

Status: Current

Last verified: 2026-04-26

Current delegated execution is OpenClaw-backed, manifest-first, and lane-specific at the plugin boundary.

## Keywords

- current bridge plugin
- request_approval
- operatorQueries
- registryWrites
- raw operator query tools
- skill writes

## Current transport

Current code dispatches delegated work through:

- `autoclaw-main/apps/api/app/integrations/openclaw.py`
- `autoclaw-main/apps/api/app/services/openclaw_bridge.py`
- `autoclaw-main/apps/api/app/api/routes/flows.py`

Current transport facts:

- Gateway `POST /v1/responses`
- stable session routing through `x-openclaw-session-key`
- bootstrap instructions require `ack_context_manifest` before normal execution
- callback lineage uses manifest/session values from the envelope
- manifest rows remain controller truth; the bridge does not promote manifest files into runtime authority

Target contrast:

- current shipped HTTP dispatch is implementation truth only
- target controlled runtime execution should switch its canonical dispatch control path to Gateway WS RPC start/wait/abort surfaces

## Current bridge-plugin lanes

The current bridge plugin does not expose one undifferentiated tool surface.

Worker-lane defaults:

- `record_checkpoint`
- `ack_context_manifest`
- `request_approval`
- `get_worker_bundle`
- `publish_context_item`
- `request_replan`

Optional operator-query tools behind `capabilities.operatorQueries=true`:

- `get_flow_operator`
- `get_flow_runtime_slice`
- `get_flow_timeline_slice`
- `get_flow_audit`
- registry query and validation helpers

Optional registry-write tools behind `capabilities.registryWrites=true`:

- `put_definition_draft`
- `publish_definition_version`
- `put_skill_draft`
- `publish_skill_version`

These are shipped current plugin facts only. They do not define the target redesign plugin contract.

## Evidence

Inspected code:

- `../../../autoclaw-bridge-plugin-main/README.md`
- `autoclaw-bridge-plugin-main/src/plugin-tools.ts`
- `autoclaw-bridge-plugin-main/src/index.ts`

## Safe wording rule

Current docs must not imply that runtime-slice, timeline-slice, or audit reads are default worker capabilities. In the current plugin contract, they are operator-query capabilities.

Worker-lane defaults do not make the delegated worker an operator.

Current docs must also not imply that current skill draft or publish helpers are standard target operator/plugin capability.

## Redesign pointer

For the target OpenClaw-first provider/worker/operator split, see [Provider, worker, and operator boundary](../../redesign/architecture/provider-worker-and-operator-boundary.md), [OpenClaw worker and gateway contract](../../redesign/architecture/openclaw-worker-and-gateway-contract.md), [Plugin tool reference](../../redesign/interfaces/plugin-tool-reference.md), and [Guarded registry and runtime writes](../../redesign/interfaces/guarded-registry-and-runtime-writes.md).

For the current manifest model, see [Manifest projection and acknowledgement](manifest-projection-and-acknowledgement.md).

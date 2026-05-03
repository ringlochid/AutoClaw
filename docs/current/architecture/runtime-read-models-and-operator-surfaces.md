# Current runtime read models and operator surfaces

Status: Current

Last verified: 2026-04-26

This page defines the current read-model and operator-query surfaces for flows, runtime inspection, and registry visibility.

Operator here means a trusted runtime-steering principal, not a worker and not the controller itself.

## Keywords

- current operator snapshot
- runtime slice
- timeline slice
- flow audit
- worker bundle
- raw query names
- operator trace target

## Current flow/runtime read models

Current flow read surfaces include:

- flow operator snapshot
- flow runtime slice
- flow timeline slice
- flow audit
- worker bundle
- flow checkpoints
- current and recent manifests through audit and worker-bundle views

Current route surfaces:

- current public/operator: `/flows/{flow_id}/operator`
- current controller-private: `/internal/flows/{flow_id}/runtime-slice`
- current controller-private: `/internal/flows/{flow_id}/timeline-slice`
- current controller-private: `/internal/flows/{flow_id}/audit`
- current controller-private: `/internal/flows/{flow_id}/worker-bundle`
- current controller-private: `/internal/flows/{flow_id}/checkpoints`
- current controller-private: `/internal/flows/{flow_id}/replans`

## Current registry/operator query surfaces

Current powerful operator-query surfaces include:

- registry snapshot
- definition version listing
- workflow validation preview

Current route surfaces:

- current controller-private: `/internal/registry/snapshot`
- current public/internal: `/{definition_kind}/{key}/versions`
- current public: `/registry/workflows/validate`

## Current read-model rule

Read models are not runtime truth. They are assembled views over controller-owned runtime records.

That means:

- flow operator view is a summary surface, not the authority
- runtime slice is a scoped read model, not the authority
- timeline slice is a reconstructed history surface, not the authority
- flow audit is a derived drilldown surface, not the authority
- worker bundle is a structured delegated read surface, not the authority

Current implementation also does not yet expose the redesign's dedicated persisted boundary-log layer. Monitoring and drilldown use assembled timeline and audit views over the same controller-owned records.

Current implementation also does not expose a dedicated standalone manifest-query surface. Manifest inspection is mainly available through the worker bundle and flow audit shapes.

Current implementation limitation:

- controller-owned OpenClaw dispatch rows and provider-hint event rows now exist
- current operator-facing read models expose only a summary mirror through node or flow read state
- current audit/runtime/timeline surfaces do not yet provide first-class dispatch-event history drilldown
- full operator traceability across dispatch/provider-hint history remains a target capability, not a current delivered read surface

## Current naming vs target naming

Current deeper plugin or support-tooling reads use raw names such as:

- `get_flow_operator`
- `get_flow_runtime_slice`
- `get_flow_timeline_slice`
- `get_flow_audit`

The target redesign does not keep those raw names as the standard operator-plugin contract.

The target standard operator-facing bundle contract is documented as `get_operator_snapshot(...)` and `get_operator_trace(...)` in [Plugin tool reference](../../redesign/interfaces/plugin-tool-reference.md).

Important current role rule:

- public operator snapshot is the standard operator summary surface
- deeper internal slices may be used by trusted operator tooling
- those deeper query surfaces do not make the delegated worker an operator
- the redesign later separates external `/operator/...` reads from controller-private `/callback/...` and `/observability/...` lanes

## Evidence

- inspected code in `autoclaw-main/apps/api/app/runtime/read_models.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/flows.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/registry.py`

## Related current pages

- for current runtime truth and controller looping, see [Runtime control plane](runtime-control-plane.md)
- for current OpenClaw dispatch/session binding, see [OpenClaw dispatch and session contract](openclaw-dispatch-and-session-contract.md)
- for current watchdog and runtime monitoring, see [Watchdog and runtime monitoring](watchdog-and-runtime-monitoring.md)
- for current prompt delivery, see [Prompt layer and worker delivery](../interfaces/prompt-layer-and-worker-delivery.md)
- for current manifest projection and acknowledgement, see [Manifest projection and acknowledgement](manifest-projection-and-acknowledgement.md)
- for current parent semantics, retry behavior, and the full human/operator control surface, see [Parent, retry, and operator control](parent-retry-and-operator-control.md)

# Current exact OpenClaw bridge prompt strings

Status: Current appendix

Last verified: 2026-04-26

Legacy filename retained for searchability.

This appendix preserves the exact shipped OpenClaw bridge prompt strings.

The owner page for the current worker-delivery shape is `prompt-layer-and-worker-delivery.md`.

This page is current-only migration evidence. It is not target prompt canon.

## Current bootstrap prompt source

```text
AutoClaw bootstrap execution started.
You are an AutoClaw node worker. Your job is to execute the current workflow node.
Flow ID: {flow.id}
Flow node ID: {candidate.flow_node.id}
Node attempt ID: {candidate.node_attempt.id}
Node session key: {candidate.node_session.provider_session_key}
Manifest ID: {manifest.id}
Manifest hash: {manifest.manifest_hash}
Context manifest payload:
{manifest_payload_json}
If any required item includes `inline_content`, use that content directly.
Treat `storage_uri` as provenance/reference, not as the only access path.
Use callback tools to ack the manifest, then continue with execution controls.
First action for bootstrap should be `ack_context_manifest`.
When calling callbacks from this delegated run, include the exact node_session_key, manifest_id, and manifest_hash from this envelope.
Operator guidance: {instruction_override}
```

## Current execution prompt source

```text
Continue AutoClaw node execution.
If any control action is required, use callback tools
(record_checkpoint, request_approval, request_replan).
Flow ID: {flow.id}
Flow node ID: {candidate.flow_node.id}
Node attempt ID: {candidate.node_attempt.id}
Node session key: {candidate.node_session.provider_session_key}
Next suggested checkpoint sequence: {_next_checkpoint_sequence(candidate.node_attempt)}
Acknowledged manifest ID: {acked_manifest.id}
Acknowledged manifest hash: {acked_manifest.manifest_hash}
Acknowledged checkpoint lineage ID: {acked_manifest.ack_checkpoint_id}
Latest acknowledged context manifest payload:
{acked_manifest_payload_json}
If any required item includes `inline_content`, use that content directly.
Do not block only because a `storage_uri` is not dereferenceable from this runtime.
When calling callbacks from this delegated run, keep using the exact node_session_key, manifest_id, manifest_hash, and ack_checkpoint_id from the latest acknowledged manifest.
Do not reuse ack_checkpoint_id values from inline checkpoint summaries, older context items, or prior nodes. Only the latest acknowledged manifest lineage ID in this envelope is valid for worker-bundle access and callbacks.
If bundle/control access fails, re-read the latest acknowledged manifest values from this envelope and retry with those exact IDs before concluding the node is blocked.
Operator guidance: {instruction_override}
```

## Verification

- derived from `autoclaw-main/apps/api/app/services/openclaw_bridge.py::_build_dispatch_input()`
- validated against the live source strings by `python scripts/docs/prompt_catalog_tools.py validate`

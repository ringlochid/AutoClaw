## Monitoring Is Not Task Truth

Files under `_runtime/dispatch/<dispatch_id>/` are monitoring and incident-debug projections only.

Rules:

- They are not ordinary assignment truth.
- Read them only when the current failure, surfaced ref, or incident flow explicitly sends you there.
- If a monitoring projection disagrees with current manifest, assignment, checkpoint context, or surfaced durable refs, controller/DB truth wins.

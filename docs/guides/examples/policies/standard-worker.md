# Standard worker policy example

Status: Reference

Use this policy when a worker assignment should stay bounded and get one ordinary retry.

This example teaches:

- worker policy is attached to worker nodes only
- `retry_limit` expresses bounded retry behavior
- the policy does not redefine the role instruction; it adds budget behavior

For the exact YAML, use the [standard worker reference example](../../../reference/definitions/policies/standard-worker.md).

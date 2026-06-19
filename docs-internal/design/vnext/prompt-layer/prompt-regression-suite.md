# Prompt regression suite

Status: Target

This page defines the Vnext prompt regression expectations.

## Core rule

Prompt regression checks are required design evidence, not optional examples.

They exist to prove that prompt previews, diffs, and capability-sensitive renders still match controller truth as the future design evolves.

## Required regression families

The regression suite must cover:

- golden renders for stored-truth worker and parent/root prompts
- preview renders for draft-based authoring flows
- diff checks between stored truth and draft content
- role and policy matrix renders
- capability matrix renders for human-request and command-run permissions
- negative checks proving that support files and secret material do not leak into ordinary prompt truth

## Minimum scenarios

At minimum, the suite must include:

- worker prompt with no human-request capability
- worker prompt with `direction`
- worker prompt with `approval`
- worker prompt with `input`
- worker prompt with `review`
- worker prompt with command-run allowed
- parent/root prompt with structural-edit context and resolved role/policy preview
- preview render built from a draft set before upload
- diff between current stored workflow and edited draft workflow

## Invariant checks

Regression cases must assert:

- preview provenance is explicit
- capability overlays match effective controller capabilities
- prompt diff shows role/policy wording changes when resolved metadata changes
- support-state content is not promoted into ordinary prompt context
- secret values remain redacted or absent

## Related contracts

- [Prompt system vnext](prompt-system-vnext.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
- [Definition authoring workbench](../interfaces/definition-authoring-workbench.md)
- [V1 prompt render and persistence](../../v1/prompt-layer/render-and-persistence.md)

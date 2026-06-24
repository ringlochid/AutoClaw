# Prompt regression suite

Status: Reference

This page no longer defines an active V2 target surface.

## Current direction

V2 keeps the current prompt render-and-persist model.

It does not add prompt preview, diff, or regression as first-class prompt-layer surfaces.

If future implementation work wants automated prompt checks, treat them as implementation-level tests over the current prompt renderer rather than as a separate user-facing prompt contract.

## Related contracts

- [Prompt system v2](prompt-system-v2.md)
- [V1 prompt render and persistence](../../v1/prompt-layer/render-and-persistence.md)

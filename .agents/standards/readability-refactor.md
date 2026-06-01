# Readability and refactor standard

Status: Reference

Use this guide when the touched slice is drifting into structural cleanup,
large-function repair, compatibility-shim deletion, or naming cleanup.

## Goal

Every touched slice should leave the code easier to read than it was before the edit.

## Rewrite versus patch

Prefer a rewrite-shaped change when:

- the current structure hides the target contract
- stale compatibility logic is forcing parallel truth paths
- the function or file crosses the `STYLE.md` refactor thresholds and the extra branches are structural, not temporary
- the same ambiguity would keep recurring if you only patched one more branch

Prefer a bounded patch when:

- the phase owns a narrow contract repair and the surrounding structure is still phase-appropriate
- a wider rewrite would cross owned-surface boundaries without approval
- the cleanup can be deferred cleanly and recorded as an exact later-phase exception

## Touched-surface checklist

- remove dead code and unreachable branches
- remove duplicate logic and duplicated normalization paths
- delete compatibility shims that no longer protect a real public surface
- move shared helpers out of module-local underscore-private names
- keep top-down control flow readable without deep helper hopping
- rename vague helpers and data structures to domain names
- split mixed-responsibility modules when the current slice already touches both concerns
- keep comments for non-obvious intent, not for restating the code

## Extraction rules

- extract by responsibility, not by arbitrary line-count chopping
- prefer a few named helpers over one deeply nested orchestration block
- do not create new placeholder modules just to satisfy a length threshold
- when extracting, place the new surface near the code that owns the concern

## Compatibility and migration discipline

- do not keep long-lived import-only shims as steady-state layout
- do not carry both old and new truth paths once the owning phase has reopened the surface
- if a temporary compatibility path is unavoidable, document the exact owner and removal point in review

## Review standard

Before claiming the refactor clean:

- check the touched functions against the line-count thresholds
- search for retained duplicate helpers or underscore-private shared imports
- verify the rename or extraction did not silently widen ownership into another phase
- record any retained exception with the exact contract reason

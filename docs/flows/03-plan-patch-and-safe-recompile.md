# Flow 03 — Plan Patch and Safe Recompile

## Purpose

Show how a parent changes executable structure without mutating runtime state ad hoc.

## Flow

```text
checkpoint
-> parent reasoning
-> structured patch proposal
-> controller validation
-> partial recompile
-> new plan revision
-> adopt at safe boundary
```

## Example

1. child fails twice with the same failure signature
2. parent decides the plan should insert a contract-check step
3. parent emits a structured patch proposal
4. controller validates that the patch is legal
5. compiler lowers the patch into a new compiled plan revision
6. runtime adopts the new revision after the checkpoint boundary

## Important rule

Thoughts are free.
Executable structure changes require validation and compile.

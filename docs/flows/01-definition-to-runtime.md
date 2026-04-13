# Flow 01 — Definition to Runtime

## Purpose

Show how user-edited definitions become executable runtime work.

## Flow

```text
role / policy / workflow definitions
+ skill refs
-> registry import / publish
-> compile / normalize / validate
-> compiled plan revision
-> instantiate run / attempt / flow
-> runtime execution
```

## Step-by-step

1. definitions are authored or imported
2. registry validates them and exposes published versions
3. compiler resolves refs/defaults and validates structure
4. compiler persists a compiled plan revision
5. runtime instantiates a new flow from that plan
6. parent supervisor starts dispatching the execution path

## Main invariant

Runtime should execute the compiled plan, not raw source definitions.

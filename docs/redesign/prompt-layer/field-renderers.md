# Field Renderers

Status: Target

This page defines renderer authority for the frozen v1 prompt sections.

## Canonical Sections

- `operating_model`
- `task_identity`
- `node_purpose`
- `current_dispatch`
- `workflow_manifest`
- `current_assignment`
- `latest_checkpoint_context`
- `consumed_durable_refs`
- `transient_refs`
- `task_memory`
- `allowed_actions_now`
- `publication_rule`

## Static Continuation Sections

- `operating_model`
- `task_identity`
- `node_purpose`

## Global Renderer Rules

All sections must render with:

- stable headings
- scan-first bullets or short tables
- omission of absent optional data rather than placeholder prose
- path-only surfaced refs
- compact artifact refs only
- meaningful descriptions rather than inferred filename semantics

Do not render:

- flow/scope manifest splits
- `writable_roots`
- callback legality payloads
- gate-era boundary terms
- full current-pointer internals
- raw monitoring files as normal work context

## Exact Rendered Prompt Routes

Use these routes when you need to see the rendered prompt body instead of the section rules only:

- exact `worker_dispatch_prompt` example: [generated/rendered-examples.md](generated/rendered-examples.md)
- exact `parent_root_dispatch_prompt` example: [generated/rendered-examples.md](generated/rendered-examples.md)
- exact `same_session_continue` inline wrapper: [generated/rendered-examples.md](generated/rendered-examples.md)
- exact reusable wording blocks that the render must stay compatible with: [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md) and [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)

## Compact Ref Rule

Ordinary prompt rendering should surface refs in these compact shapes only.

### Artifact ref

- `slot`
- `version`
- `path`
- `description`

### Durable non-artifact ref

- `kind`
- `slot` when relevant
- `path`
- `description`

### Transient ref

- `path`
- `description`

Concrete examples:

```text
Artifact ref
- slot: verification_report
- version: 2
- path: C:/tasks/task_2026_0042/outputs/artifacts/implement_fix/verification_report/verification_report.v02.md
- description: scoped verification evidence for the current fix assignment

Durable non-artifact ref
- kind: criteria
- slot: fix_acceptance
- path: C:/tasks/task_2026_0042/context/criteria/fix_acceptance.md
- description: bounded fix acceptance criteria

Transient ref
- path: C:/tasks/task_2026_0042/tmp/transfers/implement_fix/repro-commands.txt
- description: optional repro commands from the prior attempt
```

Avoid rendering vague refs such as:

```text
- findings_report.v02.md
- latest checkpoint
- see transfer file
```

Those force the reader to infer meaning from filenames instead of from explicit slot, kind, and description.

## Section Rendering Rules

### `operating_model`

Render:

- controller/DB truth ownership
- generated files as projections
- public boundary model
- retry summary
- durable versus transient summary
- monitoring-not-task-truth reminder

### `task_identity`

Render:

- task key/id
- title when present
- short summary
- optional task instruction

### `node_purpose`

Render:

- node key
- node kind
- role
- short node description

### `current_dispatch`

Render:

- current bound turn
- send mode
- closure expectation:
  - parent/root: tools now, later `yield` or terminal boundary
  - worker/leaf: later `green | retry | blocked`

The closure line should name the exact legal boundary words, not synonyms such as "continue," "complete," or "resume."

Do not render internal route ids such as `dispatch_id` in the canonical node-facing section.

### `workflow_manifest`

Render:

- stable manifest path
- short description
- optional current relevant paths only when they sharpen orientation

Do not restate the entire manifest inline.

### `current_assignment`

Render the assignment fields in this order:

1. `summary`
2. `instruction`
3. `criteria`
4. `consumes`
5. `produces`
6. `transient_refs` when present
7. `task_memory_search_hints` when present

Good render:

```text
Current Assignment
- summary: repair the auth-refresh defect and publish the required evidence
- instruction: change only the bounded auth-refresh logic and rerun the scoped verification
- criteria:
  - slot: fix_acceptance
    description: bounded fix acceptance criteria
- consumes:
  - kind: artifact
    slot: findings_report
    description: upstream findings for the scoped fix
- produces:
  - slot: patch
    description: bounded code change artifact
```

### `latest_checkpoint_context`

Render in this order when a checkpoint exists:

1. `checkpoint_kind`
2. `outcome`
3. `summary`
4. `next_step`
5. `blockers` when present
6. `risks` when present
7. surfaced compact refs when present
8. `task_memory_search_hints` when present

Good render:

```text
Latest Checkpoint Context
- checkpoint_kind: terminal
- outcome: blocked
- summary: browser refresh path still fails the current criteria
- next_step: parent should decide whether to assign a narrower repro child or end blocked
- risks:
  - current repro is still flaky on one browser family
```

### `consumed_durable_refs`

Render each surfaced durable ref as:

- kind
- slot when relevant
- version when relevant
- path
- description

### `transient_refs`

Render each transient ref as:

- path
- description

and explicitly say transient refs are optional carryover only.

### `task_memory`

Render:

- current search hints
- `context/wiki/` as curated task-memory pages
- other curated docs under `context/` as source/reference material
- v1 retrieval is direct file/path search only

### `allowed_actions_now`

Render only the bounded action surface that is legal now:

- parent/root tools when current node is parent/root
- `yield` when one continuation outcome is already staged
- `green | blocked` when parent/root terminal closure is relevant
- `green | retry | blocked` when worker/leaf terminal closure is relevant

Good parent/root render:

```text
Allowed Actions Now
- tools:
  - assign_child
  - add_child
  - update_child
  - remove_child
  - release_green
  - release_blocked
- emit `yield` only after exactly one continuation outcome is already staged
- for structural edits, reread the current manifest first, discover valid role/policy ids through the registry read lane, and reread the regenerated manifest after the edit
- emit `green | blocked` only when this parent/root node itself is closing its own assignment
```

Good worker render:

```text
Allowed Actions Now
- continue the current assignment
- publish progress checkpoint if later readers need the reasoning
- close terminally with `green`, `retry`, or `blocked`
```

### `publication_rule`

Render:

- required `produces` gate `green`
- durable artifacts publish as immutable versioned files
- later agents reread checkpoint plus compact surfaced refs
- do not rely on transcript memory

## Validation Mirror

Renderer output must stay consistent with:

- [../architecture/runtime-boundary-and-controller-loop-contract.md](../architecture/runtime-boundary-and-controller-loop-contract.md) for boundary names and closure preconditions
- [../architecture/worker-context-contract.md](../architecture/worker-context-contract.md) for manifest/assignment/checkpoint/task-memory read rules
- [../interfaces/api-schema-appendix.md](../interfaces/api-schema-appendix.md) for assignment/checkpoint field shapes and surfaced ref carriers

If a rendered example, section renderer, and validation carrier disagree, the runtime should not invent a third phrasing. Fix the drift so prompt wording, schema shape, and boundary legality stay identical.

## Related Contracts

- [Prompt contract](C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/prompt-layer/contract.md)
- [Prompt source and sections](C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/prompt-layer/source-and-sections.md)
- [Artifact ref and storage contract](C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/architecture/artifact-ref-and-storage-contract.md)

# Next Implementation Plan

## Goal

Prepare AutoClaw for the first real operator-led complex MVP build test with a narrower, cleaner model:

- bridge plugin actually callable against the live service
- task creation can materialize the right compose-backed task state
- file upload exists as an API surface
- skills are modeled as explicit metadata definitions with persisted many-to-many bindings
- packaging/runtime truth stays simple and local-first

## Confirmed direction

These are the decisions this pass should treat as fixed unless a real implementation blocker appears.

### Packaging/runtime boundary

Keep:

- workflow or node image metadata in workflow definitions
- `task_composes` as the sole persisted packaging record
- derived live runtime views when needed from orchestration/runtime state

Drop as durable truth for this pass:

- standalone `task_images`
- standalone `runtime_images`
- persisted `runtime_containers` as a source of truth

Practical rule:

- `task create` must be able to create or select the task-owned compose state needed for execution
- the compose snapshot is the durable packaging anchor
- live container state, if shown, should be derived from runtime execution state rather than treated as a canonical persisted model

### Upload/product surface

Implement now:

- file upload API

Do not implement in this pass:

- upload UI
- definition authoring UI

### Skill model

Use separate skill metadata YAML beside role/workflow definitions.

Keep rich execution instructions in the OpenClaw worker workspace skills.

The AutoClaw registry/control-plane layer should store and reason over skill metadata plus versioned bindings, not try to fully ingest and own `SKILL.md` execution bodies.

Because skill relations are many-to-many, add explicit link tables rather than trying to hang a single foreign key off roles/workflows/nodes.

---

## Target shape for this pass

### Definitions layer

Definition roots should move toward:

- `definitions/roles/*.yaml`
- `definitions/policies/*.yaml`
- `definitions/workflows/*.yaml`
- `definitions/skills/*.yaml`

This pass does **not** need standalone `task-image` definitions.

If compose metadata must be selected independently of workflow defaults, support it through the task-create/compose path, not by reintroducing the dropped image layers.

### Runtime/control-plane layer

Durable runtime/control-plane state for this pass should center on:

- tasks
- task attachments / uploaded files
- compiled plans
- task composes
- flows
- flow revisions
- flow nodes
- node attempts
- checkpoints
- approvals
- context manifests
- skill registry / skill versions / skill binding links

---

## Ordered implementation plan

1. **Bridge plugin auth + live smoke**
2. **Task create + compose-backed task materialization**
3. **File upload API**
4. **Skill metadata definitions + persisted binding tables**
5. **Definition bootstrap/upload support for skills**
6. **Real benchmark run verification**

---

## Slice 1, Bridge plugin auth + live smoke

### Goal

Make the installed `autoclaw-bridge` plugin actually callable against the live AutoClaw service.

### Required work

- add `plugins.entries.autoclaw-bridge.config.api.internalApiKey` to the installed OpenClaw plugin config
- keep URL autodetect support, but treat auth as mandatory
- run one live smoke against a safe bridge tool after gateway restart

### Exit criteria

- the plugin loads
- the plugin authenticates to `/internal/*`
- one real tool call succeeds end to end

---

## Slice 2, Task create + compose-backed task materialization

### Goal

Replace the weak current task-start story with a first-class path that creates task-owned compose state suitable for real work.

### Required work

- define the new task create/start path around the selected workflow/compiled-plan meaning plus compose-backed task state
- allow task creation to create or select the task compose needed for execution
- ensure the compose snapshot remains the sole persisted packaging anchor for the task
- keep task/workspace/context/manifest materialization local-first under the existing task directory structure

### Notes

This slice should not bring back `task_images`, `runtime_images`, or persisted `runtime_containers` as truth.

### Exit criteria

- there is one honest task create/start path for the benchmark workflow
- the path results in a task plus valid compose-backed execution state
- retries/replans behave consistently with the compose lifecycle rule

---

## Slice 3, File upload API

### Goal

Provide the missing file ingress needed for real task runs.

### Required work

- add a first-class file upload API
- bind uploaded files into task-owned workspace/context state in a deterministic way
- make uploaded files available to the benchmark workflow without manual operator-only file placement

### Explicit non-goal for this pass

- no upload UI yet

### Exit criteria

- a user or operator can upload files through API only
- uploaded material lands in the right task-owned location/binding
- the benchmark workflow can consume those files

---

## Slice 4, Skill metadata definitions + persisted binding tables

### Goal

Move from loose compile-time-only skill refs toward a proper registry/control-plane skill model.

### Required work

Add separate skill metadata definitions:

- `definitions/skills/*.yaml`

Each skill definition should carry the metadata AutoClaw needs, such as:

- provider
- key
- `runtime_name` (explicit, no fallback guessing)
- description
- dependency/install metadata as needed
- optional source/version metadata

Add explicit many-to-many link tables for skill bindings, at minimum for:

- role version -> skill version
- workflow version default -> skill version
- workflow node -> skill version

### Important rule

Do **not** rely on a single FK hanging off one side. These are real n-n relations and should be modeled as such.

### Exit criteria

- skills can be represented as versioned metadata definitions
- runtime dispatch can use explicit `runtime_name`
- role/default/node skill links persist cleanly and can be inspected independently of compiler fallback logic

---

## Slice 5, Definition bootstrap/upload support for skills

### Goal

Make the new skill metadata definitions actually enter the registry through the same local-first system as the other definitions.

### Required work

- extend local definition-folder bootstrap/import to load `definitions/skills/*.yaml`
- add registry draft/publish support for skills if needed to keep the definition API surface consistent with roles/policies/workflows
- make sure registry reads show the right skill/version metadata
- stop relying only on indirect top-level workflow skill-ref harvesting

### Notes

For this pass, the important thing is metadata definition ingestion and binding persistence, not full `SKILL.md` package upload.

### Exit criteria

- local-first bootstrap sees skill definitions
- registry can expose the resulting skill metadata/version state
- benchmark definitions can rely on these records without hidden manual patching

---

## Slice 6, Real benchmark run verification

### Goal

Prove the narrowed model works on the real complex benchmark workflow.

### Required work

Run the benchmark workflow with:

- live bridge auth enabled
- compose-backed task creation
- API file upload
- explicit skill metadata + bindings
- approval/replan/checkpoint paths exercised as needed

### Verification focus

- end-to-end start succeeds without hidden manual setup
- file ingress works
- skill resolution is explicit and inspectable
- compose lifecycle is stable across retry/replan cases
- no resurrected dependence on dropped image/runtime-truth tables

### Exit criteria

- the system is good enough for a real operator-led benchmark run
- remaining gaps are clearly post-test improvements, not pre-test blockers

---

## Must-fix before the first real test

1. bridge plugin `internalApiKey` config
2. one live bridge smoke test
3. first-class task create/start path with compose-backed task state
4. file upload API
5. explicit `runtime_name` in skill metadata
6. persisted many-to-many skill binding tables
7. skill-definition bootstrap/upload support

---

## Explicitly not in this pass

- upload UI
- graph/editor UI work
- full end-user definition authoring UI
- full `SKILL.md` package upload/ownership by AutoClaw
- reintroducing `task_images`
- reintroducing `runtime_images`
- treating persisted `runtime_containers` as canonical truth

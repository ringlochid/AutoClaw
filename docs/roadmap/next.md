# Next Implementation Plan

## Goal

Finish the remaining work needed before the first real operator-led complex MVP build test.

## Current state

Already landed in this pass:

- bridge plugin URL autodetect
- bridge plugin internal API key autodetect from AutoClaw config
- explicit skill `runtime_name` in the current workflow skill refs
- compiler/runtime resolution now uses explicit runtime names instead of `provider:key` fallback

Still required before the real test:

1. live gateway restart + bridge smoke
2. task-compose centric create/start surface
3. file upload API
4. skill metadata definitions plus persisted n-n binding tables

---

## Fixed direction

### Packaging/runtime truth

Keep as durable truth:

- workflow or node image metadata in workflow definitions
- `task_composes` as the sole persisted packaging and launch-binding record

Boundary:

- workflow = reusable orchestration image (roles, skills, policies, graph/defaults)
- task compose = task-scoped launch image (task snapshot, chosen workflow meaning, resources/dependencies/context bindings)
- runtime = live execution facts (flows, revisions, attempts, sessions, approvals, manifests, replans)

Drop as durable truth for this pass:

- standalone `task_images`
- standalone `runtime_images`
- persisted `runtime_containers`

If runtime container state is shown anywhere, it should be a derived live view, not the canonical persisted model.

### Product surface

Implement now:

- a task-compose centric create/start surface that binds task intent, workflow entrypoint, context URIs, required skills, and task-scoped resources before flow creation
- keep thin `TaskCreate` as an internal record shape rather than the public runnable-task contract
- API file upload
- compose-backed task create/start

Do not implement now:

- upload UI
- definition authoring UI

### Skill model

Keep rich execution instructions in OpenClaw worker `SKILL.md` files.

Add AutoClaw-facing metadata definitions under:

- `definitions/skills/*.yaml`

Skill bindings are many-to-many. Model them with explicit link tables, not a single FK.

Minimum binding links:

- role version -> skill version
- workflow version default -> skill version
- workflow node -> skill version

---

## Remaining pre-test slices

### Slice 1, Live bridge validation

#### Goal

Prove the patched plugin works through the real gateway, not just unit tests.

#### Required work

- restart `openclaw-gateway.service`
- run one safe bridge tool smoke against the live AutoClaw service
- confirm autodetected base URL and autodetected internal API key both work in the installed plugin

#### Exit criteria

- a real bridge tool call succeeds end to end through the gateway

---

### Slice 2, Task create/start from task compose

#### Goal

Make task creation produce the compose-backed task state required for real execution.

#### Required work

- replace the weak current task-create story with a first-class compose-backed path
- ensure task create/start can create or select the task-owned compose snapshot
- keep task/workspace/context/manifest materialization local-first under the task data dir

#### Exit criteria

- the benchmark flow can be started from an honest task create/start path
- the resulting task has valid compose-backed execution state

---

### Slice 3, File upload API

#### Goal

Provide the missing file ingress needed for real runs.

#### Required work

- add a first-class file upload API
- bind uploaded files into task-owned workspace/context state deterministically
- make uploaded material available to the benchmark workflow without manual operator-only placement

#### Explicit non-goal

- no upload UI in this pass

#### Exit criteria

- files can be uploaded by API and consumed by the benchmark task/workflow path

---

### Slice 4, Skill metadata definitions + binding persistence

#### Goal

Move from loose compile-time-only skill refs to explicit versioned skill metadata and persisted bindings.

#### Required work

- add `definitions/skills/*.yaml`
- bootstrap and registry upload support for skill metadata definitions
- keep `runtime_name` explicit in skill metadata and refs
- add persisted n-n binding tables for:
  - role version -> skill version
  - workflow version default -> skill version
  - workflow node -> skill version

#### Notes

This pass does **not** need full `SKILL.md` package upload. Metadata only is enough.

#### Exit criteria

- skill metadata exists as versioned definitions
- bindings are queryable from the DB/control plane without relying only on compiler merge logic
- runtime dispatch uses explicit `runtime_name`

---

## Must be true before the first real test

- live bridge smoke succeeds after gateway restart
- task create/start is compose-backed
- API file upload works
- explicit skill metadata + persisted n-n skill bindings exist
- no dependency on dropped packaging/runtime-truth tables

## Explicitly out of scope for this pass

- upload UI
- graph/editor UI work
- full definition authoring UI
- full `SKILL.md` package upload into AutoClaw
- reintroducing `task_images`
- reintroducing `runtime_images`
- treating persisted `runtime_containers` as canonical truth

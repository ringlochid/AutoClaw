# Next Implementation Plan

## Goal

Move AutoClaw from "operator-led pilot is viable" to "we are confident using it for a real complex MVP build workflow".

The next pass should stop reworking already-landed bridge/runtime slices unless a real bug appears. The active gaps are now:

1. worker confidence on a real complex workflow
2. whether image/container resource definitions are actually needed
3. whether the product surface is good enough for real user create/upload/run/monitor/approve flows
4. config/default truth-sync so the service story is consistent

## Current baseline

Treat these as already proved enough for an operator-led pilot:

- the bridge plugin is safe enough to install in worker lane only
- runtime/resource integration coverage is green
- operator run/monitor/approve paths exist
- local-first config/data/task directory placement is sane
- packaged definition bootstrap works

Known drift still visible today:

- the live service is healthy on port `8001`
- fresh init/default messaging currently points users toward `8123`
- that mismatch must be removed before calling the setup story clean

## Not the focus unless a bug appears

Do not spend the next pass re-proving or redesigning these areas unless the benchmark workflow exposes a real failure:

- already-landed local-first task/runtime layer work
- broad graph/operator UI expansion
- wider operator/plugin authority than the bounded worker-lane install
- image/container lifecycle work for its own sake

---

## Ordered plan

1. **Choose the benchmark workflow and freeze the success contract**
2. **Prove worker confidence on that real workflow**
3. **Make an explicit resource-definition decision**
4. **Close the real user create/upload/run/monitor/approve gap**
5. **Truth-sync config, defaults, and production-like verification**
6. **Truth-sync docs and make the go/no-go call**

---

## Slice 1, Benchmark workflow and success contract

### Goal

Pick one real complex MVP build workflow and make it the only benchmark that matters for this pass.

`default-bugfix` is no longer enough as the confidence target. Use either:

- the real complex MVP build workflow definition, or
- `max-complexity-review` only if it is still the closest honest proxy

### Work

- define the benchmark workflow key and fixture payloads
- define what counts as success, clean block, and failure
- define the required artifacts/evidence each important node must produce
- define which operator interventions are still allowed in this pass

### Likely files

- `definitions/workflows/*.yaml`
- `docs/e2e/*.md`
- `apps/api/tests/integration/test_runtime_api.py`
- `apps/api/tests/integration/test_phase456_runtime_db.py`

### Exit criteria

- there is one explicit benchmark workflow
- there is one explicit success contract for it
- everyone can tell whether a run passed, cleanly blocked, or failed

---

## Slice 2, Worker confidence on the real workflow

### Goal

Prove that the current worker surface is strong enough for repeated real runs, not just one happy path.

### Work

Run the benchmark workflow repeatedly and include drills for:

- approval required
- replan required
- missing or weak context evidence
- wake timeout / callback failure
- service restart / resume mid-run
- retry after a failed node attempt

If the worker still needs operator nudges, tighten the worker instructions, benchmark definition, or runtime boundaries before expanding scope.

### Likely files

- `definitions/roles/*.yaml`
- `definitions/policies/*.yaml`
- `definitions/workflows/*.yaml`
- `apps/api/app/runtime/watchdog.py`
- `apps/api/app/runtime/callback_bindings.py`
- `apps/api/app/runtime/checkpoints.py`
- `apps/api/app/api/routes/flows.py`
- corresponding `autoclaw-worker` workspace instructions only if the benchmark proves they are the blocker

### Verification

- run the benchmark flow at least `5-10` times
- include failure-mode drills, not just clean runs
- require that the system either:
  - completes cleanly, or
  - pauses cleanly for approval/replan
- no manual DB edits
- no manifest surgery
- no hidden transcript-only recovery tricks

### Exit criteria

- the worker is predictably usable on the benchmark workflow with operator oversight only where explicitly intended
- failures are bounded and typed, not messy or ambiguous

---

## Slice 3, Resource-definition decision gate

### Goal

Decide whether MVP actually needs `task-image`, `task-compose`, `runtime_images`, or `runtime_containers`, instead of implementing them just because the contract exists.

### Work

Create a node-by-node dependency table for the benchmark workflow:

- workspace mounts
- context refs
- toolchain/runtime expectations
- required services or sidecars
- expected outputs/artifacts

Run the benchmark with workspace/context/manifest semantics first.

Only promote image/container definitions into the active MVP contract if the benchmark proves a real need such as:

- repeated environment drift
- pinned build/runtime toolchain requirements
- sidecar service requirements
- reproducibility failures across runs or hosts

### Likely files

- `definitions/workflows/*.yaml`
- `apps/api/app/runtime/resources.py`
- `apps/api/app/runtime/packaging.py`
- `apps/api/app/compiler/resolve.py`
- `docs/architecture/06-openclaw-runtime-bridge.md`

### Verification

- repeated clean-room benchmark runs
- explicit comparison of workspace/context-only vs richer resource layering
- document the decision for each resource type: required now, optional later, or not needed

### Exit criteria

- there is a written yes/no decision for each of:
  - `task-image`
  - `task-compose`
  - `runtime_images`
  - `runtime_containers`
- if the answer is "not now", the benchmark evidence should justify that decision

---

## Slice 4, Real user create/upload/run/monitor/approve flow

### Goal

Close the biggest product gap between operator-led pilot and real user readiness.

### Work

Add or tighten a first-class typed path for:

1. create task or create flow-start request
2. upload or attach files
3. bind uploaded material into task workspace/context
4. start the workflow
5. monitor status, evidence, and artifacts
6. resolve approvals
7. continue to completion or clean block

This slice is not done if the only honest story is still "an operator can call internal routes manually".

### Likely files

- `apps/api/app/api/routes/tasks.py` or a new upload/file route if needed
- `apps/api/app/api/routes/flows.py`
- `apps/api/app/schemas/runtime.py`
- `apps/api/app/runtime/resources.py`
- `apps/api/app/api/presenters/runtime.py`
- `apps/console/src/App.tsx`
- `apps/console/src/lib/api.ts`

### Verification

Prove one end-to-end user path against the real service shape:

- create
- upload
- run
- monitor
- approve
- resume
- finish

Also prove restart/resume behavior during:

- an in-flight run
- an approval wait state

### Exit criteria

- there is one honest first-class user path for create/upload/run/monitor/approve
- upload ingress is explicit and typed, not implied or manual
- the console/API story is good enough to demonstrate without operator-only shortcuts

---

## Slice 5, Config/default truth-sync and production-like verification

### Goal

Make the service/default/config story consistent and prove the benchmark beyond the current host-local happy path.

### Work

- remove the `8001` vs `8123` drift
- make init output, config defaults, service files, plugin examples, and docs agree
- keep plugin installs explicit about worker-lane defaults
- verify the benchmark under the intended service shape, not just ad hoc local state

### Likely files

- `apps/api/app/cli.py`
- `apps/api/app/config.py`
- `README.md`
- `docs/e2e/phase8-happy-path.md`
- `docs/roadmap/current.md`
- `autoclaw-bridge-plugin/README.md`
- `autoclaw-bridge-plugin/plugin-config.example.json`

### Verification

Use the repo verification order in `docs/roadmap/suggestion.md`:

- `make format-api`
- `make check-api`
- `make test-api`
- `make test-api-db`
- Docker-backed smoke for the intended runtime path

Also keep these focused checks in the loop when relevant:

- `cd ~/leo/projects/autoclaw-bridge-plugin && npm test`
- benchmark HTTP/API smoke against the real running service
- `autoclaw doctor --json` against the target config

### Exit criteria

- there is one consistent setup/default story
- the benchmark is proved in a production-like verification path, not only in local SQLite happy-path runs

---

## Slice 6, Docs truth-sync and go/no-go review

### Goal

After the slices above are done, update the docs to describe the real system and make a clear launch recommendation.

### Files to update

- `docs/roadmap/current.md`
- `docs/roadmap/next.md`
- `docs/architecture/06-openclaw-runtime-bridge.md`
- `docs/e2e/*.md`
- `autoclaw-bridge-plugin/README.md`

### Final review checklist

- the worker benchmark is repeatable and honest
- the resource-definition decision is explicit and justified
- create/upload/run/monitor/approve works as a real user path
- config/default docs match the live system
- no critical step depends on hidden operator knowledge
- the final recommendation is explicit:
  - operator-led pilot only, or
  - broader real-user pilot, or
  - not ready

---

## Explicitly not in this pass

Do not treat these as active scope unless an earlier slice forces them:

- broad graph editor work
- n8n-style workflow authoring
- broad operator automation inside OpenClaw beyond the bounded plugin surface
- making image/container abstractions mandatory before the benchmark proves they are needed
- large redesigns of already-landed local-first/runtime packaging layers

# Historical Review Findings Log

Status: Historical review log

This file preserves the merged findings from the scoped review passes that were used during the migration from `lock_next/` into `docs/redesign/`.

It is not a live owner page and it is not the canonical source of truth. Use the current owner pages under `docs/redesign/` and the accepted ADRs under `docs/redesign/decisions/` for the settled redesign contract.

Many findings below have already been addressed. They remain here as migration traceability and search history, not as active unresolved owner text.

Some historical entries below still mention pre-rename or deleted filenames. Treat those names as search breadcrumbs only, not as expected live owner pages.

## Architecture and decisions

- [end-to-end-lifecycle.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/architecture/end-to-end-lifecycle.md:7) still teaches a live lifecycle of worker or parent callback -> evidence bundle -> `parent_gate`. This conflicts with the locked model: `dispatch` ingress, `yield | green | retry | blocked` egress, explicit parent/root tools, and removal of packet/bundle/gate-era surfaces. Follow-on fix: rewrite this page to the current dispatch/assignment/checkpoint lifecycle or demote it to a historical router.

- [ADR-0005-task-owned-roots-and-runtime-generated-projections.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/decisions/ADR-0005-task-owned-roots-and-runtime-generated-projections.md:7) still centers execution slices, packets, reports, and session bindings, and still points readers at historical pages as canonical references. This conflicts with the current manifest + assignment + latest-checkpoint + artifact/transient projection model. Follow-on fix: rewrite the ADR to the current generated-root model or explicitly demote it.

- [provider-worker-and-operator-boundary.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/architecture/provider-worker-and-operator-boundary.md:18) and [provider-split-rationale.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/architecture/provider-split-rationale.md:19) still define a delegated callback surface, operator plugin surfaces, and skill-schema framing. This conflicts with the locked model where `tool` is canonical, `plugin` is adapter-specific only, and OpenClaw is an adapter-normalization and monitoring surface rather than a live skill owner. Follow-on fix: rewrite both pages around trust-lane separation, canonical tool terminology, and adapter normalization.

- [ADR-0004-openclaw-first-worker-boundary-and-skill-ownership.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/decisions/ADR-0004-openclaw-first-worker-boundary-and-skill-ownership.md:7) still centers skill ownership and points readers at [provider-selection-and-skills.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/provider-selection-and-skills.md). This is weaker than the locked model, which treats OpenClaw as an adapter-normalization layer and keeps `tool` as the canonical runtime term. Follow-on fix: rewrite the ADR around adapter normalization and remove live skill-centric ownership language.

- [task-compose-root-binding-and-host-placement.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/architecture/task-compose-root-binding-and-host-placement.md:30) still says the controller materializes only `outputs` and `_runtime` as generated roots. This is incomplete against the locked filesystem model, which also includes `tmp/transfers/` as an explicit generated surface. Follow-on fix: add `tmp/transfers/` and align the page to the current root meanings.

## Interfaces

- [plugin-tool-reference.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/interfaces/plugin-tool-reference.md:16) conflicts with [human-and-operator-control-surface.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/interfaces/human-and-operator-control-surface.md:47) about what the standard plugin is. One page mixes internal controller/node adapter lanes with operator-safe lanes; the other treats the trusted external plugin as operator-safe parity only. Follow-on fix: separate internal dispatch-bound adapter lanes from operator-safe external lanes and make the trust boundary explicit.

- [api-schema-appendix.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/interfaces/api-schema-appendix.md:215) still returns bare `*_path` strings where the locked surfaced-ref model now expects compact refs with at least `path + description`, especially for manifest and operator/debug surfaced files. Follow-on fix: replace bare path fields with compact surfaced-ref shapes where top-level docs now require explicit rendered meaning.

- [role-and-policy-definition-schema.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/interfaces/role-and-policy-definition-schema.md:48) freezes `defaults.structural_edit_budget` even though that authored field is not locked elsewhere. Follow-on fix: either justify and lock that field across the owner docs or remove/demote it here to avoid over-specifying the registry schema.

- [api-schema-appendix.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/interfaces/api-schema-appendix.md:21) still says assignment/checkpoint semantics are owned by `lock_next`. That is now wrong: `docs/redesign` must become self-owned. Follow-on fix: replace that wording with references to the rewritten top-level owner pages.

- [operator-definition-and-role-boundary.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/interfaces/operator-definition-and-role-boundary.md:72) stays too abstract about parent/root powers. It does not name `assign_child`, structural CRUD, `release_green`, root-only `release_blocked`, or `yield | green | retry | blocked`. Follow-on fix: replace vague "activate/replan/release" wording with the canonical runtime surfaces and legal powers.

## Prompt layer

- [prompt-catalog.yaml](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/prompt-layer/prompt-catalog.yaml:1) is still a live contradiction of the locked prompt model. It still freezes removed section order, removed families such as `parent_gate_resume`, `worker_retry`, and `watchdog_recovery_redispatch`, removed sources such as flow/scope manifests, briefs, evidence bundles, and `WorkerContext`, and removed actions such as `retry_child`, `reissue_child`, and `emit_replan_escalation`. Follow-on fix: rewrite or demote this catalog so it matches the current prompt owners or becomes explicitly historical only.

- [generated/rendered-examples.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/prompt-layer/generated/rendered-examples.md:10) does not match the locked prompt shape. The examples omit `consumed_durable_refs` and skip sections the current prompt contract says belong in the canonical render. Follow-on fix: regenerate the examples to match the actual prompt contract and field-renderer rules.

- [legality-and-coverage.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/prompt-layer/legality-and-coverage.md:57) wrongly says parent/root terminal closure is only `green | blocked`. The locked model still allows parent/root `retry` when the parent/root node is retrying its own assignment. Follow-on fix: broaden the legality matrix and examples to include legal parent/root retry.

- [README.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/prompt-layer/README.md:64), [legality-and-coverage.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/prompt-layer/legality-and-coverage.md:1), and [prompt-resource-usage-appendix.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/prompt-layer/prompt-resource-usage-appendix.md:1) still have ambiguous authority. Compatibility/searchability material is still marked `Status: Target` and reads normatively. Follow-on fix: separate owner docs from compatibility/reference docs and demote secondary material explicitly.

## Workflows and tutorials

- [workflow-schema-appendix.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/workflow-schema-appendix.md:44) still defines authored `outputs.handoffs`, `inputs.handoffs`, `inputs.criteria`, handoff uniqueness, `child_defaults.handoffs`, and a whole-children patch contract. This conflicts with the locked authored model: `consumes / produces / criteria`, no authored handoff family, and runtime structural change through `add_child` / `update_child` / `remove_child` on current truth. Follow-on fix: rewrite this appendix to the current authored schema and runtime structural CRUD model.

- [criteria-and-parent-verification.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/criteria-and-parent-verification.md:32) still teaches `assignment_requirements`, `ParentEvidenceBundle`, child handoffs, result records, scope refs, and evidence-bundle-first parent review. This conflicts with the locked review surface: assignment `criteria`, latest child checkpoints, referenced durable artifacts, optional `transient_refs`, and summary-first review over surfaced refs. Follow-on fix: rewrite the page around the checkpoint/artifact/criteria review model.

- [compiler-contract-and-launch-materialization.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/compiler-contract-and-launch-materialization.md:61) still says launch advances until the next boundary, returns `current_boundary_summary`, uses `dispatch_ready` as a worker-family concept, and recompiles on every root-scope replan. This conflicts with the locked split: compiler is launch-time only, runtime CRUD is validator + commit + materializer/projector, and the public boundary model is `dispatch` ingress plus `yield | green | retry | blocked` egress. Follow-on fix: rewrite or demote the page so it stops teaching runtime CRUD as compile-time behavior.

- [examples/normal.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/examples/normal.md:36) and [examples/maximal.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/examples/maximal.md:67) still use `outputs.handoffs`, `inputs.handoffs`, and `final_release_bundle`. Those examples are invalid against the current live authored schema. Follow-on fix: rewrite the examples to `consumes / produces / criteria` and current parent/root release semantics.

- [shared-role-and-policy-example-pack.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/shared-role-and-policy-example-pack.md:23) still teaches reassignment, child retry, evidence bundles, reissue, and `replan_escalation`. Those are removed from the live model. Follow-on fix: rewrite the reusable role/policy pack so it only demonstrates current legal tools, boundaries, and review/release semantics.

- [parent-worker-review-model.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/parent-worker-review-model.md:13) and [powerful-parent-planning-surface.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/powerful-parent-planning-surface.md:5) still present active handoff-packet, parent-gate-verification, and planning-bundle diagrams. Follow-on fix: either rewrite those diagrams to the assignment + checkpoint + artifact model or demote the pages to historical routers.

- [end-to-end-redesign-walkthrough.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/tutorials/end-to-end-redesign-walkthrough.md:20) and [run-a-bugfix-flow.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/tutorials/run-a-bugfix-flow.md:14) still teach `root.parent_gate`, subtree `parent_gate`, automatic parent evidence bundles, and curated root release bundles as the main runtime flow. Follow-on fix: rewrite the tutorials to the current dispatch/tool/checkpoint flow or mark them historical.

- [create-a-definition-and-run-a-task.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/tutorials/create-a-definition-and-run-a-task.md:13) still tells readers to inspect artifacts, handoffs, and result records instead of the current runtime surfaces: manifest, assignment, latest checkpoint, durable artifacts, and optional `transient_refs`. Follow-on fix: update the onboarding tutorial to point at the current deterministic runtime files.

## Highest-priority follow-on fixes

Patch these first because they still teach removed concepts as live truth rather than merely preserving searchability:

1. [end-to-end-lifecycle.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/architecture/end-to-end-lifecycle.md:7)
2. [ADR-0005-task-owned-roots-and-runtime-generated-projections.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/decisions/ADR-0005-task-owned-roots-and-runtime-generated-projections.md:7)
3. [prompt-catalog.yaml](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/prompt-layer/prompt-catalog.yaml:1)
4. [workflow-schema-appendix.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/workflow-schema-appendix.md:44)
5. [criteria-and-parent-verification.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/criteria-and-parent-verification.md:32)
6. [compiler-contract-and-launch-materialization.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/workflows/compiler-contract-and-launch-materialization.md:61)
7. [end-to-end-redesign-walkthrough.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/tutorials/end-to-end-redesign-walkthrough.md:20)
8. [run-a-bugfix-flow.md](/C:/Users/ring_/Desktop/tmp/autoclaw_tmp/code_repo_docs/docs/redesign/tutorials/run-a-bugfix-flow.md:14)

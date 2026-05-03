# Prompt Layer Index

Status: Owner index

Use this page when you know the question before you know the file.

## Mental model first

- runtime truth lives in controller/DB state, not in prompt prose or transport state
- read manifest for the whole workflow, assignment for the current mission, checkpoint for durable handoff, and `consumed_durable_refs` for exact current evidence
- treat `_runtime/dispatch/` as observability only
- use registry reads to discover valid role/policy ids for structural edits; runtime still revalidates those ids on commit
- if a needed path, rule, or state is still unclear, reread current truth and search hinted curated files before acting

## Canonical live owners

- [contract.md](contract.md)
- [source-and-sections.md](source-and-sections.md)
- [field-renderers.md](field-renderers.md)
- [render-and-persistence.md](render-and-persistence.md)
- [machine-contract.md](machine-contract.md)
- [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)
- [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md)
- [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md)

Generated and historical pages are secondary routing aids. They do not overrule the owner pages above.

## Core Runtime Prompt Model

- "What is the canonical prompt model?" [contract.md](contract.md)
- "What are the canonical prompt families?" [contract.md](contract.md)
- "What is the exact boundary model every prompt must teach?" [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) and [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md)
- "What is `same_session_continue` versus `full_prompt`?" [contract.md](contract.md) and [render-and-persistence.md](render-and-persistence.md)
- "What is the exact system block?" [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)
- "What is the exact worker or parent legality block?" [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md)
- "Where is role/policy description and instruction assembly defined?" [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) and [../interfaces/role-and-policy-definition-schema.md](../interfaces/role-and-policy-definition-schema.md)
- "Where is the authored task title / summary / instruction launch shape?" [../workflows/task-compose-schema.md](../workflows/task-compose-schema.md)

## Prompt Inputs And Sections

- "Which runtime surfaces feed the prompt?" [source-and-sections.md](source-and-sections.md)
- "What is the section order?" [contract.md](contract.md) and [generated/inventory.md](generated/inventory.md)
- "What should current assignment and latest checkpoint look like in the prompt?" [field-renderers.md](field-renderers.md)
- "Which exact example shows those sections with real runtime state and context transfer?" [generated/rendered-examples.md](generated/rendered-examples.md)

## Rendering Rules

- "How are artifacts rendered?" [field-renderers.md](field-renderers.md)
- "How are path-only refs rendered?" [field-renderers.md](field-renderers.md)
- "Where do `instruction`, `criteria`, `consumes`, and `produces` appear?" [source-and-sections.md](source-and-sections.md) and [field-renderers.md](field-renderers.md)
- "Where is the exact `same_session_continue` wrapper wording?" [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)
- "Where is the exact rendered `same_session_continue` wrapper example?" [generated/rendered-examples.md](generated/rendered-examples.md)

## Prompt Pack

- "Which reusable wording blocks are canonical?" [prompt-pack/README.md](prompt-pack/README.md)
- "Where are runtime-rule wording blocks?" [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md)
- "Where is the system/provider wording?" [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)
- "Where are the exact validation and reject wording blocks?" [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md)

## Generated And Secondary Live Example Material

- "Where is the machine-readable prompt catalog?" [prompt-catalog.yaml](prompt-catalog.yaml)
- "Where is the generated prompt inventory?" [generated/inventory.md](generated/inventory.md)
- "Where are rendered examples?" [generated/rendered-examples.md](generated/rendered-examples.md)
- "Where is the exact `full_prompt` / `same_session_continue` request composition and wrapper validation example?" [composition-example.md](composition-example.md)

## Validation And Reject Routes

- "Where is the prompt-layer page with exact reject wording examples?" [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md)
- "Where are the exact prompt-layer reject wording and the current API reject carrier fields?" [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md) and [../interfaces/api-schema-appendix.md](../interfaces/api-schema-appendix.md)
- "Where is the exact human-facing reject message substance?" [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md)
- "Where is the exact route-lane legality for checkpoint, boundary, and tool calls?" [../interfaces/api-surface-and-trust-lane-map.md](../interfaces/api-surface-and-trust-lane-map.md)
- "Where is the exact `boundary_precondition_failed` meaning that prompt closure wording must respect?" [../architecture/runtime-boundary-and-controller-loop-contract.md](../architecture/runtime-boundary-and-controller-loop-contract.md)

## Historical / Migration Searches

- "Where did the old prompt/artifact-layer page go?" [historical-prompt-and-artifact-layers.md](historical-prompt-and-artifact-layers.md)
- "Where did packet prose examples go?" [prompt-pack/historical-packet-prose-examples.md](prompt-pack/historical-packet-prose-examples.md)
- "Where are old dispatch-family packs and overlay pages explained?" [prompt-pack/dispatch-family-packs.md](prompt-pack/dispatch-family-packs.md) and [prompt-pack/state-and-boundary-overlays.md](prompt-pack/state-and-boundary-overlays.md)

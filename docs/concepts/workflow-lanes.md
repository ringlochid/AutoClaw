# Workflow lanes

Status: Reference

AutoClaw ships workflow lanes for different purposes. Pick a lane by the problem the run must solve, the evidence needed for closure, and the amount of coordination required.

## Engineering lanes

### Minimal

Use the minimal lane for one bounded implementation step with a fast proof loop.

- one focused worker path
- small scope
- quickest way to prove local launch and runtime materialization

### Normal

Use the normal lane for standard delivery work with a clearer review handoff.

- one implementation track
- explicit review before closure
- good default when one round of review should happen before release

### Maximal

Use the maximal lane for larger work that needs multiple coordinated tracks and shared closure evidence.

- multiple workstreams
- broader validation
- final coordination before release

### Bugfix review release

Use the bugfix lane when the work starts from a reported defect.

- triage and reproduce before patching
- keep the fix narrow
- verify the regression behavior before release

### Delivery batch

Use the delivery batch lane when a larger purpose needs package planning before execution.

- create bounded delivery units
- execute one selected package
- verify and review package evidence before release

## Product and planning lanes

### Idea discovery

Use idea discovery before committing to a build direction.

- gather evidence
- compare options
- critique scope
- recommend the next workflow shape

### Planning only

Use planning only when the output is a plan, not an implementation.

- define scope
- map work packages
- review risks and contradictions
- publish a final plan

### MVP build

Use MVP build when the goal is a thin usable slice that proves core user value.

- define MVP scope and deferrals
- implement the thin slice
- verify the demo path
- review code and product fit

### Core-only build

Use core-only build when the goal is a durable foundation layer.

- design contracts and invariants
- implement core behavior
- verify compatibility and contract behavior
- defer full-product polish

### Feature implementation

Use feature implementation for adding one feature to an existing product.

- inspect existing context
- plan integration
- review scope before patching
- verify and review the feature before release

## Non-code lanes

### Marketing campaign

Use marketing campaign for audience, positioning, and campaign planning.

- research audience and channels
- shape positioning and asset plan
- review proof, approvals, and risk
- do not externally publish from this lane

### Project management delivery

Use project management delivery for coordination without implementation.

- capture objectives
- decompose work
- review delivery risks
- publish a current delivery plan

## Exact examples

- [Design workflows and instructions](../guides/design-workflows-and-instructions.md)
- [Guide examples for workflows](../guides/examples/workflows/minimal.md)
- [Reference workflow examples](../reference/definitions/workflows/README.md)

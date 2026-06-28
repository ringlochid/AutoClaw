# Choose a workflow lane

Status: Reference

Pick a workflow lane by the purpose of the run, the evidence needed for honest closure, and the amount of coordination required.

Use the smallest lane that can prove the work is done. If two lanes look similar, choose by output: a bug fix needs reproduction and regression proof, an MVP needs proof of user value, planning-only needs a plan and no implementation, and marketing needs audience and approval evidence without external publishing.

## Quick choice

| If the run needs | Use |
| --- | --- |
| one bounded implementation step | `minimal-implement-change` |
| implementation plus one review handoff | `normal-implementation-review` |
| multiple coordinated engineering tracks | `maximal-delivery-review` |
| a reported defect fixed safely | `bugfix-review-release` |
| package planning before execution | `delivery-batch` |
| options before committing to a direction | `idea-discovery` |
| an execution plan without building | `planning-only` |
| a thin usable slice proving core value | `mvp-build` |
| a durable foundation layer | `core-only-build` |
| one feature in an existing product | `feature-implementation` |
| campaign planning without external publishing | `marketing-campaign` |
| delivery coordination without implementation | `project-management-delivery` |

## Engineering delivery lanes

### Start with minimal when

- one bounded implementation step is enough
- you want the fastest proof loop
- you are validating a new local environment or a small change

### Move to normal when

- one review handoff matters before closure
- the work is still mostly linear
- you want a cleaner release handoff than the minimal lane

### Move to maximal when

- multiple coordinated workstreams are required
- evidence needs to converge across several branches
- final closure depends on broader validation and coordination

### Use bugfix review release when

- the work starts from a reported defect
- triage or reproduction is required before patching
- the fix must stay narrow
- regression proof matters before release

### Use delivery batch when

- a larger purpose needs package planning before execution
- one selected package should be implemented before the whole batch
- package evidence needs review before release

## Product and planning lanes

### Use idea discovery when

- you need options before committing to a build direction
- the main output is a recommendation
- critique and tradeoffs matter more than implementation

### Use planning only when

- the output is a plan, not a patch
- scope, milestones, dependencies, and risks need review
- implementation should explicitly stay out of scope

### Use MVP build when

- the goal is a thin usable slice
- proof of core user value matters more than complete product polish
- product-fit review matters alongside code review

### Use core-only build when

- the goal is a durable domain, API, data, or service foundation
- contracts and invariants matter more than full UX
- launch polish should be deferred unless explicitly scoped

### Use feature implementation when

- one feature is being added to an existing product
- compatibility with existing patterns matters
- implementation, verification, and review all need to stay tied to the accepted scope

## Non-code lanes

### Use marketing campaign when

- the work is audience, positioning, channel, asset, or approval planning
- the workflow should not publish externally
- review should check proof, risk, approvals, and channel fit

### Use project management delivery when

- the work is coordination, not implementation
- objectives, packages, risks, dependencies, and status need a current plan
- the output should help humans or later workflows execute

## When lanes look similar

- choose bugfix over feature implementation when the key proof is reproduction and regression behavior
- choose MVP build over feature implementation when the key proof is core user value, not product completeness
- choose core-only build over MVP build when the output is a foundation layer, not a usable product slice
- choose planning-only over delivery batch when no implementation should happen in the run
- choose marketing campaign over project management delivery when audience, positioning, channels, and approvals define success

## Exact examples

- [Design workflows and instructions](design-workflows-and-instructions.md)
- [Minimal workflow guide example](examples/workflows/minimal.md)
- [Normal workflow guide example](examples/workflows/normal.md)
- [Maximal workflow guide example](examples/workflows/maximal.md)

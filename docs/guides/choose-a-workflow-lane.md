# Choose a workflow lane

Status: Reference

Pick the smallest workflow shape that still matches the review and coordination you need.

## Start with minimal when

- one bounded implementation step is enough
- you want the fastest proof loop
- you are validating a new local environment or a small change

## Move to normal when

- one review handoff matters before closure
- the work is still mostly linear
- you want a cleaner release handoff than the minimal lane

## Move to maximal when

- multiple coordinated workstreams are required
- evidence needs to converge across several branches
- final closure depends on broader validation and coordination

## Pick a purpose lane when

- `idea-discovery`: you need options and a recommendation before build work
- `planning-only`: you need a scoped plan and acceptance criteria without implementation
- `mvp-build`: you need a thin usable slice proving core user value
- `core-only-build`: you need foundation contracts, APIs, data, or domain core without full-product polish
- `feature-implementation`: you need one integrated feature in an existing product
- `bugfix-review-release`: you need reproduction, fix, regression proof, review, and release
- `marketing-campaign`: you need audience, positioning, asset, and approval planning without external publishing
- `project-management-delivery`: you need decomposition, risk, dependency, and status planning without implementation

## Exact examples

- [Design workflows and instructions](design-workflows-and-instructions.md)
- [Minimal workflow guide example](examples/workflows/minimal.md)
- [Normal workflow guide example](examples/workflows/normal.md)
- [Maximal workflow guide example](examples/workflows/maximal.md)

# Idea discovery workflow example

Status: Reference

This example mirrors the shipped `idea-discovery` workflow fixture.

```yaml
kind: workflow
id: idea-discovery
description: Gather evidence, compare directions, critique scope, and recommend a direction without implementation.
root:
  id: root
  role: root_planning_lead
  policy: standard-root-planning
  description: Preserve the idea-discovery purpose and close only when the recommendation is evidence-backed and non-implementation scope is clear.
  instruction: >-
    Route research, option shaping, critique, and recommendation work as separate evidence steps. Do not let discovery drift into build work.
  criteria:
    - slot: idea_discovery_criteria
      description: Hard criteria for closing idea discovery.
      criteria:
        - final recommendation explains the problem, options, tradeoffs, and evidence
        - recommendation states what should be built, deferred, or rejected
        - no implementation, publication, or external commitment is performed by this workflow
  children:
    - id: gather_context
      role: researcher
      policy: standard-worker
      description: Gather focused evidence for the idea, audience, constraints, and decision.
      instruction: >-
        Publish only evidence that changes option selection, feasibility, or next-step direction.
      produces:
        artifacts:
          - slot: discovery_context
            file_hint: discovery_context.md
            description: Evidence, constraints, uncertainties, and decision implications for the idea.
    - id: shape_options
      role: product_planner
      policy: standard-product-planning
      description: Shape candidate directions from discovery evidence.
      instruction: >-
        Compare options by user value, feasibility, risk, scope, and confidence. Do not choose by taste alone.
      consumes:
        artifacts:
          - slot: discovery_context
      produces:
        artifacts:
          - slot: option_brief
            file_hint: option_brief.md
            description: Candidate directions with tradeoffs, scope, and acceptance implications.
    - id: critique_options
      role: scope_reviewer
      policy: standard-scope-review
      description: Critique candidate directions for weak evidence, contradictions, and scope risk.
      instruction: >-
        Identify overreach, missing proof, hidden dependencies, and contradictions before recommendation.
      consumes:
        artifacts:
          - slot: option_brief
        criteria:
          - slot: idea_discovery_criteria
      produces:
        artifacts:
          - slot: scope_critique
            file_hint: scope_critique.md
            description: Critique of candidate directions and required corrections.
    - id: recommend_direction
      role: product_reviewer
      policy: standard-scope-review
      description: Recommend the next direction from evidence, options, and critique.
      instruction: >-
        Publish the recommendation, rationale, rejected alternatives, and safest next workflow shape.
      consumes:
        artifacts:
          - slot: discovery_context
          - slot: option_brief
          - slot: scope_critique
        criteria:
          - slot: idea_discovery_criteria
      produces:
        artifacts:
          - slot: recommendation_report
            file_hint: recommendation_report.md
            description: Evidence-backed recommendation and next workflow shape.
```


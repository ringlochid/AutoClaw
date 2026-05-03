# Normal workflow reference

Status: Target

This page provides the canonical normal workflow example for the live v1 contract.

```mermaid
flowchart TD
    A["root"] --> B["implementation_subtree"]
    A --> C["release_closure"]
    B --> D["investigate_issue"]
    B --> E["implement_change"]
    B --> F["review_change"]
```

Figure: the normal example adds one parent subtree and one ordinary release child, while keeping review and release as ordinary authored work.

The YAML below is shown in canonical file form for CLI scan/import.

```yaml
kind: workflow
id: normal-parent-first-release
description: Execute one implementation subtree, review it through ordinary child work, and release only after root verifies current evidence.
root:
  id: root
  role: root_planning_lead
  policy: standard-root-planning
  description: Verify implementation and release evidence before final closure.
  criteria:
    - slot: root_delivery_rules
      description: Root acceptance criteria.
      criteria:
        - final closure happens only after root verifies current code, review, and test evidence
    - slot: root_closure_criteria
      description: Final release criteria.
      criteria:
        - release work uses only surfaced evidence and current criteria
        - release work does not reopen implementation scope
  children:
    - id: implementation_subtree
      role: planning_lead
      policy: standard-parent-planning
      description: Coordinate investigation, implementation, and ordinary review work inside the bounded subtree only.
      criteria:
        - slot: implementation_subtree_requirements
          description: Local execution requirements for this implementation subtree.
          criteria:
            - findings and implementation stay inside the current subtree
            - review evidence must address the current patch and verification evidence
      child_defaults:
        criteria:
          - implementation_subtree_requirements
      children:
        - id: investigate_issue
          role: researcher
          description: Inspect the issue and publish a findings report for downstream implementation.
          produces:
            artifacts:
              - slot: findings_report
                file_hint: findings_report.md
                description: Findings needed by downstream implementation.
        - id: implement_change
          role: engineer
          policy: standard-worker
          description: Implement the change and publish patch plus verification evidence.
          consumes:
            artifacts:
              - slot: findings_report
          criteria:
            - slot: implement_change_delivery_criteria
              description: Delivery criteria for the implementation step.
              criteria:
                - patch matches the scoped assignment
                - verification evidence supports the claimed fix
          produces:
            artifacts:
              - slot: change_patch
                file_hint: change_patch.diff
                description: Patch for the scoped change.
              - slot: verification_report
                file_hint: verification_report.md
                description: Verification evidence for the scoped change.
        - id: review_change
          role: reviewer
          policy: standard-review
          description: Review the implementation evidence and publish a bounded review report.
          consumes:
            artifacts:
              - slot: change_patch
              - slot: verification_report
            criteria:
              - slot: implementation_subtree_requirements
          produces:
            artifacts:
              - slot: review_report
                file_hint: review_report.md
                description: Review findings and review disposition for the subtree.
    - id: release_closure
      role: release_operator
      policy: standard-release
      description: Perform the final bounded release work from current surfaced evidence.
      consumes:
        artifacts:
          - slot: change_patch
          - slot: verification_report
          - slot: review_report
        criteria:
          - slot: root_closure_criteria
      produces:
        artifacts:
          - slot: closure_report
            file_hint: closure_report.md
            description: Final bounded release or closure report.
```

## Expected runtime path

Typical execution order is:

1. root dispatch
2. `implementation_subtree` assignment
3. `investigate_issue`
4. `implement_change`
5. `review_change`
6. root review of current subtree evidence
7. `release_closure`
8. root final release decision

The authored tree does not force that exact order, but it gives runtime enough structure to make each step explicit through assignments, checkpoints, and durable artifact refs.

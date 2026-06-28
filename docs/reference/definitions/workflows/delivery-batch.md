# Delivery batch workflow example

Status: Reference

This example mirrors the shipped `delivery-batch` workflow fixture.

```yaml
kind: workflow
id: delivery-batch
description: Turn a larger purpose into bounded delivery units, execute one unit, verify, review, and release.
root:
  id: root
  role: root_planning_lead
  policy: standard-root-planning
  description: Preserve the higher-level purpose, delegate package planning, and release only after implementation, verification, and review evidence agree.
  instruction: Start purpose-first. Use the package plan to guide assignment, but challenge weak evidence before release.
  criteria:
    - slot: package_release_criteria
      description: Hard criteria for releasing a completed delivery unit.
      criteria:
        - package plan explains purpose, scope, dependencies, artifacts, criteria, and verification gates
        - implementation, verification, and review evidence all refer to the same package scope
        - unresolved high-risk items are fixed, explicitly deferred by criteria, or block release
  children:
    - id: plan_packages
      role: delivery_planner
      policy: standard-delivery-planning
      description: Convert the larger purpose into bounded delivery units and gates.
      instruction: Produce scoped packages with sequencing, dependencies, consumes, produces, criteria, review, verification, and risks.
      produces:
        artifacts:
          - slot: package_plan
            file_hint: package_plan.md
            description: Purpose-oriented package plan and execution gates.
    - id: execute_package
      role: planning_lead
      policy: standard-parent-planning
      description: Coordinate implementation, verification, and review for one package inside the owned subtree.
      instruction: Use child mission packets and current evidence. Replan only when package shape or dependencies are wrong.
      consumes:
        artifacts:
          - slot: package_plan
      criteria:
        - slot: package_subtree_criteria
          description: Hard criteria for package subtree work.
          criteria:
            - children stay inside the selected package scope
            - checkpoint handoffs explain evidence read, criteria status, and next action
            - verification and review evidence agree before subtree green
      child_defaults:
        criteria:
          - package_subtree_criteria
      children:
        - id: implement_package
          role: engineer
          policy: standard-worker
          description: Implement the selected package and publish the required patch.
          instruction: Read the package plan and criteria first. Keep implementation scoped and publish residual risk.
          consumes:
            artifacts:
              - slot: package_plan
          produces:
            artifacts:
              - slot: package_patch
                file_hint: package_patch.diff
                description: Scoped package implementation patch.
        - id: verify_package
          role: test_verifier
          policy: standard-verification
          description: Verify the selected package against current criteria.
          instruction: Publish reproducible evidence, untested areas, and blockers.
          consumes:
            artifacts:
              - slot: package_plan
              - slot: package_patch
          produces:
            artifacts:
              - slot: package_verification_report
                file_hint: package_verification_report.md
                description: Verification evidence for the selected package.
        - id: review_package
          role: code_reviewer
          policy: standard-review
          description: Critically review package implementation and verification evidence.
          instruction: Publish findings with severity, evidence, reasoning, approval or rejection, and residual risk.
          consumes:
            artifacts:
              - slot: package_patch
              - slot: package_verification_report
            criteria:
              - slot: package_subtree_criteria
          produces:
            artifacts:
              - slot: package_review_report
                file_hint: package_review_report.md
                description: Review findings for the selected package.
    - id: release_closure
      role: release_operator
      policy: standard-release
      description: Perform final bounded release work for the selected package.
      instruction: Use only package plan, implementation, verification, review evidence, and release criteria. Report gaps instead of reopening scope.
      consumes:
        artifacts:
          - slot: package_plan
          - slot: package_patch
          - slot: package_verification_report
          - slot: package_review_report
        criteria:
          - slot: package_release_criteria
      produces:
        artifacts:
          - slot: closure_report
            file_hint: closure_report.md
            description: Final release or closure report for the selected package.
```

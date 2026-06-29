# Maximal workflow example

Status: Reference

This example mirrors the shipped `maximal-parent-first-release` workflow fixture.

```yaml
kind: workflow
id: maximal-parent-first-release
description: Execute staged discovery, planning, implementation, review, QA, and release work for the authentication overhaul with purpose-first parent control.
root:
  id: root
  role: root_planning_lead
  policy: standard-root-planning
  description: Preserve the authentication-overhaul purpose, coordinate staged work, and decide final bounded closure from current evidence.
  instruction: >-
    Read manifest, root assignment, child checkpoints, surfaced refs, criteria, and task-memory hints. Challenge weak evidence before release.
  criteria:
    - slot: root_delivery_rules
      description: Shared delivery rules before final closure.
      criteria:
        - unresolved high-risk issues block green
        - final release evidence cites the exact current refs consumed
        - root routes weak evidence to review, verification, failure analysis, or replan before release
    - slot: root_closure_criteria
      description: Final release criteria.
      criteria:
        - release work uses only surfaced release evidence and current criteria
        - release work does not reopen planning or implementation scope
  children:
    - id: discovery
      role: planning_lead
      policy: standard-parent-planning
      description: Coordinate discovery work and verify that discovery outputs are useful before downstream planning.
      instruction: >-
        Keep discovery scoped to evidence needed for downstream planning. Preserve rejected leads and uncertainty in checkpoints.
      criteria:
        - slot: discovery_requirements
          description: Shared discovery requirements.
          criteria:
            - findings are internally consistent
            - findings are specific enough for downstream planning
            - open uncertainties are named before downstream assignment
      child_defaults:
        criteria:
          - discovery_requirements
      children:
        - id: gather_evidence
          role: researcher
          description: Gather discovery evidence and publish findings plus notes needed by downstream stages.
          instruction: >-
            Publish discovery findings, raw notes, uncertainties, and next-decision implications only.
          produces:
            artifacts:
              - slot: findings_report
                file_hint: findings_report.md
                description: Discovery findings for downstream planning and implementation.
              - slot: discovery_notes
                file_hint: discovery_notes.md
                description: Raw discovery notes for the subtree.
    - id: implementation_loop
      role: planning_lead
      policy: standard-parent-planning
      description: Coordinate planning, implementation, review, and QA from current surfaced discovery outputs.
      instruction: >-
        Prepare child mission packets with purpose, mode, refs, criteria, required outputs, known failures, and untouched scope.
      criteria:
        - slot: implementation_loop_requirements
          description: Shared implementation requirements.
          criteria:
            - implementation stays inside the assigned subtree
            - verification and review evidence must be mutually consistent before green
            - child checkpoints explain evidence read, reasoning, criteria status, and next action
        - slot: implementation_review_criteria
          description: Review criteria for implementation verification.
          criteria:
            - patch and verification evidence are mutually consistent
            - open risks are either closed or explicitly documented
      child_defaults:
        criteria:
          - implementation_loop_requirements
      children:
        - id: plan_iteration
          role: planner
          description: Publish the current delivery plan from surfaced discovery evidence.
          instruction: >-
            Convert discovery findings into bounded sequencing, dependencies, criteria, risks, and verification gates. Do not implement the plan.
          consumes:
            artifacts:
              - slot: findings_report
          produces:
            artifacts:
              - slot: delivery_plan
                file_hint: delivery_plan.md
                description: Current implementation plan for the subtree.
        - id: implement_change
          role: engineer
          policy: standard-worker
          description: Implement the scoped change and publish patch plus verification evidence.
          instruction: >-
            Read findings, plan, and criteria before editing. Keep patch scoped, verify behavior, and checkpoint residual risks.
          consumes:
            artifacts:
              - slot: findings_report
              - slot: delivery_plan
          criteria:
            - slot: implement_change_delivery_criteria
              description: Delivery criteria for engineering.
              criteria:
                - patch matches the scoped assignment
                - verification evidence supports the claimed fix
                - checkpoint names evidence read, checks run, and any residual risk
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
          description: Critically review implementation evidence and publish an ordinary review report.
          instruction: >-
            Review current patch, verification evidence, and criteria. Record approval, rejection, evidence gaps, and residual risk.
          consumes:
            artifacts:
              - slot: change_patch
              - slot: verification_report
            criteria:
              - slot: implementation_review_criteria
          produces:
            artifacts:
              - slot: review_report
                file_hint: review_report.md
                description: Review findings and disposition for the subtree.
        - id: qa_sweep
          role: architect
          description: Run a bounded QA or architecture sweep over current implementation evidence.
          instruction: >-
            Inspect current implementation, verification, review evidence, and criteria only. Publish risk tradeoffs and pass/fail reasoning.
          consumes:
            artifacts:
              - slot: change_patch
              - slot: verification_report
              - slot: review_report
          produces:
            artifacts:
              - slot: qa_report
                file_hint: qa_report.md
                description: QA and architecture sweep findings for the subtree.
    - id: release_closure
      role: release_operator
      policy: standard-release
      description: Perform final bounded release work from current surfaced evidence.
      instruction: >-
        Use only surfaced release evidence and closure criteria. Report release gaps instead of reopening planning or implementation scope.
      consumes:
        artifacts:
          - slot: findings_report
          - slot: delivery_plan
          - slot: change_patch
          - slot: verification_report
          - slot: review_report
          - slot: qa_report
        criteria:
          - slot: root_closure_criteria
      produces:
        artifacts:
          - slot: closure_report
            file_hint: closure_report.md
            description: Final bounded release or closure report.
```

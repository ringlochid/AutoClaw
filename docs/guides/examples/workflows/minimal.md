# Minimal workflow guide example

Status: Reference

Use the minimal workflow when one bounded engineering change plus direct verification is enough.

This example teaches:

- one parent/root lane can verify one worker lane cleanly
- criteria and produced artifact slots stay explicit
- it is the quickest path to prove local task start and runtime outputs

```yaml
kind: workflow
id: minimal-implement-change
description: Execute one bounded engineering change under parent ownership.
root:
  id: root
  role: planning_lead
  description: Verify one bounded engineering worker and release only when current evidence is sufficient.
  instruction: Keep the release decision tied to current controller evidence.
  criteria:
    - slot: implementation_rules
      description: Parent acceptance criteria for the bounded engineering child.
      criteria:
        - keep the child inside the current bounded assignment
        - publish patch and verification evidence only through declared produce slots
  children:
    - id: implement_change
      role: engineer
      policy: standard-worker
      description: Implement the change and publish patch plus verification evidence only for the current bounded assignment.
      instruction: Read the current criteria before editing and publish only scoped patch and verification evidence.
      criteria:
        - slot: implement_change_delivery_criteria
          description: Delivery criteria for the bounded engineering change.
          criteria:
            - patch is limited to the assigned path
            - verification evidence demonstrates the intended fix
      produces:
        artifacts:
          - slot: change_patch
            file_hint: change_patch.diff
            description: Patch for the bounded change.
          - slot: verification_report
            file_hint: verification_report.md
            description: Verification evidence for the bounded change.
```

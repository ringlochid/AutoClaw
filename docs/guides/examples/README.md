# Guide examples

Use examples as patterns, not as a fixed menu of everything AutoClaw can do.

## How to use examples

1. Read [design workflows and instructions](../design-workflows-and-instructions.md).
2. Pick the closest example by workflow shape, not by role name.
3. Copy only the parts that match your evidence path.
4. Replace task-specific criteria, artifacts, scope limits, and tool assumptions.
5. Run a small pilot before turning the pattern into a larger workflow.

The shipped examples show valid shapes. Your definition set should still be purpose-specific.

## Example families

- [Roles](roles/README.md)
- [Policies](policies/README.md)
- [Workflows](workflows/README.md)
- [Task-compose](task-compose/README.md)

## Check before copying

- Does the role match the node kind?
- Does the policy budget match root/parent/worker authority?
- Does the workflow evidence path fit your task?
- Are required tools available in your harness?
- Does task-compose omit roots intentionally, or bind the right workspace and context roots?

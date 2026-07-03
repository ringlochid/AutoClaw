# Recover or replan a task

Use this guide when you need to operate a task that stopped making useful progress, or when you are designing a workflow that may need structural recovery.

Recovery starts with runtime truth. Replan belongs in workflow instructions only when a parent or root node is allowed to change the running node tree.

## Inspect first

Before changing anything, inspect:

- the workflow manifest
- the current assignment
- latest relevant checkpoints
- published artifacts
- operator snapshot and trace
- pending human requests or command runs

Do not treat a quiet dispatch as proof that the task is stuck. A task may be waiting on a controller-owned human request, command run, or provider handoff.

## Operator recovery

Use operator recovery when the running task state needs human action:

- resolve a pending human request
- inspect or cancel a command run
- pause, continue, or cancel a task
- diagnose weak, missing, or contradictory evidence
- decide whether a follow-up task or workflow change is needed

Do not recover by editing generated task files. Use the console, operator read surfaces, and task-control commands so controller state stays authoritative.

## Replan in workflow design

Mention replan in a workflow only when the node owns routing or closure judgment.

Good places:

- root node instruction for whole-task purpose mismatch
- parent node instruction for subtree shape mismatch
- failure-analysis worker instruction that asks for a replan recommendation
- reviewer or verifier instruction that asks them to flag wrong criteria or missing stages

Bad places:

- ordinary worker instructions
- fixed one-worker workflows with no alternate shape
- generic role text shared by unrelated workers
- filler such as "retry or replan if stuck"

Workers can report that the workflow shape is wrong. Parent and root nodes decide whether to change the structure.

## Good replan triggers

Use replan when current evidence shows the workflow shape is wrong:

- required work is missing from the node tree
- dependencies force work in the wrong order
- review or verification criteria judge the wrong output
- repeated child failures show assignment shape mismatch, not weak execution
- user intent and the current node tree no longer match
- a needed specialist, review step, or failure-analysis step is absent

Replan changes structure. It is not another attempt at the same assignment.

## Do not replan for this

Do not use replan when the current shape is still honest:

- one worker failed because of a small fixable mistake
- evidence is weak and needs review or verification
- a human decision is missing
- a long command is still running
- a required external fact, permission, or tool is unavailable
- the workflow should close as blocked from current evidence

Use retry for another attempt at the same assignment shape. Use human request for human judgment. Use command-run capability for long command work. Use blocked closure when progress depends on unavailable external state.

## Instruction patterns

Good parent/root instruction:

```yaml
instruction: >-
    Inspect child checkpoints, surfaced refs, criteria, and artifacts before
    assigning the next child. If the current subtree cannot produce honest closure
    evidence, use structural replan to add, update, or remove the smallest needed
    child inside the owned subtree, then reread the manifest before assigning work.
    Do not replan for weak execution when review, verification, or failure analysis
    can answer the gap.
```

Good worker instruction:

```yaml
instruction: >-
    Stay inside the current assignment. If the workflow shape appears wrong,
    record the evidence and recommend the smallest replan; do not edit the node
    tree yourself.
```

Bad instruction:

```yaml
instruction: >-
    If anything goes wrong, retry, replan, or block.
```

That does not say who owns the decision, what evidence proves shape mismatch, or what smaller recovery path should be tried first.

## Design checklist

Before shipping a workflow that mentions replan, check:

- only parent/root nodes are told to perform structural replan
- workers are told to report or recommend, not mutate the node tree
- criteria say what evidence can block release
- failure-analysis or review nodes exist when repeated failure is likely
- human request capability is used for human judgment, not workflow shape
- command-run capability is used for long command work, not ordinary retry
- blocked closure is reserved for unavailable facts, permissions, tools, or external state

## Related pages

- [Inspect and control a task](inspect-and-control-a-task.md)
- [Handle ambiguity and incidents](handle-ambiguity-and-incidents.md)
- [Design workflows and instructions](design-workflows-and-instructions.md)
- [Write a workflow](write-a-workflow.md)
- [Runtime model](../concepts/runtime-model.md)

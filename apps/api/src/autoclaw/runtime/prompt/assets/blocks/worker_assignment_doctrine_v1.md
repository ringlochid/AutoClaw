## Worker Doctrine

Start by understanding the task purpose, current assignment, constraints, criteria, consumes, and required produces before acting.

Then operate in the assigned mode instead of redesigning the whole workflow.

| Mode                   | Expected behavior                                                                                  |
| ---------------------- | -------------------------------------------------------------------------------------------------- |
| Implementation         | Produce bounded changes plus verification evidence.                                                |
| Planning               | Produce a concrete plan artifact and do not also implement it unless explicitly assigned.          |
| Review or verification | Judge current evidence against criteria and explain approval, rejection, gaps, and residual risks. |
| Failure analysis       | Explain root cause, uncertainty, next experiment, and which role should act next.                  |

Rules:

- Use workspace reads, surfaced refs, and task-memory search hints to acquire enough truth for this assignment.
- Do not rely on hidden chat memory or broad directory scanning.
- If evidence is missing, contradictory, or outside scope, checkpoint the exact gap and choose `retry` or `blocked` only when the current assignment justifies it.
- Before terminal closure, write a checkpoint that preserves intent, evidence read, reasoning, criteria status, produced artifacts, remaining risks, and the next action.

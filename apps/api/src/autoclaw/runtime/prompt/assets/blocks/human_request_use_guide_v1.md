### Human Request Use Guide

Use `open_human_request` only when the current effective capability allows the exact human request kind you need.

| Kind        | Use                                                                                       |
| ----------- | ----------------------------------------------------------------------------------------- |
| `direction` | Ask the human to choose scope, priority, tradeoff, or next direction.                     |
| `approval`  | Ask before a sensitive, risky, destructive, external, or policy-gated action.             |
| `input`     | Ask for missing structured facts or values that cannot be recovered from surfaced truth.  |
| `review`    | Ask the human to inspect, judge, or accept evidence before the node continues.            |

Rules:

- Pick one request kind; if that kind is denied, do not substitute a different kind just to get a human involved.
- Human request is not a workflow boundary, task continue action, generic chat message, or routine status update.
- Do not open a human request when a bounded child assignment, checkpoint, retry, or blocked closure is the correct runtime move.
- Ask only for decisions or inputs that materially change the next legal action.
- Keep each item concrete. For `direction`, `approval`, and `review`, provide options and a `recommended_option` when you can. For `input`, provide `input_payload_schema`.
- Fill `title`, `summary`, `items`, `suggested_human_instruction`, and optional `timeout.default_behavior` so the human knows how to answer and what happens if they do not.
- After `open_human_request` succeeds, stop this dispatch turn and wait for controller redispatch with human-request continuation context.

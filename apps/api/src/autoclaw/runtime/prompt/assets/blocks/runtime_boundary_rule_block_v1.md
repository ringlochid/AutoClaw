### Runtime Boundary Rules

Use boundaries exactly this way.

| Boundary            | Rule                                                                                                                                                                                                                                                               |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `dispatch`          | Controller -> node ingress.                                                                                                                                                                                                                                        |
| `record_checkpoint` | Durable publication lane for what happened and what should happen next.                                                                                                                                                                                            |
| `yield`             | Non-terminal current parent/root closure; legal only after exactly one staged child assignment already exists for this open dispatch.                                                                                                                              |
| `green`             | Terminal current-node success closure after a terminal green checkpoint exists and any required durable publication or release basis already exists.                                                                                                               |
| `retry`             | Terminal current-node retry closure after a terminal retry checkpoint exists; retry keeps the same assignment, mints a new attempt, and uses `full_prompt`.                                                                                                        |
| `blocked`           | Terminal current-node blocked closure after a terminal blocked checkpoint exists. Non-root parent `blocked` returns control to its parent without requiring all children to have run. Root whole-flow `blocked` closure also requires committed `release_blocked`. |

Rules:

- Structural CRUD alone does not create `yield` basis and does not justify `yield`.
- `release_green` and root `release_blocked` do not create `yield` basis. They are terminal preconditions only.
- When one staged child assignment exists and the dispatch stays non-terminal, close with `yield`.
- `yield` is boundary truth only. It is not a checkpoint outcome.
- `green | retry | blocked` are terminal checkpoint outcomes and closing boundaries.
- `blocked` is a current-node terminal boundary; only root whole-flow closure needs `release_blocked`.
- After a successful `yield`, `green`, `retry`, or `blocked`, stop the current outer assistant turn immediately. Do not keep reasoning, make another tool call, or append extra prose after the successful boundary result.

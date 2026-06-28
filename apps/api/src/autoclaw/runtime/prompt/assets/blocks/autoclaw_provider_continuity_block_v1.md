## Provider Continuity

Provider continuity is transport only.

Rules:

- Provider session state, adapter delivery state, raw provider event names, and transport acknowledgements do not become runtime truth by themselves.
- Do not infer assignment success from provider transport success.
- Use current runtime boundaries, tools, checkpoints, and surfaced refs rather than raw provider callback-era wording.

## Live Send Modes

| Send mode | Meaning |
| --- | --- |
| `full_prompt` | Fresh inline send of the full prompt package; required for every live dispatch, including same-attempt parent/root redispatch. |

Retry is node-self only. It keeps the same assignment, mints a new attempt, uses `full_prompt`, and rereads the prior terminal checkpoint as durable handover.

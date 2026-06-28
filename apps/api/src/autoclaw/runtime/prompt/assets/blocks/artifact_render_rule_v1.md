### Durable Artifact Refs

When you cite a surfaced durable artifact ref in a prompt, checkpoint, or reasoning, use this compact shape:

| Field         | Meaning                                            |
| ------------- | -------------------------------------------------- |
| `slot`        | The produced or consumed artifact slot name.       |
| `version`     | The current durable version surfaced by runtime.   |
| `path`        | The local task-root path to read.                  |
| `description` | The runtime-projected description of the artifact. |

Rules:

- Use this shape only for runtime-resolved durable refs such as `consumed_durable_refs` and checkpoint artifact lists.
- When the same artifact slot appears both in semantic assignment/checkpoint prose and in surfaced `consumed_durable_refs`, prefer the surfaced current ref for slot, path, and version truth.
- Do not inline controller-only pointer fields such as currentness history, assignment lineage, or attempt lineage.
- Do not ask the node to infer meaning from filenames like `latest.md` or from directory scans.
- Do not turn semantic assignment `produces` requirements into fake published refs.

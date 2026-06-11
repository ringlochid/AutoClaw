# Create your first definition set

Status: Reference

The smallest useful definition set for the shipped minimal lane is two roles, one policy, one workflow, and one task-compose file that launches the workflow.

## Start from shipped examples

Use the public reference examples as your exact starter surface for the shipped minimal lane.

Copy the fenced YAML from each reference page into these local files:

- `planning_lead.yaml` from [Planning lead role](../reference/definitions/roles/planning-lead.md)
- `engineer.yaml` from [Engineer role](../reference/definitions/roles/engineer.md)
- `standard_worker.yaml` from [Standard worker policy](../reference/definitions/policies/standard-worker.md)
- `minimal_implement_change.yaml` from [Minimal workflow](../reference/definitions/workflows/minimal.md)
- `task-compose.yaml` from [Minimal task-compose example](../reference/definitions/task-compose/minimal.md)

Only the fenced YAML body should be copied into those `.yaml` files. The reference pages are documentation wrappers around the example content.

## Import the definitions

Upload each definition file explicitly:

```bash
autoclaw definitions import --file ./planning_lead.yaml
autoclaw definitions import --file ./engineer.yaml
autoclaw definitions import --file ./standard_worker.yaml
autoclaw definitions import --file ./minimal_implement_change.yaml
```

The current shipped root CLI wrapper imports one definition file at a time. The minimal workflow does not require `standard_root_planning.yaml`; that policy becomes relevant when you move up to the normal or maximal workflow lanes.

## Launch it

Create a task-compose file that references the workflow, then start it with:

```bash
autoclaw task-compose start --file ./task-compose.yaml
```

## Teaching examples

If you want the shorter explanation-first pages before the exact YAML, start here:

- [Guide role examples](examples/roles/planning-lead.md)
- [Guide policy examples](examples/policies/standard-worker.md)
- [Guide workflow examples](examples/workflows/minimal.md)
- [Guide task-compose examples](examples/task-compose/minimal.md)

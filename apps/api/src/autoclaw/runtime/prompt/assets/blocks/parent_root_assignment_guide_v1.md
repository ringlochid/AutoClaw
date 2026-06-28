### Parent/Root Assignment Writing Guide

When you prepare a child assignment, do bounded research first.

Start from:

1. Current workflow manifest.
2. Current assignment.
3. Latest relevant checkpoint.
4. Surfaced `consumed_durable_refs`.

Inspect additional workspace, context, or source files only until you can answer:

- What exact problem or question does the child own?
- Which surfaced durable refs and constraints should the child trust first?
- Which interfaces, module boundaries, contracts, side effects, or consumers might the child need to respect?
- Which test scenes or proof lanes would convince you without redoing the child's work?
- Which owner docs, references, examples, or troubleshooting notes should be updated, and which docs should be left alone?
- What evidence or outputs must the child return?
- What scope boundaries or untouched areas protect the rest of the task?

#### Assignment Fields

| Field                                         | Use                                                                                                                                                               |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `assignment_intent.summary`                   | One crisp owned objective or question.                                                                                                                            |
| `assignment_intent.instruction`               | How the child should acquire truth before acting: what to read first, what to compare, what evidence to return, and any required sequencing or acceptance nuance. |
| `supplemental_durable_context.artifact_slots` | Durable artifact slots the child should trust or compare against.                                                                                                 |
| `supplemental_durable_context.criteria_slots` | Acceptance or guardrail criteria that must govern the child's decisions.                                                                                          |
| `transient_surfaces`                          | Array/list of short-lived `{ path, description }` objects that runtime projects to the child as `transient_refs`.                                                 |
| `task_memory_search_hints`                    | Semantic retrieval prompts for prior defects, rejected approaches, root causes, or artifact names.                                                                |

Write the child brief as an acquisition plan, not just loose assignment prose.

Ask the child to return the interface map, test-scene map, or documentation navigation only when that judgment is needed for this slice.

#### Refs and Slots

Parent/root assignment authors do not write concrete `consumed_durable_refs` for the child.

Use:

- `artifact_slots` and `criteria_slots` to tell runtime which current durable refs to surface to the child.
- `transient_surfaces` as a list of `{ path, description }` objects for short-lived notes or local context that help this turn but should not become durable truth.
- `task_memory_search_hints` for semantic retrieval prompts, not generic tags.

Runtime projects accepted `transient_surfaces` to the child as `transient_refs`; do not author projected `transient_refs` directly in `assign_child`.

JSON shape is an array of objects: `[{ "path": "...", "description": "..." }, { "path": "...", "description": "..." }]`.

In `instruction`, tell the child which surfaced durable refs and transient refs to read first, what question to answer, and what evidence or recommendation to return.

Use `task_memory_search_hints` as semantic retrieval prompts for prior defects, rejected approaches, root causes, or artifact names.

Avoid generic hints like `ui`, `bug`, or `page`.

Bad child brief:

    assign_child:
      child_node_key: fix_task_start
      assignment_intent:
        summary: Check the page and fix issues.
        instruction: null
      task_memory_search_hints:
        - task start
        - bug

Better child assignment:

    assign_child:
      child_node_key: verify_task_start_cta
      assignment_intent:
        summary: Verify Task Start CTA state and nav behavior on the current page.
        instruction: >
          Read the latest review checkpoint, surfaced page artifacts, and transient
          browser note first. Identify the UI contract and responsive test scenes
          before changing source. If you patch, keep the change scoped to Task Start
          only and return exact artifact paths, checks run, docs touched or
          intentionally skipped, plus the next blocker if the page still fails.
      supplemental_durable_context:
        artifact_slots:
          - slot: page_html
          - slot: page_review_report
        criteria_slots:
          - slot: page_review_acceptance
      transient_surfaces:
        - path: tmp/transfers/task-start-browser-note.md
          description: Browser note showing 390px header overflow after latest review artifact.
        - path: tmp/transfers/task-start-viewport-note.md
          description: Exact viewport notes for desktop and mobile review scenes.
      task_memory_search_hints:
        - task start prior CTA rejection state
        - task start nav artifact leak guardrail

Question-style child assignment:

    assign_child:
      child_node_key: plan_task_start_fix
      assignment_intent:
        summary: Map Task Start interface and proof plan before implementation.
        instruction: >
          Question to answer: which source modules, rendered UI contracts, and
          responsive scenes must an implementer respect to fix Task Start safely?
          Read the surfaced page artifact, latest review checkpoint, acceptance
          criteria, and transient open-question note first. Return an interface map,
          recommended implementation slice, proof lanes, docs update recommendation,
          and any uncertainty. Do not patch source in this assignment.
      supplemental_durable_context:
        artifact_slots:
          - slot: page_html
          - slot: page_review_report
        criteria_slots:
          - slot: page_review_acceptance
      transient_surfaces:
        - path: tmp/transfers/task-start-open-question.md
          description: Parent's current uncertainty about whether CTA width or nav wrap owns the failure.
        - path: tmp/transfers/task-start-proof-lanes.md
          description: Candidate proof lanes the parent wants compared before implementation.
      task_memory_search_hints:
        - task start prior responsive overflow cause
        - task start proof lane rejection history

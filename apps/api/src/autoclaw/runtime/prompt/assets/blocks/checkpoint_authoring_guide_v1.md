### Checkpoint Authoring Guide

Treat every checkpoint as a durable handoff, not a diary entry or polished status report.

Write only the decision-relevant delta that the next reader should not have to rediscover.

#### Required Shape

| Field                      | Use                                                                                                          |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `handoff.summary`          | What changed, what was learned, or what failed in a way that materially affects the next move.               |
| `handoff.next_step`        | One concrete next action, not a vague continuation note.                                                     |
| `handoff.blockers`         | Only blockers that actually change execution.                                                                |
| `handoff.risks`            | Only risks that affect routing, quality, or release confidence.                                              |
| `produced_artifacts`       | Exact durable claims you are making now: one `artifact` claim per produced slot plus the produced file path. |
| `transient_surfaces`       | Array/list of temporary `{ path, description }` objects that genuinely help the next turn start faster.      |
| `task_memory_search_hints` | Semantic retrieval prompts for this exact defect, rejection, root cause, or artifact thread.                 |

Rules:

- If no durable output exists yet, omit `produced_artifacts` rather than guessing.
- Author `transient_surfaces` as a list of `{ path, description }` objects; omit the field when there is no temporary carryover.
- A terminal `green` checkpoint must include or already have every required durable publication for the current assignment.
- Before boundary closure, a later terminal checkpoint may supersede an earlier terminal checkpoint; use that only to correct the latest terminal outcome, not as a progress log.
- Use `task_memory_search_hints` as semantic retrieval prompts for this exact defect, rejection, root cause, or artifact thread.
- Do not use generic search hints like `retry`, `fix`, or `bug`.
- If prose mentions an older artifact path or prior version for a slot that also appears in surfaced current refs later, that older mention is history only, not current truth.

Bad checkpoint:

    record_checkpoint:
      checkpoint_kind: progress
      outcome: green
      handoff:
        summary: Made progress, still checking.
        next_step: Continue.
      task_memory_search_hints:
        - fix
        - retry

Better progress checkpoint:

    record_checkpoint:
      checkpoint_kind: progress
      outcome: null
      handoff:
        summary: Reproduced Task Start header overflow at `390px`. No source patch
          yet. The failure comes from CTA min-width plus nav wrap.
        next_step: Assign implementation to reduce the CTA min-width in Task Start
          only, then rerender desktop and mobile.
        risks:
          - The fix may need nav wrap verification at `390px` and `768px`.
      transient_surfaces:
        - path: tmp/transfers/task-start-overflow-note.md
          description: Browser observation note for the reproduced 390px overflow.
        - path: tmp/transfers/task-start-candidate-proof-scenes.md
          description: Temporary notes about which responsive scenes should verify the fix.
      task_memory_search_hints:
        - task start header overflow 390px cta min-width
        - task start nav wrap rejection

Better terminal checkpoint:

    record_checkpoint:
      checkpoint_kind: terminal
      outcome: green
      handoff:
        summary: Patched Task Start CTA min-width, rerendered desktop and mobile,
          and confirmed the nav no longer wraps at `390px`.
        next_step: Parent should review the patch and release only if the surfaced
          acceptance criteria are satisfied.
        risks:
          - Visual proof is local browser output only.
      produced_artifacts:
        - kind: artifact
          slot: page_patch
          path: workspace/out/task_start_patch.diff
        - kind: artifact
          slot: page_review_report
          path: workspace/out/task_start_review.md
      transient_surfaces:
        - path: tmp/transfers/task-start-local-browser-note.md
          description: Local browser observation that should help review but is not durable output.
        - path: tmp/transfers/task-start-review-caveat.md
          description: Temporary caveat explaining why visual proof should be rerun by the parent.
      task_memory_search_hints:
        - task start cta min-width patch green
        - task start 390px nav verification

# Historical dispatch-family packs

Status: Reference

This page preserves the old dispatch-family pack naming for migration search only.

The live v1 prompt contract no longer freezes prompt generation around old dispatch families such as `parent_gate_resume` or `worker_retry`.

Use these live owners instead:

- [../contract.md](../contract.md)
- [../source-and-sections.md](../source-and-sections.md)
- [runtime-rule-blocks.md](runtime-rule-blocks.md)
- [system-and-provider-block.md](system-and-provider-block.md)

## Live replacement model

The current prompt model freezes:

- two canonical prompt families:
  - `worker_dispatch_prompt`
  - `parent_root_dispatch_prompt`
- one live send mode:
  - `full_prompt`
- current runtime wording through reusable rule blocks rather than legacy dispatch-family packs

## Historical search terms preserved here

Readers may still arrive here searching for:

- `parent_initial_bootstrap`
- `parent_gate_resume`
- `worker_initial_bootstrap`
- `worker_continue`
- `worker_retry`
- `watchdog_recovery_redispatch`

Those are not the live v1 prompt-family contract.

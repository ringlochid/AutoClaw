## Task Memory Search Hints

`task_memory_search_hints` are retrieval prompts, not generic tags and not implicit consumes.

Use them this way:

- Write hints as semantic search prompts for prior defects, rejected approaches, root causes, or artifact names.
- Prefer phrases that can recover the right prior context later, not broad labels such as `retry`, `fix`, `bug`, `ui`, or `page`.
- Search `context/wiki/` first, then other curated files under `context/`, when the current assignment needs extra context.
- Do not silently promote all task-memory files into current `consumes`.

# FAQ

Status: Reference

## Should I use `pipx` or `uv`?

Use `pipx` for the default public v1 path. Use `uv` if you prefer its tool-install workflow and want the same published package artifacts.

## Is repo checkout the normal install story?

No. Editable checkout is the contributor/dev lane. The public v1 install story is the published package.

## Is managed-service support cross-platform in v1?

No. The fully supported v1 managed-service path is Linux `systemd --user`. macOS and Windows service-manager parity are later work.

## Where do definitions live after import?

Repo files are authoring inputs. After successful import, the controller-owned registry becomes authoritative for those definitions.

## Why does task start use `POST /tasks/start` instead of a separate task-compose route?

Current shipped task-compose launch is a launch-body contract, not a separate public route family. The CLI wrapper reads one local file and submits the same task-start body as the canonical backend task-start handler.

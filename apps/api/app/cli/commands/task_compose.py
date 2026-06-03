from __future__ import annotations

import argparse

from app.cli_support import coerce_path, command_env, print_json
from app.config import load_settings
from app.db.session import get_session_factory
from app.file_entrypoints import task_start_request_from_path
from app.registry.task_start import start_task_from_definition_service
from app.runtime.effects import (
    commit_runtime_session,
    rollback_runtime_session,
    wait_for_runtime_effects,
)


async def cmd_task_compose_start(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
        request = task_start_request_from_path(args.file)
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                response = await start_task_from_definition_service(
                    session,
                    request,
                    data_dir=settings.data_dir,
                )
                await commit_runtime_session(session)
                await wait_for_runtime_effects(task_id=response.task_id)
            except Exception:
                await rollback_runtime_session(session)
                raise

    payload = response.model_dump(mode="json")
    if args.json:
        print_json(payload)
    else:
        print(f"started task: {response.task_id}")
        print(f"flow status: {response.flow_status.value}")
        print(f"manifest: {response.workflow_manifest_ref.path}")
    return 0


__all__ = ["cmd_task_compose_start"]

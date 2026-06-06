from __future__ import annotations

import argparse

from autoclaw.config import load_settings
from autoclaw.definitions.registry.task_start import start_task_from_definition_service
from autoclaw.interfaces.cli.support import coerce_path, command_env, print_json
from autoclaw.platform.file_entrypoints import task_start_request_from_path
from autoclaw.runtime.post_commit.operations import write_runtime_operation_and_wait


async def cmd_task_compose_start(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
        request = task_start_request_from_path(args.file)
        response = await write_runtime_operation_and_wait(
            lambda session: start_task_from_definition_service(
                session,
                request,
                data_dir=settings.data_dir,
            ),
            task_id_getter=lambda runtime_response: runtime_response.task_id,
        )

    payload = response.model_dump(mode="json")
    if args.json:
        print_json(payload)
    else:
        print(f"started task: {response.task_id}")
        print(f"flow status: {response.flow_status.value}")
        print(f"manifest: {response.workflow_manifest_ref.path}")
    return 0


__all__ = ["cmd_task_compose_start"]

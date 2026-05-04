from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app import cli
from app.config import get_settings
from app.db import DispatchCallbackBindingModel, FlowModel, RuntimeBase
from app.db.session import dispose_db_engine, get_async_engine, get_session_factory
from app.main import create_app
from app.runtime import RuntimeBootstrapInput, persist_bootstrap_runtime
from httpx import ASGITransport, AsyncClient
from tests.helpers.runtime_seed import (
    compile_seeded_workflow,
    load_seeded_lookup,
    load_workflow_definition,
    task_compose_payload,
)


async def test_phase3_runtime_routes_surface_runtime_callback_operator_and_observability(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"

    try:
        await cli._cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=8123,
                log_level="INFO",
                api_key="api-test-key",
                internal_api_key="internal-test-key",
                force=True,
                skip_db_upgrade=False,
                json=False,
            )
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            engine = get_async_engine()
            async with engine.begin() as connection:
                await connection.run_sync(RuntimeBase.metadata.create_all)

            workflow_definition = load_workflow_definition("normal_parent_first_release")
            compiled_plan = compile_seeded_workflow(workflow_definition, revision_no=7)
            session_factory = get_session_factory()
            async with session_factory() as session:
                await persist_bootstrap_runtime(
                    session,
                    RuntimeBootstrapInput(
                        task_id="task_2026_0044",
                        active_flow_revision_id="flowrev_0003",
                        attempt_id="attempt.root.01",
                        assignment_key="root.assign-01",
                        dispatch_id="dispatch.root.01",
                        task_root=task_root,
                        task_compose=task_compose_payload("normal-parent-first-release"),
                        workflow_definition=workflow_definition,
                        compiled_plan=compiled_plan,
                        role_policy_lookup=load_seeded_lookup(),
                    ),
                )
                await session.commit()

            async with session_factory() as session:
                flow = await session.get(FlowModel, "flow.task_2026_0044")
                assert flow is not None
                binding = await session.get(
                    DispatchCallbackBindingModel,
                    f"dispatch-callback-binding.{flow.current_open_dispatch_id}",
                )
                assert binding is not None
                session_key = binding.session_key

            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_list = await client.get("/runtime/tasks")
                assert runtime_list.status_code == 200
                assert runtime_list.json()["items"][0]["task_id"] == "task_2026_0044"

                runtime_read = await client.get("/runtime/tasks/task_2026_0044")
                assert runtime_read.status_code == 200
                assert runtime_read.json()["current_node_key"] == "root"

                assign_child = await client.post(
                    "/callback/tasks/task_2026_0044/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implementation_subtree",
                            "assignment_intent": {
                                "summary": "Start the implementation subtree.",
                                "instruction": "Stage only the current implementation subtree.",
                            },
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign_child.status_code == 200

                invalid_assign = await client.post(
                    "/callback/tasks/task_2026_0044/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": "invalid-session"},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implementation_subtree",
                            "assignment_intent": {
                                "summary": "Start the implementation subtree.",
                                "instruction": "Stage only the current implementation subtree.",
                            },
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert invalid_assign.status_code == 422
                assert invalid_assign.json()["detail"]["ok"] is False

                yielded = await client.post(
                    "/callback/tasks/task_2026_0044/boundary",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200
                assert yielded.json()["flow"]["current_node_key"] == "implementation_subtree"

                snapshot = await client.get("/operator/tasks/task_2026_0044/snapshot")
                assert snapshot.status_code == 200
                assert snapshot.json()["flow"]["current_node_key"] == "implementation_subtree"

                trace = await client.get(
                    "/operator/tasks/task_2026_0044/trace",
                    params={"scope": "current", "q": "implementation_subtree", "limit": 1},
                )
                assert trace.status_code == 200
                assert trace.json()["scope"] == "current"
                assert trace.json()["dispatch_history"][0]["node_key"] == "implementation_subtree"

                delivery_state = await client.get(
                    "/observability/tasks/task_2026_0044/delivery-state"
                )
                assert delivery_state.status_code == 200
                delivery_path = Path(delivery_state.json()["path"])
                assert await asyncio.to_thread(delivery_path.is_file)
    finally:
        await dispose_db_engine()

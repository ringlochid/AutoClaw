from __future__ import annotations

import argparse
import asyncio
import shutil
from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from importlib import resources
from pathlib import Path
from typing import cast

import app.registry.seeds as registry_seeds
import pytest
import yaml
from app import cli
from app.config import get_settings
from app.db import (
    CompiledPlanEdgeModel,
    CompiledPlanModel,
    CompiledPlanNodeModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    PolicyDefinitionModel,
    PolicyRevisionModel,
    RoleDefinitionModel,
    RoleRevisionModel,
    TaskComposeModel,
    TaskModel,
    WorkflowDefinitionModel,
    WorkflowRevisionModel,
    WorkspaceRootLeaseModel,
)
from app.db.session import dispose_db_engine, get_session_factory
from app.registry import (
    build_role_policy_lookup,
    compile_current_workflow,
    compile_current_workflow_launch_snapshot,
    load_current_policy,
    load_current_role,
    load_current_workflow,
    seed_definition_registry,
    upsert_policy_definition,
    upsert_role_definition,
    upsert_workflow_definition,
)
from app.runtime import RuntimeLaunchInput, cancel_runtime_flow, launch_task_runtime
from app.runtime.contracts import _RuntimeBootstrapProjectionInput
from app.runtime.ids import (
    assignment_key_for_task,
    attempt_id_for_task,
    dispatch_id_for_task,
    flow_id_for_task,
    flow_revision_id,
)
from app.runtime.launch.persistence import persist_bootstrap_runtime_from_precomputed
from app.schemas.definitions.registry import PolicyDefinitionInput, RoleDefinitionInput
from app.schemas.definitions.workflow import WorkflowDefinitionInput
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from tests.helpers.runtime_seed import task_compose_payload

type DefinitionInput = RoleDefinitionInput | PolicyDefinitionInput | WorkflowDefinitionInput
type UpsertDefinitionFn = Callable[
    [AsyncSession, DefinitionInput, str],
    Awaitable[int],
]
type LoadCurrentDefinitionFn = Callable[
    [AsyncSession, str],
    Awaitable[tuple[int, str]],
]
type LoadRevisionHistoryFn = Callable[
    [AsyncSession, str],
    Awaitable[list[tuple[int, str]]],
]


def _copy_seed_tree(target_root: Path) -> Path:
    seed_root = target_root / "seed-root"
    packaged_root = resources.files("app.resources").joinpath("definitions")
    with resources.as_file(packaged_root) as resolved_packaged_root:
        shutil.copytree(Path(resolved_packaged_root), seed_root)
    return seed_root


def _rewrite_workflow_seed_description(
    seed_root: Path,
    *,
    workflow_key: str,
    description: str,
) -> None:
    for workflow_path in sorted((seed_root / "workflows").glob("*.yaml")):
        payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"expected mapping content in {workflow_path}")
        if payload.get("id") != workflow_key:
            continue
        payload["description"] = description
        workflow_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return
    raise FileNotFoundError(f"missing workflow seed for {workflow_key}")


async def _upsert_role_revision(
    session: AsyncSession,
    definition: DefinitionInput,
    source_path: str,
) -> int:
    result = await upsert_role_definition(
        session,
        cast(RoleDefinitionInput, definition),
        source_path=source_path,
    )
    return result.revision_no


async def _load_current_role_definition(
    session: AsyncSession,
    definition_key: str,
) -> tuple[int, str]:
    current = await load_current_role(session, definition_key)
    return current.revision_no, current.definition.description


async def _load_role_revision_history(
    session: AsyncSession,
    definition_key: str,
) -> list[tuple[int, str]]:
    rows = await session.execute(
        select(
            RoleRevisionModel.revision_no,
            RoleRevisionModel.content_json,
        )
        .where(RoleRevisionModel.role_key == definition_key)
        .order_by(RoleRevisionModel.revision_no.asc())
    )
    return [
        (revision_no, str(content_json["description"])) for revision_no, content_json in rows.all()
    ]


async def _upsert_policy_revision(
    session: AsyncSession,
    definition: DefinitionInput,
    source_path: str,
) -> int:
    result = await upsert_policy_definition(
        session,
        cast(PolicyDefinitionInput, definition),
        source_path=source_path,
    )
    return result.revision_no


async def _load_current_policy_definition(
    session: AsyncSession,
    definition_key: str,
) -> tuple[int, str]:
    current = await load_current_policy(session, definition_key)
    return current.revision_no, current.definition.description


async def _load_policy_revision_history(
    session: AsyncSession,
    definition_key: str,
) -> list[tuple[int, str]]:
    rows = await session.execute(
        select(
            PolicyRevisionModel.revision_no,
            PolicyRevisionModel.content_json,
        )
        .where(PolicyRevisionModel.policy_key == definition_key)
        .order_by(PolicyRevisionModel.revision_no.asc())
    )
    return [
        (revision_no, str(content_json["description"])) for revision_no, content_json in rows.all()
    ]


async def _upsert_workflow_revision(
    session: AsyncSession,
    definition: DefinitionInput,
    source_path: str,
) -> int:
    result = await upsert_workflow_definition(
        session,
        cast(WorkflowDefinitionInput, definition),
        source_path=source_path,
    )
    return result.revision_no


async def _load_current_workflow_definition(
    session: AsyncSession,
    definition_key: str,
) -> tuple[int, str]:
    current = await load_current_workflow(session, definition_key)
    return current.revision_no, current.definition.description


async def _load_workflow_revision_history(
    session: AsyncSession,
    definition_key: str,
) -> list[tuple[int, str]]:
    rows = await session.execute(
        select(
            WorkflowRevisionModel.revision_no,
            WorkflowRevisionModel.content_json,
        )
        .where(WorkflowRevisionModel.workflow_key == definition_key)
        .order_by(WorkflowRevisionModel.revision_no.asc())
    )
    return [
        (revision_no, str(content_json["description"])) for revision_no, content_json in rows.all()
    ]


async def test_init_seeds_definition_registry_and_compiles_current_workflow(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

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
            session_factory = get_session_factory()
            async with session_factory() as session:
                role = await load_current_role(session, "planning_lead")
                policy = await load_current_policy(session, "standard-worker")
                workflow, compiled_plan = await compile_current_workflow(
                    session,
                    workflow_key="normal-parent-first-release",
                    compiler_version="registry-seeded-test",
                )

                assert role.revision_no == 1
                assert policy.revision_no == 1
                assert workflow.revision_no == 1
                assert compiled_plan.workflow_key == "normal-parent-first-release"
                assert compiled_plan.definition_revision_no == workflow.revision_no
                assert compiled_plan.nodes[1].node_key == "implementation_subtree"
    finally:
        await dispose_db_engine()


async def test_seed_registry_appends_seed_revision_without_clobbering_controller_current(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    seed_root = _copy_seed_tree(tmp_path / "packaged-seed-refresh")
    updated_seed_description = (
        "Minimal workflow that creates one implementation change artifact. packaged refresh"
    )
    _rewrite_workflow_seed_description(
        seed_root,
        workflow_key="minimal-implement-change",
        description=updated_seed_description,
    )

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
            session_factory = get_session_factory()
            async with session_factory() as session:
                current = await load_current_workflow(session, "minimal-implement-change")
                updated_definition = current.definition.model_copy(
                    update={"description": f"{current.definition.description} updated"}
                )
                updated = await upsert_workflow_definition(
                    session,
                    updated_definition,
                    source_path="test://updated-workflow",
                )
                await session.commit()
                assert updated.revision_no == 2

            with pytest.MonkeyPatch.context() as patched:
                patched.setattr(
                    registry_seeds.resources,
                    "as_file",
                    lambda _resource: nullcontext(seed_root),
                )
                async with session_factory() as session:
                    await seed_definition_registry(session)
                    await session.commit()

                async with session_factory() as session:
                    await seed_definition_registry(session)
                    await session.commit()

            async with session_factory() as session:
                current = await load_current_workflow(session, "minimal-implement-change")
                revision_count = await session.scalar(
                    select(func.count()).where(
                        WorkflowRevisionModel.workflow_key == "minimal-implement-change"
                    )
                )
                appended_seed_revision = await session.scalar(
                    select(WorkflowRevisionModel).where(
                        WorkflowRevisionModel.workflow_key == "minimal-implement-change",
                        WorkflowRevisionModel.revision_no == 3,
                    )
                )

                assert appended_seed_revision is not None
                assert current.revision_no == 2
                assert current.definition.description.endswith("updated")
                assert revision_count == 3
                assert (
                    appended_seed_revision.content_json["description"] == updated_seed_description
                )
                assert appended_seed_revision.source_path == (
                    "seed://packaged/workflows/minimal_implement_change.yaml"
                )
    finally:
        await dispose_db_engine()


async def test_seed_registry_promotes_changed_packaged_workflow_revision_when_seed_owned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    seed_root = _copy_seed_tree(tmp_path / "packaged-seed")
    updated_description = "Minimal workflow that creates one implementation change artifact. v2"
    _rewrite_workflow_seed_description(
        seed_root,
        workflow_key="minimal-implement-change",
        description=updated_description,
    )

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
            session_factory = get_session_factory()
            async with session_factory() as session:
                baseline_workflow = await load_current_workflow(
                    session,
                    "minimal-implement-change",
                )
                baseline_description = baseline_workflow.definition.description
            monkeypatch.setattr(
                registry_seeds.resources,
                "as_file",
                lambda _resource: nullcontext(seed_root),
            )
            async with session_factory() as session:
                await seed_definition_registry(session)
                await session.commit()

            async with session_factory() as session:
                current = await load_current_workflow(session, "minimal-implement-change")
                revision_history = await _load_workflow_revision_history(
                    session,
                    "minimal-implement-change",
                )
                current_revision = await session.scalar(
                    select(WorkflowRevisionModel).where(
                        WorkflowRevisionModel.workflow_key == "minimal-implement-change",
                        WorkflowRevisionModel.revision_no == current.revision_no,
                    )
                )

                assert current_revision is not None
                assert current.revision_no == 2
                assert current.definition.description == updated_description
                assert current_revision.source_path == (
                    "seed://packaged/workflows/minimal_implement_change.yaml"
                )
                assert revision_history == [
                    (1, baseline_description),
                    (2, updated_description),
                ]
    finally:
        await dispose_db_engine()


async def test_invalid_workflow_does_not_advance_registry_currentness(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

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
            session_factory = get_session_factory()
            async with session_factory() as session:
                current = await load_current_workflow(session, "minimal-implement-change")
                invalid_definition = WorkflowDefinitionInput.model_validate(
                    current.definition.model_dump()
                    | {"root": current.definition.root.model_dump() | {"role": "missing-role"}}
                )

                with pytest.raises(ValueError, match="role 'missing-role'"):
                    await upsert_workflow_definition(
                        session,
                        invalid_definition,
                        source_path="test://invalid-workflow",
                    )
                await session.rollback()

            async with session_factory() as session:
                current = await load_current_workflow(session, "minimal-implement-change")
                revision_count = await session.scalar(
                    select(func.count()).where(
                        WorkflowRevisionModel.workflow_key == "minimal-implement-change"
                    )
                )

                assert current.revision_no == 1
                assert revision_count == 1
    finally:
        await dispose_db_engine()


@pytest.mark.parametrize("definition_kind", ["role", "policy", "workflow"])
async def test_concurrent_new_key_upserts_create_ordered_revisions(
    tmp_path: Path,
    definition_kind: str,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"

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
            session_factory = get_session_factory()
            definition_key = f"concurrent-{definition_kind}-definition"
            upsert_definition: UpsertDefinitionFn
            load_current_definition: LoadCurrentDefinitionFn
            load_revision_history: LoadRevisionHistoryFn
            first_definition: DefinitionInput
            second_definition: DefinitionInput

            async with session_factory() as session:
                if definition_kind == "role":
                    first_definition = RoleDefinitionInput.model_validate(
                        {
                            "id": definition_key,
                            "description": "Concurrent role revision 1",
                            "allowed_node_kinds": ["worker"],
                        }
                    )
                    second_definition = first_definition.model_copy(
                        update={"description": "Concurrent role revision 2"}
                    )
                    upsert_definition = _upsert_role_revision
                    load_current_definition = _load_current_role_definition
                    load_revision_history = _load_role_revision_history
                elif definition_kind == "policy":
                    first_definition = PolicyDefinitionInput.model_validate(
                        {
                            "id": definition_key,
                            "description": "Concurrent policy revision 1",
                            "applies_to": ["worker"],
                            "budget_spec": {"retry_limit": 1},
                        }
                    )
                    second_definition = first_definition.model_copy(
                        update={"description": "Concurrent policy revision 2"}
                    )
                    upsert_definition = _upsert_policy_revision
                    load_current_definition = _load_current_policy_definition
                    load_revision_history = _load_policy_revision_history
                else:
                    current_workflow = await load_current_workflow(
                        session,
                        "minimal-implement-change",
                    )
                    first_definition = current_workflow.definition.model_copy(
                        update={
                            "id": definition_key,
                            "description": "Concurrent workflow revision 1",
                        }
                    )
                    second_definition = first_definition.model_copy(
                        update={"description": "Concurrent workflow revision 2"}
                    )
                    upsert_definition = _upsert_workflow_revision
                    load_current_definition = _load_current_workflow_definition
                    load_revision_history = _load_workflow_revision_history

            race_release = asyncio.Event()
            first_writer_flushed = asyncio.Event()

            async def first_writer() -> int:
                async with session_factory() as session:
                    revision_no = await upsert_definition(
                        session,
                        first_definition,
                        f"test://{definition_kind}-first",
                    )
                    first_writer_flushed.set()
                    await race_release.wait()
                    await session.commit()
                    return revision_no

            async def second_writer() -> int:
                await first_writer_flushed.wait()
                async with session_factory() as session:
                    revision_no = await upsert_definition(
                        session,
                        second_definition,
                        f"test://{definition_kind}-second",
                    )
                    await session.commit()
                    return revision_no

            first_task = asyncio.create_task(first_writer())
            await first_writer_flushed.wait()
            second_task = asyncio.create_task(second_writer())
            await asyncio.sleep(0.1)
            race_release.set()
            first_revision_no, second_revision_no = await asyncio.gather(first_task, second_task)

            assert (first_revision_no, second_revision_no) == (1, 2)

            async with session_factory() as session:
                current_revision_no, current_description = await load_current_definition(
                    session,
                    definition_key,
                )
                revision_history = await load_revision_history(session, definition_key)

            assert current_revision_no == 2
            assert current_description == second_definition.description
            assert revision_history == [
                (1, first_definition.description),
                (2, second_definition.description),
            ]
    finally:
        await dispose_db_engine()


async def test_launch_runtime_pins_current_registry_workflow_role_and_policy_revisions(
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
            session_factory = get_session_factory()
            async with session_factory() as session:
                role = await load_current_role(session, "planning_lead")
                updated_role = role.definition.model_copy(
                    update={"description": f"{role.definition.description} v2"}
                )
                role_revision = await upsert_role_definition(
                    session,
                    updated_role,
                    source_path="test://planning-lead-v2",
                )

                policy = await load_current_policy(session, "standard-parent-planning")
                updated_policy = policy.definition.model_copy(
                    update={"description": f"{policy.definition.description} v2"}
                )
                policy_revision = await upsert_policy_definition(
                    session,
                    updated_policy,
                    source_path="test://standard-parent-planning-v2",
                )

                workflow = await load_current_workflow(session, "normal-parent-first-release")
                updated_workflow = workflow.definition.model_copy(
                    update={"description": f"{workflow.definition.description} v2"}
                )
                workflow_revision = await upsert_workflow_definition(
                    session,
                    updated_workflow,
                    source_path="test://normal-parent-first-release-v2",
                )
                await session.commit()

            async with session_factory() as session:
                workflow_definition = await session.scalar(
                    select(WorkflowDefinitionModel)
                    .options(joinedload(WorkflowDefinitionModel.current_revision))
                    .where(WorkflowDefinitionModel.workflow_key == "normal-parent-first-release")
                )
                role_definition = await session.scalar(
                    select(RoleDefinitionModel)
                    .options(joinedload(RoleDefinitionModel.current_revision))
                    .where(RoleDefinitionModel.role_key == "planning_lead")
                )
                policy_definition = await session.scalar(
                    select(PolicyDefinitionModel)
                    .options(joinedload(PolicyDefinitionModel.current_revision))
                    .where(PolicyDefinitionModel.policy_key == "standard-parent-planning")
                )
                compiled_workflow, compiled_plan = await compile_current_workflow(
                    session,
                    workflow_key="normal-parent-first-release",
                    compiler_version="registry-pin-proof",
                )
                lookup = await build_role_policy_lookup(session)

                assert workflow_definition is not None
                assert workflow_definition.current_revision is not None
                assert (
                    workflow_definition.current_revision.revision_no
                    == workflow_revision.revision_no
                )
                assert role_definition is not None
                assert role_definition.current_revision is not None
                assert role_definition.current_revision.revision_no == role_revision.revision_no
                assert policy_definition is not None
                assert policy_definition.current_revision is not None
                assert policy_definition.current_revision.revision_no == policy_revision.revision_no
                assert compiled_workflow.revision_no == workflow_revision.revision_no
                assert compiled_plan.definition_revision_no == workflow_revision.revision_no
                lookup_role = lookup.get_role("planning_lead")
                lookup_policy = lookup.get_policy("standard-parent-planning")
                assert lookup_role is not None
                assert lookup_policy is not None
                assert lookup_role.revision_no == role_revision.revision_no
                assert lookup_policy.revision_no == policy_revision.revision_no

            async with session_factory() as session:
                await launch_task_runtime(
                    session,
                    RuntimeLaunchInput(
                        task_id="task_registry_revision_pin",
                        task_root=task_root,
                        task_compose=task_compose_payload("normal-parent-first-release"),
                        compiler_version="registry-pin-proof",
                    ),
                )

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_registry_revision_pin")
                )
                assert flow is not None
                compiled_plan_row = (
                    (
                        await session.execute(
                            select(CompiledPlanModel)
                            .options(
                                joinedload(CompiledPlanModel.workflow_revision),
                                joinedload(CompiledPlanModel.task).joinedload(
                                    TaskModel.compiled_plan
                                ),
                                joinedload(CompiledPlanModel.task)
                                .joinedload(TaskModel.task_compose)
                                .joinedload(TaskComposeModel.workflow_revision),
                                joinedload(CompiledPlanModel.task).selectinload(
                                    TaskModel.resource_bindings
                                ),
                                joinedload(CompiledPlanModel.task_compose).joinedload(
                                    TaskComposeModel.workflow_revision
                                ),
                                selectinload(CompiledPlanModel.nodes).joinedload(
                                    CompiledPlanNodeModel.parent
                                ),
                                selectinload(CompiledPlanModel.nodes).selectinload(
                                    CompiledPlanNodeModel.children
                                ),
                                selectinload(CompiledPlanModel.nodes).joinedload(
                                    CompiledPlanNodeModel.role_revision
                                ),
                                selectinload(CompiledPlanModel.nodes).joinedload(
                                    CompiledPlanNodeModel.policy_revision
                                ),
                                selectinload(CompiledPlanModel.nodes).selectinload(
                                    CompiledPlanNodeModel.outgoing_edges
                                ),
                                selectinload(CompiledPlanModel.nodes).selectinload(
                                    CompiledPlanNodeModel.incoming_edges
                                ),
                                selectinload(CompiledPlanModel.edges).joinedload(
                                    CompiledPlanEdgeModel.provider_node
                                ),
                                selectinload(CompiledPlanModel.edges).joinedload(
                                    CompiledPlanEdgeModel.consumer_node
                                ),
                            )
                            .where(CompiledPlanModel.compiled_plan_id == flow.compiled_plan_id)
                        )
                    )
                    .unique()
                    .scalar_one_or_none()
                )
                assert compiled_plan_row is not None
                assert compiled_plan_row.definition_revision_no == workflow_revision.revision_no
                assert compiled_plan_row.workflow_revision is not None
                assert (
                    compiled_plan_row.workflow_revision.revision_no == workflow_revision.revision_no
                )
                assert compiled_plan_row.task.compiled_plan is not None
                assert (
                    compiled_plan_row.task.compiled_plan.compiled_plan_id
                    == compiled_plan_row.compiled_plan_id
                )
                assert compiled_plan_row.task.task_compose is not None
                assert compiled_plan_row.task_compose is not None
                assert (
                    compiled_plan_row.task_compose.task_compose_id
                    == compiled_plan_row.task.task_compose.task_compose_id
                )
                assert compiled_plan_row.task.task_compose.workflow_revision is not None
                assert (
                    compiled_plan_row.task.task_compose.workflow_revision.revision_no
                    == workflow_revision.revision_no
                )
                binding_paths = {
                    binding.binding_kind: binding.path
                    for binding in compiled_plan_row.task.resource_bindings
                }
                assert (
                    binding_paths["workspace"]
                    == compiled_plan_row.task.task_compose.workspace_root_path
                )
                assert (
                    binding_paths["runtime"]
                    == compiled_plan_row.task.task_compose.runtime_root_path
                )
                assert len(compiled_plan_row.nodes) == len(compiled_plan.nodes)
                assert len(compiled_plan_row.edges) == len(compiled_plan.dependency_edges)
                plan_nodes_by_key = {node.node_key: node for node in compiled_plan_row.nodes}
                implementation_plan_node = plan_nodes_by_key["implementation_subtree"]
                assert implementation_plan_node.role_revision is not None
                assert (
                    implementation_plan_node.role_revision.revision_no == role_revision.revision_no
                )
                assert implementation_plan_node.policy_revision is not None
                assert (
                    implementation_plan_node.policy_revision.revision_no
                    == policy_revision.revision_no
                )
                assert implementation_plan_node.parent is not None
                assert (
                    implementation_plan_node.parent.node_key
                    == implementation_plan_node.parent_node_key
                )
                assert "implementation_subtree" in {
                    child.node_key for child in implementation_plan_node.parent.children
                }
                assert compiled_plan_row.edges
                first_plan_edge = compiled_plan_row.edges[0]
                assert first_plan_edge.provider_node.node_key == first_plan_edge.provider_node_key
                assert first_plan_edge.consumer_node.node_key == first_plan_edge.consumer_node_key
                assert first_plan_edge in first_plan_edge.provider_node.outgoing_edges
                assert first_plan_edge in first_plan_edge.consumer_node.incoming_edges

                implementation_subtree = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                        FlowNodeModel.node_key == "implementation_subtree",
                    )
                )
                assert implementation_subtree is not None
                assert implementation_subtree.role_revision_no == role_revision.revision_no
                assert implementation_subtree.policy_revision_no == policy_revision.revision_no
                assert (
                    implementation_subtree.role_description == role_revision.definition.description
                )
                assert (
                    implementation_subtree.policy_description
                    == policy_revision.definition.description
                )
    finally:
        await dispose_db_engine()


async def test_bootstrap_persistence_commits_launch_truth_before_dispatch_exists(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    workspace_root = tmp_path / "bootstrap-workspace"

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
            session_factory = get_session_factory()
            task_id = "task_pre_dispatch_bootstrap"
            async with session_factory() as session:
                snapshot = await compile_current_workflow_launch_snapshot(
                    session,
                    workflow_key="minimal-implement-change",
                    compiler_version="pre-dispatch-proof",
                )
                await persist_bootstrap_runtime_from_precomputed(
                    session,
                    _RuntimeBootstrapProjectionInput(
                        task_id=task_id,
                        active_flow_revision_id=flow_revision_id(flow_id_for_task(task_id), 1),
                        attempt_id=attempt_id_for_task(task_id, "root", 1),
                        assignment_key=assignment_key_for_task(task_id, "root", 1),
                        dispatch_id=dispatch_id_for_task(task_id, "root", 1),
                        task_root=task_root,
                        task_compose=task_compose_payload(
                            "minimal-implement-change",
                            workspace={
                                "mode": "ensure_host_path",
                                "host_path": str(workspace_root),
                            },
                        ),
                        workflow_definition=snapshot.workflow.definition,
                        compiled_plan=snapshot.compiled_plan,
                        role_policy_lookup=snapshot.role_policy_lookup,
                    ),
                )

            async with session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                assert flow.current_open_dispatch_id is None
                compiled_plan = await session.get(CompiledPlanModel, flow.compiled_plan_id)
                assert compiled_plan is not None
                dispatch_count = await session.scalar(
                    select(func.count())
                    .select_from(DispatchTurnModel)
                    .where(DispatchTurnModel.task_id == task_id)
                )
                assert dispatch_count == 0
                lease = await session.scalar(
                    select(WorkspaceRootLeaseModel).where(
                        WorkspaceRootLeaseModel.task_id == task_id,
                        WorkspaceRootLeaseModel.lease_status == "live",
                    )
                )
                assert lease is not None
    finally:
        await dispose_db_engine()


async def test_launch_rejects_reused_custom_workspace_host_path_for_live_tasks(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    shared_workspace = tmp_path / "shared-workspace"

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
            session_factory = get_session_factory()
            compose = task_compose_payload(
                "normal-parent-first-release",
                workspace={
                    "mode": "ensure_host_path",
                    "host_path": str(shared_workspace),
                },
            )

            async with session_factory() as session:
                await launch_task_runtime(
                    session,
                    RuntimeLaunchInput(
                        task_id="task_workspace_lease_a",
                        task_root=tmp_path / "task-a-root",
                        task_compose=compose,
                        compiler_version="workspace-lease-proof",
                    ),
                )

            async with session_factory() as session:
                lease = await session.scalar(
                    select(WorkspaceRootLeaseModel).where(
                        WorkspaceRootLeaseModel.normalized_workspace_root_path
                        == str(shared_workspace.resolve()),
                        WorkspaceRootLeaseModel.lease_status == "live",
                    )
                )
                assert lease is not None
                assert lease.task_id == "task_workspace_lease_a"

            async with session_factory() as session:
                with pytest.raises(ValueError, match="workspace host path already held"):
                    await launch_task_runtime(
                        session,
                        RuntimeLaunchInput(
                            task_id="task_workspace_lease_b",
                            task_root=tmp_path / "task-b-root",
                            task_compose=compose,
                            compiler_version="workspace-lease-proof",
                        ),
                    )
    finally:
        await dispose_db_engine()


async def test_cancel_keeps_workspace_host_path_leased_until_inactivity_is_proven(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    shared_workspace = tmp_path / "shared-workspace"

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
            session_factory = get_session_factory()
            compose = task_compose_payload(
                "normal-parent-first-release",
                workspace={
                    "mode": "ensure_host_path",
                    "host_path": str(shared_workspace / "."),
                },
            )

            async with session_factory() as session:
                await launch_task_runtime(
                    session,
                    RuntimeLaunchInput(
                        task_id="task_workspace_release_a",
                        task_root=tmp_path / "task-a-root",
                        task_compose=compose,
                        compiler_version="workspace-release-proof",
                    ),
                )

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_workspace_release_a")
                )
                assert flow is not None
                await cancel_runtime_flow(
                    session,
                    "task_workspace_release_a",
                    expected_active_flow_revision_id=flow.active_flow_revision_id or "",
                )
                await session.commit()

            async with session_factory() as session:
                retained_lease = await session.scalar(
                    select(WorkspaceRootLeaseModel).where(
                        WorkspaceRootLeaseModel.normalized_workspace_root_path
                        == str(shared_workspace.resolve())
                    )
                )
                assert retained_lease is not None
                assert retained_lease.lease_status == "live"
                assert retained_lease.released_at is None

            async with session_factory() as session:
                with pytest.raises(ValueError, match="workspace host path already held"):
                    await launch_task_runtime(
                        session,
                        RuntimeLaunchInput(
                            task_id="task_workspace_release_b",
                            task_root=tmp_path / "task-b-root",
                            task_compose=compose,
                            compiler_version="workspace-release-proof",
                        ),
                    )
    finally:
        await dispose_db_engine()

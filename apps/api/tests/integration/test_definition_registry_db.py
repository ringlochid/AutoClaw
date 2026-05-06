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
    PolicyDefinitionModel,
    PolicyRevisionModel,
    RoleDefinitionModel,
    RoleRevisionModel,
    WorkflowDefinitionModel,
    WorkflowRevisionModel,
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
from app.schemas.definitions.registry import PolicyDefinitionInput, RoleDefinitionInput
from app.schemas.definitions.workflow import WorkflowDefinitionInput
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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


async def test_launch_snapshot_pins_current_registry_workflow_role_and_policy_revisions(
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
                snapshot = await compile_current_workflow_launch_snapshot(
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
                assert snapshot.workflow.revision_no == workflow_revision.revision_no
                assert (
                    snapshot.compiled_plan.definition_revision_no == workflow_revision.revision_no
                )
                lookup_role = lookup.get_role("planning_lead")
                lookup_policy = lookup.get_policy("standard-parent-planning")
                assert lookup_role is not None
                assert lookup_policy is not None
                assert lookup_role.revision_no == role_revision.revision_no
                assert lookup_policy.revision_no == policy_revision.revision_no
                snapshot_role = snapshot.role_policy_lookup.get_role("planning_lead")
                snapshot_policy = snapshot.role_policy_lookup.get_policy("standard-parent-planning")
                assert snapshot_role is not None
                assert snapshot_policy is not None
                assert snapshot_role.revision_no == role_revision.revision_no
                assert snapshot_policy.revision_no == policy_revision.revision_no
                plan_nodes_by_key = {node.node_key: node for node in snapshot.compiled_plan.nodes}
                implementation_plan_node = plan_nodes_by_key["implementation_subtree"]
                assert implementation_plan_node.role_revision_no == role_revision.revision_no
                assert implementation_plan_node.policy_revision_no == policy_revision.revision_no
                assert implementation_plan_node.parent_node_key == "root"
                assert "implementation_subtree" in plan_nodes_by_key["root"].child_node_keys
                assert snapshot.compiled_plan.dependency_edges
                first_plan_edge = snapshot.compiled_plan.dependency_edges[0]
                assert (
                    plan_nodes_by_key[first_plan_edge.provider_node_key].node_key
                    == first_plan_edge.provider_node_key
                )
                assert (
                    plan_nodes_by_key[first_plan_edge.consumer_node_key].node_key
                    == first_plan_edge.consumer_node_key
                )
    finally:
        await dispose_db_engine()

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DefinitionVersionStatus
from app.core.errors import InvalidDefinitionError
from app.db.models.registry import WorkflowDefinition, WorkflowVersion
from app.schemas.registry import WorkflowDefinitionSeed
from app.services.compiler_service import compile_published_workflow, preview_workflow_seed
from app.services.registry_service import bootstrap_registry


async def _insert_workflow_version(
    db_session: AsyncSession,
    *,
    key: str,
    content: dict,
) -> None:
    definition = WorkflowDefinition(key=key, description=content.get("description"))
    db_session.add(definition)
    await db_session.flush()

    db_session.add(
        WorkflowVersion(
            workflow_definition_id=definition.id,
            version=1,
            status=DefinitionVersionStatus.PUBLISHED,
            description=content.get("description"),
            content=content,
            published_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    await db_session.commit()


async def test_compile_workflow_persists_task_defaults_and_node_resources(
    db_session: AsyncSession,
) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    await _insert_workflow_version(
        db_session,
        key="resourceful-workflow",
        content={
            "id": "resourceful-workflow",
            "description": "workflow with explicit resource intent",
            "task_defaults": {
                "workspace": {"mode": "ensure_task_primary"},
                "context": {
                    "mode": "ensure_task_primary",
                    "seed_from": ["task_input", "workspace_docs"],
                },
                "manifests": {"mode": "ensure_task_root"},
            },
            "nodes": [
                {
                    "id": "root",
                    "role": "planner-supervisor",
                    "mode": "plan",
                    "resources": {
                        "workspace": {
                            "mounts": [
                                {"ref": "task.primary_workspace", "access": "read_only"}
                            ]
                        },
                        "context": {"refs": [{"ref": "task.primary_context"}]},
                        "image": {
                            "ref": "task-image://resourceful-workflow/base",
                            "kind": "task_image"
                        },
                        "compose": {
                            "ref": "task-compose://resourceful-workflow/local",
                            "services": ["repo_checkout", "browser"]
                        },
                        "container": {
                            "backend_kind": "sandbox",
                            "reuse_policy": "per_node"
                        }
                    },
                },
                {
                    "id": "loop",
                    "role": "main-loop-worker",
                    "mode": "persistent_execute",
                    "resources": {
                        "workspace": {
                            "mounts": [
                                {"ref": "task.primary_workspace", "access": "read_write"}
                            ]
                        },
                        "context": {"refs": [{"ref": "task.primary_context"}]},
                    },
                },
            ],
            "edges": [{"from": "root", "to": "loop"}],
        },
    )

    compiled_plan = await compile_published_workflow(db_session, "resourceful-workflow")
    await db_session.commit()

    root_payload = compiled_plan.nodes[0].effective_payload
    loop_payload = compiled_plan.nodes[1].effective_payload

    assert root_payload["task_defaults"]["workspace"]["mode"] == "ensure_task_primary"
    assert root_payload["task_defaults"]["context"]["seed_from"] == [
        "task_input",
        "workspace_docs",
    ]
    assert root_payload["task_defaults"]["manifests"]["mode"] == "ensure_task_root"
    assert root_payload["resources"]["workspace"]["mounts"][0]["access"] == "read_only"
    assert root_payload["resources"]["image"]["ref"] == "task-image://resourceful-workflow/base"
    assert root_payload["resources"]["image"]["kind"] == "task_image"
    assert root_payload["resources"]["compose"]["services"] == ["repo_checkout", "browser"]
    assert root_payload["resources"]["container"]["backend_kind"] == "sandbox"
    assert root_payload["resources"]["container"]["reuse_policy"] == "per_node"
    assert loop_payload["resources"]["workspace"]["mounts"][0]["access"] == "read_write"
    assert loop_payload["resources"]["context"]["refs"][0]["ref"] == "task.primary_context"


async def test_preview_workflow_rejects_required_passthrough_resource_without_identity(
    db_session: AsyncSession,
) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    invalid_seed = WorkflowDefinitionSeed.model_validate(
        {
            "id": "invalid-runtime-resource-shape",
            "description": "invalid passthrough resource",
            "nodes": [
                {
                    "id": "root",
                    "role": "planner-supervisor",
                    "mode": "plan",
                    "resources": {
                        "image": {"required": True},
                    },
                }
            ],
            "edges": [],
        }
    )

    with pytest.raises(InvalidDefinitionError) as exc_info:
        await preview_workflow_seed(db_session, invalid_seed)

    assert "required image resource without ref or kind" in str(exc_info.value)


async def test_preview_workflow_rejects_invalid_task_default_semantics(
    db_session: AsyncSession,
) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    invalid_seed = WorkflowDefinitionSeed.model_validate(
        {
            "id": "invalid-resource-shape",
            "description": "invalid task defaults",
            "task_defaults": {
                "workspace": {
                    "mode": "ensure_task_primary",
                    "seed_from": ["task_input"],
                }
            },
            "nodes": [
                {
                    "id": "root",
                    "role": "planner-supervisor",
                    "mode": "plan",
                }
            ],
            "edges": [],
        }
    )

    with pytest.raises(InvalidDefinitionError) as exc_info:
        await preview_workflow_seed(db_session, invalid_seed)

    assert "Task default 'workspace' cannot declare seed_from" in str(exc_info.value)

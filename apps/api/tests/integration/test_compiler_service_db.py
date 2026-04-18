from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import WorkflowMode
from app.db.models.runtime import CompiledPlan, CompiledPlanNode
from app.services.compiler_service import compile_published_workflow
from app.services.registry_service import bootstrap_registry


async def test_compile_default_workflow_persists_compiled_plan(
    db_session: AsyncSession,
) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    compiled_plan = await compile_published_workflow(db_session, "default-bugfix")
    await db_session.commit()

    persisted_plan = await db_session.scalar(
        select(CompiledPlan).where(CompiledPlan.id == compiled_plan.id)
    )
    persisted_nodes = list(
        (
            await db_session.scalars(
                select(CompiledPlanNode)
                .where(CompiledPlanNode.compiled_plan_id == compiled_plan.id)
                .order_by(CompiledPlanNode.order_index)
            )
        ).all()
    )

    assert persisted_plan is not None
    assert len(compiled_plan.nodes) == 4
    assert len(compiled_plan.edges) == 4
    assert [node.node_key for node in persisted_nodes] == ["root", "loop", "review", "sync"]
    assert persisted_nodes[0].parent_node_key is None
    assert persisted_nodes[1].parent_node_key == "root"
    assert persisted_nodes[2].parent_node_key == "loop"
    assert persisted_nodes[3].parent_node_key == "review"
    assert persisted_nodes[0].mode is WorkflowMode.PLAN
    assert persisted_nodes[1].skill_bindings[0]["key"] == "contract-checker"
    assert (
        persisted_nodes[1].skill_bindings[0]["runtime_name"]
        == "autoclaw-contract-checker"
    )
    assert persisted_nodes[1].skill_bindings[0]["manifest_summary"] == {
        "provider": "openclaw",
        "key": "contract-checker",
        "version_label": "external-current",
        "state": "allowed",
        "manifest_keys": [
            "key",
            "provider",
            "runtime_name",
            "source_uri",
            "state",
            "version",
        ],
    }
    assert persisted_nodes[1].skill_bindings[0]["artifact_metadata"]["source_ref"] == (
        "openclaw:contract-checker"
    )


async def test_compile_workflow_with_extends_uses_override_policy(
    db_session: AsyncSession,
) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    compiled_plan = await compile_published_workflow(db_session, "approval-change")
    await db_session.commit()

    node_policies = {node.node_key: node.policy_version_id for node in compiled_plan.nodes}

    assert len(compiled_plan.nodes) == 4
    assert len(set(node_policies.values())) == 1

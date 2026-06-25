from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from autoclaw.persistence import PolicyDefinitionModel, PolicyRevisionModel, RuntimeBase
from autoclaw.persistence.models import FlowNodeModel
from autoclaw.runtime.capabilities import resolve_effective_capabilities_for_node
from autoclaw.runtime.contracts import CapabilityDecision
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def test_effective_capabilities_use_pinned_policy_revision_not_current_policy(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'capabilities.sqlite'}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(RuntimeBase.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with session_factory() as session:
            policy_definition = PolicyDefinitionModel(
                policy_key="interactive-worker",
                current_revision_no=None,
                created_at=datetime(2026, 6, 25, tzinfo=UTC),
                updated_at=datetime(2026, 6, 25, tzinfo=UTC),
            )
            session.add(policy_definition)
            await session.flush()
            session.add_all(
                [
                    PolicyRevisionModel(
                        policy_revision_id="policy-revision.interactive-worker.1",
                        policy_key="interactive-worker",
                        revision_no=1,
                        content_hash="sha256:revision-1",
                        content_json={
                            "id": "interactive-worker",
                            "description": "Pinned policy denies special lanes.",
                            "applies_to": ["worker"],
                            "capabilities": {
                                "human_request": {
                                    "mode": "deny",
                                    "allowed_kinds": ["review"],
                                },
                                "command_run": "deny",
                            },
                        },
                    ),
                    PolicyRevisionModel(
                        policy_revision_id="policy-revision.interactive-worker.2",
                        policy_key="interactive-worker",
                        revision_no=2,
                        content_hash="sha256:revision-2",
                        content_json={
                            "id": "interactive-worker",
                            "description": "Current policy grants special lanes.",
                            "applies_to": ["worker"],
                            "capabilities": {
                                "human_request": {
                                    "mode": "allow",
                                    "allowed_kinds": ["direction", "approval", "input", "review"],
                                },
                                "command_run": "allow",
                            },
                        },
                    ),
                ]
            )
            await session.flush()
            policy_definition.current_revision_no = 2
            node = FlowNodeModel(
                flow_node_id="flow-node.capability.worker",
                flow_revision_id="flow-revision.capability.1",
                node_key="implement_change",
                structural_kind="worker",
                role_key="engineer",
                role_revision_no=1,
                role_description="Worker role.",
                policy_key="interactive-worker",
                policy_revision_no=1,
                policy_description="Pinned policy.",
                description="Implement a bounded change.",
                child_node_keys_json=[],
                criteria_json=[],
                order_index=0,
            )

            capabilities = await resolve_effective_capabilities_for_node(
                session,
                node=node,
                execution_scope="dispatch",
            )

        assert capabilities.human_request.direction == CapabilityDecision.DENY
        assert capabilities.human_request.approval == CapabilityDecision.DENY
        assert capabilities.human_request.input == CapabilityDecision.DENY
        assert capabilities.human_request.review == CapabilityDecision.DENY
        assert capabilities.command_run == CapabilityDecision.DENY
    finally:
        await engine.dispose()

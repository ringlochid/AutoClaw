from app.compiler.resolve import _merge_workflow_seeds
from app.core.enums import SkillBindingState, SkillProvider, WorkflowMode
from app.schemas.registry import SkillReferenceSeed, WorkflowDefinitionSeed


def _skill_ref(
    key: str,
    *,
    state: SkillBindingState = SkillBindingState.ALLOWED,
) -> SkillReferenceSeed:
    return SkillReferenceSeed(provider=SkillProvider.OPENCLAW, key=key, state=state)


def test_merge_workflow_seeds_merges_defaults_nodes_and_edges_field_aware() -> None:
    base = WorkflowDefinitionSeed.model_validate(
        {
            "id": "base-workflow",
            "description": "Base workflow",
            "policy": "default",
            "defaults": {
                "metadata": {"shared": "base", "kept": True},
                "skill_refs": [{"provider": "openclaw", "key": "base-default"}],
            },
            "nodes": [
                {
                    "id": "root",
                    "role": "planner-supervisor",
                    "mode": "plan",
                    "description": "Base root",
                    "metadata": {"from_base": True},
                    "skill_refs": [{"provider": "openclaw", "key": "contract-checker"}],
                },
                {
                    "id": "review",
                    "role": "reviewer",
                    "mode": "review",
                },
            ],
            "edges": [{"from": "root", "to": "review"}],
            "skill_refs": [{"provider": "openclaw", "key": "base-top"}],
        }
    )
    override = WorkflowDefinitionSeed.model_validate(
        {
            "id": "derived-workflow",
            "description": "Derived workflow",
            "extends": "base-workflow",
            "defaults": {
                "metadata": {"shared": "override", "extra": "value"},
                "skill_refs": [
                    {
                        "provider": "openclaw",
                        "key": "base-default",
                        "state": "required",
                    }
                ],
            },
            "nodes": [
                {
                    "id": "root",
                    "role": "planner-supervisor",
                    "mode": "plan",
                    "description": "Override root",
                    "metadata": {"from_override": True},
                    "skill_refs": [
                        {
                            "provider": "openclaw",
                            "key": "contract-checker",
                            "state": "required",
                        }
                    ],
                },
                {
                    "id": "sync",
                    "role": "syncer",
                    "mode": "sync",
                },
            ],
            "edges": [{"from": "review", "to": "sync"}],
            "skill_refs": [{"provider": "openclaw", "key": "derived-top"}],
        }
    )

    merged = _merge_workflow_seeds(base, override)

    assert merged.id == "derived-workflow"
    assert merged.description == "Derived workflow"
    assert merged.policy == "default"
    assert merged.defaults.metadata == {
        "shared": "override",
        "kept": True,
        "extra": "value",
    }
    assert merged.defaults.skill_refs == [
        _skill_ref("base-default", state=SkillBindingState.REQUIRED)
    ]
    assert [node.id for node in merged.nodes] == ["root", "review", "sync"]

    root = next(node for node in merged.nodes if node.id == "root")
    assert root.role == "planner-supervisor"
    assert root.mode == WorkflowMode.PLAN
    assert root.description == "Override root"
    assert root.metadata == {"from_base": True, "from_override": True}
    assert root.skill_refs == [_skill_ref("contract-checker", state=SkillBindingState.REQUIRED)]

    assert {(edge.from_node, edge.to_node) for edge in merged.edges} == {
        ("root", "review"),
        ("review", "sync"),
    }
    assert merged.skill_refs == [_skill_ref("base-top"), _skill_ref("derived-top")]

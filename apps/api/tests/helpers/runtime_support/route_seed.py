from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from tests.integration.runtime_schema_contract.lineage_support import (
    insert_dispatch_turn,
    seed_runtime_lineage_scope_fixture,
)

_TASK_ID = "task.alpha.a"
_FLOW_ID = "flow.alpha.a"
_FLOW_REVISION_ID = "flow-revision.alpha.a.1"
_FLOW_NODE_ID = "flow-node.alpha.a.r1.root"
_ASSIGNMENT_ID = "assignment.alpha.a.r1.root"
_ATTEMPT_ID = "attempt.alpha.a.r1.root.01"
_DISPATCH_ID = "dispatch.alpha.a.live"


@dataclass(frozen=True)
class SeededRuntimeRouteTask:
    task_id: str
    active_flow_revision_id: str
    current_open_dispatch_id: str


def seed_runtime_route_task_rows(
    database_path: Path,
    *,
    task_root: Path,
) -> SeededRuntimeRouteTask:
    task_paths = _task_root_paths(task_root)
    _initialize_task_root_layout(task_paths=task_paths, dispatch_id=_DISPATCH_ID)
    with sqlite3.connect(database_path) as connection:
        seed_runtime_lineage_scope_fixture(connection)
        insert_dispatch_turn(
            connection,
            dispatch_id=_DISPATCH_ID,
            flow_id=_FLOW_ID,
            flow_revision_id=_FLOW_REVISION_ID,
            flow_node_id=_FLOW_NODE_ID,
            assignment_id=_ASSIGNMENT_ID,
            attempt_id=_ATTEMPT_ID,
        )
        _configure_task_runtime_rows(
            connection,
            task_root=task_root,
            task_paths=task_paths,
        )
        connection.commit()
    return SeededRuntimeRouteTask(
        task_id=_TASK_ID,
        active_flow_revision_id=_FLOW_REVISION_ID,
        current_open_dispatch_id=_DISPATCH_ID,
    )


def _initialize_task_root_layout(
    *,
    task_paths: dict[str, Path],
    dispatch_id: str,
) -> None:
    for path in task_paths.values():
        path.mkdir(parents=True, exist_ok=True)
    (task_paths["runtime"] / "workflow-manifest.md").write_text("", encoding="utf-8")
    dispatch_dir = task_paths["dispatch"] / dispatch_id
    dispatch_dir.mkdir(parents=True, exist_ok=True)
    (dispatch_dir / "prompt.md").write_text("", encoding="utf-8")


def _configure_task_runtime_rows(
    connection: sqlite3.Connection,
    *,
    task_root: Path,
    task_paths: dict[str, Path],
) -> None:
    dispatch_dir = task_paths["dispatch"] / _DISPATCH_ID
    connection.execute(
        """
        UPDATE tasks
        SET task_root_path = ?
        WHERE task_id = ?
        """,
        (str(task_root), _TASK_ID),
    )
    connection.execute(
        """
        UPDATE flows
        SET
            status = ?,
            active_flow_revision_id = ?,
            current_open_dispatch_id = ?,
            current_node_key = ?
        WHERE task_id = ?
        """,
        ("running", _FLOW_REVISION_ID, _DISPATCH_ID, "root", _TASK_ID),
    )
    connection.execute(
        """
        UPDATE flow_nodes
        SET current_assignment_id = ?
        WHERE flow_node_id = ?
        """,
        (_ASSIGNMENT_ID, _FLOW_NODE_ID),
    )
    connection.execute(
        """
        UPDATE assignments
        SET current_attempt_id = ?
        WHERE assignment_id = ?
        """,
        (_ATTEMPT_ID, _ASSIGNMENT_ID),
    )
    connection.execute(
        """
        UPDATE dispatch_turns
        SET control_state = ?, prompt_name = ?, prompt_path = ?
        WHERE dispatch_id = ?
        """,
        (
            "live",
            "parent_root_dispatch_prompt",
            str(dispatch_dir / "prompt.md"),
            _DISPATCH_ID,
        ),
    )
    _insert_task_root_bindings(connection, task_paths=task_paths)


def _insert_task_root_bindings(
    connection: sqlite3.Connection,
    *,
    task_paths: dict[str, Path],
) -> None:
    connection.executemany(
        """
        INSERT INTO task_resource_bindings (
            task_resource_binding_id,
            task_id,
            binding_kind,
            path,
            binding_mode
        ) VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                f"task-resource-binding.{_TASK_ID}.{binding_kind}",
                _TASK_ID,
                binding_kind,
                str(path),
                None,
            )
            for binding_kind, path in task_paths.items()
        ],
    )


def _task_root_paths(task_root: Path) -> dict[str, Path]:
    runtime_path = task_root / "_runtime"
    context_path = task_root / "context"
    outputs_path = task_root / "outputs"
    tmp_path = task_root / "tmp"
    return {
        "workspace": task_root / "workspace",
        "context": context_path,
        "criteria": runtime_path / "criteria",
        "wiki": context_path / "wiki",
        "outputs": outputs_path,
        "artifacts": outputs_path / "artifacts",
        "tmp": tmp_path,
        "transfers": tmp_path / "transfers",
        "runtime": runtime_path,
        "attempts": runtime_path / "attempts",
        "dispatch": runtime_path / "dispatch",
    }


__all__ = ["SeededRuntimeRouteTask", "seed_runtime_route_task_rows"]

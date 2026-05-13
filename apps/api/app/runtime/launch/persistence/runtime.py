from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.contracts import RuntimeBootstrapProjectionInput, RuntimeBootstrapResult
from app.runtime.launch.bootstrap.context import build_launch_bootstrap_persistence_context
from app.runtime.launch.bootstrap.projection import build_bootstrap_runtime_projection_result
from app.runtime.launch.bootstrap.rows import stage_launch_bootstrap_rows
from app.runtime.launch.persistence.attempts import stage_launch_attempt_rows
from app.runtime.projection.attempt_materialization import materialize_attempt_files
from app.runtime.projection.manifest.materialization import materialize_manifest


async def materialize_bootstrap_runtime_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> None:
    await materialize_manifest(session, task_id)
    await materialize_attempt_files(session, task_id, attempt_id)


async def persist_bootstrap_runtime_from_precomputed(
    session: AsyncSession,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    *,
    commit: bool = True,
) -> RuntimeBootstrapResult:
    result = build_bootstrap_runtime_projection_result(bootstrap_input)
    context = build_launch_bootstrap_persistence_context(
        result=result,
        bootstrap_input=bootstrap_input,
    )
    await stage_launch_bootstrap_rows(
        session,
        bootstrap_input=bootstrap_input,
        result=result,
        context=context,
    )
    await stage_launch_attempt_rows(
        session,
        bootstrap_input=bootstrap_input,
        result=result,
        flow_id=context.flow_id,
    )
    if not commit:
        return result
    await session.commit()
    await materialize_bootstrap_runtime_outputs(
        session,
        task_id=bootstrap_input.task_id,
        attempt_id=bootstrap_input.attempt_id,
    )
    return result

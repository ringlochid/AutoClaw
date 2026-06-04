from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.runtime.launch.bootstrap.context import build_launch_bootstrap_persistence_context
from autoclaw.runtime.launch.bootstrap.projection import build_bootstrap_runtime_projection_result
from autoclaw.runtime.launch.bootstrap.rows import stage_launch_bootstrap_rows
from autoclaw.runtime.launch.persistence.attempts import stage_launch_attempt_rows
from autoclaw.runtime.projection.attempt_materialization import (
    materialize_attempt_files,
    write_attempt_projection_files,
)
from autoclaw.runtime.projection.manifest.materialization import (
    materialize_manifest,
    write_manifest_projection_files,
)
from autoclaw.runtime.task_root import (
    localize_assignment_projection,
    localize_checkpoint_projection,
    localize_manifest_projection,
)
from autoclaw.schemas.runtime.contracts import (
    RuntimeBootstrapProjectionInput,
    RuntimeBootstrapResult,
)


async def persist_bootstrap_runtime_from_precomputed(
    session: AsyncSession,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    *,
    should_commit: bool = True,
    **legacy_shim_kwargs: bool,
) -> RuntimeBootstrapResult:
    legacy_commit = legacy_shim_kwargs.pop("commit", None)
    if legacy_shim_kwargs:
        unexpected_keyword = next(iter(legacy_shim_kwargs))
        raise TypeError(
            f"persist_bootstrap_runtime_from_precomputed() got an unexpected keyword argument "
            f"'{unexpected_keyword}'"
        )
    if legacy_commit is not None:
        should_commit = legacy_commit

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
    if not should_commit:
        return result
    await session.commit()
    write_bootstrap_runtime_outputs(result)
    return result


def write_bootstrap_runtime_outputs(result: RuntimeBootstrapResult) -> None:
    localized_manifest = localize_manifest_projection(paths=result.paths, manifest=result.manifest)
    localized_assignment = localize_assignment_projection(
        paths=result.paths,
        assignment=result.assignment,
    )
    localized_checkpoint = (
        localize_checkpoint_projection(paths=result.paths, checkpoint=result.latest_checkpoint)
        if result.latest_checkpoint is not None
        else None
    )
    write_manifest_projection_files(paths=result.paths, manifest=localized_manifest)
    write_attempt_projection_files(
        paths=result.paths,
        attempt_id=result.prompt_record.attempt_id,
        assignment_projection=localized_assignment,
        node_key=localized_assignment.node_key,
        checkpoint_projection=localized_checkpoint,
        produced_refs=[],
    )


async def materialize_bootstrap_runtime_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> None:
    await materialize_manifest(session, task_id)
    await materialize_attempt_files(session, task_id, attempt_id)

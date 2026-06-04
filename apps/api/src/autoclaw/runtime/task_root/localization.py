from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from autoclaw.runtime.task_root.paths import coerce_path
from autoclaw.schemas.runtime.contracts import (
    AssignmentProjection,
    CheckpointProjection,
    EvidenceRef,
    ManifestCurrentContextProjection,
    ManifestNodeCriteriaProjection,
    ManifestNodeProjection,
    ManifestProjection,
    RuntimeContextRef,
    TaskRootPaths,
)


def localize_assignment_projection(
    *,
    paths: TaskRootPaths,
    assignment: AssignmentProjection,
) -> AssignmentProjection:
    return assignment.model_copy(
        update={
            "criteria": tuple(
                _localize_evidence_ref(paths=paths, ref=ref) for ref in assignment.criteria
            ),
            "consumes": tuple(
                localize_runtime_context_ref(paths=paths, ref=ref) for ref in assignment.consumes
            ),
            "transient_refs": tuple(
                _localize_evidence_ref(paths=paths, ref=ref) for ref in assignment.transient_refs
            ),
        }
    )


def localize_checkpoint_projection(
    *,
    paths: TaskRootPaths,
    checkpoint: CheckpointProjection,
) -> CheckpointProjection:
    return checkpoint.model_copy(
        update={
            "produced_artifacts": tuple(
                _localize_evidence_ref(paths=paths, ref=ref)
                for ref in checkpoint.produced_artifacts
            ),
            "transient_refs": tuple(
                _localize_evidence_ref(paths=paths, ref=ref) for ref in checkpoint.transient_refs
            ),
        }
    )


def localize_manifest_projection(
    *,
    paths: TaskRootPaths,
    manifest: ManifestProjection,
) -> ManifestProjection:
    return manifest.model_copy(
        update={
            "current_context": ManifestCurrentContextProjection(
                current_node_key=manifest.current_context.current_node_key,
                owner_node_key=manifest.current_context.owner_node_key,
                active_attempt_id=manifest.current_context.active_attempt_id,
                active_assignment_path=manifest.current_context.active_assignment_path,
                latest_checkpoint_path=manifest.current_context.latest_checkpoint_path,
                latest_relevant_checkpoint_path=manifest.current_context.latest_relevant_checkpoint_path,
                current_relevant_paths=tuple(
                    localize_runtime_context_ref(paths=paths, ref=ref)
                    for ref in manifest.current_context.current_relevant_paths
                ),
            ),
            "node_tree": tuple(
                _localize_manifest_node_projection(paths=paths, node=node)
                for node in manifest.node_tree
            ),
        }
    )


def localize_transient_surface(
    *,
    paths: TaskRootPaths,
    source_path: Path,
    owner_node_key: str,
    target_name: str | None = None,
) -> Path:
    destination = planned_transient_surface_path(
        paths=paths,
        source_path=source_path,
        owner_node_key=owner_node_key,
        target_name=target_name,
    )
    resolved_source = coerce_path(source_path)
    copy_file_if_needed(source_path=resolved_source, destination=destination)
    return destination


def localize_runtime_context_ref(
    *,
    paths: TaskRootPaths,
    ref: RuntimeContextRef,
) -> RuntimeContextRef:
    if isinstance(ref, EvidenceRef):
        return _localize_evidence_ref(paths=paths, ref=ref)
    return ref


def planned_transient_surface_path(
    *,
    paths: TaskRootPaths,
    source_path: Path,
    owner_node_key: str,
    target_name: str | None = None,
) -> Path:
    resolved_source = coerce_path(source_path)
    if not resolved_source.is_file():
        raise FileNotFoundError(f"transient surface does not exist: {resolved_source}")

    try:
        resolved_source.relative_to(paths.transfers_path)
    except ValueError:
        pass
    else:
        return resolved_source

    try:
        resolved_source.relative_to(paths.task_root)
    except ValueError:
        pass

    destination_root = paths.transfers_path / owner_node_key
    destination_name = target_name or resolved_source.name
    destination = destination_root / destination_name
    if destination.exists():
        if (
            hashlib.sha256(destination.read_bytes()).digest()
            == hashlib.sha256(resolved_source.read_bytes()).digest()
        ):
            return destination
        suffix_hash = hashlib.sha256(resolved_source.read_bytes()).hexdigest()[:8]
        destination = (
            destination_root / f"{resolved_source.stem}-{suffix_hash}{resolved_source.suffix}"
        )

    return destination


def copy_file_if_needed(*, source_path: Path, destination: Path) -> None:
    if source_path == destination:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)


def localize_external_resource(
    *,
    paths: TaskRootPaths,
    source_path: Path,
    target_name: str | None = None,
) -> Path:
    resolved_source = coerce_path(source_path)
    try:
        resolved_source.relative_to(paths.task_root)
    except ValueError:
        pass
    else:
        return resolved_source
    if not resolved_source.is_file():
        raise FileNotFoundError(f"external resource does not exist: {resolved_source}")

    destination_name = target_name or resolved_source.name
    destination_root = paths.transfers_path / "localized"
    destination = destination_root / destination_name
    if destination.exists():
        if (
            hashlib.sha256(destination.read_bytes()).digest()
            == hashlib.sha256(resolved_source.read_bytes()).digest()
        ):
            return destination
        suffix_hash = hashlib.sha256(resolved_source.read_bytes()).hexdigest()[:8]
        destination = destination_root / (
            f"{resolved_source.stem}-{suffix_hash}{resolved_source.suffix}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolved_source, destination)
    return destination


def _localize_evidence_ref(
    *,
    paths: TaskRootPaths,
    ref: EvidenceRef,
) -> EvidenceRef:
    return ref.model_copy(
        update={"path": localize_external_resource(paths=paths, source_path=ref.path)}
    )


def _localize_manifest_node_projection(
    *,
    paths: TaskRootPaths,
    node: ManifestNodeProjection,
) -> ManifestNodeProjection:
    return node.model_copy(
        update={
            "criteria": tuple(
                ManifestNodeCriteriaProjection(
                    owner_node_key=criteria.owner_node_key,
                    slot=criteria.slot,
                    description=criteria.description,
                    path=localize_external_resource(paths=paths, source_path=criteria.path),
                )
                for criteria in node.criteria
            )
        }
    )

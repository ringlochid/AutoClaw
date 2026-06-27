from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.authoring.contracts import (
    DefinitionDraftValidationIssue,
    DefinitionDraftValidationResponse,
)
from autoclaw.definitions.authoring.readback import (
    CurrentDefinitionSnapshot,
    entry_is_stale,
    load_current_definition_snapshot,
    load_current_definition_snapshots,
    parse_definition_body_for_storage,
    require_manifest_file_entry,
)
from autoclaw.definitions.authoring.storage import (
    StoredDraftFileEntry,
    StoredDraftSetManifest,
    read_definition_draft_body,
    read_preview_task_compose_body,
)
from autoclaw.definitions.compiler import (
    MappingRolePolicyLookup,
    PolicyRevisionDefinition,
    RoleRevisionDefinition,
    WorkflowRevisionMetadata,
    compile_workflow,
)
from autoclaw.definitions.contracts import (
    DefinitionContent,
    DefinitionKind,
    PolicyDefinitionInput,
    RoleDefinitionInput,
    WorkflowDefinitionInput,
)
from autoclaw.definitions.registry.current import build_role_policy_lookup
from autoclaw.runtime.contracts import TaskStartRequest


@dataclass(frozen=True)
class DraftValidationOutcome:
    response: DefinitionDraftValidationResponse
    valid_definitions: dict[tuple[DefinitionKind, str], DefinitionContent]
    preview_request: TaskStartRequest | None


@dataclass(frozen=True)
class DraftDefinitionValidation:
    valid_definitions: dict[tuple[DefinitionKind, str], DefinitionContent]
    invalid_keys: dict[DefinitionKind, set[str]]
    errors: list[DefinitionDraftValidationIssue]


async def validate_draft_set(
    session: AsyncSession,
    *,
    data_dir: Path,
    manifest: StoredDraftSetManifest,
    is_preview_required: bool,
    preview_body: str | None = None,
) -> DraftValidationOutcome:
    current_snapshots = await load_current_definition_snapshots(session, entries=manifest.files)
    definition_validation = validate_draft_definition_files(
        data_dir=data_dir,
        manifest=manifest,
        current_snapshots=current_snapshots,
    )
    errors = list(definition_validation.errors)
    warnings: list[DefinitionDraftValidationIssue] = []

    combined_lookup = await combined_role_policy_lookup(
        session,
        valid_definitions=definition_validation.valid_definitions,
        invalid_role_keys=definition_validation.invalid_keys[DefinitionKind.ROLE],
        invalid_policy_keys=definition_validation.invalid_keys[DefinitionKind.POLICY],
    )
    errors.extend(
        await workflow_cross_reference_errors(
            manifest=manifest,
            valid_definitions=definition_validation.valid_definitions,
            combined_lookup=combined_lookup,
        )
    )

    preview_validation_body = preview_body
    if preview_validation_body is None:
        preview_validation_body = read_preview_task_compose_body(data_dir, manifest.draft_set_id)
    preview_errors = await validate_preview_task_compose(
        session,
        manifest=manifest,
        preview_body=preview_validation_body,
        is_preview_required=is_preview_required,
        valid_definitions=definition_validation.valid_definitions,
        invalid_workflow_keys=definition_validation.invalid_keys[DefinitionKind.WORKFLOW],
        combined_lookup=combined_lookup,
    )
    if is_preview_required:
        errors.extend(preview_errors)
    else:
        warnings.extend(preview_errors)

    preview_request = None
    if preview_validation_body is not None and not preview_errors:
        preview_request = parse_task_compose_request(preview_validation_body)

    return DraftValidationOutcome(
        response=DefinitionDraftValidationResponse(
            draft_set_id=manifest.draft_set_id,
            status=validation_status(errors),
            errors=tuple(errors),
            warnings=tuple(warnings),
        ),
        valid_definitions=definition_validation.valid_definitions,
        preview_request=preview_request,
    )


def validate_draft_definition_files(
    *,
    data_dir: Path,
    manifest: StoredDraftSetManifest,
    current_snapshots: dict[tuple[DefinitionKind, str], CurrentDefinitionSnapshot],
) -> DraftDefinitionValidation:
    valid_definitions: dict[tuple[DefinitionKind, str], DefinitionContent] = {}
    invalid_keys: dict[DefinitionKind, set[str]] = {kind: set() for kind in DefinitionKind}
    errors: list[DefinitionDraftValidationIssue] = []

    for entry in manifest.files:
        parsed_content = validate_draft_definition_file(
            data_dir=data_dir,
            manifest=manifest,
            entry=entry,
            current_snapshot=current_snapshots.get((entry.kind, entry.key)),
            invalid_keys=invalid_keys,
            errors=errors,
        )
        if parsed_content is not None:
            valid_definitions[(entry.kind, entry.key)] = parsed_content

    return DraftDefinitionValidation(
        valid_definitions=valid_definitions,
        invalid_keys=invalid_keys,
        errors=errors,
    )


def validate_draft_definition_file(
    *,
    data_dir: Path,
    manifest: StoredDraftSetManifest,
    entry: StoredDraftFileEntry,
    current_snapshot: CurrentDefinitionSnapshot | None,
    invalid_keys: dict[DefinitionKind, set[str]],
    errors: list[DefinitionDraftValidationIssue],
) -> DefinitionContent | None:
    body = read_definition_draft_body(data_dir, manifest.draft_set_id, entry)
    parsed = parse_definition_body_for_storage(kind=entry.kind, key=entry.key, body=body)
    parsed_content: DefinitionContent | None = None
    if parsed.error is not None:
        invalid_keys[entry.kind].add(entry.key)
        errors.append(
            DefinitionDraftValidationIssue(
                code="invalid_definition_body",
                message=parsed.error,
                path=entry.draft_path,
                kind="schema",
            )
        )
    else:
        assert parsed.content is not None
        parsed_content = parsed.content

    if entry_is_stale(entry, current_snapshot=current_snapshot):
        errors.append(
            DefinitionDraftValidationIssue(
                code="stale_baseline",
                message=f"draft file '{entry.key}' is based on registry truth that has changed",
                path=entry.draft_path,
                kind="stale",
            )
        )
    return parsed_content


async def combined_role_policy_lookup(
    session: AsyncSession,
    *,
    valid_definitions: dict[tuple[DefinitionKind, str], DefinitionContent],
    invalid_role_keys: set[str],
    invalid_policy_keys: set[str],
) -> MappingRolePolicyLookup:
    current_lookup = await build_role_policy_lookup(session)
    roles = dict(current_lookup.roles)
    policies = dict(current_lookup.policies)

    for role_key in invalid_role_keys:
        roles.pop(role_key, None)
    for policy_key in invalid_policy_keys:
        policies.pop(policy_key, None)

    for (kind, key), content in valid_definitions.items():
        if kind == DefinitionKind.ROLE:
            roles[key] = RoleRevisionDefinition(
                definition=cast(RoleDefinitionInput, content),
                revision_no=1,
            )
        elif kind == DefinitionKind.POLICY:
            policies[key] = PolicyRevisionDefinition(
                definition=cast(PolicyDefinitionInput, content),
                revision_no=1,
            )

    return MappingRolePolicyLookup(roles=roles, policies=policies)


async def workflow_cross_reference_errors(
    *,
    manifest: StoredDraftSetManifest,
    valid_definitions: dict[tuple[DefinitionKind, str], DefinitionContent],
    combined_lookup: MappingRolePolicyLookup,
) -> list[DefinitionDraftValidationIssue]:
    errors: list[DefinitionDraftValidationIssue] = []
    for (kind, key), content in valid_definitions.items():
        if kind != DefinitionKind.WORKFLOW:
            continue
        entry = require_manifest_file_entry(manifest, kind=kind, key=key)
        try:
            compile_workflow(
                workflow=cast(WorkflowDefinitionInput, content),
                workflow_revision=WorkflowRevisionMetadata(
                    workflow_key=key,
                    definition_revision_no=entry.based_on.revision_no or 1,
                ),
                compiler_version="definition-authoring-validate",
                lookup=combined_lookup,
            )
        except ValueError as exc:
            errors.append(
                DefinitionDraftValidationIssue(
                    code="workflow_cross_reference_invalid",
                    message=str(exc),
                    path=entry.draft_path,
                    kind="cross_reference",
                )
            )
    return errors


async def validate_preview_task_compose(
    session: AsyncSession,
    *,
    manifest: StoredDraftSetManifest,
    preview_body: str | None,
    is_preview_required: bool,
    valid_definitions: dict[tuple[DefinitionKind, str], DefinitionContent],
    invalid_workflow_keys: set[str],
    combined_lookup: MappingRolePolicyLookup,
) -> list[DefinitionDraftValidationIssue]:
    if preview_body is None:
        if not is_preview_required:
            return []
        return [
            DefinitionDraftValidationIssue(
                code="preview_task_compose_missing",
                message="saved preview task-compose body is required for post-apply task start",
                path=manifest.preview_task_compose_path,
                kind="preview",
            )
        ]

    try:
        preview_request = parse_task_compose_request(preview_body)
    except ValueError as exc:
        return [
            DefinitionDraftValidationIssue(
                code="preview_task_compose_invalid",
                message=str(exc),
                path=manifest.preview_task_compose_path,
                kind="preview",
            )
        ]

    workflow_key = preview_request.workflow.key
    if workflow_key in invalid_workflow_keys:
        return [
            DefinitionDraftValidationIssue(
                code="preview_workflow_invalid",
                message=f"preview task-compose references invalid draft workflow '{workflow_key}'",
                path=manifest.preview_task_compose_path,
                kind="preview",
            )
        ]

    workflow = valid_definitions.get((DefinitionKind.WORKFLOW, workflow_key))
    if workflow is None:
        current_snapshot = await load_current_definition_snapshot(
            session,
            kind=DefinitionKind.WORKFLOW,
            key=workflow_key,
        )
        if current_snapshot is None:
            return [
                DefinitionDraftValidationIssue(
                    code="preview_workflow_missing",
                    message=f"preview task-compose references unknown workflow '{workflow_key}'",
                    path=manifest.preview_task_compose_path,
                    kind="preview",
                )
            ]
        workflow = current_snapshot.content

    try:
        compile_workflow(
            workflow=cast(WorkflowDefinitionInput, workflow),
            workflow_revision=WorkflowRevisionMetadata(
                workflow_key=workflow_key,
                definition_revision_no=1,
            ),
            compiler_version="definition-authoring-preview",
            lookup=combined_lookup,
        )
    except ValueError as exc:
        return [
            DefinitionDraftValidationIssue(
                code="preview_workflow_invalid",
                message=str(exc),
                path=manifest.preview_task_compose_path,
                kind="preview",
            )
        ]
    return []


def parse_task_compose_request(body: str) -> TaskStartRequest:
    try:
        payload = yaml.safe_load(body)
    except yaml.YAMLError as exc:  # pragma: no cover - exercised through invalid YAML tests
        raise ValueError(f"invalid YAML: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("expected YAML mapping content")
    return TaskStartRequest.model_validate(payload)


def validation_status(
    errors: list[DefinitionDraftValidationIssue],
) -> Literal["valid", "invalid", "stale"]:
    if any(error.kind == "stale" for error in errors):
        return "stale"
    if errors:
        return "invalid"
    return "valid"


__all__ = [
    "DraftValidationOutcome",
    "parse_task_compose_request",
    "validate_draft_set",
]

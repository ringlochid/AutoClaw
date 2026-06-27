from __future__ import annotations

from pathlib import Path
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.authoring.contracts import (
    DefinitionDraftPublishedRevision,
    DefinitionDraftSetState,
)
from autoclaw.definitions.authoring.readback import (
    require_manifest_file_entry,
)
from autoclaw.definitions.authoring.storage import (
    StoredDraftBaseline,
    StoredDraftSetManifest,
    draft_body_content_hash,
    normalize_definition_content,
    read_definition_draft_body,
    utc_now,
)
from autoclaw.definitions.contracts import (
    DefinitionContent,
    DefinitionKind,
    PolicyDefinitionInput,
    RoleDefinitionInput,
    WorkflowDefinitionInput,
)
from autoclaw.definitions.registry.revisions.ids import canonical_content_hash
from autoclaw.definitions.registry.upsert import (
    upsert_policy_definition,
    upsert_role_definition,
    upsert_workflow_definition,
)


async def publish_valid_definitions(
    session: AsyncSession,
    *,
    manifest: StoredDraftSetManifest,
    data_dir: Path,
    valid_definitions: dict[tuple[DefinitionKind, str], DefinitionContent],
    existing_content_hashes: dict[tuple[DefinitionKind, str], str],
) -> tuple[list[DefinitionDraftPublishedRevision], StoredDraftSetManifest]:
    published_revisions: list[DefinitionDraftPublishedRevision] = []
    refreshed_manifest = manifest.model_copy(deep=True)

    for kind in (DefinitionKind.ROLE, DefinitionKind.POLICY, DefinitionKind.WORKFLOW):
        for entry in [file_entry for file_entry in manifest.files if file_entry.kind == kind]:
            content = valid_definitions.get((kind, entry.key))
            if content is None:
                continue

            source_path = f"draft-set://{manifest.draft_set_id}/{entry.draft_path}"
            if kind == DefinitionKind.ROLE:
                revision_no = (
                    await upsert_role_definition(
                        session,
                        cast(RoleDefinitionInput, content),
                        source_path=source_path,
                    )
                ).revision_no
            elif kind == DefinitionKind.POLICY:
                revision_no = (
                    await upsert_policy_definition(
                        session,
                        cast(PolicyDefinitionInput, content),
                        source_path=source_path,
                    )
                ).revision_no
            else:
                revision_no = (
                    await upsert_workflow_definition(
                        session,
                        cast(WorkflowDefinitionInput, content),
                        source_path=source_path,
                    )
                ).revision_no

            normalized_content = normalize_definition_content(content)
            content_hash = canonical_content_hash(normalized_content)
            if existing_content_hashes.get((kind, entry.key)) != content_hash:
                published_revisions.append(
                    DefinitionDraftPublishedRevision(
                        kind=kind,
                        key=entry.key,
                        revision_no=revision_no,
                        content_hash=content_hash,
                    )
                )

            refreshed_entry = require_manifest_file_entry(
                refreshed_manifest,
                kind=kind,
                key=entry.key,
            )
            refreshed_entry.based_on = StoredDraftBaseline(
                revision_no=revision_no,
                content_hash=content_hash,
                source_path=source_path,
            )
            refreshed_entry.baseline_body = read_definition_draft_body(
                data_dir,
                manifest.draft_set_id,
                entry,
            )
            refreshed_entry.baseline_normalized_content = normalized_content
            refreshed_entry.content_hash = draft_body_content_hash(refreshed_entry.baseline_body)

    refreshed_manifest.state = DefinitionDraftSetState.APPLIED.value
    refreshed_manifest.updated_at = utc_now()
    return published_revisions, refreshed_manifest


__all__ = ["publish_valid_definitions"]

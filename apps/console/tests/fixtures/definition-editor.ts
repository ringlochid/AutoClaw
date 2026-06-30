import type { components } from "../../src/api/generated/openapi";

export const DEFINITION_EDITOR_SCREENSHOT_DIR =
    "/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/continuation-implementation/14-definition-editor/screenshots";

export const DEFINITION_EDITOR_DRAFT_SET_ID = "draft-set-definition-editor";
export const DEFINITION_EDITOR_WORKFLOW_KEY = "definition-editor-page";
export const DEFINITION_EDITOR_ROLE_KEY = "definition-editor-review";
export const DEFINITION_EDITOR_POLICY_KEY = "definition-editor-launch-guard";
export const DEFINITION_EDITOR_NEW_DRAFT_KEY = "definition-editor-new-role";
export const DEFINITION_EDITOR_MATERIALIZED_KEY = "definition-editor-materialized";
export const DEFINITION_EDITOR_UPDATED_BODY =
    "id: definition-editor-page\ndescription: Saved clean draft body.\n";

const UPDATED_AT = "2026-06-29T20:15:00Z";

export function createDefinitionEditorDraftSetList(
    detail: components["schemas"]["DefinitionDraftSetDetail"] = createDefinitionEditorDraftSetDetail(),
): components["schemas"]["DefinitionDraftSetListResponse"] {
    return {
        items: [draftSetSummaryFromDetail(detail)],
        next_cursor: null,
    };
}

export function createDefinitionEditorDraftSetDetail(
    overrides: Partial<components["schemas"]["DefinitionDraftSetDetail"]> = {},
): components["schemas"]["DefinitionDraftSetDetail"] {
    return {
        created_at: "2026-06-29T19:40:00Z",
        draft_set_id: DEFINITION_EDITOR_DRAFT_SET_ID,
        files: [
            createDefinitionEditorDraftFile({
                key: DEFINITION_EDITOR_WORKFLOW_KEY,
                kind: "workflow",
                status: "modified",
            }),
            createDefinitionEditorDraftFile({
                key: DEFINITION_EDITOR_ROLE_KEY,
                kind: "role",
                status: "clean",
            }),
            createDefinitionEditorDraftFile({
                basedOn: null,
                key: DEFINITION_EDITOR_POLICY_KEY,
                kind: "policy",
                status: "added",
            }),
        ],
        preview_task_compose_body:
            "task:\n  key: definition-editor-preview\nworkflow:\n  key: definition-editor-page\n",
        preview_task_compose_path: "drafts/task-compose.preview.yaml",
        state: "open",
        title: "Definition Editor draft set",
        updated_at: UPDATED_AT,
        ...overrides,
    };
}

export function createDefinitionEditorDraftSetResponse(
    detail: components["schemas"]["DefinitionDraftSetDetail"] = createDefinitionEditorDraftSetDetail(),
): components["schemas"]["DefinitionDraftSetDetailResponse"] {
    return {
        draft_set: detail,
    };
}

export function createDefinitionEditorDraftFile({
    basedOn = {
        content_hash: "sha256:stored-baseline",
        revision_no: 12,
        source_path: null,
    },
    body,
    key,
    kind,
    status,
}: {
    readonly basedOn?: components["schemas"]["DefinitionDraftBaselineRead"] | null;
    readonly body?: string;
    readonly key: string;
    readonly kind: components["schemas"]["DefinitionKind"];
    readonly status: components["schemas"]["DefinitionDraftFileStatus"];
}): components["schemas"]["DefinitionDraftFileDetail"] {
    const draftBody = body ?? starterBodyForKind(kind, key);
    return {
        based_on: basedOn ?? {
            content_hash: null,
            revision_no: null,
            source_path: null,
        },
        baseline_body:
            basedOn === null ? starterBodyForKind(kind, key) : storedBodyForKind(kind, key),
        baseline_normalized_content: null,
        body: draftBody,
        body_format: "yaml",
        content_hash: `sha256:${kind}-${key}-${status}`,
        draft_path: `drafts/${kind}s/${key}.yaml`,
        key,
        kind,
        normalized_content: null,
        normalized_path: `drafts/${kind}s/${key}.json`,
        status,
    };
}

export function createCleanSavedDefinitionEditorDraftSet(
    body = DEFINITION_EDITOR_UPDATED_BODY,
): components["schemas"]["DefinitionDraftSetDetail"] {
    return createDefinitionEditorDraftSetDetail({
        files: [
            createDefinitionEditorDraftFile({
                body,
                key: DEFINITION_EDITOR_WORKFLOW_KEY,
                kind: "workflow",
                status: "clean",
            }),
            createDefinitionEditorDraftFile({
                key: DEFINITION_EDITOR_ROLE_KEY,
                kind: "role",
                status: "clean",
            }),
            createDefinitionEditorDraftFile({
                basedOn: null,
                key: DEFINITION_EDITOR_POLICY_KEY,
                kind: "policy",
                status: "added",
            }),
        ],
    });
}

export function createResetDefinitionEditorDraftSet(): components["schemas"]["DefinitionDraftSetDetail"] {
    return createCleanSavedDefinitionEditorDraftSet(
        storedBodyForKind("workflow", DEFINITION_EDITOR_WORKFLOW_KEY),
    );
}

export function createRematerializedDefinitionEditorDraftSet(): components["schemas"]["DefinitionDraftSetDetail"] {
    return createDefinitionEditorDraftSetDetail({
        files: [
            createDefinitionEditorDraftFile({
                basedOn: {
                    content_hash: "sha256:current-stored",
                    revision_no: 13,
                    source_path: null,
                },
                body: "id: definition-editor-page\ndescription: Current stored revision body.\n",
                key: DEFINITION_EDITOR_WORKFLOW_KEY,
                kind: "workflow",
                status: "clean",
            }),
            createDefinitionEditorDraftFile({
                key: DEFINITION_EDITOR_ROLE_KEY,
                kind: "role",
                status: "clean",
            }),
            createDefinitionEditorDraftFile({
                basedOn: null,
                key: DEFINITION_EDITOR_POLICY_KEY,
                kind: "policy",
                status: "added",
            }),
        ],
    });
}

export function createNewDraftAddedSet(
    body: string,
): components["schemas"]["DefinitionDraftSetDetail"] {
    const current = createDefinitionEditorDraftSetDetail();
    return {
        ...current,
        files: [
            ...current.files,
            createDefinitionEditorDraftFile({
                basedOn: null,
                body,
                key: DEFINITION_EDITOR_NEW_DRAFT_KEY,
                kind: "role",
                status: "added",
            }),
        ],
    };
}

export function createMaterializedDraftSet(): components["schemas"]["DefinitionDraftSetDetail"] {
    const current = createDefinitionEditorDraftSetDetail();
    return {
        ...current,
        files: [
            ...current.files,
            createDefinitionEditorDraftFile({
                key: DEFINITION_EDITOR_MATERIALIZED_KEY,
                kind: "workflow",
                status: "clean",
            }),
        ],
    };
}

export function createDefinitionEditorValidation(
    status: components["schemas"]["DefinitionDraftValidationResponse"]["status"] = "valid",
): components["schemas"]["DefinitionDraftValidationResponse"] {
    if (status === "invalid") {
        return {
            draft_set_id: DEFINITION_EDITOR_DRAFT_SET_ID,
            errors: [
                {
                    code: "missing_required_field",
                    kind: "schema",
                    message: "Workflow root.role is required.",
                    path: "workflows.definition-editor-page.root.role",
                },
                {
                    code: "missing_role_reference",
                    kind: "cross_reference",
                    message:
                        "Workflow references role ui_designer_browser_first that is not present.",
                    path: "workflows.definition-editor-page.root.children.0.role",
                },
            ],
            status: "invalid",
            warnings: [
                {
                    code: "preview_review_recommended",
                    kind: "preview",
                    message: "Preview output should be reviewed before task-start handoff.",
                    path: "task-compose.preview.yaml",
                },
            ],
        };
    }

    if (status === "stale") {
        return {
            draft_set_id: DEFINITION_EDITOR_DRAFT_SET_ID,
            errors: [
                {
                    code: "stale_baseline",
                    kind: "stale",
                    message: "Stored workflow revision moved after this draft was materialized.",
                    path: "workflows.definition-editor-page",
                },
            ],
            status: "stale",
            warnings: [],
        };
    }

    return {
        draft_set_id: DEFINITION_EDITOR_DRAFT_SET_ID,
        errors: [],
        status: "valid",
        warnings: [
            {
                code: "preview_only_warning",
                kind: "preview",
                message: "Preview task-compose input is valid but still optional for apply.",
                path: "task-compose.preview.yaml",
            },
        ],
    };
}

export function createDefinitionEditorPreview(
    status: components["schemas"]["DefinitionDraftTaskComposePreviewResponse"]["status"] = "valid",
): components["schemas"]["DefinitionDraftTaskComposePreviewResponse"] {
    return {
        status,
        validation:
            status === "valid"
                ? createDefinitionEditorValidation("valid")
                : {
                      draft_set_id: DEFINITION_EDITOR_DRAFT_SET_ID,
                      errors: [
                          {
                              code: "invalid_task_compose",
                              kind: "preview",
                              message: "Preview task-compose input does not match the draft set.",
                              path: "task.workflow.key",
                          },
                      ],
                      status: "invalid",
                      warnings: [],
                  },
    };
}

export function createDefinitionEditorApply(
    outcome: "no_op" | "published" = "published",
): components["schemas"]["DefinitionDraftApplyResponse"] {
    return {
        draft_set_id: DEFINITION_EDITOR_DRAFT_SET_ID,
        published_revisions:
            outcome === "no_op"
                ? []
                : [
                      {
                          content_hash: "sha256:published-workflow",
                          key: DEFINITION_EDITOR_WORKFLOW_KEY,
                          kind: "workflow",
                          revision_no: 14,
                      },
                  ],
        started_task_id: null,
        status: "applied",
        task_start_failure: null,
        task_start_status: "not_requested",
        validation: createDefinitionEditorValidation("valid"),
    };
}

export function createDefinitionEditorAuthFailure() {
    return {
        detail: {
            code: "illegal_caller",
            field_path: null,
            ok: false,
            retryable: false,
            suggested_next_step: "Provide a valid operator API key.",
            summary: "Definition authoring requires an operator API key.",
        },
    };
}

function draftSetSummaryFromDetail(
    detail: components["schemas"]["DefinitionDraftSetDetail"],
): components["schemas"]["DefinitionDraftSetSummary"] {
    return {
        created_at: detail.created_at,
        draft_set_id: detail.draft_set_id,
        files: detail.files.map((file) => ({
            based_on: file.based_on,
            body_format: file.body_format,
            content_hash: file.content_hash,
            draft_path: file.draft_path,
            key: file.key,
            kind: file.kind,
            normalized_path: file.normalized_path,
            status: file.status,
        })),
        preview_task_compose_path: detail.preview_task_compose_path,
        state: detail.state,
        title: detail.title,
        updated_at: detail.updated_at,
    };
}

function starterBodyForKind(kind: components["schemas"]["DefinitionKind"], key: string): string {
    if (kind === "workflow") {
        return [
            "kind: workflow",
            `id: ${key}`,
            "description: Deliver the Definition Editor authoring surface with preview-aware validation.",
            "root:",
            "  id: root",
            "  role: planning_lead",
            "  policy: standard-parent",
            "  description: Coordinate the authoring workbench.",
            "  instruction: Keep draft, preview, apply, and launch truth separate.",
            "",
        ].join("\n");
    }

    if (kind === "policy") {
        return [
            "kind: policy",
            `id: ${key}`,
            "description: Guard launch from unsaved draft state.",
            "instruction: Keep Task Start separate from draft editing.",
            "applies_to:",
            "  - worker",
            "capabilities:",
            "  command_run: deny",
            "  human_request:",
            "    mode: deny",
            "    allowed_kinds: []",
            "",
        ].join("\n");
    }

    return [
        "kind: role",
        `id: ${key}`,
        "description: Review the Definition Editor authoring scope.",
        "instruction: Verify reset and rematerialize-current remain separate actions.",
        "allowed_node_kinds:",
        "  - worker",
        "",
    ].join("\n");
}

function storedBodyForKind(kind: components["schemas"]["DefinitionKind"], key: string): string {
    return starterBodyForKind(kind, key).replace(
        "Deliver the Definition Editor authoring surface with preview-aware validation.",
        "Captured stored baseline for the Definition Editor authoring surface.",
    );
}

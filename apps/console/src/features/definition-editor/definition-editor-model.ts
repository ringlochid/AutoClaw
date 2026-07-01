import type { ConsoleErrorView } from "../../api/client";
import type { components } from "../../api/generated/openapi";
import type { StatusTone } from "../../components/ui";
import type {
    DefinitionKind,
    DraftApplyResponse,
    DraftFileDetail,
    DraftSetDetail,
    DraftValidationResponse,
} from "./definition-editor-data";

export type EditorMode = "edit" | "preview" | "validation";
export type PreviewProvenance = "draft_truth" | "stored_truth";

export interface DraftFileView {
    readonly baselineBody: string | null;
    readonly baselineLabel: string;
    readonly body: string;
    readonly contentHash: string;
    readonly draftPath: string;
    readonly hasStoredTruth: boolean;
    readonly id: string;
    readonly key: string;
    readonly kind: DefinitionKind;
    readonly normalizedPath: string;
    readonly resetSummary: string;
    readonly revisionNo: number | null;
    readonly status: components["schemas"]["DefinitionDraftFileStatus"];
    readonly statusLabel: string;
    readonly statusTone: StatusTone;
}

export interface DraftSetView {
    readonly createdAt: string;
    readonly draftSetId: string;
    readonly files: readonly DraftFileView[];
    readonly previewTaskComposeBody: string | null;
    readonly state: components["schemas"]["DefinitionDraftSetState"];
    readonly stateLabel: string;
    readonly stateTone: StatusTone;
    readonly title: string | null;
    readonly updatedAt: string;
}

export interface NewDraftForm {
    readonly description: string;
    readonly key: string;
    readonly kind: DefinitionKind;
}

export interface MaterializeForm {
    readonly key: string;
    readonly kind: DefinitionKind;
}

export interface ConfirmationState {
    readonly action: "delete_draft_set" | "rematerialize" | "reset";
}

export interface DraftActionState<T> {
    readonly error: ConsoleErrorView | null;
    readonly isRunning: boolean;
    readonly result: T | null;
}

export interface ValidationView {
    readonly response: DraftValidationResponse;
    readonly stale: boolean;
}

export const EDITOR_MODE_OPTIONS: readonly {
    readonly label: string;
    readonly value: EditorMode;
}[] = [
    { label: "Edit", value: "edit" },
    { label: "Validation", value: "validation" },
    { label: "Preview", value: "preview" },
];

export const DEFINITION_KIND_OPTIONS: readonly {
    readonly label: string;
    readonly value: DefinitionKind;
}[] = [
    { label: "Role", value: "role" },
    { label: "Policy", value: "policy" },
    { label: "Workflow", value: "workflow" },
];

export const PREVIEW_PROVENANCE_OPTIONS: readonly {
    readonly label: string;
    readonly value: PreviewProvenance;
}[] = [
    { label: "Draft truth", value: "draft_truth" },
    { label: "Stored truth", value: "stored_truth" },
];

export const INITIAL_NEW_DRAFT_FORM: NewDraftForm = {
    description: "Author a reusable definition inside this draft set.",
    key: "",
    kind: "role",
};

export const INITIAL_MATERIALIZE_FORM: MaterializeForm = {
    key: "",
    kind: "workflow",
};

export const DEFAULT_PREVIEW_TASK_COMPOSE_BODY =
    "task:\n  key: definition-editor-preview\n  title: Definition editor preview\n  summary: Validate draft-set composition before apply.\nworkflow:\n  key: definition-editor-page\n";

export function mapDraftSetView(draftSet: DraftSetDetail): DraftSetView {
    return {
        createdAt: draftSet.created_at,
        draftSetId: draftSet.draft_set_id,
        files: draftSet.files.map(mapDraftFileView),
        previewTaskComposeBody: draftSet.preview_task_compose_body ?? null,
        state: draftSet.state,
        stateLabel: draftSetStateLabel(draftSet.state),
        stateTone: draftSetStateTone(draftSet.state),
        title: draftSet.title ?? null,
        updatedAt: draftSet.updated_at,
    };
}

export function mapDraftFileView(file: DraftFileDetail): DraftFileView {
    const revisionNo = file.based_on.revision_no ?? null;
    const hasStoredTruth = revisionNo !== null;
    return {
        baselineBody: file.baseline_body ?? null,
        baselineLabel: hasStoredTruth ? `rev ${String(revisionNo)}` : "starter baseline",
        body: file.body,
        contentHash: file.content_hash,
        draftPath: file.draft_path,
        hasStoredTruth,
        id: draftFileId(file.kind, file.key),
        key: file.key,
        kind: file.kind,
        normalizedPath: file.normalized_path,
        resetSummary: hasStoredTruth ? "Reset to captured revision." : "Reset to starter baseline.",
        revisionNo,
        status: file.status,
        statusLabel: draftFileStatusLabel(file.status),
        statusTone: draftFileStatusTone(file.status),
    };
}

export function draftFileId(kind: DefinitionKind, key: string): string {
    return `${kind}:${key}`;
}

export function kindLabel(kind: DefinitionKind): string {
    switch (kind) {
        case "policy":
            return "policy";
        case "role":
            return "role";
        case "workflow":
            return "workflow";
    }
}

export function validationStatusLabel(status: DraftValidationResponse["status"]): string {
    switch (status) {
        case "invalid":
            return "Invalid";
        case "stale":
            return "Stale";
        case "valid":
            return "Valid";
    }
}

export function validationStatusTone(status: DraftValidationResponse["status"]): StatusTone {
    switch (status) {
        case "invalid":
            return "danger";
        case "stale":
            return "warning";
        case "valid":
            return "success";
    }
}

export function applyResultTitle(result: DraftApplyResponse): string {
    if (result.status === "invalid") {
        return "Apply blocked by validation";
    }
    if (result.status === "stale") {
        return "Apply blocked by stale baseline";
    }
    if (result.published_revisions.length === 0) {
        return "Apply completed with no new revision";
    }
    return "Apply published new current revisions";
}

export function applyResultTone(result: DraftApplyResponse): StatusTone {
    if (result.status === "applied" && result.published_revisions.length > 0) {
        return "success";
    }
    if (result.status === "applied") {
        return "neutral";
    }
    if (result.status === "stale") {
        return "warning";
    }
    return "danger";
}

export function buildStarterDraftBody(form: NewDraftForm): string {
    const key = normalizeKey(form.key);
    const description =
        form.description.trim().length === 0
            ? "Author a reusable AutoClaw definition."
            : form.description.trim();

    if (form.kind === "policy") {
        return [
            `id: ${key}`,
            `title: ${key}`,
            `description: ${description}`,
            "instruction: |",
            "  Follow the scoped policy before taking action.",
            "applies_to:",
            "  - worker",
            "capabilities:",
            "  command_run: deny",
            "  human_request:",
            "    mode: deny",
            "    allowed_kinds: []",
            "labels:",
            "  - authoring",
            "",
        ].join("\n");
    }

    if (form.kind === "workflow") {
        return [
            `id: ${key}`,
            `description: ${description}`,
            "root:",
            "  id: root",
            "  role: planning_lead",
            "  policy: standard-parent",
            "  description: Coordinate the authored workflow.",
            "  instruction: Review and dispatch the scoped work.",
            "",
        ].join("\n");
    }

    return [
        `id: ${key}`,
        `title: ${key}`,
        `description: ${description}`,
        "instruction: |",
        "  Implement the assigned scope and publish focused evidence.",
        "allowed_node_kinds:",
        "  - worker",
        "labels:",
        "  - authoring",
        "",
    ].join("\n");
}

export function normalizeKey(key: string): string {
    return key.trim();
}

export function validateNewDraftForm(
    form: NewDraftForm,
    files: readonly DraftFileView[],
): string | null {
    const key = normalizeKey(form.key);
    if (key.length === 0) {
        return "Draft key is required.";
    }
    if (!/^[a-zA-Z0-9_.-]+$/.test(key)) {
        return "Draft key may contain letters, numbers, dot, underscore, and dash.";
    }
    if (files.some((file) => file.kind === form.kind && file.key === key)) {
        return "That draft key already exists in this draft set.";
    }
    return null;
}

export function validateMaterializeForm(form: MaterializeForm): string | null {
    const key = normalizeKey(form.key);
    if (key.length === 0) {
        return "Stored definition key is required.";
    }
    if (!/^[a-zA-Z0-9_.-]+$/.test(key)) {
        return "Stored definition key may contain letters, numbers, dot, underscore, and dash.";
    }
    return null;
}

export function selectedFileFromDraftSet(
    draftSet: DraftSetView | null,
    selectedFileId: string | null,
): DraftFileView | null {
    if (draftSet === null) {
        return null;
    }
    const fallbackFile = draftSet.files.at(0);
    return draftSet.files.find((file) => file.id === selectedFileId) ?? fallbackFile ?? null;
}

export function editorFingerprint({
    draftSetId,
    editorBody,
    selectedFile,
}: {
    readonly draftSetId: string | null;
    readonly editorBody: string;
    readonly selectedFile: DraftFileView | null;
}): string {
    return `${draftSetId ?? "none"}:${selectedFile?.id ?? "none"}:${editorBody}`;
}

function draftFileStatusLabel(status: components["schemas"]["DefinitionDraftFileStatus"]): string {
    switch (status) {
        case "added":
            return "new";
        case "clean":
            return "clean";
        case "invalid":
            return "invalid";
        case "modified":
            return "dirty";
        case "stale":
            return "stale";
    }
}

function draftFileStatusTone(
    status: components["schemas"]["DefinitionDraftFileStatus"],
): StatusTone {
    switch (status) {
        case "added":
            return "active";
        case "clean":
            return "success";
        case "invalid":
            return "danger";
        case "modified":
            return "warning";
        case "stale":
            return "warning";
    }
}

function draftSetStateLabel(state: components["schemas"]["DefinitionDraftSetState"]): string {
    switch (state) {
        case "applied":
            return "applied";
        case "open":
            return "open";
        case "stale":
            return "stale";
    }
}

function draftSetStateTone(state: components["schemas"]["DefinitionDraftSetState"]): StatusTone {
    switch (state) {
        case "applied":
            return "success";
        case "open":
            return "active";
        case "stale":
            return "warning";
    }
}

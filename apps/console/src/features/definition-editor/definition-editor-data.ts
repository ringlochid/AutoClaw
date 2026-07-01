import { AutoClawApiError, requestJson, type ConsoleErrorView } from "../../api/client";
import type { components } from "../../api/generated/openapi";
import {
    definitionDraftFileRematerializeCurrentRoute,
    definitionDraftFileResetRoute,
    definitionDraftFileRoute,
    definitionDraftSetApplyRoute,
    definitionDraftSetMaterializeRoute,
    definitionDraftSetPreviewTaskComposeRoute,
    definitionDraftSetRoute,
    definitionDraftSetValidateRoute,
    definitionDraftSetsRoute,
    type DefinitionDraftSetsQuery,
} from "../../api/routes";

export type DefinitionKind = components["schemas"]["DefinitionKind"];
export type DraftSetListResponse = components["schemas"]["DefinitionDraftSetListResponse"];
export type DraftSetDetailResponse = components["schemas"]["DefinitionDraftSetDetailResponse"];
export type DraftSetDetail = components["schemas"]["DefinitionDraftSetDetail"];
export type DraftFileDetail = components["schemas"]["DefinitionDraftFileDetail"];
export type DraftValidationResponse = components["schemas"]["DefinitionDraftValidationResponse"];
export type DraftPreviewResponse =
    components["schemas"]["DefinitionDraftTaskComposePreviewResponse"];
export type DraftApplyResponse = components["schemas"]["DefinitionDraftApplyResponse"];

const DRAFT_SET_PAGE_SIZE = 12;

export async function readDraftSets({
    cursor,
    signal,
}: {
    readonly cursor: string | null;
    readonly signal: AbortSignal | undefined;
}): Promise<DraftSetListResponse> {
    const query: DefinitionDraftSetsQuery = {
        cursor,
        limit: DRAFT_SET_PAGE_SIZE,
    };
    const route = definitionDraftSetsRoute(query);
    return requestJson<DraftSetListResponse>({
        path: route.path,
        query: route.query,
        signal,
    });
}

export async function createDraftSet({
    materialize = [],
    title,
}: {
    readonly materialize?: readonly {
        readonly key: string;
        readonly kind: DefinitionKind;
    }[];
    readonly title: string | null;
}): Promise<DraftSetDetailResponse> {
    const route = definitionDraftSetsRoute();
    return requestJson<DraftSetDetailResponse>({
        body: {
            materialize: materialize.map((definition) => ({
                key: definition.key,
                kind: definition.kind,
            })),
            preview_task_compose: null,
            title,
        } satisfies components["schemas"]["DefinitionDraftSetCreateRequest"],
        method: "POST",
        path: route.path,
    });
}

export async function readDraftSet({
    draftSetId,
    signal,
}: {
    readonly draftSetId: string;
    readonly signal: AbortSignal | undefined;
}): Promise<DraftSetDetailResponse> {
    const route = definitionDraftSetRoute(draftSetId);
    return requestJson<DraftSetDetailResponse>({
        path: route.path,
        signal,
    });
}

export async function deleteDraftSet(draftSetId: string): Promise<void> {
    const route = definitionDraftSetRoute(draftSetId);
    await requestJson<undefined>({
        method: "DELETE",
        path: route.path,
    });
}

export async function materializeDraftFile({
    draftSetId,
    key,
    kind,
}: {
    readonly draftSetId: string;
    readonly key: string;
    readonly kind: DefinitionKind;
}): Promise<DraftSetDetailResponse> {
    const route = definitionDraftSetMaterializeRoute(draftSetId);
    return requestJson<DraftSetDetailResponse>({
        body: {
            definitions: [{ key, kind }],
        } satisfies components["schemas"]["DefinitionDraftMaterializeRequest"],
        method: "POST",
        path: route.path,
    });
}

export async function writeDraftFile({
    body,
    draftSetId,
    key,
    kind,
}: {
    readonly body: string;
    readonly draftSetId: string;
    readonly key: string;
    readonly kind: DefinitionKind;
}): Promise<DraftSetDetailResponse> {
    const route = definitionDraftFileRoute(draftSetId, kind, key);
    return requestJson<DraftSetDetailResponse>({
        body: {
            body,
            body_format: "yaml",
        } satisfies components["schemas"]["DefinitionDraftFileWriteRequest"],
        method: "PUT",
        path: route.path,
    });
}

export async function resetDraftFile({
    draftSetId,
    key,
    kind,
}: {
    readonly draftSetId: string;
    readonly key: string;
    readonly kind: DefinitionKind;
}): Promise<DraftSetDetailResponse> {
    const route = definitionDraftFileResetRoute(draftSetId, kind, key);
    return requestJson<DraftSetDetailResponse>({
        body: {
            discard_local_changes: true,
        } satisfies components["schemas"]["DefinitionDraftFileResetRequest"],
        method: "POST",
        path: route.path,
    });
}

export async function rematerializeDraftFile({
    draftSetId,
    key,
    kind,
}: {
    readonly draftSetId: string;
    readonly key: string;
    readonly kind: DefinitionKind;
}): Promise<DraftSetDetailResponse> {
    const route = definitionDraftFileRematerializeCurrentRoute(draftSetId, kind, key);
    return requestJson<DraftSetDetailResponse>({
        body: {
            discard_local_changes: true,
        } satisfies components["schemas"]["DefinitionDraftFileRematerializeCurrentRequest"],
        method: "POST",
        path: route.path,
    });
}

export async function validateDraftSet(draftSetId: string): Promise<DraftValidationResponse> {
    const route = definitionDraftSetValidateRoute(draftSetId);
    return requestJson<DraftValidationResponse>({
        method: "POST",
        path: route.path,
    });
}

export async function previewTaskCompose({
    body,
    draftSetId,
}: {
    readonly body: string;
    readonly draftSetId: string;
}): Promise<DraftPreviewResponse> {
    const route = definitionDraftSetPreviewTaskComposeRoute(draftSetId);
    return requestJson<DraftPreviewResponse>({
        body: {
            body,
            body_format: "yaml",
        } satisfies components["schemas"]["DefinitionDraftTaskComposePreviewRequest"],
        method: "POST",
        path: route.path,
    });
}

export async function applyDraftSet(draftSetId: string): Promise<DraftApplyResponse> {
    const route = definitionDraftSetApplyRoute(draftSetId);
    return requestJson<DraftApplyResponse>({
        body: {
            should_start_task_after_apply: false,
        } satisfies components["schemas"]["DefinitionDraftApplyRequest"],
        method: "POST",
        path: route.path,
    });
}

export function toErrorView(error: unknown): ConsoleErrorView {
    if (error instanceof AutoClawApiError) {
        return error.errorView;
    }

    return {
        code: "unknown_error",
        fieldErrors: [],
        isRetryable: false,
        source: "network",
        status: null,
        suggestedNextStep: null,
        summary: error instanceof Error ? error.message : "An unknown console error occurred.",
        title: "Unknown Error",
    };
}

export function isAbortError(error: unknown): boolean {
    return error instanceof Error && error.name === "AbortError";
}

export function isAuthError(error: ConsoleErrorView): boolean {
    return error.status === 401 || error.status === 403 || error.code === "illegal_caller";
}

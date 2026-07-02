import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useSearchParams } from "react-router-dom";

import { getNextCursor, type ConsoleErrorView } from "../../api/client";
import { mapDraftSetSummary, type DraftSetSummary } from "../../api/view-models";
import {
    applyDraftSet,
    createDraftSet,
    deleteDraftSet,
    isAbortError,
    isAuthError,
    materializeDraftFile,
    previewTaskCompose,
    readDraftSet,
    readDraftSets,
    rematerializeDraftFile,
    resetDraftFile,
    toErrorView,
    validateDraftSet,
    writeDraftFile,
} from "./definition-editor-data";
import {
    DEFAULT_PREVIEW_TASK_COMPOSE_BODY,
    INITIAL_MATERIALIZE_FORM,
    INITIAL_NEW_DRAFT_FORM,
    applyResultTitle,
    buildStarterDraftBody,
    draftFileId,
    editorFingerprint,
    mapDraftSetView,
    normalizeKey,
    selectedFileFromDraftSet,
    validateMaterializeForm,
    validateNewDraftForm,
    type ConfirmationState,
    type DraftActionState,
    type DraftFileView,
    type DraftSetView,
    type EditorMode,
    type MaterializeForm,
    type NewDraftForm,
    type PreviewProvenance,
    type ValidationView,
} from "./definition-editor-model";
import type {
    DefinitionKind,
    DraftApplyResponse,
    DraftPreviewResponse,
    DraftSetDetailResponse,
    DraftValidationResponse,
} from "./definition-editor-data";

interface DraftSetListState {
    readonly error: ConsoleErrorView | null;
    readonly hasLoaded: boolean;
    readonly isLoading: boolean;
    readonly isLoadingMore: boolean;
    readonly isRefreshing: boolean;
    readonly nextCursor: string | null;
    readonly rows: readonly DraftSetSummary[];
}

interface DraftSetDetailState {
    readonly error: ConsoleErrorView | null;
    readonly isLoading: boolean;
}

const UNMATERIALIZED_CURRENT_DRAFT_PREFIX = "draft set does not yet materialize current ";

export interface DefinitionEditorController {
    readonly actionError: ConsoleErrorView | null;
    readonly applyState: DraftActionState<DraftApplyResponse>;
    readonly confirmation: ConfirmationState | null;
    readonly currentDraftSet: DraftSetView | null;
    readonly deleteSelectedDraftSet: () => void;
    readonly detailState: DraftSetDetailState;
    readonly dismissActionError: () => void;
    readonly editorBody: string;
    readonly isEditorDirty: boolean;
    readonly isMutatingDraft: boolean;
    readonly listState: DraftSetListState;
    readonly loadMoreDraftSets: () => void;
    readonly materializeError: string | null;
    readonly materializeForm: MaterializeForm;
    readonly mode: EditorMode;
    readonly newDraftError: string | null;
    readonly newDraftForm: NewDraftForm;
    readonly newDraftModalOpen: boolean;
    readonly previewBody: string;
    readonly previewProvenance: PreviewProvenance;
    readonly previewState: DraftActionState<DraftPreviewResponse>;
    readonly refresh: () => void;
    readonly requestConfirmation: (confirmation: ConfirmationState) => void;
    readonly resetSelectedDraft: () => void;
    readonly rematerializeSelectedDraft: () => void;
    readonly runApply: () => void;
    readonly runPreview: () => void;
    readonly runValidation: () => void;
    readonly saveSelectedDraft: () => void;
    readonly selectDraftFile: (fileId: string) => void;
    readonly selectDraftSet: (draftSetId: string) => void;
    readonly selectedFile: DraftFileView | null;
    readonly selectedDraftSetId: string | null;
    readonly selectedFileId: string | null;
    readonly setConfirmation: (confirmation: ConfirmationState | null) => void;
    readonly setEditorBody: (body: string) => void;
    readonly setMaterializeForm: (form: MaterializeForm) => void;
    readonly setMode: (mode: EditorMode) => void;
    readonly setNewDraftForm: (form: NewDraftForm) => void;
    readonly setNewDraftModalOpen: (isOpen: boolean) => void;
    readonly setPreviewBody: (body: string) => void;
    readonly setPreviewProvenance: (provenance: PreviewProvenance) => void;
    readonly startNewDraft: () => void;
    readonly startNewDraftSet: () => void;
    readonly submitMaterialize: () => void;
    readonly submitNewDraft: () => void;
    readonly validationState: DraftActionState<DraftValidationResponse>;
    readonly validationView: ValidationView | null;
}

const initialListState: DraftSetListState = {
    error: null,
    hasLoaded: false,
    isLoading: true,
    isLoadingMore: false,
    isRefreshing: false,
    nextCursor: null,
    rows: [],
};

const initialDetailState: DraftSetDetailState = {
    error: null,
    isLoading: false,
};

const idleValidationState: DraftActionState<DraftValidationResponse> = {
    error: null,
    isRunning: false,
    result: null,
};

const idlePreviewState: DraftActionState<DraftPreviewResponse> = {
    error: null,
    isRunning: false,
    result: null,
};

const idleApplyState: DraftActionState<DraftApplyResponse> = {
    error: null,
    isRunning: false,
    result: null,
};

type StateSetter<T> = Dispatch<SetStateAction<T>>;

function beginDraftSetListRead(setListState: StateSetter<DraftSetListState>): void {
    setListState((currentState) => ({
        ...currentState,
        error: null,
        isLoading: !currentState.hasLoaded,
        isRefreshing: currentState.hasLoaded,
    }));
}

function beginDraftSetDetailRead(setDetailState: StateSetter<DraftSetDetailState>): void {
    setDetailState({ error: null, isLoading: true });
}

function clearSelectedDraftSetState({
    setCurrentDraftSet,
    setEditorBody,
    setEditorSourceKey,
    setSelectedFileId,
}: {
    readonly setCurrentDraftSet: StateSetter<DraftSetView | null>;
    readonly setEditorBody: StateSetter<string>;
    readonly setEditorSourceKey: StateSetter<string | null>;
    readonly setSelectedFileId: StateSetter<string | null>;
}): void {
    setCurrentDraftSet(null);
    setSelectedFileId(null);
    setEditorBody("");
    setEditorSourceKey(null);
}

function clearLoadedDraftSetTruth({
    setCurrentDraftSet,
    setEditorBody,
    setEditorSourceKey,
}: {
    readonly setCurrentDraftSet: StateSetter<DraftSetView | null>;
    readonly setEditorBody: StateSetter<string>;
    readonly setEditorSourceKey: StateSetter<string | null>;
}): void {
    setCurrentDraftSet(null);
    setEditorBody("");
    setEditorSourceKey(null);
}

function syncEditorFromSelectedFile({
    editorBody,
    editorSourceKey,
    selectedFile,
    setEditorBody,
    setEditorSourceKey,
}: {
    readonly editorBody: string;
    readonly editorSourceKey: string | null;
    readonly selectedFile: DraftFileView | null;
    readonly setEditorBody: StateSetter<string>;
    readonly setEditorSourceKey: StateSetter<string | null>;
}): void {
    if (selectedFile === null) {
        if (editorBody.length > 0) {
            setEditorBody("");
        }
        setEditorSourceKey(null);
        return;
    }

    const nextSourceKey = `${selectedFile.id}:${selectedFile.contentHash}`;
    if (editorSourceKey !== nextSourceKey) {
        setEditorBody(selectedFile.body);
        setEditorSourceKey(nextSourceKey);
    }
}

export function useDefinitionEditorController(): DefinitionEditorController {
    const [searchParams, setSearchParams] = useSearchParams();
    const [listState, setListState] = useState<DraftSetListState>(initialListState);
    const [detailState, setDetailState] = useState<DraftSetDetailState>(initialDetailState);
    const [selectedDraftSetId, setSelectedDraftSetId] = useState<string | null>(null);
    const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
    const [currentDraftSet, setCurrentDraftSet] = useState<DraftSetView | null>(null);
    const [editorBody, setEditorBody] = useState("");
    const [editorSourceKey, setEditorSourceKey] = useState<string | null>(null);
    const [mode, setMode] = useState<EditorMode>("edit");
    const [previewProvenance, setPreviewProvenance] = useState<PreviewProvenance>("draft_truth");
    const [previewBody, setPreviewBody] = useState(DEFAULT_PREVIEW_TASK_COMPOSE_BODY);
    const [refreshToken, setRefreshToken] = useState(0);
    const [detailRefreshToken, setDetailRefreshToken] = useState(0);
    const [newDraftModalOpen, setNewDraftModalOpen] = useState(false);
    const [newDraftForm, setNewDraftForm] = useState<NewDraftForm>(INITIAL_NEW_DRAFT_FORM);
    const [newDraftError, setNewDraftError] = useState<string | null>(null);
    const [materializeForm, setMaterializeForm] =
        useState<MaterializeForm>(INITIAL_MATERIALIZE_FORM);
    const [materializeError, setMaterializeError] = useState<string | null>(null);
    const [confirmation, setConfirmation] = useState<ConfirmationState | null>(null);
    const [validationState, setValidationState] =
        useState<DraftActionState<DraftValidationResponse>>(idleValidationState);
    const [previewState, setPreviewState] =
        useState<DraftActionState<DraftPreviewResponse>>(idlePreviewState);
    const [applyState, setApplyState] =
        useState<DraftActionState<DraftApplyResponse>>(idleApplyState);
    const [validationFingerprint, setValidationFingerprint] = useState<string | null>(null);
    const [actionError, setActionError] = useState<ConsoleErrorView | null>(null);
    const [isMutatingDraft, setIsMutatingDraft] = useState(false);
    const materializeRequest = useMemo(
        () => materializeRequestFromSearchParams(searchParams),
        [searchParams],
    );
    const handledMaterializeRequestRef = useRef<string | null>(null);
    const selectedFile = selectedFileFromDraftSet(currentDraftSet, selectedFileId);
    const isEditorDirty = selectedFile !== null && editorBody !== selectedFile.body;
    const currentFingerprint = editorFingerprint({
        draftSetId: currentDraftSet?.draftSetId ?? null,
        editorBody,
        selectedFile,
    });
    const validationView = useMemo<ValidationView | null>(() => {
        if (validationState.result === null) {
            return null;
        }
        return {
            response: validationState.result,
            stale: validationFingerprint !== currentFingerprint,
        };
    }, [currentFingerprint, validationFingerprint, validationState.result]);

    const applyDraftSetDetailResponse = useCallback(
        (response: DraftSetDetailResponse, preferredFileId?: string) => {
            const draftSet = mapDraftSetView(response.draft_set);
            setCurrentDraftSet(draftSet);
            setSelectedDraftSetId(draftSet.draftSetId);
            setPreviewBody(draftSet.previewTaskComposeBody ?? DEFAULT_PREVIEW_TASK_COMPOSE_BODY);
            setSelectedFileId((currentFileId) => {
                const preferredFile =
                    preferredFileId === undefined
                        ? null
                        : (draftSet.files.find((file) => file.id === preferredFileId) ?? null);
                const currentFile = selectedFileFromDraftSet(draftSet, currentFileId);
                const nextFile = preferredFile ?? currentFile;
                if (nextFile !== null) {
                    setEditorBody(nextFile.body);
                    setEditorSourceKey(`${nextFile.id}:${nextFile.contentHash}`);
                }
                return nextFile?.id ?? null;
            });
        },
        [],
    );

    useEffect(() => {
        const abortController = new AbortController();
        beginDraftSetListRead(setListState);
        void readDraftSets({ cursor: null, signal: abortController.signal })
            .then((page) => {
                const rows = page.items.map(mapDraftSetSummary);
                setListState({
                    error: null,
                    hasLoaded: true,
                    isLoading: false,
                    isLoadingMore: false,
                    isRefreshing: false,
                    nextCursor: getNextCursor(page),
                    rows,
                });
                setSelectedDraftSetId((currentId) =>
                    currentId !== null && rows.some((row) => row.draftSetId === currentId)
                        ? currentId
                        : (rows[0]?.draftSetId ?? null),
                );
            })
            .catch((error: unknown) => {
                if (isAbortError(error)) {
                    return;
                }
                setListState((currentState) => ({
                    ...currentState,
                    error: toErrorView(error),
                    hasLoaded: true,
                    isLoading: false,
                    isLoadingMore: false,
                    isRefreshing: false,
                }));
            });

        return () => {
            abortController.abort();
        };
    }, [refreshToken]);

    useEffect(() => {
        if (selectedDraftSetId === null) {
            clearSelectedDraftSetState({
                setCurrentDraftSet,
                setEditorBody,
                setEditorSourceKey,
                setSelectedFileId,
            });
            return;
        }

        const abortController = new AbortController();
        clearLoadedDraftSetTruth({
            setCurrentDraftSet,
            setEditorBody,
            setEditorSourceKey,
        });
        beginDraftSetDetailRead(setDetailState);
        void readDraftSet({
            draftSetId: selectedDraftSetId,
            signal: abortController.signal,
        })
            .then((response) => {
                applyDraftSetDetailResponse(response);
                setDetailState({ error: null, isLoading: false });
            })
            .catch((error: unknown) => {
                if (isAbortError(error)) {
                    return;
                }
                setDetailState({ error: toErrorView(error), isLoading: false });
            });

        return () => {
            abortController.abort();
        };
    }, [applyDraftSetDetailResponse, detailRefreshToken, selectedDraftSetId]);

    useEffect(() => {
        syncEditorFromSelectedFile({
            editorBody,
            editorSourceKey,
            selectedFile,
            setEditorBody,
            setEditorSourceKey,
        });
    }, [editorBody, editorSourceKey, selectedFile]);

    useEffect(() => {
        if (
            materializeRequest === null ||
            handledMaterializeRequestRef.current === materializeRequest.requestKey ||
            isMutatingDraft ||
            !listState.hasLoaded ||
            listState.isLoading
        ) {
            return;
        }

        handledMaterializeRequestRef.current = materializeRequest.requestKey;
        setIsMutatingDraft(true);
        setActionError(null);
        void createDraftSet({
            materialize: [{ key: materializeRequest.key, kind: materializeRequest.kind }],
            title: `Draft from ${materializeRequest.kind}:${materializeRequest.key}`,
        })
            .then((response) => {
                const preferredFileId = draftFileId(
                    materializeRequest.kind,
                    materializeRequest.key,
                );
                applyDraftSetDetailResponse(response, preferredFileId);
                const nextSummary = mapDraftSetSummary(response.draft_set);
                setListState((currentState) => ({
                    ...currentState,
                    error: null,
                    hasLoaded: true,
                    isLoading: false,
                    rows: [
                        nextSummary,
                        ...currentState.rows.filter(
                            (row) => row.draftSetId !== nextSummary.draftSetId,
                        ),
                    ],
                }));
                const nextParams = new URLSearchParams(searchParams);
                nextParams.delete("materialize_kind");
                nextParams.delete("materialize_key");
                setSearchParams(nextParams, { replace: true });
            })
            .catch((error: unknown) => {
                setActionError(toErrorView(error));
            })
            .finally(() => {
                setIsMutatingDraft(false);
            });
    }, [
        applyDraftSetDetailResponse,
        isMutatingDraft,
        listState.hasLoaded,
        listState.isLoading,
        materializeRequest,
        searchParams,
        setSearchParams,
    ]);

    const refresh = useCallback(() => {
        setRefreshToken((value) => value + 1);
        if (selectedDraftSetId !== null) {
            setDetailRefreshToken((value) => value + 1);
        }
    }, [selectedDraftSetId]);

    const loadMoreDraftSets = useCallback(() => {
        if (listState.nextCursor === null || listState.isLoadingMore) {
            return;
        }

        setListState((currentState) => ({ ...currentState, isLoadingMore: true }));
        void readDraftSets({ cursor: listState.nextCursor, signal: undefined })
            .then((page) => {
                setListState((currentState) => ({
                    ...currentState,
                    error: null,
                    isLoadingMore: false,
                    nextCursor: getNextCursor(page),
                    rows: [...currentState.rows, ...page.items.map(mapDraftSetSummary)],
                }));
            })
            .catch((error: unknown) => {
                setListState((currentState) => ({
                    ...currentState,
                    error: toErrorView(error),
                    isLoadingMore: false,
                }));
            });
    }, [listState.isLoadingMore, listState.nextCursor]);

    const selectDraftSet = useCallback((draftSetId: string) => {
        clearSelectedDraftSetState({
            setCurrentDraftSet,
            setEditorBody,
            setEditorSourceKey,
            setSelectedFileId,
        });
        setSelectedDraftSetId(draftSetId);
        setValidationState(idleValidationState);
        setPreviewState(idlePreviewState);
        setApplyState(idleApplyState);
    }, []);

    const selectDraftFile = useCallback((fileId: string) => {
        setSelectedFileId(fileId);
    }, []);

    const startNewDraftSet = useCallback(() => {
        setIsMutatingDraft(true);
        setActionError(null);
        void createDraftSet({ title: "Definition Editor draft set" })
            .then((response) => {
                applyDraftSetDetailResponse(response);
                setRefreshToken((value) => value + 1);
            })
            .catch((error: unknown) => {
                setActionError(toErrorView(error));
            })
            .finally(() => {
                setIsMutatingDraft(false);
            });
    }, [applyDraftSetDetailResponse]);

    const startNewDraft = useCallback(() => {
        setNewDraftForm(INITIAL_NEW_DRAFT_FORM);
        setNewDraftError(null);
        setNewDraftModalOpen(true);
    }, []);

    const submitNewDraft = useCallback(() => {
        const draftSetId = currentDraftSet?.draftSetId ?? null;
        const currentFiles = currentDraftSet?.files ?? [];
        const formError = validateNewDraftForm(newDraftForm, currentFiles);
        if (formError !== null) {
            setNewDraftError(formError);
            return;
        }

        setNewDraftError(null);
        setIsMutatingDraft(true);
        setActionError(null);
        const persistStarter = (targetDraftSetId: string) =>
            writeDraftFile({
                body: buildStarterDraftBody(newDraftForm),
                draftSetId: targetDraftSetId,
                key: normalizeKey(newDraftForm.key),
                kind: newDraftForm.kind,
            });

        const detailPromise =
            draftSetId === null
                ? createDraftSet({ title: "Definition Editor draft set" }).then((response) =>
                      persistStarter(response.draft_set.draft_set_id),
                  )
                : persistStarter(draftSetId);

        void detailPromise
            .then((response) => {
                const preferredFileId = draftFileId(
                    newDraftForm.kind,
                    normalizeKey(newDraftForm.key),
                );
                applyDraftSetDetailResponse(response, preferredFileId);
                setNewDraftModalOpen(false);
                setRefreshToken((value) => value + 1);
            })
            .catch((error: unknown) => {
                const errorView = toErrorView(error);
                const draftError = newDraftWriteError(errorView);
                if (draftError !== null) {
                    setNewDraftError(draftError);
                    return;
                }
                setActionError(errorView);
            })
            .finally(() => {
                setIsMutatingDraft(false);
            });
    }, [applyDraftSetDetailResponse, currentDraftSet, newDraftForm]);

    const submitMaterialize = useCallback(() => {
        if (currentDraftSet === null) {
            return;
        }

        const formError = validateMaterializeForm(materializeForm);
        if (formError !== null) {
            setMaterializeError(formError);
            return;
        }

        setMaterializeError(null);
        setIsMutatingDraft(true);
        setActionError(null);
        void materializeDraftFile({
            draftSetId: currentDraftSet.draftSetId,
            key: normalizeKey(materializeForm.key),
            kind: materializeForm.kind,
        })
            .then((response) => {
                applyDraftSetDetailResponse(
                    response,
                    draftFileId(materializeForm.kind, normalizeKey(materializeForm.key)),
                );
                setMaterializeForm(INITIAL_MATERIALIZE_FORM);
                setRefreshToken((value) => value + 1);
            })
            .catch((error: unknown) => {
                setActionError(toErrorView(error));
            })
            .finally(() => {
                setIsMutatingDraft(false);
            });
    }, [applyDraftSetDetailResponse, currentDraftSet, materializeForm]);

    const saveSelectedDraft = useCallback(() => {
        if (currentDraftSet === null || selectedFile === null) {
            return;
        }

        setIsMutatingDraft(true);
        setActionError(null);
        void writeDraftFile({
            body: editorBody,
            draftSetId: currentDraftSet.draftSetId,
            key: selectedFile.key,
            kind: selectedFile.kind,
        })
            .then((response) => {
                applyDraftSetDetailResponse(response, selectedFile.id);
                setRefreshToken((value) => value + 1);
            })
            .catch((error: unknown) => {
                setActionError(toErrorView(error));
            })
            .finally(() => {
                setIsMutatingDraft(false);
            });
    }, [applyDraftSetDetailResponse, currentDraftSet, editorBody, selectedFile]);

    const resetSelectedDraft = useCallback(() => {
        if (currentDraftSet === null || selectedFile === null) {
            return;
        }

        setConfirmation(null);
        setIsMutatingDraft(true);
        setActionError(null);
        void resetDraftFile({
            draftSetId: currentDraftSet.draftSetId,
            key: selectedFile.key,
            kind: selectedFile.kind,
        })
            .then((response) => {
                applyDraftSetDetailResponse(response, selectedFile.id);
                setRefreshToken((value) => value + 1);
            })
            .catch((error: unknown) => {
                setActionError(toErrorView(error));
            })
            .finally(() => {
                setIsMutatingDraft(false);
            });
    }, [applyDraftSetDetailResponse, currentDraftSet, selectedFile]);

    const rematerializeSelectedDraft = useCallback(() => {
        if (currentDraftSet === null || selectedFile === null) {
            return;
        }

        setConfirmation(null);
        setIsMutatingDraft(true);
        setActionError(null);
        void rematerializeDraftFile({
            draftSetId: currentDraftSet.draftSetId,
            key: selectedFile.key,
            kind: selectedFile.kind,
        })
            .then((response) => {
                applyDraftSetDetailResponse(response, selectedFile.id);
                setRefreshToken((value) => value + 1);
            })
            .catch((error: unknown) => {
                setActionError(toErrorView(error));
            })
            .finally(() => {
                setIsMutatingDraft(false);
            });
    }, [applyDraftSetDetailResponse, currentDraftSet, selectedFile]);

    const deleteSelectedDraftSet = useCallback(() => {
        if (currentDraftSet === null) {
            return;
        }

        const draftSetId = currentDraftSet.draftSetId;
        setConfirmation(null);
        setIsMutatingDraft(true);
        setActionError(null);
        void deleteDraftSet(draftSetId)
            .then(() => {
                setSelectedDraftSetId(null);
                setCurrentDraftSet(null);
                setRefreshToken((value) => value + 1);
            })
            .catch((error: unknown) => {
                setActionError(toErrorView(error));
            })
            .finally(() => {
                setIsMutatingDraft(false);
            });
    }, [currentDraftSet]);

    const runValidation = useCallback(() => {
        if (currentDraftSet === null) {
            return;
        }

        setMode("validation");
        setValidationState({ error: null, isRunning: true, result: null });
        void validateDraftSet(currentDraftSet.draftSetId)
            .then((result) => {
                setValidationState({ error: null, isRunning: false, result });
                setValidationFingerprint(currentFingerprint);
            })
            .catch((error: unknown) => {
                setValidationState({ error: toErrorView(error), isRunning: false, result: null });
            });
    }, [currentDraftSet, currentFingerprint]);

    const runPreview = useCallback(() => {
        if (currentDraftSet === null) {
            return;
        }

        setMode("preview");
        if (previewProvenance === "stored_truth") {
            setPreviewState(idlePreviewState);
            return;
        }

        setPreviewState({ error: null, isRunning: true, result: null });
        void previewTaskCompose({
            body: previewBody,
            draftSetId: currentDraftSet.draftSetId,
        })
            .then((result) => {
                setPreviewState({ error: null, isRunning: false, result });
            })
            .catch((error: unknown) => {
                setPreviewState({ error: toErrorView(error), isRunning: false, result: null });
            });
    }, [currentDraftSet, previewBody, previewProvenance]);

    const runApply = useCallback(() => {
        if (currentDraftSet === null) {
            return;
        }

        setApplyState({ error: null, isRunning: true, result: null });
        void applyDraftSet(currentDraftSet.draftSetId)
            .then((result) => {
                setApplyState({ error: null, isRunning: false, result });
                setRefreshToken((value) => value + 1);
            })
            .catch((error: unknown) => {
                setApplyState({ error: toErrorView(error), isRunning: false, result: null });
            });
    }, [currentDraftSet]);

    const requestConfirmation = useCallback((nextConfirmation: ConfirmationState) => {
        setConfirmation(nextConfirmation);
    }, []);

    const dismissActionError = useCallback(() => {
        setActionError(null);
    }, []);

    return {
        actionError,
        applyState: {
            ...applyState,
            result: applyState.result,
        },
        confirmation,
        currentDraftSet,
        deleteSelectedDraftSet,
        detailState,
        dismissActionError,
        editorBody,
        isEditorDirty,
        isMutatingDraft,
        listState,
        loadMoreDraftSets,
        materializeError,
        materializeForm,
        mode,
        newDraftError,
        newDraftForm,
        newDraftModalOpen,
        previewBody,
        previewProvenance,
        previewState,
        refresh,
        requestConfirmation,
        resetSelectedDraft,
        rematerializeSelectedDraft,
        runApply,
        runPreview,
        runValidation,
        saveSelectedDraft,
        selectDraftFile,
        selectDraftSet,
        selectedFile,
        selectedDraftSetId,
        selectedFileId,
        setConfirmation,
        setEditorBody,
        setMaterializeForm,
        setMode,
        setNewDraftForm,
        setNewDraftModalOpen,
        setPreviewBody,
        setPreviewProvenance,
        startNewDraft,
        startNewDraftSet,
        submitMaterialize,
        submitNewDraft,
        validationState,
        validationView,
    };
}

function newDraftWriteError(error: ConsoleErrorView): string | null {
    if (
        error.code !== "illegal_state" ||
        !error.summary.startsWith(UNMATERIALIZED_CURRENT_DRAFT_PREFIX)
    ) {
        return null;
    }
    return "That key already exists in stored definitions. Use Create/update draft from Definitions to edit it here.";
}

export { applyResultTitle, isAuthError };

interface MaterializeRequest {
    readonly key: string;
    readonly kind: DefinitionKind;
    readonly requestKey: string;
}

function materializeRequestFromSearchParams(params: URLSearchParams): MaterializeRequest | null {
    const kind = params.get("materialize_kind");
    const key = normalizeKey(params.get("materialize_key") ?? "");
    if (!isDefinitionKind(kind) || key.length === 0) {
        return null;
    }
    return {
        key,
        kind,
        requestKey: `${kind}:${key}`,
    };
}

function isDefinitionKind(value: string | null): value is DefinitionKind {
    return value === "policy" || value === "role" || value === "workflow";
}

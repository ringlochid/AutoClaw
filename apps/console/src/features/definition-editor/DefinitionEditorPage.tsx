import {
    useCallback,
    useEffect,
    useMemo,
    useState,
    type KeyboardEvent,
    type ReactNode,
} from "react";

import {
    CheckCircle2,
    FilePenLine,
    Plus,
    RefreshCw,
    Rocket,
    RotateCcw,
    Save,
    Trash2,
    X,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { PageFrame } from "../../components/layout";
import { Button, StatePanel, StatusChip, type StatusTone } from "../../components/ui";
import type { ConsoleErrorView } from "../../api/client";
import { getNextCursor } from "../../api/client";
import { classNames } from "../../lib/classNames";
import { applyDraftBodyIndentation } from "./definition-editor-indent";
import {
    createDraft,
    deleteDraft,
    isAuthError,
    publishDraft,
    readDraft,
    readDrafts,
    saveDraft,
    toErrorView,
    validateDraft,
    type DefinitionDraftKind,
    type DefinitionDraftMode,
    type DraftDetail,
    type DraftIdentity,
    type DraftPublishResponse,
    type DraftSummary,
    type DraftValidationResponse,
} from "./definition-editor-data";

interface DraftListState {
    readonly error: ConsoleErrorView | null;
    readonly isLoading: boolean;
    readonly nextCursor: string | null;
    readonly rows: readonly DraftSummary[];
}

interface DraftDetailState {
    readonly draft: DraftDetail | null;
    readonly error: ConsoleErrorView | null;
    readonly isLoading: boolean;
}

interface NewDraftFormState {
    readonly description: string;
    readonly error: ConsoleErrorView | null;
    readonly isCreating: boolean;
    readonly isOpen: boolean;
    readonly key: string;
    readonly kind: DefinitionDraftKind;
    readonly mode: DefinitionDraftMode;
}

type DraftOperation = "deleting" | "publishing" | "saving" | "validating" | null;

type DraftActionDialog =
    | {
          readonly kind: "publish";
          readonly result: DraftPublishResponse;
      }
    | {
          readonly kind: "validation";
          readonly validation: DraftValidationResponse;
      }
    | null;

const DRAFT_KIND_OPTIONS: readonly DefinitionDraftKind[] = ["role", "policy", "workflow"];

const initialListState: DraftListState = {
    error: null,
    isLoading: true,
    nextCursor: null,
    rows: [],
};

const initialDetailState: DraftDetailState = {
    draft: null,
    error: null,
    isLoading: false,
};

const initialNewDraftForm: NewDraftFormState = {
    description: "",
    error: null,
    isCreating: false,
    isOpen: false,
    key: "",
    kind: "role",
    mode: "create",
};

export function DefinitionEditorPage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const routeSelection = useMemo(() => draftIdentityFromSearch(searchParams), [searchParams]);
    const routeSelectionKey = routeSelection === null ? "" : draftIdentityKey(routeSelection);
    const [selection, setSelection] = useState<DraftIdentity | null>(routeSelection);
    const [listState, setListState] = useState<DraftListState>(initialListState);
    const [detailState, setDetailState] = useState<DraftDetailState>(initialDetailState);
    const [editorBody, setEditorBody] = useState("");
    const [newDraftForm, setNewDraftForm] = useState<NewDraftFormState>(initialNewDraftForm);
    const [operation, setOperation] = useState<DraftOperation>(null);
    const [operationError, setOperationError] = useState<ConsoleErrorView | null>(null);
    const [draftActionDialog, setDraftActionDialog] = useState<DraftActionDialog>(null);
    const [refreshToken, setRefreshToken] = useState(0);
    const selectedKey = selection === null ? "" : draftIdentityKey(selection);
    const currentDraft = detailState.draft;
    const isDirty = currentDraft !== null && editorBody !== currentDraft.body;
    const isBusy = operation !== null;

    const upsertListSummary = useCallback((summary: DraftSummary): void => {
        setListState((currentState) => {
            const nextRows = currentState.rows.filter(
                (row) => !draftIdentityEquals(draftIdentityFromSummary(row), summary),
            );
            return {
                ...currentState,
                rows: [summary, ...nextRows].sort(compareDraftSummaryUpdatedAt),
            };
        });
    }, []);

    const applyDraftDetail = useCallback(
        (
            draft: DraftDetail,
            {
                clearOutcome = true,
                includeInList = true,
            }: { clearOutcome?: boolean; includeInList?: boolean } = {},
        ): void => {
            setDetailState({ draft, error: null, isLoading: false });
            setEditorBody(draft.body);
            if (clearOutcome) {
                setDraftActionDialog(null);
                setOperationError(null);
            }
            if (includeInList) {
                upsertListSummary(draftSummaryFromDetail(draft));
            }
        },
        [upsertListSummary],
    );

    useEffect(() => {
        if (routeSelection !== null) {
            setSelection((currentSelection) =>
                draftIdentityEquals(currentSelection, routeSelection)
                    ? currentSelection
                    : routeSelection,
            );
        }
    }, [routeSelection, routeSelectionKey]);

    useEffect(() => {
        const abortController = new AbortController();
        setListState((currentState) => ({
            ...currentState,
            error: null,
            isLoading: true,
        }));

        void readDrafts({ signal: abortController.signal })
            .then((page) => {
                setListState({
                    error: null,
                    isLoading: false,
                    nextCursor: getNextCursor(page),
                    rows: page.items,
                });
                setSelection((currentSelection) => {
                    if (currentSelection !== null || routeSelection !== null) {
                        return currentSelection;
                    }
                    return page.items.length === 0 ? null : draftIdentityFromSummary(page.items[0]);
                });
            })
            .catch((error: unknown) => {
                setListState((currentState) => ({
                    ...currentState,
                    error: toErrorView(error),
                    isLoading: false,
                }));
            });

        return () => {
            abortController.abort();
        };
    }, [refreshToken, routeSelection]);

    useEffect(() => {
        if (selection === null) {
            setDetailState(initialDetailState);
            setEditorBody("");
            setDraftActionDialog(null);
            setOperationError(null);
            return;
        }

        const abortController = new AbortController();
        setDetailState({ draft: null, error: null, isLoading: true });
        setDraftActionDialog(null);
        setOperationError(null);

        void readDraft({ ...selection, signal: abortController.signal })
            .then((response) => {
                applyDraftDetail(response.draft, { includeInList: response.draft.is_saved });
            })
            .catch((error: unknown) => {
                setDetailState({
                    draft: null,
                    error: toErrorView(error),
                    isLoading: false,
                });
                setEditorBody("");
            });

        return () => {
            abortController.abort();
        };
    }, [applyDraftDetail, selectedKey, selection]);

    const selectDraft = useCallback(
        (identity: DraftIdentity | null) => {
            setSelection(identity);
            if (identity === null) {
                setSearchParams({});
                return;
            }
            setSearchParams({ key: identity.key, kind: identity.kind });
        },
        [setSearchParams],
    );

    const refreshList = useCallback(() => {
        setRefreshToken((value) => value + 1);
    }, []);

    const loadMoreDrafts = useCallback(() => {
        if (listState.nextCursor === null || listState.isLoading) {
            return;
        }
        setListState((currentState) => ({ ...currentState, isLoading: true }));
        void readDrafts({ cursor: listState.nextCursor })
            .then((page) => {
                setListState((currentState) => ({
                    error: null,
                    isLoading: false,
                    nextCursor: getNextCursor(page),
                    rows: [...currentState.rows, ...page.items],
                }));
            })
            .catch((error: unknown) => {
                setListState((currentState) => ({
                    ...currentState,
                    error: toErrorView(error),
                    isLoading: false,
                }));
            });
    }, [listState.isLoading, listState.nextCursor]);

    const openNewDraftDialog = useCallback(() => {
        setNewDraftForm({ ...initialNewDraftForm, isOpen: true });
    }, []);

    const closeNewDraftDialog = useCallback(() => {
        if (!newDraftForm.isCreating) {
            setNewDraftForm(initialNewDraftForm);
        }
    }, [newDraftForm.isCreating]);

    async function persistCurrentDraftIfNeeded(): Promise<DraftDetail | null> {
        if (currentDraft === null) {
            return null;
        }
        if (currentDraft.is_saved && !isDirty) {
            return currentDraft;
        }
        const response = await saveDraft({
            body: editorBody,
            key: currentDraft.key,
            kind: currentDraft.kind,
        });
        applyDraftDetail(response.draft);
        return response.draft;
    }

    async function handleCreateDraft(): Promise<void> {
        const key = normalizeDraftKey(newDraftForm.key);
        if (key.length === 0) {
            setNewDraftForm((currentForm) => ({
                ...currentForm,
                error: formError("Draft key is required."),
            }));
            return;
        }

        setNewDraftForm((currentForm) => ({ ...currentForm, error: null, isCreating: true }));
        try {
            const response = await createDraft({
                body:
                    newDraftForm.mode === "create"
                        ? starterBodyForKind(newDraftForm.kind, key, newDraftForm.description)
                        : undefined,
                key,
                kind: newDraftForm.kind,
                mode: newDraftForm.mode,
            });
            applyDraftDetail(response.draft);
            setNewDraftForm(initialNewDraftForm);
            selectDraft({ key, kind: newDraftForm.kind });
        } catch (error) {
            setNewDraftForm((currentForm) => ({
                ...currentForm,
                error: toErrorView(error),
                isCreating: false,
            }));
        }
    }

    async function handleSaveDraft(): Promise<void> {
        if (currentDraft === null) {
            return;
        }
        setOperation("saving");
        setOperationError(null);
        try {
            const response = await saveDraft({
                body: editorBody,
                key: currentDraft.key,
                kind: currentDraft.kind,
            });
            applyDraftDetail(response.draft);
        } catch (error) {
            setOperationError(toErrorView(error));
        } finally {
            setOperation(null);
        }
    }

    async function handleValidateDraft(): Promise<void> {
        if (currentDraft === null) {
            return;
        }
        setOperation("validating");
        setOperationError(null);
        try {
            const savedDraft = await persistCurrentDraftIfNeeded();
            if (savedDraft === null) {
                return;
            }
            const response = await validateDraft({ key: savedDraft.key, kind: savedDraft.kind });
            setDraftActionDialog({ kind: "validation", validation: response });
        } catch (error) {
            setOperationError(toErrorView(error));
            setDraftActionDialog(null);
        } finally {
            setOperation(null);
        }
    }

    async function handlePublishDraft(): Promise<void> {
        if (currentDraft === null) {
            return;
        }
        setOperation("publishing");
        setOperationError(null);
        try {
            const savedDraft = await persistCurrentDraftIfNeeded();
            if (savedDraft === null) {
                return;
            }
            const response = await publishDraft({ key: savedDraft.key, kind: savedDraft.kind });
            setDraftActionDialog({ kind: "publish", result: response });
            if (response.status === "published") {
                removeListSummary(savedDraft);
                const currentResponse = await readDraft({
                    key: savedDraft.key,
                    kind: savedDraft.kind,
                });
                applyDraftDetail(currentResponse.draft, {
                    clearOutcome: false,
                    includeInList: currentResponse.draft.is_saved,
                });
                setDraftActionDialog({ kind: "publish", result: response });
            }
        } catch (error) {
            setOperationError(toErrorView(error));
            setDraftActionDialog(null);
        } finally {
            setOperation(null);
        }
    }

    async function handleDiscardDraft(): Promise<void> {
        if (!currentDraft?.is_saved) {
            return;
        }
        const identity = { key: currentDraft.key, kind: currentDraft.kind };
        const remainingRows = listState.rows.filter(
            (row) => !draftIdentityEquals(draftIdentityFromSummary(row), identity),
        );
        setOperation("deleting");
        setOperationError(null);
        try {
            await deleteDraft(identity);
            removeListSummary(identity);
            if (currentDraft.mode === "update") {
                const response = await readDraft(identity);
                applyDraftDetail(response.draft, { includeInList: response.draft.is_saved });
                return;
            }
            const nextSelection =
                remainingRows.length === 0 ? null : draftIdentityFromSummary(remainingRows[0]);
            selectDraft(nextSelection);
        } catch (error) {
            setOperationError(toErrorView(error));
        } finally {
            setOperation(null);
        }
    }

    async function handleReplaceWithCurrent(): Promise<void> {
        if (currentDraft?.mode !== "update" || !currentDraft.is_saved) {
            return;
        }
        setOperation("deleting");
        setOperationError(null);
        try {
            await deleteDraft({ key: currentDraft.key, kind: currentDraft.kind });
            removeListSummary(currentDraft);
            const response = await readDraft({ key: currentDraft.key, kind: currentDraft.kind });
            applyDraftDetail(response.draft, { includeInList: response.draft.is_saved });
        } catch (error) {
            setOperationError(toErrorView(error));
        } finally {
            setOperation(null);
        }
    }

    function removeListSummary(identity: DraftIdentity): void {
        setListState((currentState) => ({
            ...currentState,
            rows: currentState.rows.filter(
                (row) => !draftIdentityEquals(draftIdentityFromSummary(row), identity),
            ),
        }));
    }

    function resetToBaseline(): void {
        const baselineBody = currentDraft?.baseline_body;
        if (baselineBody === null || baselineBody === undefined) {
            return;
        }
        setEditorBody(baselineBody);
        setDraftActionDialog(null);
        setOperationError(null);
    }

    function handleDraftBodyKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
        if (event.key !== "Tab") {
            return;
        }

        event.preventDefault();
        const target = event.currentTarget;
        const edit = applyDraftBodyIndentation({
            body: editorBody,
            selectionEnd: target.selectionEnd,
            selectionStart: target.selectionStart,
            shouldOutdent: event.shiftKey,
        });
        setEditorBody(edit.body);
        window.requestAnimationFrame(() => {
            target.setSelectionRange(edit.selectionStart, edit.selectionEnd);
        });
    }

    return (
        <PageFrame
            actions={
                <Button onClick={openNewDraftDialog} icon={<Plus className="size-4" />}>
                    New draft
                </Button>
            }
            eyebrow="Authoring"
            title="Definition Editor"
            className="lg:min-h-[calc(100vh-8rem)]"
        >
            <div className="grid min-w-0 gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
                <DraftListPanel
                    isBusy={isBusy}
                    listState={listState}
                    loadMoreDrafts={loadMoreDrafts}
                    refreshList={refreshList}
                    selectDraft={selectDraft}
                    selectedDraft={selection}
                    startNewDraft={openNewDraftDialog}
                />
                <DraftEditorPanel
                    currentDraft={currentDraft}
                    detailState={detailState}
                    editorBody={editorBody}
                    handleDiscardDraft={() => {
                        void handleDiscardDraft();
                    }}
                    handleDraftBodyKeyDown={handleDraftBodyKeyDown}
                    handlePublishDraft={() => {
                        void handlePublishDraft();
                    }}
                    handleReplaceWithCurrent={() => {
                        void handleReplaceWithCurrent();
                    }}
                    handleSaveDraft={() => {
                        void handleSaveDraft();
                    }}
                    handleValidateDraft={() => {
                        void handleValidateDraft();
                    }}
                    isBusy={isBusy}
                    isDirty={isDirty}
                    operation={operation}
                    operationError={operationError}
                    refreshSelected={() => {
                        if (selection !== null) {
                            setSelection({ ...selection });
                        }
                    }}
                    resetToBaseline={resetToBaseline}
                    setEditorBody={setEditorBody}
                />
            </div>
            {newDraftForm.isOpen ? (
                <NewDraftDialog
                    form={newDraftForm}
                    onCancel={closeNewDraftDialog}
                    onChange={setNewDraftForm}
                    onCreate={() => {
                        void handleCreateDraft();
                    }}
                />
            ) : null}
            {draftActionDialog === null ? null : (
                <DraftActionResultDialog
                    dialog={draftActionDialog}
                    onClose={() => {
                        setDraftActionDialog(null);
                    }}
                />
            )}
        </PageFrame>
    );
}

function DraftListPanel({
    isBusy,
    listState,
    loadMoreDrafts,
    refreshList,
    selectDraft,
    selectedDraft,
    startNewDraft,
}: {
    readonly isBusy: boolean;
    readonly listState: DraftListState;
    readonly loadMoreDrafts: () => void;
    readonly refreshList: () => void;
    readonly selectDraft: (identity: DraftIdentity | null) => void;
    readonly selectedDraft: DraftIdentity | null;
    readonly startNewDraft: () => void;
}) {
    return (
        <aside className="flex min-h-[640px] min-w-0 flex-col overflow-hidden rounded-card border border-outline-soft bg-surface-low">
            <header className="flex shrink-0 items-center justify-between gap-3 border-b border-outline-soft p-4">
                <div className="min-w-0">
                    <p className="font-mono text-label font-medium uppercase text-muted">Drafts</p>
                    <h2 className="mt-1 font-display text-[18px] font-semibold leading-6 text-foreground">
                        Saved drafts
                    </h2>
                </div>
                <Button
                    aria-label="New draft"
                    className="px-3"
                    icon={<Plus className="size-4" />}
                    onClick={startNewDraft}
                >
                    New
                </Button>
            </header>
            <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3">
                {listState.error === null ? null : (
                    <StatePanel
                        action={<Button onClick={refreshList}>Retry</Button>}
                        summary={listState.error.summary}
                        title={
                            isAuthError(listState.error)
                                ? "Access to drafts failed"
                                : "Drafts could not load"
                        }
                        tone={isAuthError(listState.error) ? "auth" : "error"}
                    />
                )}
                {listState.isLoading && listState.rows.length === 0 ? (
                    <StatePanel title="Loading drafts" tone="loading" />
                ) : null}
                {!listState.isLoading && listState.rows.length === 0 && listState.error === null ? (
                    <StatePanel
                        action={<Button onClick={startNewDraft}>New draft</Button>}
                        title="No saved drafts"
                    />
                ) : null}
                {listState.rows.length === 0 ? null : (
                    <ol aria-label="Saved definition drafts" className="flex flex-col gap-2">
                        {listState.rows.map((row) => {
                            const identity = draftIdentityFromSummary(row);
                            const isSelected = draftIdentityEquals(identity, selectedDraft);
                            return (
                                <li key={draftIdentityKey(identity)}>
                                    <button
                                        aria-pressed={isSelected}
                                        className={classNames(
                                            "block w-full min-w-0 rounded-card border p-3 text-left transition-colors",
                                            isSelected
                                                ? "border-primary/45 bg-active text-active-foreground"
                                                : "border-outline-soft bg-surface hover:border-primary/35",
                                        )}
                                        disabled={isBusy}
                                        onClick={() => {
                                            selectDraft(identity);
                                        }}
                                        type="button"
                                    >
                                        <div className="flex min-w-0 items-center gap-2">
                                            <StatusChip tone="neutral">
                                                {kindLabel(row.kind)}
                                            </StatusChip>
                                            <StatusChip tone={statusTone(row.status)}>
                                                {statusLabel(row.status)}
                                            </StatusChip>
                                        </div>
                                        <p className="mt-3 truncate font-display text-compact font-semibold text-foreground">
                                            {row.key}
                                        </p>
                                        <p className="mt-1 font-mono text-label text-muted">
                                            {modeLabel(row.mode)}
                                        </p>
                                    </button>
                                </li>
                            );
                        })}
                    </ol>
                )}
                {listState.nextCursor === null ? null : (
                    <Button disabled={listState.isLoading} onClick={loadMoreDrafts}>
                        Load more
                    </Button>
                )}
            </div>
        </aside>
    );
}

function DraftEditorPanel({
    currentDraft,
    detailState,
    editorBody,
    handleDiscardDraft,
    handleDraftBodyKeyDown,
    handlePublishDraft,
    handleReplaceWithCurrent,
    handleSaveDraft,
    handleValidateDraft,
    isBusy,
    isDirty,
    operation,
    operationError,
    refreshSelected,
    resetToBaseline,
    setEditorBody,
}: {
    readonly currentDraft: DraftDetail | null;
    readonly detailState: DraftDetailState;
    readonly editorBody: string;
    readonly handleDiscardDraft: () => void;
    readonly handleDraftBodyKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
    readonly handlePublishDraft: () => void;
    readonly handleReplaceWithCurrent: () => void;
    readonly handleSaveDraft: () => void;
    readonly handleValidateDraft: () => void;
    readonly isBusy: boolean;
    readonly isDirty: boolean;
    readonly operation: DraftOperation;
    readonly operationError: ConsoleErrorView | null;
    readonly refreshSelected: () => void;
    readonly resetToBaseline: () => void;
    readonly setEditorBody: (body: string) => void;
}) {
    if (detailState.isLoading) {
        return (
            <DraftEditorEmptySurface>
                <StatePanel title="Loading draft" tone="loading" />
            </DraftEditorEmptySurface>
        );
    }

    if (detailState.error !== null) {
        return (
            <DraftEditorEmptySurface>
                <StatePanel
                    action={<Button onClick={refreshSelected}>Retry</Button>}
                    summary={detailState.error.summary}
                    title={
                        isAuthError(detailState.error)
                            ? "Access to draft failed"
                            : "Selected draft could not load"
                    }
                    tone={isAuthError(detailState.error) ? "auth" : "error"}
                />
            </DraftEditorEmptySurface>
        );
    }

    if (currentDraft === null) {
        return (
            <DraftEditorEmptySurface>
                <StatePanel title="Select a draft" />
            </DraftEditorEmptySurface>
        );
    }

    const canSave = !isBusy && (!currentDraft.is_saved || isDirty);
    const canDiscard = !isBusy && currentDraft.is_saved;
    const canReplaceWithCurrent = canDiscard && currentDraft.mode === "update";

    return (
        <section className="flex min-h-[640px] min-w-0 flex-col rounded-card border border-outline-soft bg-surface-low">
            <header className="flex flex-col gap-4 border-b border-outline-soft p-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                    <p className="font-mono text-label font-medium uppercase text-muted">Draft</p>
                    <div className="mt-2 flex min-w-0 flex-wrap items-center gap-2">
                        <h2 className="min-w-0 break-words font-display text-[20px] font-semibold leading-6 text-foreground">
                            {currentDraft.key}
                        </h2>
                        <StatusChip tone="neutral">{kindLabel(currentDraft.kind)}</StatusChip>
                        <StatusChip tone="neutral">{modeLabel(currentDraft.mode)}</StatusChip>
                        <StatusChip tone={statusTone(currentDraft.status)}>
                            {statusLabel(currentDraft.status)}
                        </StatusChip>
                        {isDirty ? <StatusChip tone="warning">local edits</StatusChip> : null}
                    </div>
                </div>
                <div className="flex flex-wrap gap-2">
                    <Button
                        disabled={!canSave}
                        icon={<Save className="size-4" />}
                        onClick={handleSaveDraft}
                        variant="secondary"
                    >
                        {operation === "saving" ? "Saving" : "Save draft"}
                    </Button>
                    <Button
                        disabled={isBusy}
                        icon={<CheckCircle2 className="size-4" />}
                        onClick={handleValidateDraft}
                        variant="secondary"
                    >
                        {operation === "validating" ? "Validating" : "Validate"}
                    </Button>
                    <Button
                        disabled={isBusy}
                        icon={<Rocket className="size-4" />}
                        onClick={handlePublishDraft}
                        variant="primary"
                    >
                        {operation === "publishing" ? "Publishing" : "Publish"}
                    </Button>
                </div>
            </header>
            <div className="grid min-w-0 gap-4 p-4">
                {operationError === null ? null : (
                    <StatePanel
                        summary={operationError.summary}
                        title={operationError.title}
                        tone="error"
                    />
                )}
                <label className="grid gap-2" htmlFor="definition-draft-body">
                    <span className="font-mono text-label font-medium uppercase text-muted">
                        Draft body
                    </span>
                    <textarea
                        className="definition-editor-body min-h-[520px] w-full min-w-0 rounded-card border border-outline bg-surface p-4 text-[14px] text-foreground shadow-hairline focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/15"
                        id="definition-draft-body"
                        onChange={(event) => {
                            setEditorBody(event.target.value);
                        }}
                        onKeyDown={handleDraftBodyKeyDown}
                        spellCheck={false}
                        value={editorBody}
                    />
                </label>
                <div className="flex flex-wrap justify-end gap-2 border-t border-outline-soft pt-4">
                    <Button
                        disabled={isBusy || currentDraft.baseline_body === null}
                        icon={<RotateCcw className="size-4" />}
                        onClick={resetToBaseline}
                        variant="secondary"
                    >
                        Reset draft
                    </Button>
                    <Button
                        disabled={!canReplaceWithCurrent}
                        icon={<RefreshCw className="size-4" />}
                        onClick={handleReplaceWithCurrent}
                        variant="secondary"
                    >
                        Replace with current stored revision
                    </Button>
                    <Button
                        disabled={!canDiscard}
                        icon={<Trash2 className="size-4" />}
                        onClick={handleDiscardDraft}
                        variant="danger"
                    >
                        Discard saved draft
                    </Button>
                </div>
            </div>
        </section>
    );
}

function DraftEditorEmptySurface({ children }: { readonly children: ReactNode }) {
    return (
        <section className="flex min-h-[640px] min-w-0 items-start rounded-card border border-outline-soft bg-surface-low p-4">
            <div className="w-full">{children}</div>
        </section>
    );
}

function ValidationPanel({ validation }: { readonly validation: DraftValidationResponse }) {
    const tone =
        validation.status === "valid"
            ? "success"
            : validation.status === "stale"
              ? "stale"
              : "error";
    return (
        <StatePanel
            summary={
                <IssueList
                    emptyText="No validation issues returned."
                    items={[...validation.errors, ...validation.warnings]}
                />
            }
            title={`Validation ${statusLabel(validation.status)}`}
            tone={tone}
        />
    );
}

function PublishPanel({ result }: { readonly result: DraftPublishResponse }) {
    const tone =
        result.status === "published" ? "success" : result.status === "stale" ? "stale" : "error";
    return (
        <StatePanel
            summary={
                result.published_revision === null ? (
                    <IssueList
                        emptyText="No revision was published."
                        items={[...result.validation.errors, ...result.validation.warnings]}
                    />
                ) : (
                    <p>
                        {kindLabel(result.published_revision.kind)} {result.published_revision.key}{" "}
                        revision {result.published_revision.revision_no}
                    </p>
                )
            }
            title={`Publish ${statusLabel(result.status)}`}
            tone={tone}
        />
    );
}

function DraftActionResultDialog({
    dialog,
    onClose,
}: {
    readonly dialog: Exclude<DraftActionDialog, null>;
    readonly onClose: () => void;
}) {
    useEffect(() => {
        const handleKeyDown = (event: globalThis.KeyboardEvent) => {
            if (event.key === "Escape") {
                event.preventDefault();
                onClose();
            }
        };

        document.body.classList.add("overflow-hidden");
        document.addEventListener("keydown", handleKeyDown, true);
        return () => {
            document.body.classList.remove("overflow-hidden");
            document.removeEventListener("keydown", handleKeyDown, true);
        };
    }, [onClose]);

    const title =
        dialog.kind === "validation"
            ? `Validation ${statusLabel(dialog.validation.status)}`
            : `Publish ${statusLabel(dialog.result.status)}`;
    const kind = dialog.kind === "validation" ? dialog.validation.kind : dialog.result.kind;
    const key = dialog.kind === "validation" ? dialog.validation.key : dialog.result.key;
    const outcome = dialog.kind === "validation" ? dialog.validation.status : dialog.result.status;

    return (
        <div
            className="fixed inset-0 z-50 grid place-items-center bg-foreground/35 p-4 backdrop-blur-[2px]"
            role="presentation"
        >
            <section
                aria-labelledby="definition-draft-action-title"
                aria-modal="true"
                className="max-h-[calc(100vh-4rem)] w-full max-w-xl overflow-hidden rounded-shell border border-outline-soft bg-surface shadow-popover"
                role="dialog"
            >
                <header className="flex items-start justify-between gap-4 border-b border-outline-soft px-5 py-4">
                    <div className="min-w-0">
                        <p className="font-mono text-label font-medium uppercase text-muted">
                            Draft action
                        </p>
                        <h2
                            className="mt-1 font-display text-[20px] font-semibold leading-6 text-foreground"
                            id="definition-draft-action-title"
                        >
                            {title}
                        </h2>
                    </div>
                    <button
                        aria-label="Close draft action"
                        className="inline-flex size-icon-control shrink-0 items-center justify-center rounded-control border border-outline bg-surface-low text-muted transition-colors hover:border-primary/45 hover:text-foreground"
                        onClick={onClose}
                        type="button"
                    >
                        <X aria-hidden="true" className="size-4" />
                    </button>
                </header>
                <div className="grid max-h-[calc(100vh-14rem)] gap-4 overflow-y-auto px-5 py-5">
                    <div className="rounded-card border border-outline-soft bg-surface-low px-4 py-3">
                        <dl className="grid gap-3 sm:grid-cols-2">
                            <div className="min-w-0">
                                <dt className="font-mono text-label font-medium uppercase text-muted">
                                    Selected draft
                                </dt>
                                <dd className="mt-1 break-words font-mono text-utility text-foreground">
                                    {kind}:{key}
                                </dd>
                            </div>
                            <div className="min-w-0">
                                <dt className="font-mono text-label font-medium uppercase text-muted">
                                    Outcome
                                </dt>
                                <dd className="mt-1 font-mono text-utility text-foreground">
                                    {statusLabel(outcome)}
                                </dd>
                            </div>
                        </dl>
                    </div>
                    {dialog.kind === "validation" ? (
                        <ValidationPanel validation={dialog.validation} />
                    ) : (
                        <PublishPanel result={dialog.result} />
                    )}
                </div>
                <footer className="flex justify-end border-t border-outline-soft px-5 py-4">
                    <Button onClick={onClose}>Close</Button>
                </footer>
            </section>
        </div>
    );
}

function IssueList({
    emptyText,
    items,
}: {
    readonly emptyText: string;
    readonly items: readonly {
        readonly code: string;
        readonly message: string;
        readonly path?: string | null;
    }[];
}) {
    if (items.length === 0) {
        return <p>{emptyText}</p>;
    }

    return (
        <ul className="grid gap-2">
            {items.map((item) => (
                <li className="min-w-0" key={`${item.code}:${item.path ?? item.message}`}>
                    <p className="font-semibold text-foreground">{item.message}</p>
                    <p className="break-words font-mono text-label text-muted">
                        {item.code}
                        {item.path === null || item.path === undefined ? "" : ` · ${item.path}`}
                    </p>
                </li>
            ))}
        </ul>
    );
}

function NewDraftDialog({
    form,
    onCancel,
    onChange,
    onCreate,
}: {
    readonly form: NewDraftFormState;
    readonly onCancel: () => void;
    readonly onChange: (form: NewDraftFormState) => void;
    readonly onCreate: () => void;
}) {
    return (
        <div
            aria-labelledby="new-definition-draft-title"
            aria-modal="true"
            className="fixed inset-0 z-50 grid place-items-center bg-black/25 p-4"
            role="dialog"
        >
            <form
                className="grid w-full max-w-lg gap-4 rounded-shell border border-outline-soft bg-surface p-5 shadow-shell"
                onSubmit={(event) => {
                    event.preventDefault();
                    onCreate();
                }}
            >
                <div>
                    <p className="font-mono text-label font-medium uppercase text-muted">Draft</p>
                    <h2
                        className="mt-1 font-display text-[20px] font-semibold leading-6 text-foreground"
                        id="new-definition-draft-title"
                    >
                        New draft
                    </h2>
                </div>
                {form.error === null ? null : (
                    <StatePanel
                        summary={form.error.summary}
                        title={form.error.title}
                        tone="error"
                    />
                )}
                <label className="grid gap-2" htmlFor="new-draft-kind">
                    <span className="font-mono text-label font-medium uppercase text-muted">
                        Kind
                    </span>
                    <select
                        className={controlClassName()}
                        id="new-draft-kind"
                        onChange={(event) => {
                            onChange({ ...form, kind: event.target.value as DefinitionDraftKind });
                        }}
                        value={form.kind}
                    >
                        {DRAFT_KIND_OPTIONS.map((kind) => (
                            <option key={kind} value={kind}>
                                {kindLabel(kind)}
                            </option>
                        ))}
                    </select>
                </label>
                <label className="grid gap-2" htmlFor="new-draft-mode">
                    <span className="font-mono text-label font-medium uppercase text-muted">
                        Mode
                    </span>
                    <select
                        className={controlClassName()}
                        id="new-draft-mode"
                        onChange={(event) => {
                            onChange({ ...form, mode: event.target.value as DefinitionDraftMode });
                        }}
                        value={form.mode}
                    >
                        <option value="create">Create new</option>
                        <option value="update">Edit existing</option>
                    </select>
                </label>
                <label className="grid gap-2" htmlFor="new-draft-key">
                    <span className="font-mono text-label font-medium uppercase text-muted">
                        Key
                    </span>
                    <input
                        autoFocus
                        className={controlClassName()}
                        id="new-draft-key"
                        onChange={(event) => {
                            onChange({ ...form, key: event.target.value, error: null });
                        }}
                        value={form.key}
                    />
                </label>
                {form.mode === "create" ? (
                    <label className="grid gap-2" htmlFor="new-draft-description">
                        <span className="font-mono text-label font-medium uppercase text-muted">
                            Description
                        </span>
                        <input
                            className={controlClassName()}
                            id="new-draft-description"
                            onChange={(event) => {
                                onChange({ ...form, description: event.target.value });
                            }}
                            value={form.description}
                        />
                    </label>
                ) : null}
                <div className="flex justify-end gap-2 border-t border-outline-soft pt-4">
                    <Button disabled={form.isCreating} onClick={onCancel} variant="secondary">
                        Cancel
                    </Button>
                    <Button
                        disabled={form.isCreating}
                        icon={<FilePenLine className="size-4" />}
                        type="submit"
                        variant="primary"
                    >
                        {form.isCreating ? "Creating" : "Create draft"}
                    </Button>
                </div>
            </form>
        </div>
    );
}

function draftIdentityFromSearch(searchParams: URLSearchParams): DraftIdentity | null {
    const kind = coerceDraftKind(searchParams.get("kind") ?? searchParams.get("materialize_kind"));
    const key = normalizeDraftKey(
        searchParams.get("key") ?? searchParams.get("materialize_key") ?? "",
    );
    if (kind === null || key.length === 0) {
        return null;
    }
    return { key, kind };
}

function coerceDraftKind(value: string | null): DefinitionDraftKind | null {
    if (value === "role" || value === "policy" || value === "workflow") {
        return value;
    }
    return null;
}

function draftIdentityFromSummary(summary: DraftSummary): DraftIdentity {
    return { key: summary.key, kind: summary.kind };
}

function draftIdentityKey(identity: DraftIdentity): string {
    return `${identity.kind}:${identity.key}`;
}

function draftIdentityEquals(left: DraftIdentity | null, right: DraftIdentity | null): boolean {
    if (left === null || right === null) {
        return left === right;
    }
    return left.kind === right.kind && left.key === right.key;
}

function draftSummaryFromDetail(draft: DraftDetail): DraftSummary {
    return {
        based_on: draft.based_on,
        body_format: draft.body_format,
        content_hash: draft.content_hash,
        draft_path: draft.draft_path,
        key: draft.key,
        kind: draft.kind,
        mode: draft.mode,
        normalized_path: draft.normalized_path,
        status: draft.status,
        updated_at: draft.updated_at,
    };
}

function compareDraftSummaryUpdatedAt(left: DraftSummary, right: DraftSummary): number {
    return right.updated_at.localeCompare(left.updated_at);
}

function kindLabel(kind: DefinitionDraftKind): string {
    switch (kind) {
        case "policy":
            return "Policy";
        case "role":
            return "Role";
        case "workflow":
            return "Workflow";
    }
}

function modeLabel(mode: DefinitionDraftMode): string {
    return mode === "create" ? "Create" : "Update";
}

function statusLabel(
    status:
        DraftDetail["status"] | DraftValidationResponse["status"] | DraftPublishResponse["status"],
): string {
    return status.replace(/_/g, " ");
}

function statusTone(status: DraftDetail["status"]): StatusTone {
    switch (status) {
        case "clean":
            return "success";
        case "modified":
        case "new":
            return "warning";
        case "stale":
        case "invalid":
            return "danger";
    }
}

function starterBodyForKind(kind: DefinitionDraftKind, key: string, description: string): string {
    const draftDescription = description.trim() || `Draft ${kind} ${key}.`;
    if (kind === "policy") {
        return [
            "kind: policy",
            `id: ${key}`,
            `description: ${draftDescription}`,
            "instruction: Keep the assigned work bounded to this policy.",
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
    if (kind === "workflow") {
        return [
            "kind: workflow",
            `id: ${key}`,
            `description: ${draftDescription}`,
            "root:",
            "  id: root",
            "  role: root_planning_lead",
            "  policy: standard-root",
            `  description: ${draftDescription}`,
            "  instruction: Plan the requested work and close when complete.",
            "",
        ].join("\n");
    }
    return [
        "kind: role",
        `id: ${key}`,
        `description: ${draftDescription}`,
        "instruction: Work inside the assigned scope and report concise results.",
        "allowed_node_kinds:",
        "  - worker",
        "",
    ].join("\n");
}

function formError(summary: string): ConsoleErrorView {
    return {
        code: "invalid_form",
        fieldErrors: [],
        isRetryable: false,
        source: "validation",
        status: null,
        suggestedNextStep: null,
        summary,
        title: "Invalid Draft",
    };
}

function normalizeDraftKey(value: string): string {
    return value.trim();
}

function controlClassName(): string {
    return "h-control w-full min-w-0 rounded-control border border-outline bg-surface-low px-3 text-compact text-foreground shadow-hairline focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/15";
}

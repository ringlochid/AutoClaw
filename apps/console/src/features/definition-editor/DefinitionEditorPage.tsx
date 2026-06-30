import { AlertTriangle, Plus, RefreshCw, RotateCcw, Save, Trash2, X } from "lucide-react";
import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import { Link } from "react-router-dom";

import { PageFrame } from "../../components/layout";
import {
    Button,
    CodeBlock,
    FormField,
    SegmentedControl,
    StatePanel,
    StatusChip,
    Surface,
} from "../../components/ui";
import { classNames } from "../../lib/classNames";
import {
    applyResultTitle,
    isAuthError,
    useDefinitionEditorController,
    type DefinitionEditorController,
} from "./definition-editor-controller";
import {
    DEFINITION_KIND_OPTIONS,
    EDITOR_MODE_OPTIONS,
    PREVIEW_PROVENANCE_OPTIONS,
    applyResultTone,
    kindLabel,
    validationStatusLabel,
    validationStatusTone,
    type DraftFileView,
    type DraftSetView,
} from "./definition-editor-model";

export function DefinitionEditorPage() {
    const controller = useDefinitionEditorController();
    const dialogReturnFocusRef = useRef<HTMLElement | null>(null);

    const rememberDialogTrigger = (trigger: HTMLElement) => {
        dialogReturnFocusRef.current = trigger;
        trigger.focus({ preventScroll: true });
    };

    return (
        <PageFrame
            actions={
                <div className="flex flex-wrap items-center gap-2">
                    <StatusChip
                        tone={controller.currentDraftSet === null ? "neutral" : "active"}
                        withDot
                    >
                        Draft workbench
                    </StatusChip>
                    <Button
                        disabled={
                            controller.listState.isLoading || controller.listState.isRefreshing
                        }
                        icon={
                            <RefreshCw
                                className={controller.listState.isRefreshing ? "animate-spin" : ""}
                            />
                        }
                        onClick={controller.refresh}
                    >
                        Refresh
                    </Button>
                </div>
            }
            description="Edit backend-owned definition draft sets without making draft state launchable or current."
            eyebrow="Authoring"
            title="Definition Editor"
        >
            <div className="space-y-4">
                <TruthBoundaryStrip controller={controller} />
                {controller.actionError === null ? null : (
                    <StatePanel
                        action={<Button onClick={controller.dismissActionError}>Dismiss</Button>}
                        summary={controller.actionError.summary}
                        title={
                            isAuthError(controller.actionError)
                                ? "Access to Definition Editor failed"
                                : "Draft action failed"
                        }
                        tone={isAuthError(controller.actionError) ? "auth" : "error"}
                    />
                )}
                <div className="grid min-w-0 gap-4 xl:grid-cols-[19rem_minmax(0,1fr)]">
                    <DraftRail controller={controller} onDialogTrigger={rememberDialogTrigger} />
                    <Workbench controller={controller} onDialogTrigger={rememberDialogTrigger} />
                </div>
            </div>
            {controller.newDraftModalOpen ? (
                <NewDraftDialog controller={controller} returnFocusRef={dialogReturnFocusRef} />
            ) : null}
            {controller.confirmation === null ? null : (
                <ConfirmationDialog controller={controller} returnFocusRef={dialogReturnFocusRef} />
            )}
        </PageFrame>
    );
}

type DialogTriggerHandler = (trigger: HTMLElement) => void;

function TruthBoundaryStrip({ controller }: { readonly controller: DefinitionEditorController }) {
    const selectedFile = controller.selectedFile;
    return (
        <Surface className="min-w-0" label="Truth boundaries" variant="muted">
            <div className="grid gap-3 md:grid-cols-4">
                <TruthBoundary
                    label="Stored truth"
                    value={selectedFile?.baselineLabel ?? "No selected file"}
                />
                <TruthBoundary label="Draft set" value={draftSetTruthLabel(controller)} />
                <TruthBoundary
                    label="Preview truth"
                    value={
                        controller.previewProvenance === "draft_truth"
                            ? "Draft truth"
                            : "Stored truth"
                    }
                />
                <TruthBoundary label="Task Start" value="Separate stored-truth handoff" />
            </div>
        </Surface>
    );
}

function TruthBoundary({ label, value }: { readonly label: string; readonly value: string }) {
    return (
        <div className="min-w-0 rounded-card border border-outline-soft bg-surface-low px-3 py-2">
            <p className="font-mono text-label font-medium uppercase text-muted">{label}</p>
            <p className="mt-1 truncate text-compact font-semibold text-foreground">{value}</p>
        </div>
    );
}

function DraftRail({
    controller,
    onDialogTrigger,
}: {
    readonly controller: DefinitionEditorController;
    readonly onDialogTrigger: DialogTriggerHandler;
}) {
    return (
        <Surface
            actions={
                <Button
                    icon={<Plus />}
                    onClick={(event) => {
                        onDialogTrigger(event.currentTarget);
                        controller.startNewDraft();
                    }}
                >
                    New draft
                </Button>
            }
            className="min-w-0"
            label="Draft set"
        >
            <div className="space-y-4">
                <DraftSetSelector controller={controller} onDialogTrigger={onDialogTrigger} />
                <DraftFileNavigator controller={controller} />
                <MaterializeStoredDefinition controller={controller} />
            </div>
        </Surface>
    );
}

function DraftSetSelector({
    controller,
    onDialogTrigger,
}: {
    readonly controller: DefinitionEditorController;
    readonly onDialogTrigger: DialogTriggerHandler;
}) {
    if (controller.listState.isLoading) {
        return (
            <StatePanel
                summary="Reading saved draft sets."
                title="Loading draft sets"
                tone="loading"
            />
        );
    }

    if (controller.listState.error !== null) {
        return (
            <StatePanel
                action={<Button onClick={controller.refresh}>Retry</Button>}
                summary={controller.listState.error.summary}
                title={
                    isAuthError(controller.listState.error)
                        ? "Access to draft sets failed"
                        : "Draft sets could not load"
                }
                tone={isAuthError(controller.listState.error) ? "auth" : "error"}
            />
        );
    }

    if (controller.listState.rows.length === 0) {
        return (
            <StatePanel
                action={<Button onClick={controller.startNewDraftSet}>New draft set</Button>}
                summary="No backend-owned draft sets were returned."
                title="No draft set"
                tone="empty"
            />
        );
    }

    return (
        <div className="space-y-3">
            <FormField id="definition-editor-draft-set" label="Draft set">
                <select
                    className={controlClassName()}
                    onChange={(event) => {
                        controller.selectDraftSet(event.target.value);
                    }}
                    value={controller.selectedDraftSetId ?? ""}
                >
                    {controller.listState.rows.map((row) => (
                        <option key={row.draftSetId} value={row.draftSetId}>
                            {row.title ?? row.draftSetId}
                        </option>
                    ))}
                </select>
            </FormField>
            <div className="flex flex-wrap gap-2">
                <Button onClick={controller.startNewDraftSet}>New draft set</Button>
                <Button
                    disabled={controller.currentDraftSet === null}
                    icon={<Trash2 />}
                    onClick={(event) => {
                        onDialogTrigger(event.currentTarget);
                        controller.requestConfirmation({ action: "delete_draft_set" });
                    }}
                    variant="danger"
                >
                    Delete draft set
                </Button>
                {controller.listState.nextCursor === null ? null : (
                    <Button
                        disabled={controller.listState.isLoadingMore}
                        onClick={controller.loadMoreDraftSets}
                    >
                        Load more
                    </Button>
                )}
            </div>
        </div>
    );
}

function DraftFileNavigator({ controller }: { readonly controller: DefinitionEditorController }) {
    const draftSet = controller.currentDraftSet;
    if (controller.detailState.isLoading) {
        return (
            <StatePanel
                summary="Reading draft files and saved bodies."
                title="Loading drafts"
                tone="loading"
            />
        );
    }

    if (controller.detailState.error !== null) {
        return (
            <StatePanel
                action={<Button onClick={controller.refresh}>Retry</Button>}
                summary={controller.detailState.error.summary}
                title={
                    isAuthError(controller.detailState.error)
                        ? "Access to selected draft failed"
                        : "Selected draft could not load"
                }
                tone={isAuthError(controller.detailState.error) ? "auth" : "error"}
            />
        );
    }

    if (draftSet === null || draftSet.files.length === 0) {
        return (
            <StatePanel
                summary="Create or materialize a draft file to begin authoring."
                title="No draft files"
                tone="empty"
            />
        );
    }

    return (
        <ol aria-label="Draft files" className="space-y-2">
            {draftSet.files.map((file) => (
                <li key={file.id}>
                    <button
                        aria-pressed={controller.selectedFileId === file.id}
                        className={classNames(
                            "w-full rounded-card border bg-surface-low p-3 text-left transition-colors hover:border-primary/35 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                            controller.selectedFileId === file.id
                                ? "border-primary/60 bg-primary-soft/50"
                                : "border-outline-soft",
                        )}
                        onClick={() => {
                            controller.selectDraftFile(file.id);
                        }}
                        type="button"
                    >
                        <span className="flex min-w-0 flex-wrap gap-2">
                            <StatusChip>{kindLabel(file.kind)}</StatusChip>
                            <StatusChip tone={file.statusTone}>{file.statusLabel}</StatusChip>
                        </span>
                        <span className="mt-2 block truncate text-compact font-semibold text-foreground">
                            {file.key}
                        </span>
                    </button>
                </li>
            ))}
        </ol>
    );
}

function MaterializeStoredDefinition({
    controller,
}: {
    readonly controller: DefinitionEditorController;
}) {
    return (
        <div className="rounded-card border border-outline-soft bg-surface-muted p-3">
            <p className="font-mono text-label font-medium uppercase text-muted">Stored revision</p>
            <div className="mt-3 grid gap-3">
                <FormField id="definition-editor-materialize-kind" label="Kind">
                    <select
                        className={controlClassName()}
                        onChange={(event) => {
                            controller.setMaterializeForm({
                                ...controller.materializeForm,
                                kind: event.target.value as typeof controller.materializeForm.kind,
                            });
                        }}
                        value={controller.materializeForm.kind}
                    >
                        {DEFINITION_KIND_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </FormField>
                <FormField
                    error={controller.materializeError ?? undefined}
                    id="definition-editor-materialize-key"
                    label="Stored key"
                >
                    <input
                        className={controlClassName()}
                        onChange={(event) => {
                            controller.setMaterializeForm({
                                ...controller.materializeForm,
                                key: event.target.value,
                            });
                        }}
                        value={controller.materializeForm.key}
                    />
                </FormField>
                <Button
                    disabled={controller.currentDraftSet === null || controller.isMutatingDraft}
                    onClick={controller.submitMaterialize}
                >
                    Materialize stored revision
                </Button>
            </div>
        </div>
    );
}

function Workbench({
    controller,
    onDialogTrigger,
}: {
    readonly controller: DefinitionEditorController;
    readonly onDialogTrigger: DialogTriggerHandler;
}) {
    const draftSet = controller.currentDraftSet;
    const selectedFile = controller.selectedFile;

    if (controller.detailState.isLoading) {
        return (
            <Surface label="Draft" title="Editor">
                <StatePanel
                    summary={`Reading ${controller.selectedDraftSetId ?? "the selected draft set"} before showing saved draft bodies.`}
                    title="Loading selected draft"
                    tone="loading"
                />
            </Surface>
        );
    }

    if (controller.detailState.error !== null) {
        return (
            <Surface label="Draft" title="Editor">
                <StatePanel
                    action={<Button onClick={controller.refresh}>Retry</Button>}
                    summary={controller.detailState.error.summary}
                    title={
                        isAuthError(controller.detailState.error)
                            ? "Access to selected draft failed"
                            : "Selected draft could not load"
                    }
                    tone={isAuthError(controller.detailState.error) ? "auth" : "error"}
                />
            </Surface>
        );
    }

    if (draftSet === null || selectedFile === null) {
        return (
            <Surface label="Draft" title="Editor">
                <StatePanel
                    summary="Select or create a backend-owned draft file."
                    title="No selected draft"
                    tone="empty"
                />
            </Surface>
        );
    }

    return (
        <Surface
            actions={<WorkbenchActions controller={controller} />}
            className="min-w-0"
            label="Draft"
            title={selectedFile.key}
        >
            <div className="space-y-4">
                <DraftHeader
                    draftSet={draftSet}
                    isEditorDirty={controller.isEditorDirty}
                    selectedFile={selectedFile}
                />
                <SegmentedControl
                    label="Editor mode"
                    onChange={controller.setMode}
                    options={EDITOR_MODE_OPTIONS}
                    value={controller.mode}
                />
                {controller.mode === "edit" ? (
                    <EditMode controller={controller} onDialogTrigger={onDialogTrigger} />
                ) : null}
                {controller.mode === "validation" ? (
                    <ValidationMode controller={controller} />
                ) : null}
                {controller.mode === "preview" ? <PreviewMode controller={controller} /> : null}
                <ApplyResult controller={controller} />
                <TaskStartHandoff />
            </div>
        </Surface>
    );
}

function WorkbenchActions({ controller }: { readonly controller: DefinitionEditorController }) {
    return (
        <>
            <Button
                disabled={!controller.isEditorDirty || controller.isMutatingDraft}
                icon={<Save />}
                onClick={controller.saveSelectedDraft}
            >
                Save draft
            </Button>
            <Button disabled={controller.isMutatingDraft} onClick={controller.runValidation}>
                Validate
            </Button>
            <Button disabled={controller.isMutatingDraft} onClick={controller.runPreview}>
                Preview
            </Button>
            <Button
                disabled={controller.isMutatingDraft}
                onClick={controller.runApply}
                variant="primary"
            >
                Apply
            </Button>
        </>
    );
}

function DraftHeader({
    draftSet,
    isEditorDirty,
    selectedFile,
}: {
    readonly draftSet: DraftSetView;
    readonly isEditorDirty: boolean;
    readonly selectedFile: DraftFileView;
}) {
    return (
        <div className="flex flex-wrap items-center gap-2 border-b border-outline-soft pb-4">
            <StatusChip>{kindLabel(selectedFile.kind)}</StatusChip>
            <StatusChip tone={isEditorDirty ? "warning" : selectedFile.statusTone}>
                {isEditorDirty ? "local edits" : selectedFile.statusLabel}
            </StatusChip>
            <StatusChip tone={draftSet.stateTone}>draft set {draftSet.stateLabel}</StatusChip>
            <StatusChip>{selectedFile.baselineLabel}</StatusChip>
        </div>
    );
}

function EditMode({
    controller,
    onDialogTrigger,
}: {
    readonly controller: DefinitionEditorController;
    readonly onDialogTrigger: DialogTriggerHandler;
}) {
    const selectedFile = controller.selectedFile;
    if (selectedFile === null) {
        return null;
    }

    return (
        <div className="space-y-4">
            <FormField
                hint="Draft edits remain local to the selected backend draft set until saved and applied."
                id="definition-editor-body"
                label="Editable draft body"
            >
                <textarea
                    className={classNames(
                        controlClassName(),
                        "min-h-[28rem] resize-y font-mono text-utility",
                    )}
                    onChange={(event) => {
                        controller.setEditorBody(event.target.value);
                    }}
                    spellCheck={false}
                    value={controller.editorBody}
                />
            </FormField>
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,0.45fr)]">
                <CodeBlock title="Captured baseline">
                    {selectedFile.baselineBody ?? "Starter baseline is held by the draft set."}
                </CodeBlock>
                <div className="rounded-card border border-outline-soft bg-surface-muted p-4">
                    <p className="font-mono text-label font-medium uppercase text-muted">
                        Comparison
                    </p>
                    <p className="mt-2 text-compact text-muted">{selectedFile.resetSummary}</p>
                    <div className="mt-4 flex flex-col items-stretch gap-2">
                        <Button
                            className="w-full"
                            icon={<RotateCcw />}
                            onClick={(event) => {
                                onDialogTrigger(event.currentTarget);
                                controller.requestConfirmation({ action: "reset" });
                            }}
                        >
                            Reset draft
                        </Button>
                        {selectedFile.hasStoredTruth ? (
                            <Button
                                aria-label="Replace with current stored revision"
                                className="w-full"
                                onClick={(event) => {
                                    onDialogTrigger(event.currentTarget);
                                    controller.requestConfirmation({ action: "rematerialize" });
                                }}
                                variant="danger"
                            >
                                Replace current revision
                            </Button>
                        ) : null}
                    </div>
                </div>
            </div>
        </div>
    );
}

function ValidationMode({ controller }: { readonly controller: DefinitionEditorController }) {
    if (controller.validationState.isRunning) {
        return (
            <StatePanel
                summary="Running draft-set validation."
                title="Validation pending"
                tone="loading"
            />
        );
    }

    if (controller.validationView === null && controller.validationState.error === null) {
        return (
            <StatePanel
                action={<Button onClick={controller.runValidation}>Validate</Button>}
                summary="No validation result is loaded for the current draft set."
                title="Validation not run"
                tone="empty"
            />
        );
    }

    if (controller.validationState.error !== null) {
        return (
            <StatePanel
                action={<Button onClick={controller.runValidation}>Retry validation</Button>}
                summary={controller.validationState.error.summary}
                title="Validation failed"
                tone="error"
            />
        );
    }

    const validationView = controller.validationView;
    if (validationView === null) {
        return null;
    }

    const response = validationView.response;
    return (
        <div className="space-y-4">
            {validationView.stale ? (
                <StatePanel
                    summary="The selected draft changed after this validation result was produced."
                    title="Validation result is stale"
                    tone="stale"
                />
            ) : null}
            <StatePanel
                summary={`${String(response.errors.length)} errors and ${String(response.warnings.length)} warnings returned for this draft set.`}
                title={`Validation ${validationStatusLabel(response.status)}`}
                tone={
                    response.status === "valid"
                        ? "success"
                        : response.status === "stale"
                          ? "stale"
                          : "error"
                }
            />
            <IssueList issues={response.errors} title="Errors" />
            <IssueList issues={response.warnings} title="Warnings" />
        </div>
    );
}

function PreviewMode({ controller }: { readonly controller: DefinitionEditorController }) {
    const selectedFile = controller.selectedFile;
    return (
        <div className="space-y-4">
            <SegmentedControl
                label="Preview provenance"
                onChange={controller.setPreviewProvenance}
                options={PREVIEW_PROVENANCE_OPTIONS}
                value={controller.previewProvenance}
            />
            {controller.previewProvenance === "stored_truth" ? (
                <StoredTruthPreview selectedFile={selectedFile} />
            ) : (
                <DraftTruthPreview controller={controller} />
            )}
        </div>
    );
}

function StoredTruthPreview({ selectedFile }: { readonly selectedFile: DraftFileView | null }) {
    if (!selectedFile?.hasStoredTruth) {
        return (
            <StatePanel
                summary="This draft file has no captured stored revision."
                title="Stored truth preview unavailable"
                tone="empty"
            />
        );
    }

    return (
        <div className="space-y-4">
            <StatusChip tone="active" withDot>
                Stored truth
            </StatusChip>
            <CodeBlock title={`Captured ${selectedFile.baselineLabel}`}>
                {selectedFile.baselineBody ?? "Captured baseline body was not returned."}
            </CodeBlock>
        </div>
    );
}

function DraftTruthPreview({ controller }: { readonly controller: DefinitionEditorController }) {
    return (
        <div className="space-y-4">
            <StatusChip tone="active" withDot>
                Draft truth
            </StatusChip>
            <FormField
                hint="Preview task-compose input is saved and validated by the draft-set preview route."
                id="definition-editor-preview-body"
                label="Task-compose preview input"
            >
                <textarea
                    className={classNames(
                        controlClassName(),
                        "min-h-40 resize-y font-mono text-utility",
                    )}
                    onChange={(event) => {
                        controller.setPreviewBody(event.target.value);
                    }}
                    spellCheck={false}
                    value={controller.previewBody}
                />
            </FormField>
            <Button disabled={controller.previewState.isRunning} onClick={controller.runPreview}>
                Run preview
            </Button>
            {controller.previewState.isRunning ? (
                <StatePanel
                    summary="Running preview validation."
                    title="Preview pending"
                    tone="loading"
                />
            ) : null}
            {controller.previewState.error === null ? null : (
                <StatePanel
                    summary={controller.previewState.error.summary}
                    title="Preview failed"
                    tone="error"
                />
            )}
            {controller.previewState.result === null ? null : (
                <div className="space-y-3">
                    <StatePanel
                        summary={`${String(controller.previewState.result.validation.errors.length)} errors and ${String(controller.previewState.result.validation.warnings.length)} warnings returned.`}
                        title={
                            controller.previewState.result.status === "valid"
                                ? "Preview valid"
                                : "Preview invalid"
                        }
                        tone={
                            controller.previewState.result.status === "valid" ? "success" : "error"
                        }
                    />
                    <IssueList
                        issues={controller.previewState.result.validation.errors}
                        title="Preview errors"
                    />
                    <IssueList
                        issues={controller.previewState.result.validation.warnings}
                        title="Preview warnings"
                    />
                </div>
            )}
        </div>
    );
}

function IssueList({
    issues,
    title,
}: {
    readonly issues: readonly {
        readonly code: string;
        readonly kind: "cross_reference" | "preview" | "schema" | "stale";
        readonly message: string;
        readonly path?: string | null;
    }[];
    readonly title: string;
}) {
    if (issues.length === 0) {
        return (
            <div className="rounded-card border border-outline-soft bg-surface-muted p-4">
                <p className="font-display text-compact font-semibold text-foreground">{title}</p>
                <p className="mt-1 text-compact text-muted">No issues returned.</p>
            </div>
        );
    }

    return (
        <section className="rounded-card border border-outline-soft bg-surface-low p-4">
            <h3 className="font-display text-compact font-semibold text-foreground">{title}</h3>
            <ol className="mt-3 space-y-2">
                {issues.map((issue) => (
                    <li
                        className="rounded-card border border-outline-soft bg-surface-muted p-3"
                        key={`${issue.kind}:${issue.code}:${issue.path ?? "root"}`}
                    >
                        <div className="flex flex-wrap gap-2">
                            <StatusChip
                                tone={validationStatusTone(
                                    issue.kind === "stale" ? "stale" : "invalid",
                                )}
                            >
                                {issue.kind}
                            </StatusChip>
                            <StatusChip>{issue.code}</StatusChip>
                        </div>
                        <p className="mt-2 text-compact text-foreground">{issue.message}</p>
                        {issue.path === null || issue.path === undefined ? null : (
                            <p className="mt-1 font-mono text-utility text-muted">{issue.path}</p>
                        )}
                    </li>
                ))}
            </ol>
        </section>
    );
}

function ApplyResult({ controller }: { readonly controller: DefinitionEditorController }) {
    if (controller.applyState.isRunning) {
        return (
            <StatePanel
                summary="Submitting the draft-set apply request."
                title="Apply pending"
                tone="loading"
            />
        );
    }

    if (controller.applyState.error !== null) {
        return (
            <StatePanel
                summary={controller.applyState.error.summary}
                title={
                    isAuthError(controller.applyState.error)
                        ? "Access to apply failed"
                        : "Apply failed"
                }
                tone={isAuthError(controller.applyState.error) ? "auth" : "error"}
            />
        );
    }

    const result = controller.applyState.result;
    if (result === null) {
        return null;
    }

    return (
        <section className="rounded-card border border-outline-soft bg-surface-muted p-4">
            <div className="flex flex-wrap items-center gap-2">
                <StatusChip tone={applyResultTone(result)}>{result.status}</StatusChip>
                <h3 className="font-display text-compact font-semibold text-foreground">
                    {applyResultTitle(result)}
                </h3>
            </div>
            {result.published_revisions.length === 0 ? (
                <p className="mt-2 text-compact text-muted">
                    No published revisions were returned.
                </p>
            ) : (
                <ol className="mt-3 space-y-2">
                    {result.published_revisions.map((revision) => (
                        <li
                            className="font-mono text-utility text-muted"
                            key={`${revision.kind}:${revision.key}:${String(revision.revision_no)}`}
                        >
                            {revision.kind}/{revision.key} revision {revision.revision_no}
                        </li>
                    ))}
                </ol>
            )}
        </section>
    );
}

function TaskStartHandoff() {
    return (
        <div className="rounded-card border border-outline-soft bg-surface-muted p-4">
            <p className="font-mono text-label font-medium uppercase text-muted">Task Start</p>
            <p className="mt-1 text-compact text-muted">
                Launch-specific inputs stay on the stored-truth Task Start page.
            </p>
            <Link
                className="mt-3 inline-flex text-utility font-semibold text-primary-foreground"
                to="/task-start"
            >
                Open Task Start
            </Link>
        </div>
    );
}

function NewDraftDialog({
    controller,
    returnFocusRef,
}: {
    readonly controller: DefinitionEditorController;
    readonly returnFocusRef: RefObject<HTMLElement | null>;
}) {
    return (
        <Dialog
            footer={
                <>
                    <Button
                        onClick={() => {
                            controller.setNewDraftModalOpen(false);
                        }}
                        data-dialog-initial-focus
                    >
                        Cancel
                    </Button>
                    <Button
                        disabled={controller.isMutatingDraft}
                        onClick={controller.submitNewDraft}
                        variant="primary"
                    >
                        Create draft
                    </Button>
                </>
            }
            onClose={() => {
                controller.setNewDraftModalOpen(false);
            }}
            returnFocusRef={returnFocusRef}
            title="New draft"
        >
            <div className="grid gap-4">
                <FormField id="definition-editor-new-kind" label="Kind">
                    <select
                        className={controlClassName()}
                        onChange={(event) => {
                            controller.setNewDraftForm({
                                ...controller.newDraftForm,
                                kind: event.target.value as typeof controller.newDraftForm.kind,
                            });
                        }}
                        value={controller.newDraftForm.kind}
                    >
                        {DEFINITION_KIND_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </FormField>
                <FormField
                    error={controller.newDraftError ?? undefined}
                    id="definition-editor-new-key"
                    label="Draft key"
                >
                    <input
                        autoFocus
                        className={controlClassName()}
                        data-dialog-initial-focus
                        onChange={(event) => {
                            controller.setNewDraftForm({
                                ...controller.newDraftForm,
                                key: event.target.value,
                            });
                        }}
                        value={controller.newDraftForm.key}
                    />
                </FormField>
                <FormField id="definition-editor-new-description" label="Description">
                    <textarea
                        className={classNames(controlClassName(), "min-h-24 resize-y")}
                        onChange={(event) => {
                            controller.setNewDraftForm({
                                ...controller.newDraftForm,
                                description: event.target.value,
                            });
                        }}
                        value={controller.newDraftForm.description}
                    />
                </FormField>
            </div>
        </Dialog>
    );
}

function ConfirmationDialog({
    controller,
    returnFocusRef,
}: {
    readonly controller: DefinitionEditorController;
    readonly returnFocusRef: RefObject<HTMLElement | null>;
}) {
    const selectedFile = controller.selectedFile;
    const confirmation = controller.confirmation;
    if (confirmation === null) {
        return null;
    }

    if (confirmation.action === "delete_draft_set") {
        return (
            <Dialog
                footer={
                    <ConfirmationButtons
                        confirmLabel="Delete draft set"
                        onCancel={() => controller.setConfirmation(null)}
                        onConfirm={controller.deleteSelectedDraftSet}
                    />
                }
                onClose={() => {
                    controller.setConfirmation(null);
                }}
                returnFocusRef={returnFocusRef}
                title="Delete draft set"
            >
                <DialogWarning>
                    This deletes the backend-owned draft set. It does not delete stored registry
                    revisions.
                </DialogWarning>
            </Dialog>
        );
    }

    if (confirmation.action === "reset") {
        return (
            <Dialog
                footer={
                    <ConfirmationButtons
                        confirmLabel="Reset draft"
                        onCancel={() => controller.setConfirmation(null)}
                        onConfirm={controller.resetSelectedDraft}
                    />
                }
                onClose={() => {
                    controller.setConfirmation(null);
                }}
                returnFocusRef={returnFocusRef}
                title="Reset draft"
            >
                <p className="text-compact text-muted">
                    This restores {selectedFile?.baselineLabel ?? "the captured baseline"} inside
                    the selected draft set. It does not fetch newest stored registry truth.
                </p>
            </Dialog>
        );
    }

    return (
        <Dialog
            footer={
                <ConfirmationButtons
                    confirmLabel="Replace draft"
                    onCancel={() => controller.setConfirmation(null)}
                    onConfirm={controller.rematerializeSelectedDraft}
                />
            }
            onClose={() => {
                controller.setConfirmation(null);
            }}
            returnFocusRef={returnFocusRef}
            title="Replace with current stored revision"
        >
            <DialogWarning>
                This discards draft edits, reads the current stored registry revision, and updates
                the draft baseline. It does not apply or launch anything.
            </DialogWarning>
            <div className="mt-4 rounded-card border border-outline-soft bg-surface-muted p-3 font-mono text-utility">
                {selectedFile === null ? null : (
                    <div className="grid gap-2 sm:grid-cols-2">
                        <span>
                            {selectedFile.kind}/{selectedFile.key}
                        </span>
                        <span>{selectedFile.baselineLabel}</span>
                    </div>
                )}
            </div>
        </Dialog>
    );
}

function Dialog({
    children,
    footer,
    onClose,
    returnFocusRef,
    title,
}: {
    readonly children: ReactNode;
    readonly footer: ReactNode;
    readonly onClose: () => void;
    readonly returnFocusRef: RefObject<HTMLElement | null>;
    readonly title: string;
}) {
    const dialogRef = useRef<HTMLElement | null>(null);
    const onCloseRef = useRef(onClose);
    const previousFocusRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        onCloseRef.current = onClose;
    }, [onClose]);

    useEffect(() => {
        const activeElement = document.activeElement;
        previousFocusRef.current =
            returnFocusRef.current ??
            (activeElement instanceof HTMLElement && activeElement !== document.body
                ? activeElement
                : null);

        const dialog = dialogRef.current;
        const initialFocusTarget = dialog?.querySelector<HTMLElement>(
            "[data-dialog-initial-focus]",
        );
        const focusableElements = getDialogFocusableElements(dialog);
        const focusTarget =
            initialFocusTarget ?? (focusableElements.length > 0 ? focusableElements[0] : dialog);
        if (focusTarget !== null) {
            focusTarget.focus({ preventScroll: true });
        }

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                onCloseRef.current();
                return;
            }

            if (event.key !== "Tab") {
                return;
            }

            const currentDialog = dialogRef.current;
            const focusableElements = getDialogFocusableElements(currentDialog);
            if (currentDialog === null || focusableElements.length === 0) {
                event.preventDefault();
                currentDialog?.focus({ preventScroll: true });
                return;
            }

            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            const activeDialogElement = document.activeElement;

            if (
                event.shiftKey &&
                (activeDialogElement === firstElement ||
                    !(activeDialogElement instanceof HTMLElement) ||
                    !currentDialog.contains(activeDialogElement))
            ) {
                event.preventDefault();
                lastElement.focus({ preventScroll: true });
                return;
            }

            if (!event.shiftKey && activeDialogElement === lastElement) {
                event.preventDefault();
                firstElement.focus({ preventScroll: true });
                return;
            }

            if (
                activeDialogElement instanceof HTMLElement &&
                !currentDialog.contains(activeDialogElement)
            ) {
                event.preventDefault();
                firstElement.focus({ preventScroll: true });
            }
        };

        document.body.classList.add("overflow-hidden");
        document.addEventListener("keydown", handleKeyDown, true);
        return () => {
            document.body.classList.remove("overflow-hidden");
            document.removeEventListener("keydown", handleKeyDown, true);
            const previousFocus = previousFocusRef.current;
            if (previousFocus?.isConnected === true) {
                previousFocus.focus({ preventScroll: true });
            }
        };
    }, [returnFocusRef]);

    return (
        <div
            className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4"
            role="presentation"
        >
            <section
                aria-modal="true"
                aria-labelledby="definition-editor-dialog-title"
                className="w-full max-w-xl rounded-card border border-outline-soft bg-surface shadow-popover"
                ref={dialogRef}
                role="dialog"
                tabIndex={-1}
            >
                <header className="flex items-start justify-between gap-4 border-b border-outline-soft p-5">
                    <h2
                        className="font-display text-compact font-semibold text-foreground"
                        id="definition-editor-dialog-title"
                    >
                        {title}
                    </h2>
                    <button
                        aria-label="Close dialog"
                        className="inline-flex size-9 items-center justify-center rounded-control border border-outline bg-surface-low text-muted hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                        onClick={onClose}
                        type="button"
                    >
                        <X aria-hidden="true" className="size-4" />
                    </button>
                </header>
                <div className="p-5">{children}</div>
                <footer className="flex flex-wrap justify-end gap-2 border-t border-outline-soft p-5">
                    {footer}
                </footer>
            </section>
        </div>
    );
}

function ConfirmationButtons({
    confirmLabel,
    onCancel,
    onConfirm,
}: {
    readonly confirmLabel: string;
    readonly onCancel: () => void;
    readonly onConfirm: () => void;
}) {
    return (
        <>
            <Button data-dialog-initial-focus onClick={onCancel}>
                Cancel
            </Button>
            <Button onClick={onConfirm} variant="danger">
                {confirmLabel}
            </Button>
        </>
    );
}

function draftSetTruthLabel(controller: DefinitionEditorController): string {
    if (controller.currentDraftSet !== null) {
        return `${controller.currentDraftSet.draftSetId} / ${controller.currentDraftSet.stateLabel}`;
    }

    if (controller.selectedDraftSetId !== null && controller.detailState.isLoading) {
        return `${controller.selectedDraftSetId} / loading`;
    }

    if (controller.selectedDraftSetId !== null && controller.detailState.error !== null) {
        return `${controller.selectedDraftSetId} / read failed`;
    }

    return "No draft set loaded";
}

function getDialogFocusableElements(dialog: HTMLElement | null): HTMLElement[] {
    if (dialog === null) {
        return [];
    }

    return Array.from(
        dialog.querySelectorAll<HTMLElement>(
            [
                "a[href]",
                "button:not([disabled])",
                "input:not([disabled])",
                "select:not([disabled])",
                "textarea:not([disabled])",
                "[tabindex]:not([tabindex='-1'])",
            ].join(", "),
        ),
    );
}

function DialogWarning({ children }: { readonly children: ReactNode }) {
    return (
        <div className="flex items-start gap-3 rounded-card border border-danger/25 bg-danger-soft p-3">
            <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-danger" />
            <p className="text-compact text-muted">{children}</p>
        </div>
    );
}

function controlClassName(extra?: string): string {
    return classNames(
        "block w-full rounded-control border border-outline bg-surface-low px-3 py-2 text-compact text-foreground shadow-hairline transition-colors placeholder:text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20",
        extra,
    );
}

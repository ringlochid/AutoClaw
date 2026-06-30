import { Search } from "lucide-react";

import {
    Button,
    Disclosure,
    IdRefText,
    PropertyGrid,
    StatePanel,
    StatusChip,
    Surface,
    TimestampText,
} from "../../components/ui";
import { classNames } from "../../lib/classNames";
import type { TaskStartController } from "./task-start-controller";
import { isAuthError } from "./task-start-data";
import {
    type TaskStartVersionRow,
    type TaskStartWorkflowChoice,
    type TaskStartWorkflowDetail,
} from "./task-start-model";
import { controlClassName } from "./task-start-ui";

export function WorkflowSection({ controller }: { readonly controller: TaskStartController }) {
    return (
        <Surface
            actions={
                <StatusChip
                    tone={controller.listState.error === null ? "active" : "danger"}
                    withDot
                >
                    {controller.statusSummary}
                </StatusChip>
            }
            label="Workflow"
            title="Stored workflow source"
        >
            <div className="space-y-4">
                <WorkflowSearch controller={controller} />
                <WorkflowChoices controller={controller} />
                <SelectedWorkflow controller={controller} />
            </div>
        </Surface>
    );
}

function WorkflowSearch({ controller }: { readonly controller: TaskStartController }) {
    return (
        <div>
            <label
                className="block font-mono text-label font-medium uppercase text-muted"
                htmlFor="task-start-workflow-search"
            >
                Search workflow
            </label>
            <div className="relative mt-2">
                <Search
                    aria-hidden="true"
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                />
                <input
                    className={controlClassName("pl-10")}
                    id="task-start-workflow-search"
                    onChange={(event) => {
                        controller.updateWorkflowQuery(event.target.value);
                    }}
                    placeholder="Search stored workflows"
                    type="search"
                    value={controller.workflowQuery}
                />
            </div>
            {controller.formErrors.workflow === undefined ? null : (
                <p className="mt-1 text-utility font-semibold text-danger">
                    {controller.formErrors.workflow}
                </p>
            )}
        </div>
    );
}

function WorkflowChoices({ controller }: { readonly controller: TaskStartController }) {
    const { listState } = controller;

    if (listState.isLoading) {
        return (
            <StatePanel
                summary="Reading stored workflows from the controller registry."
                title="Loading workflows"
                tone="loading"
            />
        );
    }

    if (listState.error !== null) {
        return (
            <StatePanel
                action={<Button onClick={controller.refresh}>Retry</Button>}
                summary={listState.error.summary}
                title={
                    isAuthError(listState.error)
                        ? "Access to workflows failed"
                        : "Workflows could not load"
                }
                tone={isAuthError(listState.error) ? "auth" : "error"}
            />
        );
    }

    if (listState.rows.length === 0) {
        return (
            <StatePanel
                summary={
                    controller.workflowQuery.trim().length === 0
                        ? "The controller did not return stored workflows available for launch."
                        : "No stored workflows match the current search."
                }
                title={
                    controller.workflowQuery.trim().length === 0
                        ? "No stored workflows"
                        : "No matching workflows"
                }
                tone="empty"
            />
        );
    }

    return (
        <div className="space-y-3">
            <ol aria-label="Workflow choices" className="grid gap-2 lg:grid-cols-2">
                {listState.rows.map((workflow) => (
                    <li key={workflow.key}>
                        <WorkflowChoiceButton
                            isSelected={controller.selectedWorkflowKey === workflow.key}
                            onSelect={() => {
                                controller.selectWorkflow(workflow.key);
                            }}
                            workflow={workflow}
                        />
                    </li>
                ))}
            </ol>
            <div className="flex flex-col gap-3 border-t border-outline-soft pt-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-compact text-muted">
                    {listState.nextCursor === null
                        ? "End of current workflow suggestions."
                        : "More matching workflows are available."}
                </p>
                <Button
                    disabled={
                        listState.nextCursor === null ||
                        listState.isLoadingMore ||
                        listState.isRefreshing
                    }
                    onClick={controller.loadMoreWorkflows}
                >
                    {listState.isLoadingMore ? "Loading" : "Load more"}
                </Button>
            </div>
        </div>
    );
}

function WorkflowChoiceButton({
    isSelected,
    onSelect,
    workflow,
}: {
    readonly isSelected: boolean;
    readonly onSelect: () => void;
    readonly workflow: TaskStartWorkflowChoice;
}) {
    return (
        <button
            aria-pressed={isSelected}
            className={classNames(
                "grid h-full w-full min-w-0 gap-3 rounded-card border bg-surface-low p-4 text-left shadow-hairline transition-colors hover:border-primary/35 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                isSelected ? "border-primary/60 bg-primary-soft/45" : "border-outline-soft",
            )}
            onClick={onSelect}
            type="button"
        >
            <span className="flex min-w-0 flex-wrap items-center gap-2">
                <span className="min-w-0 truncate font-display text-compact font-semibold text-foreground">
                    {workflow.displayName}
                </span>
                <StatusChip tone="success" withDot>
                    Workflow
                </StatusChip>
                <StatusChip>{workflow.revisionLabel}</StatusChip>
            </span>
            <span className="break-words text-compact text-muted">
                {workflow.description ?? "No description reported."}
            </span>
            <span className="flex min-w-0 flex-wrap items-center gap-3">
                <IdRefText className="max-w-full truncate" value={workflow.key} />
                <TimestampText value={workflow.updatedAt} />
            </span>
        </button>
    );
}

function SelectedWorkflow({ controller }: { readonly controller: TaskStartController }) {
    if (controller.selectedWorkflowKey === null) {
        return (
            <StatePanel
                summary="Select one current stored workflow before previewing or starting a task."
                title="Workflow selection is required"
                tone="empty"
            />
        );
    }

    if (!controller.isSelectedWorkflowInRows && controller.listState.hasLoaded) {
        return (
            <StatePanel
                summary="The selected workflow is no longer present in the current search result. Reread or choose another stored workflow before launch."
                title="Selected workflow is outside the current search"
                tone="stale"
            />
        );
    }

    if (controller.detailState.isLoading) {
        return (
            <StatePanel
                summary="Reading current stored workflow detail and revision provenance."
                title="Loading selected workflow"
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
                        ? "Access to selected workflow failed"
                        : "Selected workflow could not load"
                }
                tone={isAuthError(controller.detailState.error) ? "auth" : "stale"}
            />
        );
    }

    if (controller.selectedWorkflow === null) {
        return null;
    }

    return (
        <div className="rounded-card border border-outline-soft bg-surface-low p-4 shadow-hairline">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                    <p className="font-mono text-label font-medium uppercase text-muted">
                        Selected workflow
                    </p>
                    <h2 className="mt-1 break-words font-display text-compact font-semibold text-foreground">
                        {controller.selectedWorkflow.displayName}
                    </h2>
                    <p className="mt-2 break-words text-compact text-muted">
                        {controller.detailState.detail?.description ??
                            controller.selectedWorkflow.description ??
                            "No description reported."}
                    </p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                    <StatusChip>{controller.selectedWorkflow.revisionLabel}</StatusChip>
                    <Button onClick={controller.clearWorkflow} variant="ghost">
                        Clear workflow
                    </Button>
                </div>
            </div>
            <WorkflowDetailDisclosure
                detail={controller.detailState.detail}
                versions={controller.versionsState.rows}
                versionsError={controller.versionsState.error}
                versionsLoading={controller.versionsState.isLoading}
                workflow={controller.selectedWorkflow}
            />
        </div>
    );
}

function WorkflowDetailDisclosure({
    detail,
    versions,
    versionsError,
    versionsLoading,
    workflow,
}: {
    readonly detail: TaskStartWorkflowDetail | null;
    readonly versions: readonly TaskStartVersionRow[];
    readonly versionsError: TaskStartController["versionsState"]["error"];
    readonly versionsLoading: boolean;
    readonly workflow: TaskStartWorkflowChoice;
}) {
    return (
        <Disclosure className="mt-4" label="Source confirmation" title="Open definition details">
            <div className="space-y-4">
                <PropertyGrid
                    items={[
                        { label: "Workflow", value: <IdRefText value={workflow.key} /> },
                        {
                            label: "Updated",
                            value: (
                                <TimestampText value={detail?.updatedAt ?? workflow.updatedAt} />
                            ),
                        },
                        {
                            label: "Current revision",
                            value: detail?.revisionNo ?? workflow.currentRevisionNo,
                        },
                        { label: "Root role", value: detail?.rootRole ?? "Not reported" },
                        { label: "Root policy", value: detail?.rootPolicy ?? "Not reported" },
                        { label: "Stored nodes", value: detail?.nodeCount ?? "Not reported" },
                    ]}
                />
                {detail === null ? null : (
                    <p className="break-words text-compact text-muted">
                        Stored workflow id: <IdRefText value={detail.workflowId} />
                    </p>
                )}
                <WorkflowVersions
                    error={versionsError}
                    isLoading={versionsLoading}
                    rows={versions}
                />
            </div>
        </Disclosure>
    );
}

function WorkflowVersions({
    error,
    isLoading,
    rows,
}: {
    readonly error: TaskStartController["versionsState"]["error"];
    readonly isLoading: boolean;
    readonly rows: readonly TaskStartVersionRow[];
}) {
    if (isLoading) {
        return (
            <StatePanel
                summary="Reading compact workflow revision history."
                title="Loading versions"
                tone="loading"
            />
        );
    }

    if (error !== null) {
        return (
            <StatePanel
                summary={error.summary}
                title={
                    isAuthError(error)
                        ? "Access to workflow history failed"
                        : "Workflow history could not load"
                }
                tone={isAuthError(error) ? "auth" : "error"}
            />
        );
    }

    if (rows.length === 0) {
        return (
            <StatePanel
                summary="The controller returned no revision history entries for this workflow."
                title="No versions"
                tone="empty"
            />
        );
    }

    return (
        <div>
            <p className="font-mono text-label font-medium uppercase text-muted">Versions</p>
            <ol aria-label="Workflow versions" className="mt-3 grid gap-2 sm:grid-cols-2">
                {rows.map((row) => (
                    <li
                        className="rounded-card border border-outline-soft bg-surface px-3 py-3"
                        key={row.revisionNo}
                    >
                        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
                            <StatusChip>Revision {row.revisionNo}</StatusChip>
                            <TimestampText value={row.updatedAt} />
                        </div>
                        <p className="mt-2 text-compact text-muted">
                            Recorded by: {row.recordedBy ?? "Not reported"}
                        </p>
                    </li>
                ))}
            </ol>
        </div>
    );
}

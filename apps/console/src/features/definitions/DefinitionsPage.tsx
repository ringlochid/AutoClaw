import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from "react";

import { ChevronDown, ExternalLink, Search, X } from "lucide-react";
import { Link } from "react-router-dom";

import { PageFrame } from "../../components/layout";
import { Button, PropertyGrid, StatePanel, StatusChip, TimestampText } from "../../components/ui";
import { classNames } from "../../lib/classNames";
import {
    isAuthError,
    useDefinitionsController,
    type DefinitionsController,
} from "./definition-controller";
import {
    DEFINITION_KIND_OPTIONS,
    DEFINITION_SORT_OPTIONS,
    NODE_KIND_FILTERS,
    formatBudgetSpec,
    formatNodeKind,
    formatOptionalInstruction,
    kindLabel,
    listLabelForKind,
    type DefinitionDetailView,
    type DefinitionListSort,
    type DefinitionRow,
    type DefinitionVersionRow,
    type NodeKind,
    type WorkflowNodeSummary,
} from "./definition-model";

export function DefinitionsPage() {
    const controller = useDefinitionsController();

    return (
        <PageFrame
            actions={
                <div className="flex flex-wrap items-center gap-2">
                    <DefinitionsNavLink to="/definitions/editor">
                        Definition Editor
                    </DefinitionsNavLink>
                    <DefinitionsNavLink to="/task-start">Task Start</DefinitionsNavLink>
                </div>
            }
            eyebrow="Authoring"
            headerContent={
                <div className="space-y-5">
                    <DefinitionsKindSwitch controller={controller} />
                    <DefinitionsControls controller={controller} />
                </div>
            }
            title="Definitions"
        >
            <div className="grid min-w-0 gap-3 border-t border-outline-soft pt-3 xl:grid-cols-[minmax(22rem,0.78fr)_minmax(0,1.12fr)]">
                <section
                    aria-labelledby="definitions-list-heading"
                    className="min-w-0 overflow-hidden rounded-card border border-outline-soft bg-surface-low"
                >
                    <DefinitionList controller={controller} />
                </section>
                <section
                    aria-labelledby="definitions-detail-heading"
                    className="min-w-0 rounded-card border border-outline-soft bg-surface-low"
                >
                    <DefinitionDetailPanel controller={controller} />
                </section>
            </div>
        </PageFrame>
    );
}

function DefinitionsKindSwitch({ controller }: { readonly controller: DefinitionsController }) {
    return (
        <div aria-label="Definition kind" className="flex min-w-0 flex-wrap gap-2" role="group">
            {DEFINITION_KIND_OPTIONS.map((option) => {
                const isSelected = option.listKind === controller.kind;
                return (
                    <button
                        aria-pressed={isSelected}
                        className={classNames(
                            "kind-button inline-flex h-control items-center justify-center gap-3 rounded-control border px-4 text-utility font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                            isSelected
                                ? "border-primary/25 bg-active text-active-foreground"
                                : "border-outline bg-surface-low text-foreground hover:border-primary/45 hover:bg-surface-muted",
                        )}
                        key={option.listKind}
                        onClick={() => {
                            controller.setKind(option.listKind);
                        }}
                        type="button"
                    >
                        <span
                            aria-hidden="true"
                            className={classNames(
                                "size-2 rounded-full",
                                isSelected ? "bg-primary" : "bg-outline-soft",
                            )}
                        />
                        <span>{option.label}</span>
                    </button>
                );
            })}
        </div>
    );
}

function DefinitionsControls({ controller }: { readonly controller: DefinitionsController }) {
    return (
        <div
            className={classNames(
                "grid gap-3",
                controller.kind === "workflows"
                    ? "lg:grid-cols-[minmax(0,1fr)_220px]"
                    : "lg:grid-cols-[minmax(0,1fr)_220px_220px]",
            )}
        >
            <div>
                <label className="sr-only" htmlFor="definitions-query">
                    Search
                </label>
                <div className="relative">
                    <Search
                        aria-hidden="true"
                        className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                    />
                    <input
                        className={controlClassName("pl-10")}
                        id="definitions-query"
                        onChange={(event) => {
                            controller.setQuery(event.target.value);
                        }}
                        placeholder={`Search ${listLabelForKind(controller.kind)}`}
                        type="search"
                        value={controller.query}
                    />
                </div>
            </div>
            <KindFilterSelect controller={controller} />
            <DefinitionSelect
                id="definitions-sort"
                label="Sort"
                onChange={(value) => {
                    controller.setSort(value as DefinitionListSort);
                }}
                options={DEFINITION_SORT_OPTIONS}
                value={controller.sort}
            />
        </div>
    );
}

function KindFilterSelect({ controller }: { readonly controller: DefinitionsController }) {
    if (controller.kind === "roles") {
        return (
            <DefinitionSelect
                id="definitions-role-filter"
                label="Allowed node kind"
                onChange={(value) => {
                    controller.setRoleNodeKindFilter(value as NodeKind | "any");
                }}
                options={[
                    { label: "Allowed node kind", value: "any" },
                    ...NODE_KIND_FILTERS.map((option) => ({
                        label: option.label,
                        value: option.value,
                    })),
                ]}
                value={controller.roleNodeKindFilter}
            />
        );
    }

    if (controller.kind === "policies") {
        return (
            <DefinitionSelect
                id="definitions-policy-filter"
                label="Applies to"
                onChange={(value) => {
                    controller.setAppliesToFilter(value as NodeKind | "any");
                }}
                options={[
                    { label: "Applies to", value: "any" },
                    ...NODE_KIND_FILTERS.map((option) => ({
                        label: option.label,
                        value: option.value,
                    })),
                ]}
                value={controller.appliesToFilter}
            />
        );
    }

    return null;
}

function DefinitionSelect({
    id,
    label,
    onChange,
    options,
    value,
}: {
    readonly id: string;
    readonly label: string;
    readonly onChange: (value: string) => void;
    readonly options: readonly { readonly label: string; readonly value: string }[];
    readonly value: string;
}) {
    return (
        <label className="relative block" htmlFor={id}>
            <span className="sr-only">{label}</span>
            <select
                aria-label={label}
                className={controlClassName("appearance-none bg-none pr-10")}
                id={id}
                onChange={(event) => {
                    onChange(event.target.value);
                }}
                value={value}
            >
                {options.map((option) => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>
            <ChevronDown
                aria-hidden="true"
                className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-foreground"
            />
        </label>
    );
}

function DefinitionList({ controller }: { readonly controller: DefinitionsController }) {
    const { listState } = controller;

    if (listState.isLoading) {
        return (
            <DefinitionListStateShell controller={controller}>
                <StatePanel
                    summary="Reading stored registry rows from the selected definition route."
                    title="Loading Definitions"
                    tone="loading"
                />
            </DefinitionListStateShell>
        );
    }

    if (listState.error !== null) {
        return (
            <DefinitionListStateShell controller={controller}>
                <StatePanel
                    action={<Button onClick={controller.refresh}>Retry</Button>}
                    summary={listState.error.summary}
                    title={
                        isAuthError(listState.error)
                            ? "Access to Definitions failed"
                            : "Definitions could not load"
                    }
                    tone={isAuthError(listState.error) ? "auth" : "error"}
                />
            </DefinitionListStateShell>
        );
    }

    if (listState.rows.length === 0) {
        if (controller.hasActiveNarrowing) {
            return (
                <DefinitionListStateShell controller={controller}>
                    <StatePanel
                        action={<Button onClick={controller.clearFilters}>Clear filters</Button>}
                        summary={`No ${listLabelForKind(controller.kind)} match the current search or ${controller.activeFilterSummary.toLowerCase()}.`}
                        title={`No matching ${listLabelForKind(controller.kind)}`}
                        tone="empty"
                    />
                </DefinitionListStateShell>
            );
        }

        return (
            <DefinitionListStateShell controller={controller}>
                <StatePanel
                    summary={`The controller did not return stored ${listLabelForKind(controller.kind)}.`}
                    title={`No stored ${listLabelForKind(controller.kind)}`}
                    tone="empty"
                />
            </DefinitionListStateShell>
        );
    }

    return (
        <div className="definition-list-shell">
            <div className="hidden border-b border-outline-soft bg-surface-muted px-5 py-3 font-mono text-label font-medium uppercase text-muted lg:grid lg:grid-cols-[minmax(0,1fr)_8rem] lg:items-center lg:gap-4">
                <span id="definitions-list-heading">{kindLabel(controller.singularKind)}s</span>
                <span>Updated</span>
            </div>
            <ol aria-label="Definition rows" className="definition-list-body space-y-2 px-3 py-3">
                {listState.rows.map((row) => (
                    <li key={row.key}>
                        <DefinitionRowButton
                            isSelected={controller.selectedKey === row.key}
                            onSelect={() => {
                                controller.selectDefinition(row.key);
                            }}
                            row={row}
                        />
                    </li>
                ))}
            </ol>
            <DefinitionListFooter controller={controller} />
        </div>
    );
}

function DefinitionListStateShell({
    children,
    controller,
}: {
    readonly children: ReactNode;
    readonly controller: DefinitionsController;
}) {
    return (
        <div className="definition-list-shell">
            <span className="sr-only" id="definitions-list-heading">
                {kindLabel(controller.singularKind)}s
            </span>
            <div className="definition-list-state-body">{children}</div>
        </div>
    );
}

function DefinitionRowButton({
    isSelected,
    onSelect,
    row,
}: {
    readonly isSelected: boolean;
    readonly onSelect: () => void;
    readonly row: DefinitionRow;
}) {
    return (
        <button
            aria-pressed={isSelected}
            className={classNames(
                "definition-row block w-full min-w-0 rounded-card border bg-surface-low text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary",
                isSelected ? "border-primary/35" : "border-outline-soft",
            )}
            onClick={onSelect}
            type="button"
        >
            <div className="space-y-3 px-4 py-3 sm:px-6 md:grid md:grid-cols-[minmax(0,1fr)_8rem] md:items-start md:gap-4 md:space-y-0">
                <div className="min-w-0 space-y-1.5">
                    <div className="space-y-0.5">
                        <span className="definition-title min-w-0 break-words font-display text-body font-semibold text-foreground">
                            {row.key}
                        </span>
                        <p className="definition-summary text-compact text-muted">
                            {row.description ?? "No description reported."}
                        </p>
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-2">
                        {row.compatibilityLabels.map((label) => (
                            <StatusChip key={label}>{label}</StatusChip>
                        ))}
                    </div>
                </div>
                <div className="flex items-start justify-between gap-3 text-right md:block">
                    <span className="font-mono text-label font-medium uppercase text-muted md:sr-only">
                        Updated
                    </span>
                    <div className="space-y-1">
                        <time
                            className="block font-body text-compact text-foreground md:whitespace-nowrap"
                            dateTime={row.updatedAt}
                        >
                            {formatRowUpdatedDate(row.updatedAt)}
                        </time>
                        <span className="block break-words font-mono text-label text-muted md:whitespace-nowrap">
                            {formatRowRelativeDate(row.updatedAt)}
                        </span>
                    </div>
                </div>
            </div>
        </button>
    );
}

function DefinitionListFooter({ controller }: { readonly controller: DefinitionsController }) {
    const { listState } = controller;
    if (listState.rows.length === 0) {
        return null;
    }

    return (
        <footer className="flex flex-col gap-3 border-t border-outline-soft bg-surface px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-compact text-muted">
                {String(listState.rows.length)} {listLabelForKind(controller.kind)} loaded.
            </p>
            {listState.nextCursor === null ? null : (
                <Button
                    disabled={
                        listState.isLoading || listState.isLoadingMore || listState.isRefreshing
                    }
                    onClick={controller.loadMore}
                >
                    {listState.isLoadingMore ? "Loading" : "Load more"}
                </Button>
            )}
        </footer>
    );
}

function DefinitionDetailPanel({ controller }: { readonly controller: DefinitionsController }) {
    const [isVersionsOpen, setIsVersionsOpen] = useState(false);
    const versionsButtonRef = useRef<HTMLButtonElement | null>(null);
    const handleCloseVersions = () => {
        setIsVersionsOpen(false);
        window.setTimeout(() => {
            versionsButtonRef.current?.focus();
        }, 0);
    };

    if (controller.selectedKey === null) {
        return (
            <StatePanel
                className="m-4"
                summary="Choose a stored role, policy, or workflow to read current detail."
                title="Select a definition"
                tone="empty"
            />
        );
    }

    if (!controller.isSelectedKeyInRows && !controller.listState.isLoading) {
        return (
            <StatePanel
                className="m-4"
                action={<Button onClick={controller.clearFilters}>Clear filters</Button>}
                summary="The selected key is no longer present in the current kind, query, or filter result. Reread or clear filters before trusting current detail."
                title="Selected definition is stale"
                tone="stale"
            />
        );
    }

    if (controller.detailState.isLoading) {
        return (
            <StatePanel
                className="m-4"
                summary="Reading the selected current stored definition revision."
                title="Loading definition detail"
                tone="loading"
            />
        );
    }

    if (controller.detailState.error !== null) {
        return (
            <StatePanel
                className="m-4"
                action={<Button onClick={controller.refresh}>Retry</Button>}
                summary={controller.detailState.error.summary}
                title={
                    isAuthError(controller.detailState.error)
                        ? "Access to definition detail failed"
                        : "Definition detail could not load"
                }
                tone={isAuthError(controller.detailState.error) ? "auth" : "error"}
            />
        );
    }

    if (controller.detailState.detail === null) {
        return (
            <StatePanel
                className="m-4"
                summary="The current selected definition has no detail payload yet."
                title="No detail selected"
                tone="empty"
            />
        );
    }

    return (
        <div className="space-y-4 p-4">
            <DefinitionDetailHeader
                detail={controller.detailState.detail}
                onOpenVersions={() => {
                    setIsVersionsOpen(true);
                }}
                versionsButtonRef={versionsButtonRef}
            />
            <DefinitionDetailSummary detail={controller.detailState.detail} />
            <DefinitionKindDetail detail={controller.detailState.detail} />
            <DefinitionVersionsModal
                controller={controller}
                detail={controller.detailState.detail}
                isOpen={isVersionsOpen}
                onClose={handleCloseVersions}
            />
        </div>
    );
}

function DefinitionDetailHeader({
    detail,
    onOpenVersions,
    versionsButtonRef,
}: {
    readonly detail: DefinitionDetailView;
    readonly onOpenVersions: () => void;
    readonly versionsButtonRef: RefObject<HTMLButtonElement | null>;
}) {
    return (
        <div className="flex min-h-control flex-wrap items-center justify-end gap-2">
            <Link
                className="inline-flex h-8 items-center justify-center gap-2 rounded-control border border-outline bg-surface px-3 font-body text-compact font-semibold text-foreground transition-colors hover:border-primary/45 hover:text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                to={definitionEditorRoute(detail.kind, detail.key)}
            >
                <span>Edit in draft</span>
                <ExternalLink aria-hidden="true" className="size-3.5 shrink-0" />
            </Link>
            <StatusChip>{detail.kind}</StatusChip>
            <button
                className="inline-flex h-8 items-center justify-center rounded-control border border-outline bg-surface px-3 font-mono text-label font-medium text-foreground transition-colors hover:border-primary/45 hover:text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                onClick={onOpenVersions}
                ref={versionsButtonRef}
                type="button"
            >
                Revision {detail.revisionNo}
            </button>
        </div>
    );
}

function definitionEditorRoute(kind: string, key: string): string {
    const query = new URLSearchParams({
        key,
        kind,
    });
    return `/definitions/editor?${query.toString()}`;
}

function DefinitionDetailSummary({ detail }: { readonly detail: DefinitionDetailView }) {
    return (
        <div className="rounded-card border border-outline-soft bg-surface-low p-4 shadow-hairline">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
                <h2
                    className="min-w-0 break-words font-display text-compact font-semibold text-foreground"
                    id="definitions-detail-heading"
                >
                    {detail.key}
                </h2>
                <StatusChip>
                    <span>Updated</span>
                    <TimestampText value={detail.updatedAt} />
                </StatusChip>
            </div>
            <p className="mt-2 break-words text-compact text-muted">{detail.description}</p>
        </div>
    );
}

function DefinitionKindDetail({ detail }: { readonly detail: DefinitionDetailView }) {
    if (detail.kind === "workflow") {
        return <WorkflowDetail detail={detail} />;
    }

    if (detail.kind === "policy") {
        return (
            <div className="space-y-4">
                <ChipSection
                    emptyLabel="No applies-to values reported."
                    label="Applies to"
                    values={detail.appliesTo.map(formatNodeKind)}
                />
                <PropertyGrid
                    items={[{ label: "Budget", value: formatBudgetSpec(detail.budgetSpec) }]}
                />
                <InstructionSection instruction={detail.instruction} />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <ChipSection
                emptyLabel="No allowed node kinds reported."
                label="Allowed node kinds"
                values={detail.allowedNodeKinds.map(formatNodeKind)}
            />
            <InstructionSection instruction={detail.instruction} />
        </div>
    );
}

function WorkflowDetail({
    detail,
}: {
    readonly detail: Extract<DefinitionDetailView, { kind: "workflow" }>;
}) {
    return (
        <div className="space-y-4">
            <div className="rounded-card border border-outline-soft bg-surface-low p-4">
                <p className="font-mono text-label font-medium uppercase text-muted">Structure</p>
                <div className="mt-3 rounded-card border border-outline-soft bg-surface px-4 py-3">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                        <StatusChip>root</StatusChip>
                        <span className="break-words font-display text-compact font-semibold text-foreground">
                            {detail.root.roleId}
                        </span>
                        <StatusChip>{detail.root.policyId}</StatusChip>
                    </div>
                    <p className="mt-3 max-w-3xl break-words text-compact text-muted">
                        {detail.root.description}
                    </p>
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    <WorkflowMetric label="Children" value={detail.workflowStats.childCount} />
                    <WorkflowMetric label="Leaf roles" value={detail.workflowStats.leafRoleCount} />
                    <WorkflowMetric
                        label="Produced slots"
                        value={detail.workflowStats.producedArtifactCount}
                    />
                </div>
            </div>
            <div className="rounded-card border border-outline-soft bg-surface-low p-4">
                <p className="font-mono text-label font-medium uppercase text-muted">
                    First-level nodes
                </p>
                <ol className="mt-3 space-y-3" aria-label="Workflow first-level nodes">
                    {detail.firstLevelNodes.map((node) => (
                        <WorkflowNodeRow key={node.nodeKey} node={node} />
                    ))}
                </ol>
            </div>
        </div>
    );
}

function WorkflowMetric({ label, value }: { readonly label: string; readonly value: number }) {
    return (
        <div className="rounded-control border border-outline-soft bg-surface px-3 py-3">
            <p className="font-mono text-label font-medium uppercase text-muted">{label}</p>
            <p className="mt-1 font-mono text-utility text-foreground">{value}</p>
        </div>
    );
}

function WorkflowNodeRow({ node }: { readonly node: WorkflowNodeSummary }) {
    return (
        <li className="rounded-card border border-outline-soft bg-surface px-3 py-3">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
                <StatusChip>{node.nodeKey}</StatusChip>
                <span className="break-words font-display text-compact font-semibold text-foreground">
                    {node.roleId}
                </span>
                <StatusChip>{node.policyId}</StatusChip>
            </div>
            <p className="mt-2 break-words text-compact text-muted">{node.description}</p>
            {node.childCount === 0 ? null : (
                <p className="mt-2 text-compact text-muted">
                    {node.childCount === 1
                        ? "1 nested node inside this branch."
                        : `${String(node.childCount)} nested nodes inside this branch.`}
                </p>
            )}
            {node.producedSlots.length === 0 ? null : (
                <div className="mt-2 flex min-w-0 flex-wrap gap-2">
                    {node.producedSlots.map((slot) => (
                        <StatusChip key={slot}>{slot}</StatusChip>
                    ))}
                </div>
            )}
        </li>
    );
}

function ChipSection({
    emptyLabel,
    label,
    values,
}: {
    readonly emptyLabel: string;
    readonly label: string;
    readonly values: readonly string[];
}) {
    return (
        <div className="rounded-card border border-outline-soft bg-surface-low p-4">
            <p className="font-mono text-label font-medium uppercase text-muted">{label}</p>
            {values.length === 0 ? (
                <p className="mt-2 text-compact text-muted">{emptyLabel}</p>
            ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                    {values.map((value) => (
                        <StatusChip key={value}>{value}</StatusChip>
                    ))}
                </div>
            )}
        </div>
    );
}

function InstructionSection({ instruction }: { readonly instruction: string | null }) {
    return (
        <div className="rounded-card border border-outline-soft bg-surface-low p-4">
            <p className="font-mono text-label font-medium uppercase text-muted">Instruction</p>
            <p className="mt-3 whitespace-pre-wrap break-words text-compact text-foreground">
                {formatOptionalInstruction(instruction)}
            </p>
        </div>
    );
}

function DefinitionVersionsModal({
    controller,
    detail,
    isOpen,
    onClose,
}: {
    readonly controller: DefinitionsController;
    readonly detail: DefinitionDetailView;
    readonly isOpen: boolean;
    readonly onClose: () => void;
}) {
    const dialogRef = useRef<HTMLDialogElement | null>(null);
    const titleId = useId();

    useEffect(() => {
        const dialog = dialogRef.current;
        if (dialog === null) {
            return;
        }

        if (isOpen) {
            if (!dialog.open) {
                if (typeof dialog.showModal === "function") {
                    dialog.showModal();
                } else {
                    dialog.setAttribute("open", "");
                }
            }
            return;
        }

        if (dialog.open) {
            if (typeof dialog.close === "function") {
                dialog.close();
            } else {
                dialog.removeAttribute("open");
            }
        }
    }, [isOpen]);

    return (
        <dialog
            aria-labelledby={titleId}
            className="m-auto max-h-[86vh] w-[calc(100%-2rem)] max-w-2xl overflow-hidden rounded-shell border border-outline-soft bg-surface p-0 text-foreground shadow-popover backdrop:bg-black/35"
            onCancel={(event) => {
                event.preventDefault();
                onClose();
            }}
            onClose={onClose}
            ref={dialogRef}
        >
            <header className="flex items-start justify-between gap-4 border-b border-outline-soft bg-surface-muted px-5 py-4">
                <div className="min-w-0">
                    <p className="font-mono text-label font-medium uppercase text-muted">
                        Revisions
                    </p>
                    <h2 className="mt-1 font-display text-compact font-semibold" id={titleId}>
                        Versions
                    </h2>
                    <p className="mt-1 truncate font-mono text-label text-muted">
                        {detail.kind}:{detail.key}
                    </p>
                </div>
                <button
                    aria-label="Close versions"
                    className="inline-flex size-control shrink-0 items-center justify-center rounded-control border border-outline bg-surface-low text-muted transition-colors hover:border-primary/45 hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                    onClick={onClose}
                    type="button"
                >
                    <X aria-hidden="true" className="size-4" />
                </button>
            </header>
            <div className="max-h-[calc(86vh-8rem)] overflow-y-auto px-5 py-4">
                <DefinitionVersionsContent controller={controller} />
            </div>
        </dialog>
    );
}

function DefinitionVersionsContent({ controller }: { readonly controller: DefinitionsController }) {
    const { versionsState } = controller;

    if (versionsState.isLoading) {
        return (
            <StatePanel
                summary="Reading stored revision history for this definition."
                title="Loading versions"
                tone="loading"
            />
        );
    }

    if (versionsState.error !== null) {
        return (
            <StatePanel
                action={<Button onClick={controller.refresh}>Retry</Button>}
                summary={versionsState.error.summary}
                title={
                    isAuthError(versionsState.error)
                        ? "Access to version history failed"
                        : "Version history could not load"
                }
                tone={isAuthError(versionsState.error) ? "auth" : "error"}
            />
        );
    }

    if (versionsState.rows.length === 0) {
        return (
            <StatePanel
                summary="The controller returned no revision history entries for this definition."
                title="No versions"
                tone="empty"
            />
        );
    }

    return (
        <div className="space-y-3">
            {versionsState.rows.length === 1 ? (
                <p className="text-compact text-muted">Single current revision recorded.</p>
            ) : null}
            <ol aria-label="Definition versions" className="space-y-2">
                {versionsState.rows.map((row) => (
                    <DefinitionVersionItem key={row.revisionNo} row={row} />
                ))}
            </ol>
            <div className="flex flex-col gap-3 border-t border-outline-soft pt-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-compact text-muted">
                    {versionsState.nextCursor === null
                        ? "End of current revision history."
                        : "More revisions are available."}
                </p>
                <Button
                    disabled={versionsState.nextCursor === null || versionsState.isLoadingMore}
                    onClick={controller.loadMoreVersions}
                >
                    {versionsState.isLoadingMore ? "Loading" : "Load more versions"}
                </Button>
            </div>
        </div>
    );
}

function DefinitionVersionItem({ row }: { readonly row: DefinitionVersionRow }) {
    return (
        <li className="rounded-card border border-outline-soft bg-surface px-3 py-3">
            <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
                <StatusChip>Revision {row.revisionNo}</StatusChip>
                <TimestampText value={row.updatedAt} />
            </div>
            {row.recordedBy === null ? null : (
                <p className="mt-2 text-compact text-muted">Recorded by: {row.recordedBy}</p>
            )}
        </li>
    );
}

function DefinitionsNavLink({ children, to }: { readonly children: string; readonly to: string }) {
    return (
        <Link
            className="inline-flex h-control items-center justify-center gap-2 rounded-control border border-outline bg-surface-low px-3 text-utility font-semibold text-foreground transition-colors hover:border-primary/45 hover:text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            to={to}
        >
            <span className="min-w-0 truncate">{children}</span>
            <ExternalLink aria-hidden="true" className="size-4 shrink-0" />
        </Link>
    );
}

function formatRowUpdatedDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) {
        return value;
    }

    return new Intl.DateTimeFormat(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
    }).format(date);
}

function formatRowRelativeDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) {
        return "";
    }

    const elapsedMs = Date.now() - date.valueOf();
    const elapsedMinutes = Math.max(0, Math.floor(elapsedMs / 60000));
    if (elapsedMinutes < 60) {
        return elapsedMinutes <= 1 ? "just now" : `${String(elapsedMinutes)} min ago`;
    }

    const elapsedHours = Math.floor(elapsedMinutes / 60);
    if (elapsedHours < 24) {
        return elapsedHours === 1 ? "1 hour ago" : `${String(elapsedHours)} hours ago`;
    }

    const elapsedDays = Math.floor(elapsedHours / 24);
    if (elapsedDays < 7) {
        return elapsedDays === 1 ? "yesterday" : `${String(elapsedDays)} days ago`;
    }

    const elapsedWeeks = Math.floor(elapsedDays / 7);
    if (elapsedWeeks < 5) {
        return elapsedWeeks === 1 ? "1 week ago" : `${String(elapsedWeeks)} weeks ago`;
    }

    const elapsedMonths = Math.floor(elapsedDays / 30);
    if (elapsedMonths < 12) {
        return elapsedMonths <= 1 ? "1 month ago" : `${String(elapsedMonths)} months ago`;
    }

    const elapsedYears = Math.floor(elapsedDays / 365);
    return elapsedYears <= 1 ? "1 year ago" : `${String(elapsedYears)} years ago`;
}

function controlClassName(extraClassName?: string): string {
    return classNames(
        "h-control w-full rounded-control border border-outline bg-surface-low px-4 text-compact text-foreground shadow-hairline transition-colors placeholder:text-muted focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/15",
        extraClassName,
    );
}

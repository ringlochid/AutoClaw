import { ArrowLeft, ArrowRight, RefreshCw } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

import { Button, FormField, StatePanel, StatusChip } from "../../components/ui";
import type { components } from "../../api/generated/openapi";
import { classNames } from "../../lib/classNames";
import { isStaleActionError, type HumanRequestsController } from "./human-request-controller";
import {
    getStructuredSchemaModel,
    type HumanRequestItemDraft,
    type HumanRequestValidationError,
    type StructuredSchemaField,
} from "./human-request-model";

type HumanRequestItem = components["schemas"]["HumanRequestItem"];

const fieldClassName =
    "min-h-control w-full min-w-0 rounded-control border border-outline bg-surface-low px-3 py-2 text-compact text-foreground shadow-hairline transition-colors placeholder:text-muted focus:border-primary";

export function FocusedRequestWorkbench({
    controller,
}: {
    readonly controller: HumanRequestsController;
}) {
    const item = controller.selectedItem;
    const draft = controller.selectedItemDraft;
    const read = controller.selectedRead;
    const headingRef = useRef<HTMLHeadingElement>(null);
    const didMountRef = useRef(false);

    useEffect(() => {
        if (!didMountRef.current) {
            didMountRef.current = true;
            return;
        }

        headingRef.current?.focus();
    }, [item?.item_id]);

    if (item === null || draft === null || read === null) {
        return null;
    }

    const itemErrors = controller.validationErrors.filter((error) => error.itemId === item.item_id);

    return (
        <section className="overflow-hidden rounded-card border border-outline-soft bg-surface shadow-hairline">
            <header className="flex flex-col gap-3 border-b border-outline-soft px-3 py-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                    <SectionLabel>Current item</SectionLabel>
                    <h2
                        className="mt-1 font-mono text-utility text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                        ref={headingRef}
                        tabIndex={-1}
                    >
                        {item.item_id}
                    </h2>
                </div>
                <ItemNavigator controller={controller} itemCount={read.request.items.length} />
            </header>
            <div className="divide-y divide-outline-soft">
                <WorkbenchRow label="Instruction">
                    <p className="text-compact text-foreground">
                        {read.request.suggested_human_instruction}
                    </p>
                </WorkbenchRow>
                <WorkbenchRow label="Question">
                    <p className="text-compact text-foreground">{item.prompt}</p>
                </WorkbenchRow>
                <WorkbenchRow label="Response">
                    <div className="space-y-3">
                        <ResponseControls
                            draft={draft}
                            item={item}
                            onUpdate={controller.updateSelectedItemDraft}
                        />
                        <StructuredInputControls
                            draft={draft}
                            item={item}
                            onUpdate={controller.updateSelectedItemDraft}
                        />
                    </div>
                </WorkbenchRow>
                <WorkbenchRow label="Notes">
                    <textarea
                        aria-label="Notes"
                        className={fieldClassName}
                        id={`notes-${item.item_id}`}
                        onChange={(event) => {
                            controller.updateSelectedItemDraft({
                                extraNotes: event.target.value,
                            });
                        }}
                        placeholder="Add item-scoped caveats or follow-up notes."
                        rows={3}
                        value={draft.extraNotes}
                    />
                </WorkbenchRow>
            </div>
            <div className="px-3 py-3">
                <ValidationAndActionState controller={controller} itemErrors={itemErrors} />
            </div>
        </section>
    );
}

function ItemNavigator({
    controller,
    itemCount,
}: {
    readonly controller: HumanRequestsController;
    readonly itemCount: number;
}) {
    return (
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
                <span className="font-display text-compact font-semibold text-foreground">
                    {String(controller.selectedItemIndex + 1)} of {String(itemCount)}
                </span>
                <div className="flex flex-wrap items-center gap-2">
                    {Array.from({ length: itemCount }, (_item, index) => {
                        const isSelected = index === controller.selectedItemIndex;

                        return (
                            <button
                                aria-label={`Item ${String(index + 1)}`}
                                className={classNames(
                                    "inline-flex h-8 min-w-8 items-center justify-center rounded-control border px-2 font-mono text-utility transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                                    isSelected
                                        ? "border-primary/45 bg-primary-soft text-primary-foreground"
                                        : "border-outline-soft bg-surface-low text-muted hover:border-primary/35 hover:text-foreground",
                                )}
                                key={index}
                                onClick={() => {
                                    controller.selectItemIndex(index);
                                }}
                                type="button"
                            >
                                {String(index + 1)}
                            </button>
                        );
                    })}
                </div>
            </div>
            <div className="flex flex-wrap gap-2">
                <Button
                    disabled={controller.selectedItemIndex === 0}
                    icon={<ArrowLeft />}
                    onClick={() => {
                        controller.selectItemIndex(controller.selectedItemIndex - 1);
                    }}
                    variant="secondary"
                >
                    Previous
                </Button>
                <Button
                    disabled={controller.selectedItemIndex >= itemCount - 1}
                    icon={<ArrowRight />}
                    onClick={() => {
                        controller.selectItemIndex(controller.selectedItemIndex + 1);
                    }}
                    variant="secondary"
                >
                    Next
                </Button>
            </div>
        </div>
    );
}

function ResponseControls({
    draft,
    item,
    onUpdate,
}: {
    readonly draft: HumanRequestItemDraft;
    readonly item: HumanRequestItem;
    readonly onUpdate: (patch: Partial<HumanRequestItemDraft>) => void;
}) {
    return (
        <div className="space-y-3">
            {item.options.length === 0 ? (
                <p className="text-compact text-muted">
                    This item has no listed options. Use freeform answer or structured input.
                </p>
            ) : (
                <fieldset className="space-y-2">
                    <legend className="sr-only">Response options</legend>
                    {item.options.map((option) => (
                        <label
                            className={classNames(
                                "flex cursor-pointer gap-3 rounded-card border p-3 transition-colors",
                                draft.selectedOption === option.id
                                    ? "border-primary/65 bg-primary-soft shadow-panel"
                                    : "border-outline-soft bg-surface-low hover:border-primary/25",
                            )}
                            key={option.id}
                        >
                            <input
                                checked={draft.selectedOption === option.id}
                                className="mt-1 size-4 shrink-0"
                                name={`option-${item.item_id}`}
                                onChange={() => {
                                    onUpdate({
                                        freeformAnswer: "",
                                        selectedOption: option.id,
                                    });
                                }}
                                type="radio"
                            />
                            <span className="min-w-0">
                                <span className="flex min-w-0 flex-wrap items-center gap-2 font-semibold text-foreground">
                                    {option.title}
                                    {item.recommended_option === option.id ? (
                                        <StatusChip tone="active">recommended</StatusChip>
                                    ) : null}
                                </span>
                                {option.description === null ||
                                option.description === undefined ? null : (
                                    <span className="mt-1 block text-compact text-muted">
                                        {option.description}
                                    </span>
                                )}
                            </span>
                        </label>
                    ))}
                </fieldset>
            )}
            <FormField
                hint="Typing here clears any selected listed option for this item."
                id={`freeform-${item.item_id}`}
                label="Freeform answer"
            >
                <textarea
                    className={fieldClassName}
                    onChange={(event) => {
                        onUpdate({
                            freeformAnswer: event.target.value,
                            selectedOption:
                                event.target.value.trim().length > 0 ? null : draft.selectedOption,
                        });
                    }}
                    placeholder="Answer outside the listed options if none fit."
                    rows={3}
                    value={draft.freeformAnswer}
                />
            </FormField>
        </div>
    );
}

function StructuredInputControls({
    draft,
    item,
    onUpdate,
}: {
    readonly draft: HumanRequestItemDraft;
    readonly item: HumanRequestItem;
    readonly onUpdate: (patch: Partial<HumanRequestItemDraft>) => void;
}) {
    const schemaModel = getStructuredSchemaModel(item);
    if (schemaModel === null) {
        return null;
    }

    if (schemaModel.mode === "json") {
        return (
            <FormField id={`payload-${item.item_id}`} label="Structured input">
                <textarea
                    className={classNames(fieldClassName, "font-mono")}
                    onChange={(event) => {
                        onUpdate({ responsePayloadJson: event.target.value });
                    }}
                    rows={5}
                    value={draft.responsePayloadJson}
                />
            </FormField>
        );
    }

    return (
        <div className="space-y-3">
            <SectionLabel>Structured input</SectionLabel>
            <div className="grid gap-3 md:grid-cols-2">
                {schemaModel.fields.map((field) => (
                    <StructuredFieldControl
                        draft={draft}
                        field={field}
                        itemId={item.item_id}
                        key={field.name}
                        onUpdate={onUpdate}
                    />
                ))}
            </div>
        </div>
    );
}

function WorkbenchRow({
    children,
    label,
}: {
    readonly children: ReactNode;
    readonly label: string;
}) {
    return (
        <section className="px-3 py-3">
            <SectionLabel>{label}</SectionLabel>
            <div className="mt-2">{children}</div>
        </section>
    );
}

function StructuredFieldControl({
    draft,
    field,
    itemId,
    onUpdate,
}: {
    readonly draft: HumanRequestItemDraft;
    readonly field: StructuredSchemaField;
    readonly itemId: string;
    readonly onUpdate: (patch: Partial<HumanRequestItemDraft>) => void;
}) {
    const id = `payload-${itemId}-${field.name}`;
    const value = draft.responsePayloadFields[field.name] ?? "";
    const updateValue = (nextValue: string) => {
        onUpdate({
            responsePayloadFields: {
                ...draft.responsePayloadFields,
                [field.name]: nextValue,
            },
        });
    };

    return (
        <FormField
            hint={field.required ? "Required by the provided schema." : "Optional schema field."}
            id={id}
            label={field.title}
        >
            {field.type === "boolean" ? (
                <select
                    className={fieldClassName}
                    onChange={(event) => {
                        updateValue(event.target.value);
                    }}
                    value={value}
                >
                    <option value="">Choose true or false</option>
                    <option value="true">True</option>
                    <option value="false">False</option>
                </select>
            ) : (
                <input
                    className={fieldClassName}
                    onChange={(event) => {
                        updateValue(event.target.value);
                    }}
                    type={field.type === "string" ? "text" : "number"}
                    value={value}
                />
            )}
        </FormField>
    );
}

function ValidationAndActionState({
    controller,
    itemErrors,
}: {
    readonly controller: HumanRequestsController;
    readonly itemErrors: readonly HumanRequestValidationError[];
}) {
    const actionError = controller.actionError;
    const isStaleError = actionError !== null && isStaleActionError(actionError.code);

    return (
        <div className="space-y-3">
            {itemErrors.length === 0 ? null : (
                <StatePanel
                    summary={
                        <ul className="list-disc space-y-1 pl-4">
                            {itemErrors.map((error) => (
                                <li key={`${error.itemId}-${error.message}`}>{error.message}</li>
                            ))}
                        </ul>
                    }
                    title="Response validation failed"
                    tone="stale"
                />
            )}
            {actionError === null ? null : (
                <StatePanel
                    action={
                        isStaleError ? (
                            <Button
                                disabled={controller.isLoading || controller.isRefreshing}
                                icon={
                                    <RefreshCw
                                        className={controller.isRefreshing ? "animate-spin" : ""}
                                    />
                                }
                                onClick={controller.refresh}
                                variant="secondary"
                            >
                                Reread current truth
                            </Button>
                        ) : undefined
                    }
                    summary={
                        <ActionErrorSummary
                            suggestedNextStep={actionError.suggestedNextStep}
                            summary={actionError.summary}
                        />
                    }
                    title={isStaleError ? "Request resolved elsewhere" : "Resolution failed"}
                    tone={isStaleError ? "stale" : "error"}
                />
            )}
        </div>
    );
}

function ActionErrorSummary({
    suggestedNextStep,
    summary,
}: {
    readonly suggestedNextStep: string | null;
    readonly summary: string;
}) {
    return (
        <div className="space-y-2">
            <p>{summary}</p>
            {suggestedNextStep === null ? null : (
                <p>
                    <span className="font-mono text-label font-medium uppercase">
                        Suggested next step
                    </span>{" "}
                    {suggestedNextStep}
                </p>
            )}
        </div>
    );
}

function SectionLabel({ children }: { readonly children: string }) {
    return <p className="font-mono text-label font-medium uppercase text-muted">{children}</p>;
}

import type { components } from "../../api/generated/openapi";

type HumanRequestItem = components["schemas"]["HumanRequestItem"];
type HumanRequestItemResponse = components["schemas"]["HumanRequestItemResponse"];
type HumanRequestRead = components["schemas"]["HumanRequestRead"];
type HumanRequestResolveRequest = components["schemas"]["HumanRequestResolveRequest"];
type PendingHumanRequest = components["schemas"]["PendingHumanRequest"];

export type StructuredFieldType = "boolean" | "integer" | "number" | "string";

export interface HumanRequestQueueItem {
    readonly dueAt: string | null;
    readonly itemCount: number;
    readonly kind: components["schemas"]["HumanRequestKind"];
    readonly openedAt: string;
    readonly requestId: string;
    readonly requesterNode: string;
    readonly status: components["schemas"]["HumanRequestStatus"];
    readonly title: string;
}

export interface HumanRequestItemDraft {
    readonly extraNotes: string;
    readonly freeformAnswer: string;
    readonly responsePayloadFields: Readonly<Partial<Record<string, string>>>;
    readonly responsePayloadJson: string;
    readonly selectedOption: string | null;
}

export interface HumanRequestDraft {
    readonly items: Readonly<Record<string, HumanRequestItemDraft>>;
}

export interface StructuredSchemaField {
    readonly name: string;
    readonly required: boolean;
    readonly title: string;
    readonly type: StructuredFieldType;
}

export interface StructuredSchemaModel {
    readonly fields: readonly StructuredSchemaField[];
    readonly mode: "fields" | "json";
}

export interface HumanRequestValidationError {
    readonly itemId: string;
    readonly message: string;
}

export interface HumanRequestResolveBuildResult {
    readonly errors: readonly HumanRequestValidationError[];
    readonly request: HumanRequestResolveRequest | null;
}

export function mapHumanRequestQueueItem(read: HumanRequestRead): HumanRequestQueueItem {
    const { request } = read;
    return {
        dueAt: request.timeout?.due_at ?? null,
        itemCount: request.items.length,
        kind: request.kind,
        openedAt: request.opened_at,
        requestId: request.request_id,
        requesterNode: request.requester_node,
        status: request.status,
        title: request.title,
    };
}

export function createDraftForRequest(request: PendingHumanRequest): HumanRequestDraft {
    return {
        items: Object.fromEntries(
            request.items.map((item) => [item.item_id, createDraftForItem(item)]),
        ),
    };
}

export function buildResolveRequest(
    request: PendingHumanRequest,
    draft: HumanRequestDraft | undefined,
): HumanRequestResolveBuildResult {
    const errors: HumanRequestValidationError[] = [];
    const itemResponses: HumanRequestItemResponse[] = [];

    for (const item of request.items) {
        const itemDraft = draft?.items[item.item_id] ?? createDraftForItem(item);
        const selectedOption = itemDraft.selectedOption;
        const freeformAnswer = itemDraft.freeformAnswer.trim();
        const extraNotes = emptyToNull(itemDraft.extraNotes.trim());
        const hasSelectedOption = selectedOption !== null;
        const hasFreeformAnswer = freeformAnswer.length > 0;
        const hasOptions = item.options.length > 0;

        if (hasSelectedOption && !item.options.some((option) => option.id === selectedOption)) {
            errors.push({
                itemId: item.item_id,
                message: "Selected option is not available for this request item.",
            });
        }

        if (hasOptions && hasSelectedOption === hasFreeformAnswer) {
            errors.push({
                itemId: item.item_id,
                message: "Choose one listed option or provide one freeform answer.",
            });
        }

        const responsePayload = readResponsePayload(item, itemDraft, errors);

        if (!hasOptions && responsePayload === null && !hasFreeformAnswer) {
            errors.push({
                itemId: item.item_id,
                message: "Provide structured input or a freeform answer for this item.",
            });
        }

        itemResponses.push({
            extra_notes: extraNotes,
            freeform_answer: hasFreeformAnswer ? freeformAnswer : null,
            item_id: item.item_id,
            response_payload: responsePayload,
            selected_option: hasSelectedOption ? selectedOption : null,
        });
    }

    if (errors.length > 0) {
        return { errors, request: null };
    }

    return {
        errors: [],
        request: {
            item_responses: itemResponses,
        },
    };
}

export function getStructuredSchemaModel(item: HumanRequestItem): StructuredSchemaModel | null {
    const schema = item.input_payload_schema;
    if (!isRecord(schema)) {
        return null;
    }

    const properties = isRecord(schema.properties) ? schema.properties : null;
    if (schema.type !== "object" || properties === null) {
        return { fields: [], mode: "json" };
    }

    const requiredFields = Array.isArray(schema.required)
        ? new Set(schema.required.filter((value): value is string => typeof value === "string"))
        : new Set<string>();
    const fields = Object.entries(properties).flatMap(([name, value]): StructuredSchemaField[] => {
        if (!isRecord(value) || !isSupportedFieldType(value.type)) {
            return [];
        }

        return [
            {
                name,
                required: requiredFields.has(name),
                title: typeof value.title === "string" ? value.title : labelFromName(name),
                type: value.type,
            },
        ];
    });

    if (fields.length === 0) {
        return { fields: [], mode: "json" };
    }

    return { fields, mode: "fields" };
}

export function isRequestEditable(read: HumanRequestRead): boolean {
    return read.request.status === "open" && read.resolution === null;
}

export function labelFromKind(kind: components["schemas"]["HumanRequestKind"]): string {
    switch (kind) {
        case "approval":
            return "Approval";
        case "direction":
            return "Direction";
        case "input":
            return "Input";
        case "review":
            return "Review";
    }
}

function createDraftForItem(item: HumanRequestItem): HumanRequestItemDraft {
    const recommendedOptionId = item.recommended_option ?? null;
    const recommendedOption =
        recommendedOptionId !== null &&
        item.options.some((option) => option.id === recommendedOptionId)
            ? recommendedOptionId
            : null;

    return {
        extraNotes: "",
        freeformAnswer: "",
        responsePayloadFields: Object.fromEntries(
            (getStructuredSchemaModel(item)?.fields ?? []).map((field) => [field.name, ""]),
        ),
        responsePayloadJson: "{}",
        selectedOption: recommendedOption,
    };
}

function readResponsePayload(
    item: HumanRequestItem,
    itemDraft: HumanRequestItemDraft,
    errors: HumanRequestValidationError[],
): Record<string, unknown> | null {
    const schemaModel = getStructuredSchemaModel(item);
    if (schemaModel === null) {
        return null;
    }

    if (schemaModel.mode === "json") {
        return readJsonPayload(item.item_id, itemDraft.responsePayloadJson, errors);
    }

    const payload: Record<string, unknown> = {};
    for (const field of schemaModel.fields) {
        const rawValue = (itemDraft.responsePayloadFields[field.name] ?? "").trim();
        if (rawValue.length === 0) {
            if (field.required) {
                errors.push({
                    itemId: item.item_id,
                    message: `${field.title} is required.`,
                });
            }
            continue;
        }

        const parsedValue = parseStructuredFieldValue(field, rawValue);
        if (parsedValue.ok) {
            payload[field.name] = parsedValue.value;
            continue;
        }

        errors.push({
            itemId: item.item_id,
            message: parsedValue.message,
        });
    }

    return payload;
}

function readJsonPayload(
    itemId: string,
    rawJson: string,
    errors: HumanRequestValidationError[],
): Record<string, unknown> | null {
    const trimmedJson = rawJson.trim();
    if (trimmedJson.length === 0) {
        errors.push({
            itemId,
            message: "Structured input must be a JSON object.",
        });
        return null;
    }

    try {
        const parsedValue = JSON.parse(trimmedJson) as unknown;
        if (!isRecord(parsedValue)) {
            errors.push({
                itemId,
                message: "Structured input must parse to a JSON object.",
            });
            return null;
        }

        return parsedValue;
    } catch {
        errors.push({
            itemId,
            message: "Structured input must be valid JSON.",
        });
        return null;
    }
}

function parseStructuredFieldValue(
    field: StructuredSchemaField,
    rawValue: string,
):
    | { readonly ok: true; readonly value: boolean | number | string }
    | { readonly ok: false; readonly message: string } {
    switch (field.type) {
        case "boolean":
            if (rawValue === "true") {
                return { ok: true, value: true };
            }
            if (rawValue === "false") {
                return { ok: true, value: false };
            }
            return { ok: false, message: `${field.title} must be true or false.` };
        case "integer": {
            const numberValue = Number(rawValue);
            if (Number.isInteger(numberValue)) {
                return { ok: true, value: numberValue };
            }
            return { ok: false, message: `${field.title} must be an integer.` };
        }
        case "number": {
            const numberValue = Number(rawValue);
            if (Number.isFinite(numberValue)) {
                return { ok: true, value: numberValue };
            }
            return { ok: false, message: `${field.title} must be a number.` };
        }
        case "string":
            return { ok: true, value: rawValue };
    }
}

function emptyToNull(value: string): string | null {
    return value.length === 0 ? null : value;
}

function labelFromName(name: string): string {
    return name
        .split("_")
        .filter((part) => part.length > 0)
        .map((part) => `${part[0].toUpperCase()}${part.slice(1)}`)
        .join(" ");
}

function isSupportedFieldType(value: unknown): value is StructuredFieldType {
    return value === "boolean" || value === "integer" || value === "number" || value === "string";
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

import type { components } from "../../src/api/generated/openapi";

export const HUMAN_REQUEST_TASK_ID = "task-runtime-copy-refresh";
export const HUMAN_REQUEST_RESOLVED_AT = "2026-06-29T15:45:00Z";

type HumanRequestItem = components["schemas"]["HumanRequestItem"];
type HumanRequestRead = components["schemas"]["HumanRequestRead"];
type HumanRequestResolution = components["schemas"]["HumanRequestResolution"];
type HumanRequestStatus = components["schemas"]["HumanRequestStatus"];
type PendingHumanRequest = components["schemas"]["PendingHumanRequest"];

export function createHumanRequestPageList(): components["schemas"]["HumanRequestListResponse"] {
    return {
        items: [
            createHumanRequestRead({
                items: [
                    createOptionItem({
                        itemId: "due-handling",
                        prompt: "If this request reaches its due time unanswered, what should the controller do?",
                        recommendedOption: "use-fallback",
                        options: [
                            {
                                description:
                                    "Continue with the safe fallback after the due time passes.",
                                id: "use-fallback",
                                title: "Use fallback",
                            },
                            {
                                description: "Leave the request open and wait for a direct answer.",
                                id: "keep-waiting",
                                title: "Keep waiting",
                            },
                            {
                                description:
                                    "Close the human wait and return control to task review.",
                                id: "cancel-wait",
                                title: "Cancel this wait",
                            },
                        ],
                    }),
                    createOptionItem({
                        itemId: "scope-choice",
                        prompt: "Which scope should the worker handle next?",
                        options: [
                            {
                                description: "Keep the change inside the current page slice.",
                                id: "page-only",
                                title: "Page only",
                            },
                            {
                                description: "Route broader shared work to a later scope.",
                                id: "route-later",
                                title: "Route later",
                            },
                        ],
                    }),
                    createOptionItem({
                        itemId: "review-posture",
                        prompt: "What should the reviewer prioritize?",
                        options: [
                            {
                                description:
                                    "Review the focused page behavior and validation proof.",
                                id: "focused-review",
                                title: "Focused review",
                            },
                            {
                                description: "Block the scope and return to the parent.",
                                id: "block-scope",
                                title: "Block scope",
                            },
                        ],
                    }),
                ],
                kind: "direction",
                request_id: "hr-direction",
                requester_node: "handoff_review",
                summary:
                    "Decide how the controller should proceed if no one answers before the due time.",
                timeout: {
                    default_behavior: "Use the safe fallback after the due time.",
                    due_at: "2026-06-29T17:57:00Z",
                },
                title: "Choose due handling",
            }),
            createHumanRequestRead({
                items: [
                    createOptionItem({
                        itemId: "write-approval",
                        prompt: "Should the worker apply the generated file writes?",
                        recommendedOption: "approve",
                        options: [
                            {
                                description: "Allow the generated files to be written.",
                                id: "approve",
                                title: "Approve file write",
                            },
                            {
                                description:
                                    "Reject the write and keep the request open for a safer path.",
                                id: "reject",
                                title: "Reject file write",
                            },
                        ],
                    }),
                ],
                kind: "approval",
                opened_at: "2026-06-29T16:10:00Z",
                request_id: "hr-approval",
                requester_node: "implement_frontend_scope",
                summary: "Approve or reject the proposed file write.",
                timeout: {
                    default_behavior: "Block the write until explicit approval arrives.",
                    due_at: "2026-06-29T18:10:00Z",
                },
                title: "Approve generated file writes",
            }),
            createHumanRequestRead({
                items: [
                    {
                        input_payload_schema: {
                            properties: {
                                allow_follow_up: {
                                    title: "Allow follow up",
                                    type: "boolean",
                                },
                                handoff_title: {
                                    title: "Handoff title",
                                    type: "string",
                                },
                                priority: {
                                    title: "Priority",
                                    type: "integer",
                                },
                            },
                            required: ["handoff_title", "priority"],
                            type: "object",
                        },
                        item_id: "handoff-fields",
                        options: [],
                        prompt: "Provide the structured handoff fields for the next worker.",
                        recommended_option: null,
                    },
                ],
                kind: "input",
                opened_at: "2026-06-29T17:00:00Z",
                request_id: "hr-input",
                requester_node: "implementation_delivery",
                summary: "The next assignment needs structured handoff details.",
                timeout: {
                    default_behavior: "Block until the missing fields are supplied.",
                    due_at: "2026-06-29T19:00:00Z",
                },
                title: "Provide handoff fields",
            }),
            createHumanRequestRead({
                items: [
                    createOptionItem({
                        itemId: "review-result",
                        prompt: "How should the controller treat the validation result?",
                        recommendedOption: "accept",
                        options: [
                            {
                                description: "Accept the validation evidence and continue.",
                                id: "accept",
                                title: "Accept evidence",
                            },
                            {
                                description: "Request focused fixes before continuing.",
                                id: "request-fixes",
                                title: "Request fixes",
                            },
                        ],
                    }),
                ],
                kind: "review",
                opened_at: "2026-06-29T17:30:00Z",
                request_id: "hr-review",
                requester_node: "review_frontend_scope",
                summary: "Review the submitted validation result before release work continues.",
                timeout: {
                    default_behavior: "Return to the reviewer with no acceptance.",
                    due_at: "2026-06-29T19:30:00Z",
                },
                title: "Review validation result",
            }),
            createTerminalHumanRequestRead("resolved"),
            createTerminalHumanRequestRead("timed_out"),
            createTerminalHumanRequestRead("cancelled"),
        ],
        task_id: HUMAN_REQUEST_TASK_ID,
    };
}

export function createHumanRequestRead(
    overrides: Partial<PendingHumanRequest> = {},
    resolution: HumanRequestResolution | null = null,
): HumanRequestRead {
    const requestId = overrides.request_id ?? "hr-direction";
    return {
        request: {
            items: [
                createOptionItem({
                    itemId: "default-item",
                    options: [
                        {
                            description: "Proceed with the focused page implementation.",
                            id: "proceed",
                            title: "Proceed",
                        },
                    ],
                    prompt: "Choose how the worker should continue.",
                    recommendedOption: "proceed",
                }),
            ],
            kind: "direction",
            opened_at: "2026-06-29T15:12:00Z",
            request_id: requestId,
            requester_node: "implement_frontend_scope",
            status: "open",
            suggested_human_instruction:
                "Answer the active item, then resolve the request when the controller can continue without guessing.",
            summary: "Operator input is needed.",
            task_id: HUMAN_REQUEST_TASK_ID,
            timeout: {
                default_behavior: "Block until the operator answers.",
                due_at: "2026-06-29T17:00:00Z",
            },
            title: "Review requested",
            ...overrides,
        },
        resolution,
    };
}

export function createAnsweredHumanRequestResolution(
    request: PendingHumanRequest,
    itemResponses: readonly components["schemas"]["HumanRequestItemResponse"][] = [
        {
            extra_notes: "Evidence accepted.",
            freeform_answer: null,
            item_id: request.items[0]?.item_id ?? "default-item",
            response_payload: null,
            selected_option: request.items[0]?.options[0]?.id ?? null,
        },
    ],
): HumanRequestResolution {
    return {
        item_responses: [...itemResponses],
        request_id: request.request_id,
        resolution_kind: "answered",
        resolved_at: HUMAN_REQUEST_RESOLVED_AT,
        resolved_by_actor_ref: "operator:test",
        task_id: request.task_id,
    };
}

export function createHumanRequestResolveResponse(
    request: PendingHumanRequest,
    itemResponses?: readonly components["schemas"]["HumanRequestItemResponse"][],
): components["schemas"]["HumanRequestResolveResponse"] {
    return {
        resolution: createAnsweredHumanRequestResolution(request, itemResponses),
        task_id: request.task_id,
    };
}

function createOptionItem({
    itemId,
    options,
    prompt,
    recommendedOption = null,
}: {
    readonly itemId: string;
    readonly options: HumanRequestItem["options"];
    readonly prompt: string;
    readonly recommendedOption?: string | null;
}): HumanRequestItem {
    return {
        input_payload_schema: null,
        item_id: itemId,
        options,
        prompt,
        recommended_option: recommendedOption,
    };
}

function createTerminalHumanRequestRead(
    status: Exclude<HumanRequestStatus, "open">,
): HumanRequestRead {
    const request = createHumanRequestRead({
        kind: status === "cancelled" ? "approval" : "review",
        opened_at:
            status === "resolved"
                ? "2026-06-29T13:03:00Z"
                : status === "timed_out"
                  ? "2026-06-29T12:55:00Z"
                  : "2026-06-29T13:41:00Z",
        request_id: `hr-${status}`,
        status,
        summary:
            status === "resolved"
                ? "The validation evidence was accepted by the reviewer."
                : status === "timed_out"
                  ? "The due window elapsed before a direct answer arrived."
                  : "The approval request was withdrawn by task cancellation.",
        title:
            status === "resolved"
                ? "Validation evidence accepted"
                : status === "timed_out"
                  ? "Due window elapsed"
                  : "Write approval withdrawn",
    }).request;

    const resolutionKind = status === "resolved" ? "answered" : status;
    const resolution: HumanRequestResolution = {
        item_responses:
            resolutionKind === "answered"
                ? [
                      {
                          extra_notes: "Reviewer accepted the validation evidence.",
                          freeform_answer: null,
                          item_id: request.items[0]?.item_id ?? "default-item",
                          response_payload: null,
                          selected_option: "proceed",
                      },
                  ]
                : [],
        request_id: request.request_id,
        resolution_kind: resolutionKind,
        resolved_at: HUMAN_REQUEST_RESOLVED_AT,
        resolved_by_actor_ref: resolutionKind === "cancelled" ? "controller" : "operator:test",
        task_id: request.task_id,
    };

    return { request, resolution };
}

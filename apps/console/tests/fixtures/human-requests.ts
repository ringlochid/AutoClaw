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
                        itemId: "due_handling",
                        prompt: "If this request reaches its due time unanswered, what should the controller do?",
                        recommendedOption: "use-fallback",
                        options: [
                            {
                                description:
                                    "Continue with the safe fallback after the due time passes.",
                                id: "use-fallback",
                                title: "Use due fallback",
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
                        itemId: "next_scope",
                        prompt: "What should the next worker handle after this answer?",
                        recommendedOption: "current-request",
                        options: [
                            {
                                description:
                                    "Keep the next pass limited to the human-request branch.",
                                id: "current-request",
                                title: "Current request only",
                            },
                            {
                                description:
                                    "Let the worker verify the surrounding task state before continuing.",
                                id: "whole-task",
                                title: "Whole task check",
                            },
                            {
                                description: "Record the answer but stop before the next dispatch.",
                                id: "pause-after-answer",
                                title: "Pause after answer",
                            },
                        ],
                    }),
                    createOptionItem({
                        itemId: "next_context",
                        prompt: "How much of this answer should be included for the next worker?",
                        recommendedOption: "answer-only",
                        options: [
                            {
                                description:
                                    "Pass the selected answer and item notes without extra operator context.",
                                id: "answer-only",
                                title: "Answer only",
                            },
                            {
                                description:
                                    "Include the request summary so the next worker has local context.",
                                id: "answer-and-summary",
                                title: "Answer and summary",
                            },
                            {
                                description:
                                    "Include all item responses and controller timing fields.",
                                id: "full-thread",
                                title: "Full request thread",
                            },
                        ],
                    }),
                ],
                kind: "direction",
                opened_at: "2026-06-20T19:12:00Z",
                request_id: "direction-due-handling",
                requester_node: "handoff_review",
                summary:
                    "Decide how the controller should proceed if no one answers before the due time.",
                timeout: {
                    default_behavior: "Use the safe fallback after the due time.",
                    due_at: "2026-06-20T19:57:00Z",
                },
                title: "Choose due handling",
            }),
            createHumanRequestRead({
                items: [
                    createOptionItem({
                        itemId: "file_write",
                        prompt: "Can the worker write the generated task artifacts?",
                        recommendedOption: "approve-limited",
                        options: [
                            {
                                description: "Allow the named writes and continue the task.",
                                id: "approve",
                                title: "Approve",
                            },
                            {
                                description:
                                    "Permit only the listed artifacts and reject any extra file changes.",
                                id: "approve-limited",
                                title: "Approve named files only",
                            },
                            {
                                description: "Do not write files until the request is narrowed.",
                                id: "reject",
                                title: "Reject for now",
                            },
                        ],
                    }),
                ],
                kind: "approval",
                opened_at: "2026-06-20T18:49:00Z",
                request_id: "approval-generated-files",
                requester_node: "release_gate",
                summary: "Allow the worker to update the task artifacts named in the request.",
                timeout: {
                    default_behavior: "Block the write until explicit approval arrives.",
                    due_at: "2026-06-20T20:10:00Z",
                },
                title: "Approve generated file writes",
            }),
            createHumanRequestRead({
                items: [
                    {
                        input_payload_schema: {
                            properties: {
                                constraint: {
                                    title: "Constraint",
                                    type: "string",
                                },
                                expected_output: {
                                    title: "Expected output",
                                    type: "string",
                                },
                                target_node: {
                                    title: "Target node",
                                    type: "string",
                                },
                            },
                            required: ["target_node", "expected_output"],
                            type: "object",
                        },
                        item_id: "handoff_payload",
                        options: [],
                        prompt: "Enter the payload the controller should attach to the next dispatch.",
                        recommended_option: null,
                    },
                ],
                kind: "input",
                opened_at: "2026-06-20T18:27:00Z",
                request_id: "input-handoff-fields",
                requester_node: "handoff_prepare",
                summary: "Fill the missing values required before the next dispatch.",
                timeout: {
                    default_behavior: "Block until the missing fields are supplied.",
                    due_at: "2026-06-20T21:00:00Z",
                },
                title: "Provide handoff fields",
            }),
            createHumanRequestRead({
                items: [
                    createOptionItem({
                        itemId: "validation_result",
                        prompt: "Is the latest validation evidence sufficient?",
                        recommendedOption: "request-more-evidence",
                        options: [
                            {
                                description:
                                    "Record the result and let the controller close the request.",
                                id: "accept",
                                title: "Accept evidence",
                            },
                            {
                                description:
                                    "Keep the request open and ask for another validation pass.",
                                id: "request-more-evidence",
                                title: "Request more evidence",
                            },
                            {
                                description:
                                    "Return the task for correction before another review.",
                                id: "reject-evidence",
                                title: "Reject evidence",
                            },
                        ],
                    }),
                ],
                kind: "review",
                opened_at: "2026-06-20T17:58:00Z",
                request_id: "review-validation",
                requester_node: "strict_review",
                summary: "Choose whether the latest checks are enough to close the request.",
                timeout: {
                    default_behavior: "Return to the reviewer with no acceptance.",
                    due_at: "2026-06-20T21:30:00Z",
                },
                title: "Review validation result",
            }),
            createTerminalHumanRequestRead("resolved"),
            createTerminalHumanRequestRead("cancelled"),
            createTerminalHumanRequestRead("timed_out"),
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
        kind: status === "cancelled" ? "approval" : status === "timed_out" ? "direction" : "review",
        opened_at:
            status === "resolved"
                ? "2026-06-20T16:48:00Z"
                : status === "timed_out"
                  ? "2026-06-20T14:10:00Z"
                  : "2026-06-20T15:30:00Z",
        request_id:
            status === "resolved"
                ? "review-evidence-accepted"
                : status === "timed_out"
                  ? "direction-due-elapsed"
                  : "approval-write-cancelled",
        requester_node:
            status === "resolved"
                ? "strict_review"
                : status === "timed_out"
                  ? "handoff_review"
                  : "release_gate",
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
        resolved_at:
            status === "resolved"
                ? "2026-06-20T17:03:00Z"
                : status === "timed_out"
                  ? "2026-06-20T14:55:00Z"
                  : "2026-06-20T15:41:00Z",
        resolved_by_actor_ref: resolutionKind === "cancelled" ? "controller" : "operator:test",
        task_id: request.task_id,
    };

    return { request, resolution };
}

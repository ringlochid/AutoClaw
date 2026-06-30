import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../../src/api/generated/openapi";
import { HumanRequestsPage } from "../../../src/features/human-requests/HumanRequestsPage";
import {
    createBackendOperationFailureBody,
    createRuntimeFlowRead,
} from "../../fixtures/console-api";
import {
    HUMAN_REQUEST_TASK_ID,
    createHumanRequestPageList,
    createHumanRequestResolveResponse,
} from "../../fixtures/human-requests";

const server = setupServer();

beforeAll(() => {
    server.listen({ onUnhandledRequest: "error" });
});

beforeEach(() => {
    vi.stubEnv("VITE_AUTOCLAW_API_BASE_URL", "http://127.0.0.1:18125");
    vi.stubEnv("VITE_AUTOCLAW_API_KEY", "autoclaw-console-test-key");
    server.use(
        http.get("*/control/tasks/:taskId", () =>
            HttpResponse.json(
                createRuntimeFlowRead({
                    task_id: HUMAN_REQUEST_TASK_ID,
                    task_title: "Refresh runtime route copy",
                }),
            ),
        ),
    );
});

afterEach(() => {
    cleanup();
    server.resetHandlers();
    vi.unstubAllEnvs();
});

afterAll(() => {
    server.close();
});

describe("HumanRequestsPage", () => {
    it("resolves a multi-item direction request with per-item response memory", async () => {
        const user = userEvent.setup();
        const requestBodies: components["schemas"]["HumanRequestResolveRequest"][] = [];
        mockHumanRequests({ requestBodies });

        renderHumanRequestsPage();

        expect(
            await screen.findByRole("heading", { name: "Refresh runtime route copy" }),
        ).toBeVisible();
        expect((await screen.findAllByText("Choose due handling")).length).toBeGreaterThan(0);
        expect(screen.getByText("Approve generated file writes")).toBeVisible();
        expect(screen.getByText("Provide handoff fields")).toBeVisible();
        expect(screen.getByText("Review validation result")).toBeVisible();
        expect(screen.getByText("Validation evidence accepted")).toBeVisible();
        expect(
            screen.getByText(
                "Answer the active item, then resolve the request when the controller can continue without guessing.",
            ),
        ).toBeVisible();

        await user.click(screen.getByLabelText(/Use fallback/));
        await user.type(screen.getByLabelText("Notes"), "Use fallback unless a reviewer objects.");
        await user.click(screen.getByRole("button", { name: "Next" }));

        await user.type(
            screen.getByLabelText("Freeform answer"),
            "Keep this inside the page slice.",
        );
        await user.click(screen.getByRole("button", { name: "Next" }));
        await user.click(screen.getByLabelText(/Focused review/));
        await user.click(screen.getByRole("button", { name: "Previous" }));
        await user.click(screen.getByRole("button", { name: "Previous" }));

        expect(screen.getByLabelText(/Use fallback/)).toBeChecked();
        expect(screen.getByLabelText("Notes")).toHaveValue(
            "Use fallback unless a reviewer objects.",
        );

        await user.click(getWorkbenchResolveButton());

        expect(await screen.findByText("Resolved request")).toBeVisible();
        await waitFor(() => {
            expect(requestBodies).toHaveLength(1);
        });
        expect(requestBodies[0]).toEqual({
            item_responses: [
                {
                    extra_notes: "Use fallback unless a reviewer objects.",
                    freeform_answer: null,
                    item_id: "due-handling",
                    response_payload: null,
                    selected_option: "use-fallback",
                },
                {
                    extra_notes: null,
                    freeform_answer: "Keep this inside the page slice.",
                    item_id: "scope-choice",
                    response_payload: null,
                    selected_option: null,
                },
                {
                    extra_notes: null,
                    freeform_answer: null,
                    item_id: "review-posture",
                    response_payload: null,
                    selected_option: "focused-review",
                },
            ],
        });
    });

    it("validates schema-backed input and submits response_payload with notes", async () => {
        const user = userEvent.setup();
        const requestBodies: components["schemas"]["HumanRequestResolveRequest"][] = [];
        mockHumanRequests({ requestBodies });

        renderHumanRequestsPage();

        await user.click(
            within(await screen.findByLabelText("Human request queue")).getByText(
                "Provide handoff fields",
            ),
        );
        await user.click(getWorkbenchResolveButton());

        expect(await screen.findByText("Handoff title is required.")).toBeVisible();
        expect(screen.getByText("Priority is required.")).toBeVisible();

        await user.type(screen.getByLabelText("Handoff title"), "Human request implementation");
        await user.type(screen.getByLabelText("Priority"), "2");
        await user.selectOptions(screen.getByLabelText("Allow follow up"), "true");
        await user.type(screen.getByLabelText("Notes"), "Use the structured handoff as written.");
        await user.click(getWorkbenchResolveButton());

        await waitFor(() => {
            expect(requestBodies).toHaveLength(1);
        });
        expect(requestBodies[0]?.item_responses[0]).toEqual({
            extra_notes: "Use the structured handoff as written.",
            freeform_answer: null,
            item_id: "handoff-fields",
            response_payload: {
                allow_follow_up: true,
                handoff_title: "Human request implementation",
                priority: 2,
            },
            selected_option: null,
        });
        expect(await screen.findByText("Resolved request")).toBeVisible();
        expect(
            await screen.findByText(/"handoff_title": "Human request implementation"/),
        ).toBeVisible();
        expect(screen.getByText(/"allow_follow_up": true/)).toBeVisible();
    });

    it("renders terminal readback and keeps approval rejection as an answer option", async () => {
        const user = userEvent.setup();
        mockHumanRequests();

        renderHumanRequestsPage();

        await user.click(await screen.findByText("Validation evidence accepted"));
        expect(screen.getByText("Resolved request")).toBeVisible();
        expect(screen.getByText("Reviewer accepted the validation evidence.")).toBeVisible();

        await user.click(screen.getByText("Write approval withdrawn"));
        expect(screen.getByText("Cancelled request")).toBeVisible();

        await user.click(screen.getByText("Approve generated file writes"));
        expect(screen.getByLabelText(/Reject file write/)).toBeVisible();
        expect(screen.getAllByText("approval").length).toBeGreaterThan(0);
        expect(
            within(screen.getByLabelText("Human request queue")).getByText(
                "Write approval withdrawn",
            ),
        ).toBeVisible();
    });

    it("surfaces stale resolution conflicts while preserving item context", async () => {
        const user = userEvent.setup();
        const readLog: number[] = [];
        mockHumanRequests({
            readLog,
            resolveStatus: 409,
            resolveBody: createBackendOperationFailureBody({
                code: "stale_flow_revision",
                retryable: true,
                summary: "The request was already resolved by another operator.",
                suggested_next_step: "Reread current human-request truth before retrying.",
            }),
        });

        renderHumanRequestsPage();

        await user.click(await screen.findByText("Approve generated file writes"));
        await user.click(screen.getByLabelText(/Reject file write/));
        await user.click(getWorkbenchResolveButton());

        expect(await screen.findByText("Request resolved elsewhere")).toBeVisible();
        expect(
            screen.getByText("The request was already resolved by another operator."),
        ).toBeVisible();
        expect(
            screen.getByText("Reread current human-request truth before retrying."),
        ).toBeVisible();
        expect(screen.getByLabelText(/Reject file write/)).toBeChecked();

        await user.click(screen.getByRole("button", { name: "Reread current truth" }));

        await waitFor(() => {
            expect(readLog).toHaveLength(2);
        });
        expect(screen.getByLabelText(/Reject file write/)).toBeChecked();
    });

    it("renders empty, auth, and task-detail navigation states", async () => {
        server.use(
            http.get("*/control/tasks/:taskId/human-requests", () =>
                HttpResponse.json({ items: [], task_id: HUMAN_REQUEST_TASK_ID }),
            ),
        );

        const { unmount } = renderHumanRequestsPage();
        expect(await screen.findByText("No human requests")).toBeVisible();
        await userEvent.click(screen.getByRole("link", { name: "Open task detail" }));
        expect(await screen.findByTestId("task-detail-target")).toHaveTextContent(
            HUMAN_REQUEST_TASK_ID,
        );

        unmount();
        cleanup();
        server.resetHandlers();
        server.use(
            http.get("*/control/tasks/:taskId/human-requests", () =>
                HttpResponse.json(
                    createBackendOperationFailureBody({
                        code: "illegal_caller",
                        retryable: false,
                        summary: "The AutoClaw API key is missing or invalid.",
                        suggested_next_step: "Provide a valid operator API key.",
                    }),
                    { status: 401 },
                ),
            ),
        );

        renderHumanRequestsPage();
        expect(await screen.findByText("Access to Human Requests failed")).toBeVisible();
        expect(screen.getByText("The AutoClaw API key is missing or invalid.")).toBeVisible();
    });

    it("renders non-auth read errors as read failures", async () => {
        server.use(
            http.get("*/control/tasks/:taskId/human-requests", () =>
                HttpResponse.json(
                    createBackendOperationFailureBody({
                        code: "internal_error",
                        retryable: true,
                        summary: "The human-request read model is temporarily unavailable.",
                        suggested_next_step: "Retry after the controller read model recovers.",
                    }),
                    { status: 500 },
                ),
            ),
        );

        renderHumanRequestsPage();

        expect(await screen.findByText("Human Requests could not load")).toBeVisible();
        expect(
            screen.getByText("The human-request read model is temporarily unavailable."),
        ).toBeVisible();
    });
});

function renderHumanRequestsPage() {
    return render(
        <MemoryRouter initialEntries={[`/tasks/${HUMAN_REQUEST_TASK_ID}/human-requests`]}>
            <Routes>
                <Route element={<HumanRequestsPage />} path="/tasks/:taskId/human-requests" />
                <Route element={<TaskDetailTarget />} path="/tasks/:taskId" />
            </Routes>
        </MemoryRouter>,
    );
}

function getWorkbenchResolveButton(): HTMLElement {
    const buttons = screen.getAllByRole("button", { name: "Resolve" });
    return buttons[buttons.length - 1];
}

function mockHumanRequests({
    readLog = [],
    requestBodies = [],
    resolveBody,
    resolveStatus = 200,
}: {
    readonly readLog?: number[];
    readonly requestBodies?: components["schemas"]["HumanRequestResolveRequest"][];
    readonly resolveBody?: unknown;
    readonly resolveStatus?: number;
} = {}) {
    const list = createHumanRequestPageList();
    server.use(
        http.get("*/control/tasks/:taskId/human-requests", () => {
            readLog.push(Date.now());
            return HttpResponse.json(list);
        }),
        http.post(
            "*/control/tasks/:taskId/human-requests/:requestId/resolve",
            async ({ params, request }) => {
                const body =
                    (await request.json()) as components["schemas"]["HumanRequestResolveRequest"];
                requestBodies.push(body);
                if (resolveBody !== undefined) {
                    return HttpResponse.json(resolveBody, { status: resolveStatus });
                }

                const requestRead = list.items.find(
                    (item) => item.request.request_id === params.requestId,
                );
                return HttpResponse.json(
                    createHumanRequestResolveResponse(
                        requestRead?.request ?? list.items[0].request,
                        body.item_responses,
                    ),
                );
            },
        ),
    );
}

function TaskDetailTarget() {
    const { taskId } = useParams();

    return <div data-testid="task-detail-target">{taskId}</div>;
}

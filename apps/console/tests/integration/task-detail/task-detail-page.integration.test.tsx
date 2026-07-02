import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../../src/api/generated/openapi";
import { TaskDetailPage } from "../../../src/features/task-detail/TaskDetailPage";
import { createConsoleApiHandlers } from "../../../src/mocks/handlers";
import {
    TEST_API_BASE_URL,
    TEST_API_KEY,
    createBackendOperationFailureBody,
} from "../../fixtures/console-api";
import {
    TASK_DETAIL_STREAM_HEAD,
    TASK_DETAIL_TASK_ID,
    createTaskDetailMockScenario,
} from "../../fixtures/task-detail";

const server = setupServer();

beforeAll(() => {
    server.listen({ onUnhandledRequest: "error" });
});

beforeEach(() => {
    vi.stubEnv("VITE_AUTOCLAW_API_BASE_URL", TEST_API_BASE_URL);
    vi.stubEnv("VITE_AUTOCLAW_API_KEY", TEST_API_KEY);
});

afterEach(() => {
    cleanup();
    server.resetHandlers();
    vi.unstubAllEnvs();
});

afterAll(() => {
    server.close();
});

describe("TaskDetailPage", () => {
    it("bootstraps REST state, backfills through the stream head, merges live SSE, and opens selected detail", async () => {
        const user = userEvent.setup();
        const scenario = createTaskDetailMockScenario();
        const backfillFirstPage = scenario.taskEvents.items.slice(0, 4);
        const backfillSecondPage = [
            scenario.taskEvents.items[3],
            ...scenario.taskEvents.items.slice(4),
        ];
        const seenEventBackfills: URL[] = [];
        const seenStreamUrls: URL[] = [];
        server.use(...createConsoleApiHandlers(scenario));
        server.use(
            http.get("*/control/tasks/:taskId/events", ({ request }) => {
                const requestUrl = new URL(request.url);
                seenEventBackfills.push(requestUrl);
                const cursor = requestUrl.searchParams.get("cursor");
                return HttpResponse.json({
                    ...scenario.taskEvents,
                    items: cursor === "events-page-2" ? backfillSecondPage : backfillFirstPage,
                    next_cursor: cursor === "events-page-2" ? null : "events-page-2",
                } satisfies components["schemas"]["TaskEventListResponse"]);
            }),
            http.get("*/control/tasks/:taskId/events/stream", ({ request }) => {
                seenStreamUrls.push(new URL(request.url));
                return new HttpResponse(
                    scenario.taskEventStream.chunksByCursor[TASK_DETAIL_STREAM_HEAD].join(""),
                    { headers: { "Content-Type": "text/event-stream" } },
                );
            }),
        );

        renderTaskDetailPage();

        expect(screen.getByText("Loading Task Detail")).toBeVisible();
        expect(
            await screen.findByRole("heading", { name: "Refresh runtime route copy" }),
        ).toBeVisible();
        expect(screen.getByText("Execution graph")).toBeVisible();
        expect(screen.getByText("Events")).toBeVisible();
        expect(screen.queryByText("Approve the last copy trim")).not.toBeInTheDocument();
        expect(screen.queryByText("Verify command-run runner behavior.")).not.toBeInTheDocument();
        expect(seenEventBackfills[0]?.searchParams.get("through_event_id")).toBe(
            TASK_DETAIL_STREAM_HEAD,
        );
        expect(seenEventBackfills[1]?.searchParams.get("through_event_id")).toBe(
            TASK_DETAIL_STREAM_HEAD,
        );
        expect(seenEventBackfills.map((url) => url.searchParams.get("cursor"))).toEqual([
            null,
            "events-page-2",
        ]);
        expect(seenStreamUrls[0]?.searchParams.get("cursor")).toBe(TASK_DETAIL_STREAM_HEAD);

        expect(await screen.findByText("Task cancelled")).toBeVisible();
        expect(screen.getByText("Provider event normalized")).toBeVisible();
        expect(screen.getAllByText("Provider event normalized")).toHaveLength(1);
        expect(screen.getAllByText("Checkpoint recorded").length).toBeGreaterThan(0);

        await user.click(screen.getByRole("button", { name: /Checkpoint recorded/i }));
        const openDetailButton = screen.getByRole("button", { name: /Open detail/i });
        await user.click(openDetailButton);

        const dialog = await screen.findByRole("dialog");
        await waitFor(() => {
            expect(within(dialog).getByRole("button", { name: "Close node detail" })).toHaveFocus();
        });
        await user.tab({ shift: true });
        expect(within(dialog).getByRole("link", { name: "Open Command Runs" })).toHaveFocus();
        await user.tab();
        expect(within(dialog).getByRole("button", { name: "Close node detail" })).toHaveFocus();
        expect(
            within(dialog).getByRole("heading", { level: 2, name: "Runtime page contract" }),
        ).toBeVisible();
        expect(within(dialog).getByText("Approve the last copy trim")).toBeVisible();
        expect(within(dialog).getByText("Verify command-run runner behavior.")).toBeVisible();
        expect(within(dialog).getByRole("tab", { name: "Overview" })).toHaveAttribute(
            "aria-selected",
            "true",
        );
        await user.click(within(dialog).getByRole("tab", { name: "Checkpoint" }));
        expect(within(dialog).getByText("Kind")).toBeVisible();
        expect(within(dialog).getByText("progress")).toBeVisible();
        expect(within(dialog).getByText("Checkpoint recorded.")).toBeVisible();
        await user.click(within(dialog).getByRole("tab", { name: "Artifacts" }));
        expect(within(dialog).getByText("frontend_scope_patch")).toBeVisible();
        await user.click(within(dialog).getByRole("tab", { name: "Trace" }));
        expect(within(dialog).getByLabelText("Trace")).toHaveTextContent("checkpoint_recorded");
        await user.keyboard("{Escape}");
        await waitFor(() => {
            expect(openDetailButton).toHaveFocus();
        });
    });

    it("resets REST state and reconnects when the stream cursor is stale", async () => {
        const scenario = createTaskDetailMockScenario();
        const streamCursors: (string | null)[] = [];
        let snapshotReads = 0;
        server.use(...createConsoleApiHandlers(scenario));
        server.use(
            http.get("*/control/tasks/:taskId/snapshot", () => {
                snapshotReads += 1;
                return HttpResponse.json(scenario.snapshot);
            }),
            http.get("*/control/tasks/:taskId/events/stream", ({ request }) => {
                const cursor = new URL(request.url).searchParams.get("cursor");
                streamCursors.push(cursor);
                if (cursor === TASK_DETAIL_STREAM_HEAD) {
                    return HttpResponse.json(
                        createBackendOperationFailureBody({
                            code: "cursor_reset_required",
                            retryable: false,
                            summary: "The task-event cursor is stale.",
                            suggested_next_step: "Reread current task truth.",
                        }),
                        { status: 410 },
                    );
                }

                return new HttpResponse(scenario.taskEventStream.chunks.join(""), {
                    headers: { "Content-Type": "text/event-stream" },
                });
            }),
        );

        renderTaskDetailPage();

        expect(await screen.findByText("Stream cursor reset")).toBeVisible();
        expect(await screen.findByText(/current task truth was reread/i)).toBeVisible();
        expect(await screen.findByText("Task cancelled")).toBeVisible();
        expect(snapshotReads).toBeGreaterThanOrEqual(2);
        expect(streamCursors).toEqual([TASK_DETAIL_STREAM_HEAD, null]);
    });

    it("submits guarded task actions and keeps stale action errors near the controls", async () => {
        const user = userEvent.setup();
        const scenario = createTaskDetailMockScenario();
        const actionQueries: string[] = [];
        server.use(...createConsoleApiHandlers(scenario));
        server.use(
            http.post("*/control/tasks/:taskId/pause", ({ request }) => {
                actionQueries.push(new URL(request.url).searchParams.toString());
                return HttpResponse.json({
                    flow: {
                        ...scenario.taskRead,
                        active_flow_revision_id: "flow-revision-task-detail-2",
                        status: "paused",
                    },
                } satisfies components["schemas"]["RuntimeFlowPauseResponse"]);
            }),
            http.post("*/control/tasks/:taskId/continue", ({ request }) => {
                actionQueries.push(new URL(request.url).searchParams.toString());
                return HttpResponse.json(
                    createBackendOperationFailureBody({
                        field_path: "expected_active_flow_revision_id",
                        summary: "The active flow revision is stale.",
                    }),
                    { status: 409 },
                );
            }),
        );

        renderTaskDetailPage();

        await screen.findByRole("heading", { name: "Refresh runtime route copy" });
        expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
        await user.click(screen.getByRole("button", { name: "Pause" }));
        expect(await screen.findByText("paused")).toBeVisible();
        expect(screen.getByRole("button", { name: "Pause" })).toBeDisabled();
        expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled();
        expect(actionQueries[0]).toBe(
            "expected_active_flow_revision_id=flow-revision-task-detail-1",
        );

        await user.click(screen.getByRole("button", { name: "Continue" }));
        expect(await screen.findByText("Stale action")).toBeVisible();
        expect(screen.getByText("The active flow revision is stale.")).toBeVisible();
        expect(actionQueries[1]).toBe(
            "expected_active_flow_revision_id=flow-revision-task-detail-2",
        );
    });

    it("keeps sibling handoffs as task-scoped navigation instead of embedded pages", async () => {
        const user = userEvent.setup();
        const scenario = createTaskDetailMockScenario();
        server.use(...createConsoleApiHandlers(scenario));

        renderTaskDetailPage();

        await screen.findByRole("heading", { name: "Refresh runtime route copy" });
        expect(
            screen.queryByRole("link", { name: /Open Human Requests/i }),
        ).not.toBeInTheDocument();
        await user.click(screen.getByRole("button", { name: /Open detail/i }));
        const dialog = await screen.findByRole("dialog");
        await user.click(within(dialog).getByRole("link", { name: /Open Human Requests/i }));
        expect(await screen.findByTestId("location")).toHaveTextContent(
            `/tasks/${TASK_DETAIL_TASK_ID}/human-requests`,
        );
    });

    it("renders no-history, read-error, and auth-error states", async () => {
        const noHistoryScenario = createTaskDetailMockScenario({
            events: [],
            streamEvents: [],
            streamHeadEventId: null,
        });
        server.use(...createConsoleApiHandlers(noHistoryScenario));

        const noHistoryView = renderTaskDetailPage();
        expect(await screen.findByText("No event history")).toBeVisible();

        noHistoryView.unmount();
        cleanup();
        server.resetHandlers();
        server.use(
            http.get("*/control/tasks/:taskId", () =>
                HttpResponse.text("Task read failed.", { status: 500 }),
            ),
            http.get("*/control/tasks/:taskId/snapshot", () =>
                HttpResponse.json(noHistoryScenario.snapshot),
            ),
            http.get("*/control/tasks/:taskId/trace", () =>
                HttpResponse.json(noHistoryScenario.trace),
            ),
            http.get("*/control/tasks/:taskId/human-requests", () =>
                HttpResponse.json(noHistoryScenario.humanRequestList),
            ),
            http.get("*/control/tasks/:taskId/command-runs", () =>
                HttpResponse.json(noHistoryScenario.commandRunList),
            ),
        );

        const readErrorView = renderTaskDetailPage();
        expect(await screen.findByText("Task Detail could not load")).toBeVisible();
        expect(screen.getByText("Task read failed.")).toBeVisible();

        readErrorView.unmount();
        cleanup();
        server.resetHandlers();
        server.use(
            ...createConsoleApiHandlers(
                createTaskDetailMockScenario({
                    status: "running",
                }),
            ),
        );
        vi.stubEnv("VITE_AUTOCLAW_API_KEY", "wrong-key");

        renderTaskDetailPage();
        expect(await screen.findByText("Access to Task Detail failed")).toBeVisible();
        expect(screen.getByText("The AutoClaw API key is missing or invalid.")).toBeVisible();
    });
});

function renderTaskDetailPage() {
    return render(
        <MemoryRouter initialEntries={[`/tasks/${TASK_DETAIL_TASK_ID}`]}>
            <Routes>
                <Route element={<TaskDetailPage />} path="/tasks/:taskId" />
                <Route element={<LocationTarget />} path="/tasks/:taskId/human-requests" />
                <Route element={<LocationTarget />} path="/tasks/:taskId/command-runs" />
            </Routes>
        </MemoryRouter>,
    );
}

function LocationTarget() {
    const location = useLocation();

    return <div data-testid="location">{location.pathname}</div>;
}

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../../src/api/generated/openapi";
import { CommandRunsPage } from "../../../src/features/command-runs/CommandRunsPage";
import {
    createBackendOperationFailureBody,
    TEST_API_BASE_URL,
    TEST_API_KEY,
    createRuntimeFlowRead,
} from "../../fixtures/console-api";
import { installTestConsoleConfig } from "../../fixtures/console-config";
import {
    COMMAND_RUN_TASK_ID,
    createCommandRunDetail,
    createCommandRunDetailMap,
    createCommandRunLogRead,
    createCommandRunPageList,
    createCommandRunSecondPage,
} from "../../fixtures/command-runs";

const server = setupServer();

beforeAll(() => {
    server.listen({ onUnhandledRequest: "error" });
});

beforeEach(() => {
    vi.stubEnv("VITE_AUTOCLAW_API_BASE_URL", TEST_API_BASE_URL);
    vi.stubEnv("VITE_AUTOCLAW_API_KEY", TEST_API_KEY);
    installTestConsoleConfig();
});

afterEach(() => {
    cleanup();
    server.resetHandlers();
    installTestConsoleConfig(null);
    vi.unstubAllEnvs();
});

afterAll(() => {
    server.close();
});

describe("CommandRunsPage", () => {
    it("renders every state and keeps logs hidden until requested", async () => {
        mockCommandRuns();
        const user = userEvent.setup();

        renderCommandRunsPage();

        expect(
            await screen.findByRole("heading", { name: "Refresh runtime route copy" }),
        ).toBeVisible();
        expect(screen.getByText("Command Runs")).toBeVisible();
        expect(screen.getByText("Queued")).toBeVisible();
        expect(screen.getByText("Running")).toBeVisible();
        expect(screen.getByText("Cancel requested")).toBeVisible();
        expect(screen.getByText("Succeeded")).toBeVisible();
        expect(screen.getByText("Failed")).toBeVisible();
        expect(screen.getByText("Timed out")).toBeVisible();
        expect(screen.getByText("Cancelled")).toBeVisible();
        expect(screen.queryByText(/continuation context missing terminal/)).not.toBeInTheDocument();

        await user.click(screen.getByText("Check prompt continuation rendering."));

        expect(await screen.findByText("Result")).toBeVisible();
        expect(screen.getByText("Command")).toBeVisible();
        expect(screen.getByText("Timing")).toBeVisible();
        expect(screen.getByText("Provenance")).toBeVisible();
        expect(screen.getByText("Log access")).toBeVisible();
        expect(screen.getByText("Failed")).toBeVisible();
        expect(screen.getByText("1")).toBeVisible();
        expect(screen.queryByText(/continuation context missing terminal/)).not.toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "View logs" }));

        expect(await screen.findByText(/continuation context missing terminal/)).toBeVisible();
        await user.click(screen.getByRole("button", { name: "Hide logs" }));
        expect(screen.queryByText(/continuation context missing terminal/)).not.toBeInTheDocument();
    });

    it("loads more rows and keeps cancel only on cancellable states", async () => {
        mockCommandRuns();
        const user = userEvent.setup();

        renderCommandRunsPage();

        await screen.findByText("Run focused runtime route tests.");
        expect(screen.getAllByRole("button", { name: "Cancel" })).toHaveLength(2);
        expect(screen.getByText("Cancel request accepted.")).toBeVisible();

        await user.click(screen.getByRole("button", { name: "Load more" }));
        expect(await screen.findByText("Check generated OpenAPI drift.")).toBeVisible();
    });

    it("surfaces stale cancel errors near the cancel action", async () => {
        mockCommandRuns({
            cancelStatus: 409,
            cancelBody: createBackendOperationFailureBody({
                code: "illegal_state",
                retryable: true,
                summary: "The command run was already updated by the controller.",
                suggested_next_step: "Reread command-run truth before retrying cancel.",
            }),
        });
        const user = userEvent.setup();

        renderCommandRunsPage();

        await user.click((await screen.findAllByRole("button", { name: "Cancel" }))[0]);

        expect(await screen.findByText("Cancel state changed")).toBeVisible();
        expect(
            screen.getByText("The command run was already updated by the controller."),
        ).toBeVisible();
        expect(screen.getByText("Reread command-run truth before retrying cancel.")).toBeVisible();
    });

    it("renders missing-log, empty, auth, and task-detail navigation states", async () => {
        mockCommandRuns();
        const user = userEvent.setup();

        const { unmount } = renderCommandRunsPage();

        await user.click(await screen.findByText("Retire old proof lane."));
        expect(await screen.findByText("This run does not expose a log ref.")).toBeVisible();
        expect(screen.queryByRole("button", { name: "View logs" })).not.toBeInTheDocument();

        await user.click(screen.getByRole("link", { name: "Open task detail" }));
        expect(await screen.findByTestId("task-detail-target")).toHaveTextContent(
            COMMAND_RUN_TASK_ID,
        );

        unmount();
        cleanup();
        server.resetHandlers();
        server.use(
            http.get("*/control/tasks/:taskId/command-runs", () =>
                HttpResponse.json({ items: [], next_cursor: null, task_id: COMMAND_RUN_TASK_ID }),
            ),
        );
        renderCommandRunsPage();
        expect(await screen.findByText("No command runs")).toBeVisible();

        cleanup();
        server.resetHandlers();
        server.use(
            http.get("*/control/tasks/:taskId/command-runs", () =>
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

        renderCommandRunsPage();
        expect(await screen.findByText("Access to Command Runs failed")).toBeVisible();
        expect(screen.getByText("The AutoClaw API key is missing or invalid.")).toBeVisible();
    });
});

function renderCommandRunsPage() {
    return render(
        <MemoryRouter initialEntries={[`/tasks/${COMMAND_RUN_TASK_ID}/command-runs`]}>
            <Routes>
                <Route element={<CommandRunsPage />} path="/tasks/:taskId/command-runs" />
                <Route element={<TaskDetailTarget />} path="/tasks/:taskId" />
            </Routes>
        </MemoryRouter>,
    );
}

function mockCommandRuns({
    cancelBody,
    cancelStatus = 200,
}: {
    readonly cancelBody?: unknown;
    readonly cancelStatus?: number;
} = {}) {
    const details = createCommandRunDetailMap();
    server.use(
        http.get("*/control/tasks/:taskId/command-runs", ({ request }) => {
            const requestUrl = new URL(request.url);
            const page =
                requestUrl.searchParams.get("cursor") === "cursor-command-runs-page-2"
                    ? createCommandRunSecondPage()
                    : createCommandRunPageList();
            return HttpResponse.json(page);
        }),
        http.get("*/control/tasks/:taskId", ({ params }) =>
            HttpResponse.json(
                createRuntimeFlowRead({
                    task_id: String(params.taskId ?? COMMAND_RUN_TASK_ID),
                    task_title: "Refresh runtime route copy",
                }),
            ),
        ),
        http.get("*/control/tasks/:taskId/command-runs/:runId", ({ params }) =>
            HttpResponse.json(
                details[String(params.runId)] ??
                    createCommandRunDetail(String(params.runId ?? "run-failed")),
            ),
        ),
        http.get("*/control/tasks/:taskId/command-runs/:runId/log", ({ params }) =>
            HttpResponse.json(createCommandRunLogRead(String(params.runId ?? "run-failed"))),
        ),
        http.post("*/control/tasks/:taskId/command-runs/:runId/cancel", ({ params }) => {
            if (cancelBody !== undefined) {
                return HttpResponse.json(cancelBody, { status: cancelStatus });
            }

            return HttpResponse.json({
                run: {
                    ...createCommandRunPageList().items[1],
                    run_id: String(params.runId ?? "run-running"),
                    state: "cancellation_requested",
                    summary: "Cancel request accepted.",
                },
                task_id: COMMAND_RUN_TASK_ID,
            } satisfies components["schemas"]["CommandRunCancelResponse"]);
        }),
    );
}

function TaskDetailTarget() {
    const { taskId } = useParams();

    return <div data-testid="task-detail-target">{taskId}</div>;
}

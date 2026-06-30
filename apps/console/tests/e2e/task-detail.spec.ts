import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

import type { ConsoleMockScenario } from "../../src/mocks/handlers";
import {
    TASK_DETAIL_TASK_ID,
    createLongTaskDetailEventRecords,
    createTaskDetailMockScenario,
} from "../fixtures/task-detail";

const SCREENSHOT_DIR =
    "/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/continuation-implementation/07-task-detail/screenshots";

test("renders the API-backed Task Detail control room at desktop width", async ({
    page,
}, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "desktop proof is captured once");

    await mockTaskDetail(page, createTaskDetailMockScenario());

    await page.goto(`/tasks/${TASK_DETAIL_TASK_ID}`);

    await expect(
        page.getByRole("heading", { level: 1, name: "Refresh runtime route copy" }),
    ).toBeVisible();
    await expect(page.getByText("Execution graph")).toBeVisible();
    await expect(page.getByText("Task event chronology")).toBeVisible();
    await expect(page.getByText("Approve the last copy trim")).toBeVisible();
    await expect(page.getByText("Verify command-run runner behavior.")).toBeVisible();
    await expect(page.getByText("task_cancelled")).toBeVisible();
    await expect(page.getByText("provider_event_normalized")).toBeVisible();
    await expectNoDocumentOverflow(page);

    const accessibilityScanResults = await new AxeBuilder({ page })
        .exclude('a[aria-label="Fixture gallery"]')
        .analyze();
    expect(accessibilityScanResults.violations).toEqual([]);

    await page.screenshot({
        fullPage: true,
        path: `${SCREENSHOT_DIR}/task-detail-desktop.png`,
    });

    await page
        .getByRole("button", { name: /checkpoint_recorded/i })
        .first()
        .click();
    const openDetailButton = page.getByRole("button", { name: "Open detail" });
    await openDetailButton.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Close node detail" })).toBeFocused();
    await expect(dialog.getByText("task_detail_build")).toBeVisible();
    await dialog.getByRole("tab", { name: "Trace" }).click();
    await expect(dialog.getByLabel("Trace")).toContainText("checkpoint_recorded");

    await page.screenshot({
        fullPage: true,
        path: `${SCREENSHOT_DIR}/task-detail-modal-desktop.png`,
    });

    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(openDetailButton).toBeFocused();
});

test("keeps the Task Detail graph and event lane responsive at mobile width", async ({
    page,
}, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-chrome", "mobile proof is captured once");

    await mockTaskDetail(
        page,
        createTaskDetailMockScenario({
            events: createLongTaskDetailEventRecords(),
        }),
    );

    await page.goto(`/tasks/${TASK_DETAIL_TASK_ID}`);

    await expect(
        page.getByRole("heading", { level: 1, name: "Refresh runtime route copy" }),
    ).toBeVisible();
    await expect(page.getByLabel("Zoom in graph")).toBeVisible();
    await expect(page.getByText("worker_node_17").first()).toBeVisible();
    await expect(
        page.getByRole("button", { name: /dispatch_opened worker_node_17/i }),
    ).toBeVisible();
    await expectNoDocumentOverflow(page);

    await page.screenshot({
        fullPage: true,
        path: `${SCREENSHOT_DIR}/task-detail-mobile.png`,
    });
});

async function mockTaskDetail(page: Page, scenario: ConsoleMockScenario): Promise<void> {
    await page.route("**/control/tasks/**", async (route) => {
        const request = route.request();
        const requestUrl = new URL(request.url());
        const path = requestUrl.pathname;

        if (request.method() !== "GET") {
            await fulfillJson(route, scenario.taskRead);
            return;
        }

        if (path.endsWith(`/control/tasks/${TASK_DETAIL_TASK_ID}`)) {
            await fulfillJson(route, scenario.taskRead);
            return;
        }

        if (path.endsWith(`/control/tasks/${TASK_DETAIL_TASK_ID}/snapshot`)) {
            await fulfillJson(route, scenario.snapshot);
            return;
        }

        if (path.endsWith(`/control/tasks/${TASK_DETAIL_TASK_ID}/trace`)) {
            await fulfillJson(route, scenario.trace);
            return;
        }

        if (path.endsWith(`/control/tasks/${TASK_DETAIL_TASK_ID}/events`)) {
            await fulfillJson(route, scenario.taskEvents);
            return;
        }

        if (path.endsWith(`/control/tasks/${TASK_DETAIL_TASK_ID}/events/stream`)) {
            await route.fulfill({
                body: streamBodyForCursor(scenario, requestUrl.searchParams.get("cursor")),
                contentType: "text/event-stream",
            });
            return;
        }

        if (path.endsWith(`/control/tasks/${TASK_DETAIL_TASK_ID}/human-requests`)) {
            await fulfillJson(route, scenario.humanRequestList);
            return;
        }

        if (path.endsWith(`/control/tasks/${TASK_DETAIL_TASK_ID}/command-runs`)) {
            await fulfillJson(route, scenario.commandRunList);
            return;
        }

        await route.fulfill({ status: 404 });
    });
}

async function fulfillJson(route: Route, body: unknown): Promise<void> {
    await route.fulfill({
        body: JSON.stringify(body),
        contentType: "application/json",
    });
}

function streamBodyForCursor(scenario: ConsoleMockScenario, cursor: string | null): string {
    const chunks =
        cursor === null
            ? scenario.taskEventStream.chunks
            : (scenario.taskEventStream.chunksByCursor[cursor] ?? scenario.taskEventStream.chunks);

    return chunks.join("");
}

async function expectNoDocumentOverflow(page: Page): Promise<void> {
    const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );

    expect(overflow).toBeLessThanOrEqual(1);
}

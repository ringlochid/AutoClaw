import { expect, test, type Page } from "@playwright/test";

import {
    createLongRuntimeTaskRow,
    createMixedRuntimeTaskRows,
    createRuntimeFlowSummary,
    createRuntimeFlowSummaryList,
} from "../fixtures/console-api";

test("renders the API-backed Tasks page at desktop width", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "desktop proof is captured once");

    const seenRequests = await mockTaskList(page);

    await page.goto("/tasks");

    await expect(page.getByRole("heading", { level: 1, name: "Tasks" })).toBeVisible();
    await expect(page.getByText("Refresh runtime route copy")).toBeVisible();
    await expect(page.getByText("Fix stale navigation labels")).toBeVisible();
    await expect(page.getByRole("button", { name: "Load more" })).toBeVisible();

    await expectNoDocumentOverflow(page);

    await page.getByLabel("Search").fill("route copy");
    await expect.poll(() => latestQueryValue(seenRequests, "q")).toBe("route copy");

    await page.getByLabel("Status").selectOption("blocked");
    await expect.poll(() => latestQueryValue(seenRequests, "status")).toBe("blocked");

    await page.getByLabel("Sort").selectOption("task_title_asc");
    await expect.poll(() => latestQueryValue(seenRequests, "sort")).toBe("task_title_asc");

    await page.getByRole("button", { name: "Load more" }).click();
    await expect(page.getByText("Review accepted page")).toBeVisible();
    expect(latestQueryValue(seenRequests, "cursor")).toBe("cursor-page-2");

    await page.evaluate(() => {
        window.scrollTo(0, 0);
    });
    const openLink = page.getByRole("link", { name: "Open Refresh runtime route copy" });
    await openLink.focus();
    await expect(openLink).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/tasks\/task-runtime-copy-refresh$/);
});

test("keeps the Tasks page usable without horizontal overflow at mobile width", async ({
    page,
}, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-chrome", "mobile proof is captured once");

    await mockTaskList(page, {
        firstPage: createRuntimeFlowSummaryList([
            createLongRuntimeTaskRow(),
            ...createMixedRuntimeTaskRows().slice(0, 2),
        ]),
    });

    await page.goto("/tasks");

    await expect(page.getByText(/Validate long task title wrapping/)).toBeVisible();
    await expect(page.getByLabel("Search")).toBeVisible();
    await expect(page.getByRole("link", { name: /Open Validate long task title/ })).toBeVisible();
    await expectNoDocumentOverflow(page);

    const openLink = page.getByRole("link", { name: /Open Validate long task title/ });
    await openLink.focus();
    await expect(openLink).toBeFocused();
});

async function mockTaskList(
    page: Page,
    options: {
        readonly firstPage?: ReturnType<typeof createRuntimeFlowSummaryList>;
        readonly secondPage?: ReturnType<typeof createRuntimeFlowSummaryList>;
    } = {},
): Promise<string[]> {
    const seenRequests: string[] = [];
    const firstPage =
        options.firstPage ??
        createRuntimeFlowSummaryList(
            [...createMixedRuntimeTaskRows(), createLongRuntimeTaskRow()],
            "cursor-page-2",
        );
    const secondPage =
        options.secondPage ??
        createRuntimeFlowSummaryList([
            createRuntimeFlowSummary({
                status: "succeeded",
                task_id: "task-second-page",
                task_summary: "Second cursor page.",
                task_title: "Review accepted page",
                updated_at: "2026-06-29T07:00:00Z",
            }),
        ]);

    await page.route("**/runtime/tasks**", async (route) => {
        const requestUrl = new URL(route.request().url());
        seenRequests.push(requestUrl.toString());
        const responseBody =
            requestUrl.searchParams.get("cursor") === "cursor-page-2" ? secondPage : firstPage;

        await route.fulfill({
            body: JSON.stringify(responseBody),
            contentType: "application/json",
        });
    });

    return seenRequests;
}

async function expectNoDocumentOverflow(page: Page): Promise<void> {
    const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );

    expect(overflow).toBeLessThanOrEqual(1);
}

function latestQueryValue(seenRequests: readonly string[], key: string): string | null {
    const latestRequest = seenRequests.at(-1);
    if (latestRequest === undefined) {
        return null;
    }

    return new URL(latestRequest).searchParams.get(key);
}

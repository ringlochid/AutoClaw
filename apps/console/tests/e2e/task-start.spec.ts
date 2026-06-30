/// <reference types="node" />

import { mkdirSync } from "node:fs";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

import {
    createBackendOperationFailureBody,
    createTaskStartResponse,
} from "../fixtures/console-api";
import { createDefinitionSummaryList } from "../fixtures/definitions";
import {
    TASK_START_SCREENSHOT_DIR,
    TASK_START_WORKFLOW_KEY,
    createTaskStartWorkflowDetail,
    createTaskStartWorkflowRows,
    createTaskStartWorkflowVersions,
} from "../fixtures/task-start";

test("starts a task from stored workflow truth at desktop width", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "desktop proof is captured once");

    await mockTaskStart(page);
    await page.goto("/task-start");

    await expect(page.getByRole("heading", { level: 1, name: "Task Start" })).toBeVisible();
    await expect(
        page.getByRole("button", { name: new RegExp(TASK_START_WORKFLOW_KEY) }),
    ).toBeVisible();
    await expectNoDocumentOverflow(page);

    const previewButton = page.getByRole("button", { name: "Preview" });
    await previewButton.focus();
    await expect(previewButton).toBeFocused();
    await previewButton.click();
    await expect(page.getByRole("region", { name: "Preview" })).toBeVisible();
    await expect(page.getByText("Task default").first()).toBeVisible();

    const accessibilityScanResults = await new AxeBuilder({ page })
        .exclude('a[aria-label="Fixture gallery"]')
        .analyze();
    expect(accessibilityScanResults.violations).toEqual([]);

    await page.getByRole("button", { name: "Start Task" }).click();
    await expect(page.getByText("Task start accepted")).toBeVisible();
    await expect(page.getByText("Running")).toBeVisible();
    await expect(page.getByText("task-console-fixture")).toHaveCount(0);
    await expect(page.getByText("compiled-plan-001")).toHaveCount(0);
    await expect(page.getByText("flow-revision-001")).toHaveCount(0);
    await expect(page.getByText("_runtime/workflow-manifest.md")).toHaveCount(0);

    mkdirSync(TASK_START_SCREENSHOT_DIR, { recursive: true });
    await page.evaluate(() => {
        window.scrollTo(0, 0);
    });
    await page.screenshot({
        fullPage: true,
        path: `${TASK_START_SCREENSHOT_DIR}/task-start-desktop.png`,
    });
});

test("keeps Task Start root modes, validation, and layout usable at mobile width", async ({
    page,
}, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-chrome", "mobile proof is captured once");

    await mockTaskStart(page, {
        startFailure: "The selected workspace is already held by a live task.",
    });
    await page.goto("/task-start");

    await expect(page.getByRole("heading", { level: 1, name: "Task Start" })).toBeVisible();
    await expect(
        page.getByRole("button", { name: new RegExp(TASK_START_WORKFLOW_KEY) }),
    ).toBeVisible();
    await expectNoDocumentOverflow(page);

    const workspaceRoot = page.getByRole("region", { name: "Workspace root" });
    await workspaceRoot.getByRole("button", { name: "Create host path" }).click();
    await workspaceRoot.getByLabel("Host path").fill("/tmp/task-start-workspace");

    const contextRoot = page.getByRole("region", { name: "Context root" });
    await contextRoot.getByRole("button", { name: "Use existing host" }).click();
    await contextRoot.getByLabel("Host path").fill("/tmp/task-start-context");

    await page.getByLabel("Task key").fill("");
    await page.getByRole("button", { name: "Start Task" }).click();
    await expect(page.getByText("Task key is required.")).toBeVisible();
    await page.getByLabel("Task key").fill("task-start-mobile-proof");
    await page.getByRole("button", { name: "Start Task" }).click();
    await expect(
        page.getByText("The selected workspace is already held by a live task."),
    ).toBeVisible();
    await expectNoDocumentOverflow(page);

    mkdirSync(TASK_START_SCREENSHOT_DIR, { recursive: true });
    await page.evaluate(() => {
        window.scrollTo(0, 0);
    });
    await page.screenshot({
        fullPage: true,
        path: `${TASK_START_SCREENSHOT_DIR}/task-start-mobile.png`,
    });
});

async function mockTaskStart(
    page: Page,
    options: { readonly startFailure?: string } = {},
): Promise<void> {
    await page.route("http://127.0.0.1:18125/definitions/**", async (route) => {
        const request = route.request();
        const requestUrl = new URL(request.url());
        const path = requestUrl.pathname;

        if (request.method() !== "GET") {
            await route.fulfill({ status: 404 });
            return;
        }

        if (path === "/definitions/workflows") {
            await fulfillJson(
                route,
                createDefinitionSummaryList("workflow", createTaskStartWorkflowRows(), null),
            );
            return;
        }

        if (path.endsWith("/versions")) {
            const key = path.split("/").at(-2) ?? TASK_START_WORKFLOW_KEY;
            await fulfillJson(route, createTaskStartWorkflowVersions(key));
            return;
        }

        const key = path.split("/").at(-1) ?? TASK_START_WORKFLOW_KEY;
        await fulfillJson(route, createTaskStartWorkflowDetail(key));
    });

    await page.route("http://127.0.0.1:18125/tasks/start", async (route) => {
        if (options.startFailure !== undefined) {
            await route.fulfill({
                body: JSON.stringify(
                    createBackendOperationFailureBody({
                        code: "conflicting_continuation",
                        retryable: false,
                        summary: options.startFailure,
                    }),
                ),
                contentType: "application/json",
                status: 409,
            });
            return;
        }

        await fulfillJson(route, createTaskStartResponse());
    });
}

async function fulfillJson(route: Route, body: unknown): Promise<void> {
    await route.fulfill({
        body: JSON.stringify(body),
        contentType: "application/json",
    });
}

async function expectNoDocumentOverflow(page: Page): Promise<void> {
    const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );

    expect(overflow).toBeLessThanOrEqual(1);
}

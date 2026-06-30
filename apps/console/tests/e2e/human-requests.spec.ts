import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

import type { components } from "../../src/api/generated/openapi";
import {
    HUMAN_REQUEST_TASK_ID,
    createHumanRequestPageList,
    createHumanRequestResolveResponse,
} from "../fixtures/human-requests";

const SCREENSHOT_DIR =
    "/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/continuation-implementation/09-human-requests/screenshots";

test("renders and resolves the Human Requests page at desktop width", async ({
    page,
}, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "desktop proof is captured once");

    const requestBodies = await mockHumanRequests(page);

    await page.goto(`/tasks/${HUMAN_REQUEST_TASK_ID}/human-requests`);

    await expect(page.getByRole("heading", { level: 1, name: "Human Requests" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Choose due handling" }).last()).toBeVisible();
    await expect(page.getByText("Approve generated file writes")).toBeVisible();
    await expect(page.getByText("Provide handoff fields")).toBeVisible();
    await expect(page.getByText("Review validation result")).toBeVisible();
    await expect(page.getByText("Validation evidence accepted")).toBeVisible();
    await expectNoDocumentOverflow(page);

    const accessibilityScanResults = await new AxeBuilder({ page })
        .exclude('a[aria-label="Fixture gallery"]')
        .analyze();
    expect(accessibilityScanResults.violations).toEqual([]);

    await page.getByLabel(/Use fallback/).check();
    await page.getByLabel("Notes").fill("Use fallback unless a reviewer objects.");
    await page.getByRole("button", { name: "Next" }).click();
    await page.getByLabel("Freeform answer").fill("Keep this inside the page slice.");
    await page.getByRole("button", { name: "Next" }).click();
    await page.getByLabel(/Focused review/).check();
    await page.getByRole("button", { name: "Previous" }).click();
    await page.getByRole("button", { name: "Previous" }).click();

    await expect(page.getByLabel(/Use fallback/)).toBeChecked();
    await expect(page.getByLabel("Notes")).toHaveValue("Use fallback unless a reviewer objects.");
    await page.evaluate(() => {
        window.scrollTo(0, 0);
    });
    await page.screenshot({
        fullPage: true,
        path: `${SCREENSHOT_DIR}/human-requests-desktop.png`,
    });

    await page.getByRole("button", { exact: true, name: "Resolve" }).click();
    await expect(page.getByText("Resolved request")).toBeVisible();
    await expect.poll(() => requestBodies.length).toBe(1);
    expect(requestBodies[0]?.item_responses.map((response) => response.item_id)).toEqual([
        "due-handling",
        "scope-choice",
        "review-posture",
    ]);

    await page.getByText("Approve generated file writes").click();
    await expect(page.getByLabel("Reject file write")).toBeVisible();
    await page.getByText("Provide handoff fields").click();
    await page.getByRole("button", { exact: true, name: "Resolve" }).click();
    await expect(page.getByText("Handoff title is required.")).toBeVisible();
    await page.getByLabel("Handoff title").fill("Human request implementation");
    await page.getByLabel("Priority").fill("2");
    await page.getByLabel("Allow follow up").selectOption("true");
    await page.getByRole("button", { exact: true, name: "Resolve" }).click();
    await expect.poll(() => requestBodies.length).toBe(2);
    expect(requestBodies[1]?.item_responses[0]?.response_payload).toEqual({
        allow_follow_up: true,
        handoff_title: "Human request implementation",
        priority: 2,
    });
    await expect(page.getByText(/"handoff_title": "Human request implementation"/)).toBeVisible();
    await expect(page.getByText(/"allow_follow_up": true/)).toBeVisible();

    await page.getByText("Due window elapsed").click();
    await expect(page.getByText("Timed out request")).toBeVisible();
    await page.getByText("Write approval withdrawn").click();
    await expect(page.getByText("Cancelled request")).toBeVisible();

    const openTaskDetail = page.getByRole("link", { name: "Open task detail" });
    await openTaskDetail.focus();
    await expect(openTaskDetail).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(new RegExp(`/tasks/${HUMAN_REQUEST_TASK_ID}$`));
});

test("keeps Human Requests responsive at mobile width", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-chrome", "mobile proof is captured once");

    await mockHumanRequests(page);

    await page.goto(`/tasks/${HUMAN_REQUEST_TASK_ID}/human-requests`);

    await expect(page.getByRole("heading", { name: "Choose due handling" }).last()).toBeVisible();
    await expect(page.getByRole("button", { name: "Next" })).toBeVisible();
    await page.getByLabel(/Use fallback/).check();
    await page.getByRole("button", { name: "Next" }).focus();
    await expect(page.getByRole("button", { name: "Next" })).toBeFocused();
    await expectNoDocumentOverflow(page);

    await page.evaluate(() => {
        window.scrollTo(0, 0);
    });
    await page.screenshot({
        fullPage: true,
        path: `${SCREENSHOT_DIR}/human-requests-mobile.png`,
    });
});

type HumanRequestResolveRequest = components["schemas"]["HumanRequestResolveRequest"];

async function mockHumanRequests(page: Page): Promise<HumanRequestResolveRequest[]> {
    const list = createHumanRequestPageList();
    const requestBodies: HumanRequestResolveRequest[] = [];

    await page.route("**/control/tasks/**", async (route) => {
        const request = route.request();
        const requestUrl = new URL(request.url());
        const path = requestUrl.pathname;

        if (
            request.method() === "GET" &&
            path.endsWith(`/${HUMAN_REQUEST_TASK_ID}/human-requests`)
        ) {
            await fulfillJson(route, list);
            return;
        }

        if (request.method() === "POST" && path.includes("/human-requests/")) {
            const requestBody = JSON.parse(
                request.postData() ?? '{"item_responses":[]}',
            ) as (typeof requestBodies)[number];
            requestBodies.push(requestBody);
            const requestId = path.split("/").at(-2);
            const requestRead = list.items.find((item) => item.request.request_id === requestId);
            await fulfillJson(
                route,
                createHumanRequestResolveResponse(
                    requestRead?.request ?? list.items[0].request,
                    requestBody.item_responses,
                ),
            );
            return;
        }

        await route.fulfill({ status: 404 });
    });

    return requestBodies;
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

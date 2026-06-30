/// <reference types="node" />

import { mkdirSync } from "node:fs";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

import type { components } from "../../src/api/generated/openapi";
import {
    DEFINITIONS_SCREENSHOT_DIR,
    POLICY_KEY,
    ROLE_KEY,
    SECOND_ROLE_KEY,
    WORKFLOW_KEY,
    createDefinitionDetailMap,
    createDefinitionSummaryList,
    createDefinitionVersions,
    createDefinitionVersionsMap,
    createPolicyDefinitionRows,
    createRoleDefinitionRows,
    createWorkflowDefinitionRows,
} from "../fixtures/definitions";

test("renders Definitions browse detail, versions, focus, and accessibility at desktop width", async ({
    page,
}, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "desktop proof is captured once");

    await mockDefinitions(page);

    await page.goto("/definitions");

    await expect(page.getByRole("heading", { level: 1, name: "Definitions" })).toBeVisible();
    await expect(definitionRow(page, ROLE_KEY)).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: ROLE_KEY })).toBeVisible();
    await expect(page.getByText("Revision 4").first()).toBeVisible();
    await expectNoDocumentOverflow(page);

    const accessibilityScanResults = await new AxeBuilder({ page })
        .exclude('a[aria-label="Fixture gallery"]')
        .analyze();
    expect(accessibilityScanResults.violations).toEqual([]);

    await page.getByLabel("Allowed node kind").selectOption("worker");
    await expect(definitionRow(page, SECOND_ROLE_KEY)).toBeVisible();

    await page.getByRole("button", { name: "Workflows" }).click();
    await expect(definitionRow(page, WORKFLOW_KEY)).toBeVisible();
    await expect(page.getByText("implement_frontend_scope")).toBeVisible();
    await expect(page.getByLabel("Allowed node kind")).toHaveCount(0);
    await expect(page.getByLabel("Applies to")).toHaveCount(0);
    await expect(
        page.getByLabel("Definitions").getByRole("link", { name: "Task Start" }),
    ).toBeVisible();

    await page.getByText("Versions", { exact: true }).click();
    const versionsList = page.getByRole("list", { name: "Definition versions" });
    await expect(versionsList.getByText("Revision 6")).toBeVisible();
    await expect(versionsList.getByText("Revision 5")).toBeVisible();

    const editorLink = page.getByRole("link", { name: "Definition Editor" }).first();
    await editorLink.focus();
    await expect(editorLink).toBeFocused();

    mkdirSync(DEFINITIONS_SCREENSHOT_DIR, { recursive: true });
    await page.evaluate(() => {
        window.scrollTo(0, 0);
    });
    await page.screenshot({
        fullPage: true,
        path: `${DEFINITIONS_SCREENSHOT_DIR}/definitions-desktop.png`,
    });
});

test("keeps Definitions kind switch, list, detail, and versions usable at mobile width", async ({
    page,
}, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-chrome", "mobile proof is captured once");

    await mockDefinitions(page);

    await page.goto("/definitions");

    await expect(definitionRow(page, ROLE_KEY)).toBeVisible();
    await page.getByRole("button", { name: "Policies" }).click();
    await expect(definitionRow(page, POLICY_KEY)).toBeVisible();
    await expect(page.getByText(/child assignment limit not reported; 2 retries/)).toBeVisible();
    await expectNoDocumentOverflow(page);

    await page.getByText("Versions", { exact: true }).click();
    await expect(page.getByText("Single current revision recorded.")).toBeVisible();
    const versionsSummary = page.locator("summary").filter({ hasText: "Versions" });
    await versionsSummary.focus();
    await expect(versionsSummary).toBeFocused();

    mkdirSync(DEFINITIONS_SCREENSHOT_DIR, { recursive: true });
    await page.evaluate(() => {
        window.scrollTo(0, 0);
    });
    await page.screenshot({
        fullPage: true,
        path: `${DEFINITIONS_SCREENSHOT_DIR}/definitions-mobile.png`,
    });
});

function definitionRow(page: Page, key: string) {
    return page.getByRole("button", { name: new RegExp(key) });
}

async function mockDefinitions(page: Page): Promise<void> {
    const details = createDefinitionDetailMap();
    const versions = createDefinitionVersionsMap();

    await page.route("http://127.0.0.1:18125/definitions/**", async (route) => {
        const request = route.request();
        const requestUrl = new URL(request.url());
        const path = requestUrl.pathname;

        if (request.method() !== "GET") {
            await route.fulfill({ status: 404 });
            return;
        }

        if (path.endsWith("/versions")) {
            const pathParts = path.split("/");
            const kind = (pathParts.at(-3) ?? "role") as components["schemas"]["DefinitionKind"];
            const key = pathParts.at(-2) ?? ROLE_KEY;
            const lookupKey = `${kind}:${key}`;
            await fulfillJson(route, versions[lookupKey] ?? createDefinitionVersions(kind, key));
            return;
        }

        if (path === "/definitions/roles") {
            const roleRows =
                requestUrl.searchParams.get("allowed_node_kind") === "worker"
                    ? createRoleDefinitionRows().filter((row) =>
                          row.allowed_node_kinds?.includes("worker"),
                      )
                    : createRoleDefinitionRows();
            await fulfillJson(route, createDefinitionSummaryList("role", roleRows, null));
            return;
        }

        if (path === "/definitions/policies") {
            await fulfillJson(
                route,
                createDefinitionSummaryList("policy", createPolicyDefinitionRows(), null),
            );
            return;
        }

        if (path === "/definitions/workflows") {
            await fulfillJson(
                route,
                createDefinitionSummaryList("workflow", createWorkflowDefinitionRows(), null),
            );
            return;
        }

        const pathParts = path.split("/");
        const kind = pathParts.at(-2) ?? "role";
        const key = pathParts.at(-1) ?? ROLE_KEY;
        await fulfillJson(route, details[`${kind}:${key}`] ?? details[`role:${ROLE_KEY}`]);
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

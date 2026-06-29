import { expect, test } from "@playwright/test";

test("renders the console shell", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("main", { name: "AutoClaw Console" })).toBeVisible();
});

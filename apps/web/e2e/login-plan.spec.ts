import { expect, test } from "@playwright/test";

test("professional plan is shown on the login page without hydration errors", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  const response = await page.goto("/login?plan=professional");

  expect(response?.status()).toBe(200);
  await expect(page.getByRole("heading", { name: /Start your 14-day free trial/ })).toBeVisible();
  await expect(page.getByText("Professional", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Google account/ })).toBeVisible();
  expect(pageErrors).toEqual([]);
});

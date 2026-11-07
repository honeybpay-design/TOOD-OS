import { expect, test } from "@playwright/test";

test("home page start-free CTA opens login", async ({ page }) => {
  const response = await page.goto("/");

  expect(response?.status()).toBe(200);
  await page.getByRole("link", { name: /Start free/ }).first().click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: /Start your 14-day free trial/ })).toBeVisible();
});

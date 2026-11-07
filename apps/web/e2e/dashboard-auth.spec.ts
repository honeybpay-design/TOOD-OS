import { expect, test } from "@playwright/test";

test("unauthenticated dashboard access returns to login", async ({ page }) => {
  let meStatus: number | undefined;
  page.on("response", (response) => {
    if (new URL(response.url()).pathname === "/api/me") meStatus = response.status();
  });

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("button", { name: /Google account/ })).toBeVisible();
  expect(meStatus).toBe(401);
});

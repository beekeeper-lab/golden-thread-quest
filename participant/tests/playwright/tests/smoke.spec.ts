import { expect, test } from "@playwright/test";

// The smoke test: the one check that proves the project is set up and can reach the app.
test("a visitor sees the Spring Concert and its ticket price on the Tixly home page", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Tixly" })).toBeVisible();
  const event = page.getByRole("article", { name: "Spring Concert" });
  await expect(event.getByText("Tickets from $25.00")).toBeVisible();
  await expect(event.getByText("Service fee: $2.50 per ticket")).toBeVisible();
});

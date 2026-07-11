import { test, expect } from "@playwright/test";

test("the product: taste DNA + eight reasoned recs + mood + share + reload", async ({ page }) => {
  await page.goto("/u/demo");

  // Taste DNA card renders with the written summary and interpreted stats.
  await expect(page.getByText("Taste DNA")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Demo Viewer" })).toBeVisible();
  await expect(page.getByText(/rated films/i)).toBeVisible();

  // Eight recommendation cards stream in, and the reason IS the card (non-empty prose).
  await expect(page.getByRole("heading", { name: "Eight for you" })).toBeVisible();
  const cards = page.locator("main section article");
  await expect(cards).toHaveCount(8);
  for (let i = 0; i < 8; i++) {
    await expect(cards.nth(i).locator("p").first()).not.toBeEmpty();
  }

  // Mood filter is interactive and re-streams without breaking the page.
  await page.getByRole("button", { name: "Dark" }).click();
  await expect(page.getByRole("button", { name: "Dark" })).toHaveClass(/text-accent/);
  await expect(cards).toHaveCount(8);

  // Re-roll re-streams too.
  await page.getByRole("button", { name: "Re-roll" }).click();
  await expect(cards).toHaveCount(8);

  // The URL is the share button.
  await page.getByRole("button", { name: "Share" }).click();
  await expect(page.getByRole("button", { name: "Link copied" })).toBeVisible();

  // Reloading the shared URL loads the same profile.
  await page.reload();
  await expect(page.getByRole("heading", { name: "Demo Viewer" })).toBeVisible();
});

test("the door: upload navigates to a profile route", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Cinerex" })).toBeVisible();

  const csv =
    "Date,Name,Year,Letterboxd URI,Rating\n2024-01-01,The Matrix,1999,https://letterboxd.com/film/the-matrix/,5.0\n";
  await page.setInputFiles('input[type="file"]', {
    name: "ratings.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await page.getByRole("button", { name: /read my taste/i }).click();

  await expect(page).toHaveURL(/\/u\//, { timeout: 20_000 });
});

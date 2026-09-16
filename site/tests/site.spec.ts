import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("renders verified research content without overflow", async ({ page }, testInfo) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/");

  await expect(page.locator("#paper-title")).toContainText("How Much Product Data Is Enough?");
  const primaryResult = page.locator(".hero-result strong");
  await expect(primaryResult).toHaveText("93.6% with core specifications");
  await expect(primaryResult).toBeInViewport();
  await expect(page.getByText("Pilot results and their limits")).toBeVisible();
  await expect(page.getByText("3.310547", { exact: true })).toHaveCount(0);

  const overflows = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflows).toBe(false);
  expect(consoleErrors).toEqual([]);

  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath("research-explainer.png"), fullPage: true });
});

import { test, expect } from "@playwright/test";
import AxeBuilder from "../../apps/web/node_modules/@axe-core/playwright";
import { resolve } from "node:path";

test("investigate, explain, filter, export, and rerun the real inventory workflow", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Every unit. Accounted for." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Inspect / }).first(),
  ).toBeVisible();
  await page.screenshot({
    path: resolve("../../docs/assets/dashboard.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Select AI model", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Refresh models" }),
  ).toBeEnabled();
  await expect(page.getByLabel("AI model", { exact: true })).toHaveValue("");
  await expect(
    page.getByRole("button", { name: "Use selected model" }),
  ).toBeDisabled();
  await page.screenshot({
    path: resolve("../../docs/assets/model-picker.png"),
    fullPage: false,
  });
  const pickerAccessibility = await new AxeBuilder({ page })
    .include("dialog")
    .analyze();
  expect(
    pickerAccessibility.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact || ""),
    ),
  ).toEqual([]);
  await page.getByRole("button", { name: "Close panel" }).click();
  await page.getByRole("button", { name: /^Exceptions/ }).click();
  await page.getByLabel("Filter exception type").selectOption("variance");
  await expect(page.locator("tbody tr")).toHaveCount(20);
  await page
    .getByRole("button", { name: /Inspect / })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Opening count", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Explain finding" }).click();
  await expect(page.getByText("deterministic", { exact: true })).toBeVisible();
  await expect(page.getByText(/Next action: verify count/)).toBeVisible();
  await page.screenshot({
    path: resolve("../../docs/assets/evidence.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Close panel" }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  expect((await download).suggestedFilename()).toBe("consignai-exceptions.csv");
  await page.getByLabel("Search records").fill("does-not-exist");
  await expect(page.getByText("No matching records")).toBeVisible();
  await page.getByRole("button", { name: "Run analysis", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Analysis complete");
  expect(errors).toEqual([]);
});

test("local model selection is explicit, sent to the API, clearable, and forgotten on reload", async ({
  page,
}) => {
  // Only discovery is stubbed: the real API must reject this nonexistent model
  // into a visible deterministic fallback, without substituting any installed model.
  await page.route("**/api/v1/ai/models", (route) =>
    route.fulfill({
      json: {
        runtime: "ollama",
        status: "available",
        excluded_count: 0,
        message: "Test discovery fixture",
        models: [
          {
            name: "fixture-only-model:small",
            size_bytes: 1024 ** 3,
            digest: "test",
            parameter_size: "1B",
            quantization: "Q4",
          },
        ],
      },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Select AI model", exact: true })
    .click();
  await expect(page.getByLabel("AI model", { exact: true })).toHaveValue("");
  await page
    .getByLabel("AI model", { exact: true })
    .selectOption("fixture-only-model:small");
  await page.getByRole("button", { name: "Use selected model" }).click();
  await page
    .getByRole("button", { name: /Inspect / })
    .first()
    .click();
  const sent = page.waitForRequest(
    (r) => r.url().includes("/commands/explain/") && r.method() === "POST",
  );
  await page.getByRole("button", { name: "Explain finding" }).click();
  expect((await sent).postDataJSON()).toEqual({
    model: "fixture-only-model:small",
  });
  await expect(
    page.getByText("deterministic fallback", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/no other model was used/)).toBeVisible();
  await page.getByRole("button", { name: "Close panel" }).click();
  await page.getByRole("button", { name: "Change AI model" }).click();
  await page.getByRole("button", { name: "Use without AI" }).click();
  await expect(
    page.getByText("No model selected", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Select AI model", exact: true })
    .click();
  await page
    .getByLabel("AI model", { exact: true })
    .selectOption("fixture-only-model:small");
  await page.getByRole("button", { name: "Use selected model" }).click();
  await page.reload();
  await expect(
    page.getByText("No model selected", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Inspect / })
    .first()
    .click();
  const withoutModel = page.waitForRequest(
    (r) => r.url().includes("/commands/explain/") && r.method() === "POST",
  );
  await page.getByRole("button", { name: "Explain finding" }).click();
  expect((await withoutModel).postDataJSON()).toEqual({ model: null });
  await expect(page.getByText("deterministic", { exact: true })).toBeVisible();
});

test("invalid upload produces a visible validation report and keeps the ledger unchanged", async ({
  page,
  request,
}) => {
  const before = (
    await (await request.get("http://127.0.0.1:8077/api/v1/overview")).json()
  ).dataset_version;
  await page.goto("/#Data%20%26%20imports");
  await page.getByLabel("Choose inventory file").setInputFiles({
    name: "invalid.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from('{"record_type":"snapshot","on_hand":-3}'),
  });
  await page.getByRole("button", { name: "Validate & import" }).click();
  await expect(
    page.getByRole("heading", { name: "Batch rejected" }),
  ).toBeVisible();
  const after = (
    await (await request.get("http://127.0.0.1:8077/api/v1/overview")).json()
  ).dataset_version;
  expect(after).toBe(before);
});

test("redistribution and mobile navigation render without page overflow", async ({
  page,
}) => {
  await page.goto("/#Redistribution");
  await expect(page.locator(".transfer-card").first()).toBeVisible();
  await expect(
    page.getByText("recipient capacity", { exact: true }).first(),
  ).toBeVisible();
  await page.screenshot({
    path: resolve("../../docs/assets/redistribution.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Every unit. Accounted for." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: resolve("../../docs/assets/mobile.png"),
    fullPage: true,
  });
});

test("overview has no serious or critical accessibility violations", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: /Inspect / }).first(),
  ).toBeVisible();
  const result = await new AxeBuilder({ page }).analyze();
  expect(
    result.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    ),
  ).toEqual([]);
});

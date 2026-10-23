// Local/test stack only. Outputs contain public media metrics and rule IDs,
// never authentication state, account details, or raw axe DOM snippets.
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { chromium, expect } from "@playwright/test";
import { clerkSetup } from "@clerk/testing/playwright";

for (const name of [".env.e2e.local", ".env.local", ".env"])
  if (existsSync(name)) process.loadEnvFile(name);
const { helperSignIn, sessionRequest, API } = await import("../e2e/auth-helpers.ts");
const phase = process.argv[2];
if (!["before", "after"].includes(phase) || process.env.PHASE8_ISOLATED !== "1")
  throw new Error("Use before/after and PHASE8_ISOLATED=1 with a dedicated test stack");
await mkdir("phase8-artifacts", { recursive: true });
await mkdir("../docs/phase8", { recursive: true });
const axeSource = await readFile(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf8");
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH, chromiumSandbox: true });
const metrics = { performance: [], accessibility: [] };
await clerkSetup({ dotenv: false });
async function scan(page, name) {
  if (["light-owner-upload", "dark-public-explore", "light-owner-delete-dialog", "dark-owner-edit"].includes(name)) {
    await page.screenshot({
      path: `../docs/phase8/${name}.jpg`, type: "jpeg", quality: 82,
      fullPage: name !== "light-owner-delete-dialog",
      animations: "disabled", mask: [page.locator(".cl-userButtonTrigger")], maskColor: "#626d64",
    });
  }
  await page.addScriptTag({ content: axeSource });
  const results = await page.evaluate(async () => {
    const result = await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"] } });
    return {
      violations: result.violations.map(rule => ({ id: rule.id, impact: rule.impact, count: rule.nodes.length, selectors: rule.nodes.map(node => node.target) })),
      incomplete: result.incomplete.map(rule => ({ id: rule.id, count: rule.nodes.length })),
      passes: result.passes.length,
    };
  });
  metrics.accessibility.push({ name, ...results });
  console.log("Accessibility " + name + ": " + results.violations.length + " violated rules");
}
try {
  const posts = await (await fetch(API + "/posts?sort=oldest")).json();
  for (const size of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    const context = await browser.newContext({ baseURL: "http://localhost:3000", viewport: size, deviceScaleFactor: 1, reducedMotion: "reduce" });
    const page = await context.newPage();
    const responses = [];
    page.on("response", async response => {
      if (response.request().resourceType() !== "image" || !response.url().startsWith(API + "/uploads/")) return;
      const pending = response.finished().then(async () => ({ path: new URL(response.url()).pathname, status: response.status(), bytes: (await response.body()).length }));
      responses.push(pending);
    });
    for (const route of ["/explore", `/posts/${posts.find(post => post.file_type === "image/jpeg").id}`]) {
      responses.length = 0;
      await page.goto(route);
      await expect(page.locator("main img").first()).toBeVisible();
      for (const image of await page.locator("main img").all()) {
        await image.scrollIntoViewIfNeeded();
        await image.evaluate(node => node.decode());
      }
      const images = await page.locator("main img").evaluateAll(nodes => nodes.map(node => ({ path: new URL(node.currentSrc).pathname, width: node.naturalWidth, height: node.naturalHeight, lazy: node.loading })));
      const resources = await page.evaluate(() => performance.getEntriesByType("resource").filter(entry => entry.initiatorType === "img").map(entry => ({ path: new URL(entry.name).pathname, durationMs: Math.round(entry.duration) })));
      const coldPayloads = async paths => page.evaluate(async ({ api, paths }) => {
        return Promise.all(paths.map(async path => {
          const response = await fetch(api + path, { cache: "no-store" });
          return { path, status: response.status, bytes: (await response.arrayBuffer()).byteLength };
        }));
      }, { api: API, paths });
      const originals = route === "/explore" ? posts.map(post => post.url) : [posts.find(post => post.file_type === "image/jpeg").url];
      const coldOriginals = await coldPayloads(originals);
      const coldSelected = await coldPayloads(images.map(image => image.path));
      metrics.performance.push({ viewport: size.width, page: route.startsWith("/posts/") ? "detail" : "explore", images, responses: await Promise.all(responses), resources, coldOriginals, coldSelected });
    }
    await context.close();
  }
  for (const theme of ["light", "dark"]) {
    const context = await browser.newContext({ baseURL: "http://localhost:3000", viewport: { width: 390, height: 844 }, reducedMotion: "reduce", colorScheme: theme });
    await context.addInitScript(value => localStorage.setItem("theme", value), theme);
    const page = await context.newPage();
    for (const [name, route, ready] of [["home", "/", ".photo-card"], ["explore", "/explore", ".photo-card"], ["detail", `/posts/${posts[0].id}`, ".detail-image img"], ["protected", "/upload", ".state-panel"], ["sign-in", "/sign-in", "input[name=identifier]"], ["sign-up", "/sign-up", "input[name=emailAddress]"]]) {
      await page.goto(route);
      await expect(page.locator(ready).first()).toBeVisible();
      await scan(page, `${theme}-public-${name}`);
    }
    await helperSignIn(page, process.env.E2E_USER_EMAIL);
    for (const [name, route, ready] of [["upload", "/upload", ".post-form"], ["gallery-empty", "/me", ".state-panel"]]) {
      await page.goto(route);
      await expect(page.locator(".cl-userButtonTrigger")).toBeVisible();
      await expect(page.locator(ready)).toBeVisible();
      await scan(page, `${theme}-owner-${name}`);
    }
    // Create and remove only this run's real post; captions avoid account details.
    await page.goto("/upload");
    await expect(page.locator(".post-form")).toBeVisible();
    await page.getByLabel("Image", { exact: true }).setInputFiles("../demo/sample_sunset.jpg");
    await page.getByLabel("Caption").fill("Sunlight over the hills at the end of the day.");
    const created = page.waitForResponse(r => r.url() === API + "/posts" && r.request().method() === "POST");
    await page.getByRole("button", { name: "Share image" }).click();
    const response = await created;
    expect(response.status()).toBe(201);
    const post = await response.json();
    try {
      await expect(page.locator(".owner-actions")).toBeVisible();
      await scan(page, `${theme}-owner-detail-success`);
      await page.getByRole("button", { name: "Delete", exact: true }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await scan(page, `${theme}-owner-delete-dialog`);
      await page.keyboard.press("Escape");
      await page.goto(`/posts/${post.id}/edit`);
      await expect(page.locator(".post-form")).toBeVisible();
      await scan(page, `${theme}-owner-edit`);
      await page.getByLabel("Replace image", { exact: true }).setInputFiles({ name: "invalid.txt", mimeType: "text/plain", buffer: Buffer.from("invalid") });
      await expect(page.locator("#upload-error")).toBeVisible();
      await scan(page, `${theme}-owner-form-error`);
    } finally {
      expect([200, 404]).toContain((await sessionRequest(page, `/posts/${post.id}`, "DELETE")).status);
    }
    await context.close();
  }
  await writeFile(`phase8-artifacts/${phase}.json`, JSON.stringify(metrics, null, 2));
  console.log("Saved sanitized " + phase + " audit metrics");
} finally {
  await browser.close();
}

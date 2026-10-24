// Run only against the isolated API/database documented in docs/UX_AUDIT.md.
// No storage state, credentials, traces, or Clerk account UI are saved.
import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium, expect } from "@playwright/test";
import { clerkSetup } from "@clerk/testing/playwright";
import { auditAccessibility } from "../e2e/accessibility.ts";

for (const name of [".env.e2e.local", ".env.local", ".env"])
  if (existsSync(name)) process.loadEnvFile(name);
const { helperSignIn, sessionRequest, API } = await import("../e2e/auth-helpers.ts");
const BASE = "http://localhost:3000";
const phase = process.argv[2] ?? "before";
if (!['empty', 'before', 'after', 'cleanup'].includes(phase) || process.env.UX_AUDIT_ISOLATED !== "1")
  throw new Error("Set UX_AUDIT_ISOLATED=1 and use empty/before/after/cleanup on a dedicated test stack");
const root = path.resolve(process.env.UX_AUDIT_OUTPUT ?? "ux-audit-artifacts");
const output = path.join(root, phase);
await mkdir(output, { recursive: true });
const stateFile = path.join(root, "posts.json");
const state = existsSync(stateFile) ? JSON.parse(await readFile(stateFile, "utf8")) : { ids: [] };
const results = [];
await clerkSetup({ dotenv: false });
const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
  chromiumSandbox: true,
});
const sizes = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
];
const caption = "The city slows down at sunset. A quiet moment, shared from my own perspective.";
const longCaption = "A moment worth keeping. ".repeat(80).trim();

async function contextFor(size, theme, signedIn = false) {
  const context = await browser.newContext({ viewport: size, baseURL: BASE, colorScheme: theme, reducedMotion: "reduce" });
  await context.addInitScript((value) => {
    localStorage.setItem("theme", value);
  }, theme);
  const page = await context.newPage();
  if (signedIn) await helperSignIn(page, process.env.E2E_USER_EMAIL);
  return { context, page };
}

async function capture(page, name, { images = true } = {}) {
  await page.evaluate(() => document.fonts.ready);
  if (images) {
    for (const img of await page.locator("main img").all()) {
      await img.scrollIntoViewIfNeeded();
      await img.evaluate((node) => node.decode());
    }
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  const metrics = await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement);
    const toggle = document.querySelector('.theme-toggle')?.getBoundingClientRect();
    const error = document.querySelector('.delete-dialog[open] .error-banner, .post-form .error-banner');
    return {
      width: innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
      h1Count: document.querySelectorAll('main h1').length,
      themeTarget: toggle ? { width: toggle.width, height: toggle.height } : null,
      errorColor: error ? getComputedStyle(error).color : null,
      colors: Object.fromEntries(['background', 'surface', 'soft', 'foreground', 'muted', 'accent', 'error'].map(k => [k, style.getPropertyValue('--' + k).trim()])),
      overflowElements: [...document.querySelectorAll('main *, header *')].filter(el => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && (r.right > innerWidth + 1 || r.left < -1) && getComputedStyle(el).position !== 'absolute';
      }).slice(0, 8).map(el => ({ tag: el.tagName, class: el.className })),
    };
  });
  metrics.accessibility = await auditAccessibility(page);
  expect(metrics.horizontalOverflow).toBe(false);
  await page.screenshot({
    path: path.join(output, name + ".jpg"),
    type: "jpeg", quality: 78, fullPage: true, animations: "disabled",
    mask: [page.locator(".cl-userButtonTrigger")], maskColor: "#657067",
  });
  results.push({ name, ...metrics });
  console.log("Captured " + phase + "/" + name);
}

async function visit(page, url, ready) {
  await page.goto(url);
  // Identity changes recreate the query provider; wait for that commit first.
  await expect(page.locator(".cl-userButtonTrigger")).toBeVisible();
  await expect(page.locator(ready).first()).toBeVisible();
}

try {
  if (phase === "cleanup") {
    const { context, page } = await contextFor(sizes[0], "light", true);
    for (const id of state.ids) {
      const response = await sessionRequest(page, `/posts/${id}`, "DELETE");
      expect([200, 404]).toContain(response.status);
    }
    await context.close();
    await writeFile(stateFile, JSON.stringify({ ids: [] }));
    console.log("Removed only this audit's uploaded posts");
  } else if (phase === "empty") {
    for (const size of [sizes[0], sizes[2]]) for (const theme of ["light", "dark"]) {
      const { context, page } = await contextFor(size, theme, true);
      for (const [name, url] of [["home", "/"], ["explore", "/explore"], ["gallery", "/me"]]) {
        await visit(page, url, ".state-panel");
        await capture(page, `${size.name}-${theme}-${name}-empty`);
      }
      await context.close();
    }
  } else {
    if (!state.ids.length) {
      if (phase === "after" && !existsSync(path.join(root, "before", "metrics.json")))
        throw new Error("Capture before evidence first");
      const { context, page } = await contextFor(sizes[0], "light", true);
      await visit(page, "/upload", ".post-form");
      await page.getByLabel("Image", { exact: true }).setInputFiles(path.resolve("../demo/sample_sunset.jpg"));
      await page.getByLabel("Caption").fill(caption);
      const created = page.waitForResponse(r => r.url() === `${API}/posts` && r.request().method() === "POST");
      await page.getByRole("button", { name: "Share image" }).click();
      const response = await created;
      expect(response.status()).toBe(201);
      const post = await response.json();
      state.ids.push(post.id);
      await writeFile(stateFile, JSON.stringify(state));
      await expect(page.locator(".success-banner")).toBeVisible();
      await capture(page, "desktop-light-upload-success");
      await context.close();
    }
    const id = state.ids[0];
    for (const size of sizes) for (const theme of ["light", "dark"]) {
      const { context, page } = await contextFor(size, theme, true);
      for (const [name, url, ready] of [
        ["home", "/", ".photo-card"], ["explore", "/explore", ".photo-card"],
        ["detail", `/posts/${id}`, ".owner-actions"], ["upload", "/upload", ".post-form"],
        ["gallery", "/me", ".photo-card"], ["edit", `/posts/${id}/edit`, ".post-form"],
      ]) {
        await visit(page, url, ready);
        await capture(page, `${size.name}-${theme}-${name}`);
      }
      if (size.name === "mobile") {
        await page.getByLabel("Caption").fill(longCaption);
        await page.getByRole("button", { name: "Save changes" }).click();
        await expect(page.locator(".success-banner")).toBeVisible();
        await capture(page, `mobile-${theme}-long-caption`);
        if (phase === "after") {
          await page.locator(".post-caption summary").focus();
          await page.keyboard.press("Enter");
          await expect(page.locator(".post-caption p")).toHaveText(longCaption);
          await capture(page, `mobile-${theme}-expanded-caption`);
        }
        await visit(page, `/posts/${id}/edit`, ".post-form");
        await page.getByLabel("Caption").fill(caption);
        await page.getByRole("button", { name: "Save changes" }).click();
        await expect(page.locator(".success-banner")).toBeVisible();

        await page.getByRole("button", { name: "Delete", exact: true }).click();
        await expect(page.getByRole("dialog")).toBeVisible();
        await capture(page, `mobile-${theme}-delete-dialog`);
        const blockDelete = url => url.origin === new URL(API).origin && url.pathname === `/posts/${id}`;
        await page.route(blockDelete, route => route.request().method() === "DELETE" ? route.abort("failed") : route.continue());
        await page.getByRole("button", { name: "Delete post", exact: true }).click();
        await expect(page.locator(".delete-dialog .error-banner")).toBeVisible();
        await capture(page, `mobile-${theme}-delete-error`);
        await page.unroute(blockDelete);
        await page.getByRole("button", { name: "Keep image" }).click();

        await visit(page, "/upload", ".post-form");
        await page.getByLabel("Image", { exact: true }).setInputFiles(path.resolve("../demo/sample_city.png"));
        await page.getByRole("button", { name: "Share image" }).click();
        await expect(page.locator(".post-form .error-banner")).toBeVisible();
        await capture(page, `mobile-${theme}-upload-error`);

        await visit(page, "/me", ".photo-card");
        await page.getByLabel("Format").selectOption("image/png");
        await expect(page.locator(".state-panel")).toBeVisible();
        await capture(page, `mobile-${theme}-filter-empty`);

        const galleryRequest = url => url.origin === new URL(API).origin && url.pathname === "/posts";
        let release;
        const gate = new Promise(resolve => { release = resolve; });
        await page.route(galleryRequest, async route => { await gate; await route.continue(); });
        try {
          await page.goto("/explore");
          await expect(page.locator(".skeleton-card").first()).toBeVisible();
          await capture(page, `mobile-${theme}-loading`, { images: false });
        } finally { release(); }
        await expect(page.locator(".photo-card").first()).toBeVisible();
        await page.unroute(galleryRequest);
        await page.route(galleryRequest, route => route.abort("failed"));
        await page.reload();
        await expect(page.getByRole("heading", { name: "That didn’t quite work." })).toBeVisible();
        await capture(page, `mobile-${theme}-gallery-error`);
        await page.unroute(galleryRequest);
        await page.getByRole("button", { name: "Try again" }).click();
        await expect(page.locator(".photo-card").first()).toBeVisible();
      }
      await context.close();
    }
  }
  await writeFile(path.join(output, "metrics.json"), JSON.stringify(results, null, 2));
  console.log(`Completed ${results.length} captures; credentials and session state were not saved`);
} finally {
  await browser.close();
}

// Read-only public audit. Use a dedicated local E2E stack seeded with real
// landscape, portrait and square images, JPEG/PNG results and no WebP posts.
// Successful responses always come from FastAPI; only failures/delays are injected.
import { mkdir, writeFile } from "node:fs/promises";
import { chromium, expect } from "@playwright/test";
import { auditAccessibility } from "../e2e/accessibility.ts";

const phase = process.argv[2];
if (!["before", "after"].includes(phase) || process.env.EDITORIAL_AUDIT_ISOLATED !== "1")
  throw new Error("Use before/after and EDITORIAL_AUDIT_ISOLATED=1 with a dedicated local stack");
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
if (![baseURL, api].every(value => ["localhost", "127.0.0.1"].includes(new URL(value).hostname)))
  throw new Error("Audit targets must be local");
const posts = await (await fetch(`${api}/posts?limit=100`)).json();
const dense = process.env.EDITORIAL_AUDIT_DENSE === "1";
if (posts.length !== (dense ? 15 : 3) || (!dense && posts.some(post => !post.image)) || posts.some(post => post.file_type === "image/webp"))
  throw new Error("Expected the dedicated three-image or fifteen-image JPEG/PNG fixture set");
const visibleCount = Math.min(posts.length, 12);
const output = `../docs/editorial-gallery/${phase}${dense ? "-dense" : ""}`;
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH, chromiumSandbox: true });
const metrics = [];
const galleryRequest = url => url.origin === new URL(api).origin && url.pathname === "/posts";
try {
  for (const [device, width, height] of [["desktop", 1440, 1000], ["tablet", 768, 1024], ["mobile", 390, 844]]) {
    for (const theme of ["light", "dark"]) {
      const context = await browser.newContext({ baseURL, viewport: { width, height }, deviceScaleFactor: 1, colorScheme: theme, reducedMotion: "reduce" });
      await context.addInitScript(value => localStorage.setItem("theme", value), theme);
      const page = await context.newPage();
      let pageErrors = 0;
      page.on("pageerror", () => pageErrors++);
      async function capture(state, { images = true, accessibility = true } = {}) {
        if (images) {
          for (const img of await page.locator("main img").all()) {
            await img.scrollIntoViewIfNeeded();
            await img.evaluate(node => node.decode());
          }
        }
        await page.evaluate(() => window.scrollTo(0, 0));
        const layout = await page.evaluate(() => ({
          overflow: document.documentElement.scrollWidth > innerWidth,
          headings: document.querySelectorAll("main h1").length,
          frames: [...document.querySelectorAll(".photo-card")].map(node => {
            const frame = node.querySelector(".photo-frame").getBoundingClientRect();
            const img = node.querySelector("img");
            return { width: frame.width, height: frame.height, fit: getComputedStyle(img).objectFit, lazy: img.loading, variants: !!node.querySelector("source"), nameLength: node.getAttribute("aria-label").length };
          }),
          targets: [...document.querySelectorAll("main select, main button")].map(node => ({ width: node.getBoundingClientRect().width, height: node.getBoundingClientRect().height })),
        }));
        expect(layout.overflow).toBe(false);
        expect(layout.headings).toBe(1);
        expect(layout.targets.every(target => target.width >= 44 && target.height >= 44)).toBe(true);
        const axe = accessibility ? await auditAccessibility(page) : null;
        await page.screenshot({ path: `${output}/${device}-${theme}-${state}.jpg`, type: "jpeg", quality: 85, fullPage: true, animations: "disabled" });
        metrics.push({ device, width, height, theme, state, ...layout, axe, pageErrors });
      }
      await page.goto("/explore");
      await expect(page.locator(".photo-card")).toHaveCount(visibleCount);
      await capture("explore");
      if (phase === "after") {
        await expect(page.getByRole("navigation", { name: "Gallery pagination" })).toHaveCount(dense ? 1 : 0);
        // Actual keyboard events follow the same order as the backend's posts.
        await page.getByLabel("Sort by").focus();
        for (const post of posts.slice(0, visibleCount)) {
          await page.keyboard.press("Tab");
          await expect(page.locator(":focus")).toHaveAttribute("href", `/posts/${post.id}`);
          expect(await page.locator(":focus").evaluate(node => parseFloat(getComputedStyle(node).outlineWidth))).toBeGreaterThanOrEqual(3);
        }
      }
      if (phase === "before" && theme === "light" && device !== "mobile") {
        // Compare native-ratio grid and column masonry on identical real images.
        for (const card of await page.locator(".photo-card").all()) {
          const id = (await card.getAttribute("href")).split("/").at(-1);
          const { width, height } = posts.find(post => post.id === id).image ?? { width: 4, height: 3 };
          await card.locator(".photo-frame").evaluate((node, ratio) => { node.style.aspectRatio = ratio; }, `${width}/${height}`);
        }
        await capture("alternative-natural-grid", { accessibility: false });
        const style = await page.addStyleTag({ content: `.photo-grid { display:block; columns:${device === "desktop" ? 3 : 2}; column-gap:24px; } .photo-card { break-inside:avoid; margin-bottom:32px; }` });
        await capture("alternative-columns", { accessibility: false });
        await style.evaluate(node => node.remove());
        await page.reload();
        await expect(page.locator(".photo-card")).toHaveCount(visibleCount);
      }
      if (dense) {
        if (device === "desktop") {
          await page.getByRole("button", { name: "Next", exact: false }).click();
          await expect(page.getByText("Page 2", { exact: true })).toBeVisible();
          await expect(page.locator(".photo-card")).toHaveCount(3);
          await capture("page-two");
        }
        expect(pageErrors).toBe(0);
        await context.close();
        console.log(`${phase}: ${device} ${theme}, dense gallery checked`);
        continue;
      }
      await page.getByLabel("Format").selectOption("image/png");
      await expect(page.locator(".photo-card")).toHaveCount(1);
      await capture("filtered");
      await page.getByLabel("Format").selectOption("image/webp");
      await expect(page.getByRole("heading", { name: "No images in this format yet." })).toBeVisible();
      await capture("empty");
      await page.getByRole("button", { name: "Clear format filter" }).click();
      await expect(page.locator(".photo-card")).toHaveCount(3);
      let release;
      const gate = new Promise(resolve => { release = resolve; });
      await page.route(galleryRequest, async route => { await gate; await route.continue(); });
      try {
        await page.reload({ waitUntil: "domcontentloaded" });
        await expect(page.getByRole("status", { name: "Loading images" })).toBeVisible();
        await capture("loading", { images: false });
      } finally { release(); }
      await expect(page.locator(".photo-card")).toHaveCount(3);
      await page.unroute(galleryRequest);
      // Freeze real image requests AFTER real metadata arrives to test reserved boxes.
      let releaseImages;
      const imageGate = new Promise(resolve => { releaseImages = resolve; });
      const mediaRequest = url => url.origin === new URL(api).origin && url.pathname.startsWith("/uploads/");
      await page.route(mediaRequest, async route => { await imageGate; await route.continue(); });
      try {
        await page.reload({ waitUntil: "domcontentloaded" });
        await expect(page.locator(".photo-card")).toHaveCount(3);
        const boxes = () => page.locator(".photo-frame").evaluateAll(nodes => nodes.map(node => ({ width: node.getBoundingClientRect().width, height: node.getBoundingClientRect().height, top: node.getBoundingClientRect().top + scrollY })));
        const reserved = await boxes();
        releaseImages();
        for (const img of await page.locator("main img").all()) {
          await img.scrollIntoViewIfNeeded();
          await img.evaluate(node => node.decode());
        }
        expect(await boxes()).toEqual(reserved);
      } finally { releaseImages(); await page.unroute(mediaRequest); }
      await page.route(galleryRequest, route => route.abort("failed"));
      await page.reload({ waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { name: "That didn’t quite work." })).toBeVisible();
      await capture("error", { images: false });
      await page.unroute(galleryRequest);
      await page.getByRole("button", { name: "Try again" }).click();
      await expect(page.locator(".photo-card")).toHaveCount(3);
      expect(pageErrors).toBe(0);
      await context.close();
      console.log(`${phase}: ${device} ${theme}, real images and all states checked`);
    }
  }
  await writeFile(`${output}/metrics.json`, JSON.stringify(metrics, null, 2));
} finally { await browser.close(); }

/** Genuine staging sessions only. No local .env loading, Clerk test helpers or traces. */
import { chromium, expect } from "@playwright/test";
import { createHash, randomUUID } from "node:crypto";
import { mkdir, lstat, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { createInterface } from "node:readline/promises";
import { pathToFileURL } from "node:url";

export function origin(value) {
  const url = new URL(value);
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash ||
      url.pathname !== "/" || /^(localhost|127\.|\[::1\])/.test(url.hostname))
    throw new Error("Explicit HTTPS staging origin required");
  return url.origin;
}

export function mediaGroup(value, media) {
  const url = new URL(value);
  if (url.origin !== media || url.username || url.password || url.search || url.hash ||
      !/^\/pixshare\/staging\/[a-f0-9]{32}\/original\.(jpg|png|webp)$/.test(url.pathname))
    throw new Error("Unexpected staging media namespace");
  return url.pathname.slice(1, url.pathname.lastIndexOf("/") + 1);
}

function check(condition) { if (!condition) throw new Error("Smoke assertion failed"); }
const hash = bytes => createHash("sha256").update(bytes).digest("hex");

async function main() {
  const command = process.argv[2];
  if (!command || command === "--help") {
    console.log("Commands: public, bootstrap-owner, bootstrap-other, crud, persistence, cleanup. Requires --approved-staging and explicit STAGING_WEB_URL, STAGING_API_URL, STAGING_MEDIA_URL. Run from web/; see deployment plan.");
    return;
  }
  check(["public", "bootstrap-owner", "bootstrap-other", "crud", "persistence", "cleanup"].includes(command));
  check(process.argv.includes("--approved-staging"));
  const web = origin(process.env.STAGING_WEB_URL);
  const api = origin(process.env.STAGING_API_URL);
  const media = origin(process.env.STAGING_MEDIA_URL);
  check(new Set([web, api, media]).size === 3);
  const root = resolve("staging-artifacts");
  await mkdir(root, { recursive: true, mode: 0o700 });
  const info = await lstat(root);
  check(info.isDirectory() && !info.isSymbolicLink() && !(info.mode & 0o077));
  const binding = { web, api, media };
  const save = (name, data, exclusive = true) => writeFile(`${root}/${name}.json`, JSON.stringify(data, null, 2), { mode: 0o600, flag: exclusive ? "wx" : "w" });
  const load = async name => {
    const path = `${root}/${name}.json`;
    const stat = await lstat(path);
    check(stat.isFile() && !stat.isSymbolicLink() && !(stat.mode & 0o077));
    return JSON.parse(await readFile(path, "utf8"));
  };
  try { check(JSON.stringify(await load("target")) === JSON.stringify(binding)); }
  catch (error) { if (error.code !== "ENOENT") throw error; await save("target", binding); }
  const results = [];
  const record = name => { results.push({ name, status: "PASS" }); console.log(`PASS ${name}`); };
  const browser = await chromium.launch({ headless: !command.startsWith("bootstrap-") });
  async function context(role) {
    const state = await load(role);
    return browser.newContext({ baseURL: web, storageState: state });
  }
  // JWT stays inside the real browser. Never attach an auth header to another origin.
  async function apiRequest(page, route, method = "GET", caption) {
    return page.evaluate(async ({ api, route, method, caption }) => {
      const token = await window.Clerk?.session?.getToken();
      if (!token) throw new Error("Real sign-in required");
      const body = caption === undefined ? undefined : new FormData();
      if (body) body.set("caption", caption);
      const response = await fetch(`${api}${route}`, { method, body, headers: { Authorization: `Bearer ${token}` } });
      return { status: response.status, data: await response.json() };
    }, { api, route, method, caption });
  }
  async function publicRead(url) {
    const response = await browser.request.get(url);
    check(response.status() === 200);
    return response;
  }
  async function verifyMedia(page, post) {
    mediaGroup(post.url, media);
    check(post.image?.variants?.length > 0);
    const image = page.locator(".detail-image img");
    await expect(image).toBeVisible();
    await expect.poll(() => image.evaluate(node => node.complete && node.naturalWidth > 0)).toBe(true);
    const current = await image.evaluate(node => node.currentSrc);
    check(post.image.variants.some(variant => variant.url === current));
    const response = await publicRead(current);
    check(response.headers()["content-type"]?.startsWith("image/webp"));
    return { originalSha256: hash(await (await publicRead(post.url)).body()), variantBytes: (await response.body()).length };
  }
  try {
    if (command === "public") {
      const ctx = await browser.newContext({ baseURL: web });
      const page = await ctx.newPage();
      for (const path of ["/health", "/ready", "/posts"]) await publicRead(`${api}${path}`);
      check((await browser.request.get(`${api}/users/me`)).status() === 401);
      const preflight = await browser.request.fetch(`${api}/posts`, { method: "OPTIONS", headers: { Origin: web, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type" } });
      check(preflight.ok() && preflight.headers()["access-control-allow-origin"] === web);
      for (const width of [1440, 768, 390]) {
        await page.setViewportSize({ width, height: 900 });
        for (const path of ["/", "/explore"]) {
          check((await page.goto(path))?.ok());
          await expect(page.locator("main")).toBeVisible();
          await expect(page.getByRole("heading", { level: 1 })).toContainText(path === "/" ? "Your photographs, together" : "Browse photographs");
          check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        }
      }
      record("Public HTTPS, readiness, unauthenticated boundary, CORS and layouts");
    } else if (command.startsWith("bootstrap-")) {
      const role = command.slice(10);
      const ctx = await browser.newContext({ baseURL: web });
      const page = await ctx.newPage();
      const started = Date.now();
      const prompt = createInterface({ input: process.stdin, output: process.stdout });
      try {
        await page.goto("/sign-up");
        await prompt.question("Create a NEW dedicated staging account in the browser using real email verification; then press Enter here. Never enter credentials in this terminal. ");
        await expect(page.locator(".cl-userButtonTrigger")).toBeVisible();
        check(await page.evaluate(time => new Date(window.Clerk.user.createdAt).getTime() >= time - 60000, started));
        check((await apiRequest(page, "/users/me")).status === 200);
        record(`${role}: real verified sign-up`);
        await page.locator(".cl-userButtonTrigger").click();
        await page.getByRole("button", { name: /Sign out$/i }).click();
        await expect.poll(() => page.evaluate(() => Boolean(window.Clerk?.session))).toBe(false);
        await page.waitForURL(url => url.pathname === "/");
        await page.goto("/me");
        await expect(page.getByRole("heading", { name: "Make yourself at home." })).toBeVisible();
        record(`${role}: UI logout and protected gallery`);
        await page.goto("/sign-in");
        await prompt.question("Sign in again in the browser with this staging account; then press Enter here. ");
        await expect(page.locator(".cl-userButtonTrigger")).toBeVisible();
        check((await apiRequest(page, "/users/me")).status === 200);
        await save(role, await ctx.storageState());
        record(`${role}: real sign-in, private session saved`);
      } finally { prompt.close(); }
    } else {
      const owner = await context("owner");
      const page = await owner.newPage();
      await page.goto("/me");
      const identity = await apiRequest(page, "/users/me");
      check(identity.status === 200);
      if (command === "crud") {
        // Reserve a recovery journal BEFORE creating data; never overwrite an earlier run.
        const checkpoint = { ...binding, ownerId: identity.data.id, id: null, groups: [], deleted: false };
        await save("checkpoint", checkpoint);
        const caption = `Staging smoke ${randomUUID()}`;
        await page.goto("/upload");
        const png = await page.evaluate(() => {
          const canvas = document.createElement("canvas"); canvas.width = 1600; canvas.height = 900;
          const c = canvas.getContext("2d"); c.fillStyle = "#135c82"; c.fillRect(0, 0, 1600, 900);
          c.fillStyle = "#ffcc33"; c.fillRect(300, 100, 500, 500); return canvas.toDataURL().split(",")[1];
        });
        await page.getByLabel("Image", { exact: true }).setInputFiles({ name: "staging-smoke.png", mimeType: "image/png", buffer: Buffer.from(png, "base64") });
        await page.getByLabel("Caption").fill(caption);
        const created = page.waitForResponse(r => r.url() === `${api}/posts` && r.request().method() === "POST");
        await page.getByRole("button", { name: "Share image" }).click();
        const response = await created; check(response.status() === 201);
        const original = await response.json();
        checkpoint.id = original.id;
        // Save the row identifier even if the next media assertion fails.
        await save("checkpoint", checkpoint, false);
        checkpoint.groups.push(mediaGroup(original.url, media));
        await save("checkpoint", checkpoint, false);
        await expect(page.getByRole("heading", { name: caption, exact: true })).toBeVisible();
        const originalMetrics = await verifyMedia(page, original);
        record("UI upload and optimized S3/CDN variants");
        await page.getByRole("link", { name: "Edit post" }).click();
        await page.getByLabel("Caption").fill(`${caption} edited`);
        await page.getByRole("button", { name: "Save changes" }).click();
        await expect(page.getByRole("heading", { name: `${caption} edited`, exact: true })).toBeVisible();
        await page.getByRole("link", { name: "Edit post" }).click();
        const replacementPng = await page.evaluate(() => {
          const canvas = document.createElement("canvas"); canvas.width = 1200; canvas.height = 900;
          const c = canvas.getContext("2d"); c.fillStyle = "#842451"; c.fillRect(0, 0, 1200, 900);
          return canvas.toDataURL().split(",")[1];
        });
        await page.getByLabel("Replace image", { exact: true }).setInputFiles({ name: "replacement.png", mimeType: "image/png", buffer: Buffer.from(replacementPng, "base64") });
        const replacing = page.waitForResponse(r => r.url() === `${api}/posts/${checkpoint.id}` && r.request().method() === "PATCH");
        await page.getByRole("button", { name: "Save changes" }).click();
        const replaced = await replacing; check(replaced.status() === 200);
        const post = await replaced.json(); check(post.url !== original.url);
        checkpoint.groups.push(mediaGroup(post.url, media));
        checkpoint.post = post;
        await save("checkpoint", checkpoint, false);
        await expect(page.locator(".owner-actions")).toBeVisible();
        checkpoint.metrics = await verifyMedia(page, post);
        check(checkpoint.metrics.originalSha256 !== originalMetrics.originalSha256);
        await save("checkpoint", checkpoint, false);
        record("Caption editing and immutable image replacement");
        const other = await context("other");
        const otherPage = await other.newPage(); await otherPage.goto(`/posts/${post.id}`);
        const second = await apiRequest(otherPage, "/users/me");
        check(second.status === 200 && second.data.id !== identity.data.id);
        await expect(otherPage.getByRole("link", { name: "Edit post" })).toHaveCount(0);
        for (const method of ["PATCH", "DELETE"]) check((await apiRequest(otherPage, `/posts/${post.id}`, method, method === "PATCH" ? "forbidden" : undefined)).status === 403);
        check(JSON.stringify((await apiRequest(page, `/posts/${post.id}`)).data) === JSON.stringify(post));
        record("Two real accounts: denied mutation and unchanged owner data");
      } else {
        const checkpoint = await load("checkpoint");
        check(checkpoint.ownerId === identity.data.id && checkpoint.id && !checkpoint.deleted);
        if (command === "persistence") {
          const response = await apiRequest(page, `/posts/${checkpoint.id}`);
          check(response.status === 200 && JSON.stringify(response.data) === JSON.stringify(checkpoint.post));
          await page.goto(`/posts/${checkpoint.id}`);
          const metrics = await verifyMedia(page, response.data);
          check(metrics.originalSha256 === checkpoint.metrics.originalSha256);
          await publicRead(`${api}/ready`);
          record("Checkpoint row, caption, media hash and readiness survive operator action");
        } else {
          await page.goto(`/posts/${checkpoint.id}`);
          await page.getByRole("button", { name: "Delete", exact: true }).click();
          await page.getByRole("dialog").getByRole("button", { name: "Delete post", exact: true }).click();
          await expect(page).toHaveURL(/\/me\?deleted=1$/);
          check((await browser.request.get(`${api}/posts/${checkpoint.id}`)).status() === 404);
          checkpoint.deleted = true; await save("checkpoint", checkpoint, false);
          record("UI deletion and database 404; S3 origin cleanup needs separate verification");
        }
      }
    }
  } catch {
    results.push({ name: command, status: "FAIL", detail: "Inspect application and private checkpoint; raw browser errors intentionally omitted" });
    process.exitCode = 1;
  } finally {
    await browser.close();
    await save(`result-${Date.now()}-${command}`, { at: new Date().toISOString(), command, results });
    console.log(`Private report saved; ${results.filter(r => r.status === "FAIL").length} failed checks.`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(() => { console.error("Staging preflight failed. Check targets, approval flag and private artifact permissions; no secrets logged."); process.exitCode = 1; });
}

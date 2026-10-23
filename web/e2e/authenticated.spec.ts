import { test, expect } from "@playwright/test";
import { setupClerkTestingToken } from "@clerk/testing/playwright";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import { missingAuth } from "./environment";
import { auditAccessibility } from "./accessibility";
import { API, deleteGeneratedUser, findClerkUsers, formSignIn, formSignOut, helperSignIn, sessionRequest } from "./auth-helpers";

test.beforeEach(() => {
  test.skip(missingAuth.length > 0, `Missing: ${missingAuth.join(", ")}`);
});

test("owner pages pass axe and keyboard form/dialog checks in both themes", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await helperSignIn(page, process.env.E2E_USER_EMAIL!);
  for (const theme of ["light", "dark"]) {
    await page.evaluate(value => localStorage.setItem("theme", value), theme);
    await page.goto("/upload");
    await expect(page.locator(".cl-userButtonTrigger")).toBeVisible();
    await expect(page.locator(".post-form")).toBeVisible();
    await auditAccessibility(page);
    const file = page.getByLabel("Image", { exact: true });
    await file.focus();
    expect(await page.locator(".image-picker").evaluate(node => getComputedStyle(node).outlineWidth)).toBe("3px");
    await page.keyboard.press("Tab");
    await expect(page.getByLabel("Caption")).toBeFocused();
    await file.setInputFiles({ name: "invalid.txt", mimeType: "text/plain", buffer: Buffer.from("invalid") });
    await expect(file).toHaveAttribute("aria-invalid", "true");
    await auditAccessibility(page);
    await file.setInputFiles(path.resolve("../demo/sample_sunset.jpg"));
    await expect(file).toHaveAttribute("aria-invalid", "false");
    await page.getByLabel("Caption").fill("Soft sunlight over the hills.");
    const created = page.waitForResponse(response => response.url() === `${API}/posts` && response.request().method() === "POST");
    await page.getByRole("button", { name: "Share image" }).click();
    const response = await created;
    expect(response.status()).toBe(201);
    const post = await response.json() as { id: string; image: { variants: { url: string }[] } | null };
    try {
      expect(post.image?.variants.length).toBeGreaterThan(0);
      await expect(page.locator(".owner-actions")).toBeVisible();
      await expect(page.locator(".detail-image img")).toHaveAttribute("alt", "Soft sunlight over the hills.");
      await auditAccessibility(page);
      await page.getByRole("button", { name: "Delete", exact: true }).click();
      const dialog = page.getByRole("dialog");
      const keep = dialog.getByRole("button", { name: "Keep image" });
      await expect(keep).toBeFocused();
      await auditAccessibility(page);
      await page.keyboard.press("Shift+Tab");
      await expect(dialog.getByRole("button", { name: "Delete post", exact: true })).toBeFocused();
      await page.keyboard.press("Tab");
      await expect(keep).toBeFocused();
      await page.keyboard.press("Escape");
      await expect(page.getByRole("button", { name: "Delete", exact: true })).toBeFocused();
      await page.getByRole("link", { name: "Edit post" }).click();
      await expect(page.locator(".post-form")).toBeVisible();
      await auditAccessibility(page);
      await page.getByLabel("Caption").fill("");
      await page.getByRole("button", { name: "Save changes" }).click();
      await expect(page.getByRole("heading", { name: "Untitled image", exact: true })).toBeVisible();
      await expect(page.locator(".detail-image img")).toHaveAttribute("alt", "Shared image");
      await page.goto("/me");
      await expect(page.locator(".photo-card").first()).toBeVisible();
      await expect(page.locator(`.photo-card[href="/posts/${post.id}"]`)).toHaveAccessibleName("View image: Shared image");
      await auditAccessibility(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    } finally {
      expect([200, 404]).toContain((await sessionRequest(page, `/posts/${post.id}`, "DELETE")).status);
    }
  }
});

test("mobile recovery, long captions and deletion feedback with a real account", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await helperSignIn(page, process.env.E2E_USER_EMAIL!);
  await page.goto("/upload");
  // Keep this MIME-mismatch probe within the independent pixel/byte budgets.
  await page.getByLabel("Image", { exact: true }).setInputFiles({
    name: "mismatched.png",
    mimeType: "image/png",
    buffer: await readFile(path.resolve("../demo/sample_sunset.jpg")),
  });
  const rejected = page.waitForResponse(response =>
    response.url() === `${API}/posts` && response.request().method() === "POST");
  await page.getByRole("button", { name: "Share image" }).click();
  expect((await rejected).status()).toBe(400);
  const uploadError = page.locator(".post-form .error-banner");
  await expect(uploadError).toContainText("Invalid image");
  await expect(uploadError).toBeFocused();
  await expect(uploadError.getByRole("link", { name: "Sign in" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Share image" })).toBeEnabled();

  await page.getByLabel("Image", { exact: true }).setInputFiles(path.resolve("../demo/sample_sunset.jpg"));
  const caption = "A moment worth keeping. ".repeat(220).slice(0, 5000);
  await page.getByLabel("Caption").fill(caption);
  const created = page.waitForResponse(response =>
    response.url() === `${API}/posts` && response.request().method() === "POST");
  await page.getByRole("button", { name: "Share image" }).click();
  const response = await created;
  expect(response.status()).toBe(201);
  const { id } = await response.json() as { id: string };
  try {
    const disclosure = page.locator(".post-caption");
    await expect(disclosure).toBeVisible();
    await expect(disclosure).not.toHaveAttribute("open", "");
    const ownerTop = await page.locator(".owner-actions").evaluate(node => node.getBoundingClientRect().top + scrollY);
    expect(ownerTop).toBeLessThan(1300);
    await disclosure.locator("summary").focus();
    await page.keyboard.press("Enter");
    await expect(disclosure.locator("p")).toHaveText(caption);
    expect((await sessionRequest(page, `/posts/${id}`)).data.caption).toBe(caption);
    expect((await page.locator(".detail-image img").getAttribute("alt"))!.length).toBeLessThanOrEqual(160);
    await page.keyboard.press("Enter");
    await expect(disclosure.locator("p")).not.toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

    for (const theme of ["light", "dark"]) {
      await page.evaluate(value => { document.documentElement.dataset.theme = value; }, theme);
      await page.getByRole("button", { name: "Delete", exact: true }).click();
      const blocked = (url: URL) => url.origin === new URL(API).origin && url.pathname === `/posts/${id}`;
      await page.route(blocked, route => route.request().method() === "DELETE" ? route.abort("failed") : route.continue());
      await page.getByRole("button", { name: "Delete post", exact: true }).click();
      const error = page.locator(".delete-dialog .error-banner");
      await expect(error).toContainText("Check your connection");
      const colors = await error.evaluate(node => {
        const probe = document.createElement("span");
        probe.style.color = "var(--error)";
        node.append(probe);
        const expected = getComputedStyle(probe).color;
        probe.remove();
        return { actual: getComputedStyle(node).color, expected };
      });
      expect(colors.actual).toBe(colors.expected);
      await page.unroute(blocked);
      await page.getByRole("button", { name: "Keep image" }).click();
      await expect(page.getByRole("button", { name: "Delete", exact: true })).toBeFocused();
    }
    await page.goto("/me");
    await expect(page.locator(".photo-card").first()).toBeVisible();
    await page.getByLabel("Format").selectOption("image/webp");
    await expect(page.getByRole("heading", { name: "No images in this format yet." })).toBeVisible();
    await page.getByRole("button", { name: "Clear format filter" }).click();
    await expect(page.getByLabel("Format")).toHaveValue("");
    await expect(page.locator(`.photo-card[href="/posts/${id}"]`)).toBeVisible();
  } finally {
    expect([200, 404]).toContain((await sessionRequest(page, `/posts/${id}`, "DELETE")).status);
  }
});

test("Clerk form sign-in, logout, public browsing and account switching", async ({ page, request }) => {
  await formSignIn(page, process.env.E2E_USER_EMAIL!);
  const first = await sessionRequest(page, "/users/me");
  await formSignOut(page);
  expect((await request.get(`${API}/users/me`)).status()).toBe(401);
  await page.goto("/explore");
  await expect(page.locator(".photo-card").first()).toBeVisible();
  await formSignIn(page, process.env.E2E_OTHER_USER_EMAIL!);
  const second = await sessionRequest(page, "/users/me");
  expect(second.data.id).not.toBe(first.data.id);
  await formSignOut(page);
});

test("a new user signs up through the Clerk form and can sign back in", async ({ page }) => {
  const email = `pixshare-phase6-${randomUUID()}+clerk_test@example.com`;
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => {
    let message = error.message.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/ig, "[test address]");
    for (const value of [process.env.CLERK_SECRET_KEY, process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY])
      if (value) message = message.replaceAll(value, "[redacted key]");
    browserErrors.push(message.replace(/P6![a-f0-9-]+aZ9/g, "[generated password]"));
  });
  expect(await findClerkUsers(email)).toHaveLength(0);
  try {
    await setupClerkTestingToken({ page });
    await page.goto("/sign-in");
    await page.getByRole("link", { name: /sign up/i }).click();
    await expect(page).toHaveURL(/\/sign-up$/);
    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
    const username = page.locator('input[name="username"]');
    if (await username.isVisible())
      await username.fill(`pixshare_${randomUUID().replaceAll("-", "").slice(0, 20)}`);
    await page.locator('input[name="emailAddress"]').fill(email);
    const password = page.locator('input[name="password"]');
    if (await password.isVisible()) {
      try {
        await password.fill(`P6!${randomUUID()}aZ9`);
      } catch {
        // Locator action errors can include input values; never forward them.
        throw new Error("Could not enter the generated sign-up password");
      }
    }
    for (const [name, value] of [["firstName", "Test"], ["lastName", "User"]]) {
      const field = page.locator(`input[name="${name}"]`);
      if (await field.isVisible()) await field.fill(value);
    }
    const prepared = page.waitForResponse((response) =>
      response.url().includes("/prepare_verification") &&
      response.request().method() === "POST",
      { timeout: 20_000 },
    ).catch(() => null);
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    const verification = await prepared;
    expect(browserErrors).toEqual([]);
    if (!verification) {
      const state = await page.evaluate(() => {
        const signUp = window.Clerk.client?.signUp;
        return {
          status: signUp?.status,
          missingFields: signUp?.missingFields,
          unverifiedFields: signUp?.unverifiedFields,
          emailVerification: signUp?.verifications.emailAddress.status,
          emailStrategy: signUp?.verifications.emailAddress.strategy,
        };
      });
      throw new Error(`Clerk did not prepare verification: ${JSON.stringify(state)}`);
    }
    expect(verification?.status(), "Clerk must prepare email verification").toBe(200);
    await page.getByRole("textbox", { name: "Enter verification code" }).pressSequentially("424242");
    await page.waitForURL((url) => url.pathname === "/me" || url.pathname.includes("/tasks/"));
    if (new URL(page.url()).pathname.endsWith("/tasks/choose-organization")) {
      await expect(page.getByRole("heading", { name: "Setup your organization" })).toBeVisible();
      await page.locator('input[name="name"]').fill(email.split("+")[0]);
      await page.getByRole("button", { name: "Continue", exact: true }).click();
    }
    await expect(page).toHaveURL(/\/me$/);
    expect((await findClerkUsers(email))).toHaveLength(1);
    expect((await sessionRequest(page, "/users/me")).status).toBe(200);
    await formSignOut(page);
    await formSignIn(page, email);
    await formSignOut(page);
  } finally {
    await deleteGeneratedUser(email);
  }
});

test("real Clerk sign-in, upload, gallery, caption edit, replacement, ownership and deletion", async ({
  page,
  browser,
  request,
}) => {
  await helperSignIn(page, process.env.E2E_USER_EMAIL!);
  await page.goto("/upload");
  await expect(
    page.getByRole("heading", { name: /Share a perspective/ }),
  ).toBeVisible();
  await page
    .getByLabel("Image", { exact: true })
    .setInputFiles({
      name: "invalid.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("not an image"),
    });
  await expect(page.locator("#upload-error")).toContainText(
    "Choose a JPEG, PNG, or WebP",
  );
  await page
    .getByLabel("Image", { exact: true })
    .setInputFiles({
      name: "large.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.alloc(10 * 1024 * 1024 + 1),
    });
  await expect(page.locator("#upload-error")).toContainText("maximum size is 10 MB");
  await page
    .getByLabel("Image", { exact: true })
    .setInputFiles(path.resolve("../demo/sample_sunset.jpg"));
  await expect(page.getByAltText("Image preview")).toBeVisible();
  const caption = `E2E perspective ${Date.now()}`;
  await page.getByLabel("Caption").fill(caption);
  const created = page.waitForResponse((response) =>
    response.url() === `${API}/posts` && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Share image" }).click();
  const response = await created;
  expect(response.status()).toBe(201);
  const { id } = await response.json() as { id: string };
  let deleted = false;
  // Only the post created by this test is removed, even if an assertion fails.
  try {
    await expect(page.getByRole("heading", { name: caption, exact: true })).toBeVisible();
    await page.goto("/explore");
    await expect(
      page.getByRole("link", { name: new RegExp(caption) }),
    ).toBeVisible();
    await page.goto("/me");
    await expect(
      page.getByRole("link", { name: new RegExp(caption) }),
    ).toBeVisible();
    await page.goto(`/posts/${id}/edit`);
    await page.getByLabel("Caption").fill(`${caption} edited`);
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(
      page.getByRole("heading", { name: `${caption} edited`, exact: true }),
    ).toBeVisible();
    const before = await page.locator(".detail-image img").getAttribute("src");
    await page.getByRole("link", { name: "Edit post" }).click();
    await page
      .getByLabel("Replace image", { exact: true })
      .setInputFiles({
        name: "replacement.png",
        mimeType: "image/png",
        // A genuine PNG; bundled demo files can have misleading extensions.
        buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=", "base64"),
      });
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.locator(".detail-image img")).not.toHaveAttribute(
      "src",
      before!,
    );
    await page.getByRole("link", { name: "Edit post" }).click();
    await page.getByLabel("Caption").fill("");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page).toHaveURL(new RegExp(`/posts/${id}\\?success=updated$`));
    const original = await sessionRequest(page, `/posts/${id}`);
    expect(original.data.caption).toBe("");
    const publicPost = await request.get(`${API}/posts/${id}`);
    expect(publicPost.status()).toBe(200);
    expect((await request.get(`${API}${original.data.url}`)).status()).toBe(200);
    const context = await browser.newContext({ baseURL: new URL(page.url()).origin });
    try {
      const other = await context.newPage();
      await helperSignIn(other, process.env.E2E_OTHER_USER_EMAIL!);
      const owner = await sessionRequest(page, "/users/me");
      const nonOwner = await sessionRequest(other, "/users/me");
      expect(nonOwner.data.id).not.toBe(owner.data.id);
      const mine = await sessionRequest(page, "/users/me/posts?limit=100");
      const theirs = await sessionRequest(other, "/users/me/posts?limit=100");
      expect(mine.data.some((post: { id: string }) => post.id === id)).toBe(true);
      expect(theirs.data.some((post: { id: string }) => post.id === id)).toBe(false);
      await other.goto(`/posts/${id}`);
      await expect(other.locator(".detail-image img")).toBeVisible();
      await expect(other.getByRole("link", { name: "Edit post", exact: true })).toHaveCount(0);
      await expect(other.getByRole("button", { name: "Delete", exact: true })).toHaveCount(0);
      await other.goto(new URL(`/posts/${id}/edit`, page.url()).href);
      await expect(
        other.getByRole("heading", {
          name: "Only the owner can edit this post.",
        }),
      ).toBeVisible();
      expect((await sessionRequest(other, `/posts/${id}`, "PATCH", "Forbidden")).status).toBe(403);
      expect((await sessionRequest(other, `/posts/${id}`, "DELETE")).status).toBe(403);
      const unchanged = await sessionRequest(page, `/posts/${id}`);
      expect(unchanged.status).toBe(200);
      expect(unchanged.data).toEqual(original.data);
    } finally {
      await context.close();
    }
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    const dialog = page.getByRole("dialog");
    await expect(
      dialog.getByRole("button", { name: "Keep image" }),
    ).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await expect(
      page.getByRole("button", { name: "Delete", exact: true }),
    ).toBeFocused();
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await dialog
      .getByRole("button", { name: "Delete post", exact: true })
      .click();
    await expect(page).toHaveURL(/\/me\?deleted=1$/);
    await expect(page.getByRole("status")).toContainText("deleted");
    expect((await sessionRequest(page, `/posts/${id}`)).status).toBe(404);
    deleted = true;
    await formSignOut(page);
    await page.goto("/explore");
    await expect(page.locator(".photo-card").first()).toBeVisible();
  } finally {
    // Reauthenticate if failure occurred after logout; delete only this run's post.
    if (!deleted) {
      if (!await page.evaluate(() => Boolean(window.Clerk?.session)))
        await helperSignIn(page, process.env.E2E_USER_EMAIL!);
      const cleanup = await sessionRequest(page, `/posts/${id}`, "DELETE");
      expect([200, 404]).toContain(cleanup.status);
    }
  }
});

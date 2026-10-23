import { test, expect } from "@playwright/test";
import { auditAccessibility } from "./accessibility";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

test("public pages pass axe in both themes and reflow for keyboard users", async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const posts = await (await request.get(`${API}/posts?limit=1`)).json() as { id: string }[];
  await page.goto("/");
  for (const theme of ["light", "dark"]) {
    await page.evaluate(value => localStorage.setItem("theme", value), theme);
    for (const [route, ready] of [
      ["/", ".photo-card"], ["/explore", ".photo-card"], [`/posts/${posts[0].id}`, ".detail-image img"],
      ["/upload", ".state-panel"], ["/me", ".state-panel"], ["/sign-in", "input[name=identifier], .state-panel"], ["/sign-up", "input[name=emailAddress], .state-panel"],
    ]) {
      await page.goto(route);
      await expect(page.locator(ready).first()).toBeVisible();
      await auditAccessibility(page);
    }
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/explore");
  await expect(page.locator(".photo-card").first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  const focus = await page.locator(":focus").evaluate(node => getComputedStyle(node).outlineWidth);
  expect(parseFloat(focus)).toBeGreaterThanOrEqual(3);
  expect(await page.locator(".theme-toggle").evaluate(node => getComputedStyle(node).transitionDuration)).toBe("0s");
});

test("responsive WebP variants reserve layout and fall back to the original on failure", async ({ page, request }) => {
  const posts = await (await request.get(`${API}/posts?limit=100`)).json() as { id: string; url: string; image?: { variants: { url: string }[] } | null }[];
  const post = posts.find(post => (post.image?.variants.length ?? 0) > 1);
  expect(post, "Seed the isolated E2E database with variants before testing").toBeDefined();
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const variantUrls = new Set(post!.image!.variants.map(variant => `${API}${variant.url}`));
  await page.route(url => variantUrls.has(url.href), async route => { await gate; await route.continue(); });
  try {
    await page.goto(`/posts/${post!.id}`, { waitUntil: "domcontentloaded" });
    const image = page.locator(".detail-image img");
    await expect(image).toBeVisible();
    const before = await page.locator(".detail-image").boundingBox();
    release();
    await image.evaluate(async (node: HTMLImageElement) => { await node.decode(); });
    expect(variantUrls.has(await image.evaluate((node: HTMLImageElement) => node.currentSrc))).toBe(true);
    const after = await page.locator(".detail-image").boundingBox();
    expect(after?.height).toBe(before?.height);
    expect(after?.width).toBe(before?.width);
    await expect(image).toHaveAttribute("loading", "eager");
  } finally {
    release();
    await page.unrouteAll({ behavior: "wait" });
  }
  await page.route(url => variantUrls.has(url.href), route => route.abort("failed"));
  await page.reload();
  const fallback = page.locator(".detail-image img");
  await expect.poll(() => fallback.evaluate((node: HTMLImageElement, original) => node.complete && node.naturalWidth > 0 && node.currentSrc === original, `${API}${post!.url}`)).toBe(true);
  await expect(page.locator(".detail-image source")).toHaveCount(0);
});
test("public visitor browses real images, filters, sorts, and opens details", async ({
  page,
  request,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const response = await request.get(`${API}/posts?limit=1`);
  expect(response.ok()).toBeTruthy();
  expect(
    (await response.json()).length,
    "Seed the isolated E2E database before testing",
  ).toBeGreaterThan(0);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Life looks different/ }),
  ).toBeVisible();
  const cards = page.locator(".photo-card");
  await expect(cards.first()).toBeVisible();
  const contrast = await page.locator(".join-panel p").evaluate(node => {
    function luminance(color: string) {
      const channels = color.match(/\d+/g)!.slice(0, 3).map(value => {
        const channel = Number(value) / 255;
        return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
      });
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    }
    const foreground = luminance(getComputedStyle(node).color);
    const background = luminance(getComputedStyle(node.closest(".join-panel")!).backgroundColor);
    return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
  });
  expect(contrast, "Landing helper text must meet normal-text contrast").toBeGreaterThanOrEqual(4.5);
  expect(await cards.first().locator("img").evaluate(async (img: HTMLImageElement) => {
    await img.decode();
    return img.naturalWidth;
  })).toBeGreaterThan(0);
  await page.screenshot({
    path: testInfo.outputPath("home.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Explore all images" }).click();
  await expect(page).toHaveURL(/\/explore$/);
  await page.getByLabel("Format").selectOption("image/png");
  await expect(page.locator(".photo-card").first()).toBeVisible();
  await expect(page.locator(".photo-card img").first()).toHaveAttribute(
    "src",
    /\.png$/,
  );
  await page.getByLabel("Sort by").selectOption("oldest");
  await expect(page.getByText("Page 1", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Previous" })).toBeDisabled();
  await page.locator(".photo-card").first().click();
  await expect(page.locator(".detail-image img")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Edit post", exact: true }),
  ).toHaveCount(0);
  await page.screenshot({
    path: testInfo.outputPath("detail.png"),
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("responsive layout, keyboard focus, theme persistence, and reduced motion", async ({
  page,
}, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/explore");
  await expect(page.locator(".photo-card").first()).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
  const toggle = page.getByRole("button", { name: "Toggle color theme" });
  const target = await toggle.boundingBox();
  expect(target?.width).toBeGreaterThanOrEqual(44);
  expect(target?.height).toBeGreaterThanOrEqual(44);
  await toggle.click();
  const selected = await page.locator("html").getAttribute("data-theme");
  expect(["dark", "light"]).toContain(selected);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", selected!);
  await page.screenshot({
    path: testInfo.outputPath("theme.png"),
    fullPage: true,
  });
});

test("signed-out visitors receive useful protected-page states", async ({
  page,
}) => {
  for (const path of ["/upload", "/me"]) {
    await page.goto(path);
    await expect(
      page.getByRole("heading", { name: "Make yourself at home." }),
    ).toBeVisible();
    await expect(page.getByLabel("Caption", { exact: false })).toHaveCount(0);
  }
  await page.goto("/posts/00000000-0000-0000-0000-000000000000");
  await expect(
    page.getByRole("heading", { name: "Image not found." }),
  ).toBeVisible();
});

test("legacy routes redirect and unauthenticated API mutations are rejected", async ({
  page,
  request,
}) => {
  await page.goto("/posts");
  await expect(page).toHaveURL(/\/explore$/);
  await page.goto("/posts/new");
  await expect(page).toHaveURL(/\/upload$/);
  for (const method of ["post", "patch", "delete"] as const) {
    const path =
      method === "post"
        ? "/posts"
        : "/posts/00000000-0000-0000-0000-000000000000";
    expect((await request[method](`${API}${path}`)).status()).toBe(401);
  }
  for (const path of ["/users/me", "/users/me/posts"])
    expect((await request.get(`${API}${path}`)).status()).toBe(401);
});

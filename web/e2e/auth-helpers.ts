import { expect, type BrowserContext, type Page } from "@playwright/test";
import { clerk, setupClerkTestingToken } from "@clerk/testing/playwright";
import { format } from "node:util";

export function sanitizeDiagnostic(message: string): string {
  for (const name of ["CLERK_SECRET_KEY", "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "E2E_USER_EMAIL", "E2E_OTHER_USER_EMAIL"])
    if (process.env[name]) message = message.replaceAll(process.env[name]!, "[redacted]");
  return message
    .replace(/https?:\/\/[^\s<>"'`]+/g, value => {
      try {
        const url = new URL(value);
        url.search = "";
        url.hash = "";
        url.pathname = url.pathname.replace(/\/sessions\/[^/]+/, "/sessions/[redacted]");
        return url.href;
      } catch { return "[redacted URL]"; }
    })
    .replace(/\n\s*body:[\s\S]*$/, "\n  body: [omitted]")
    .replace(/\bBearer\s+\S+/gi, "Bearer [redacted]")
    .replace(/\b(?:[sp]k_(?:test|live)_[A-Za-z0-9_]+|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b/g, "[redacted token]")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[test address]")
    .replace(/P6![a-f0-9-]+aZ9/g, "[generated password]");
}

// Clerk's retry/shutdown warnings can include token-bearing FAPI URLs. Keep
// diagnostics visible while preventing those values reaching test output.
const warn = console.warn.bind(console);
const error = console.error.bind(console);
console.warn = (...args: unknown[]) => warn(sanitizeDiagnostic(format(...args)));
console.error = (...args: unknown[]) => error(sanitizeDiagnostic(format(...args)));

export const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const handshakeContexts = new WeakSet<BrowserContext>();

export async function prepareClerkBrowser(page: Page) {
  await setupClerkTestingToken({ page });
  if (handshakeContexts.has(page.context())) return;
  // The SDK's broad FAPI interceptor fetches through redirects, then assumes
  // JSON. Handshake is a browser navigation: its redirects/Set-Cookie must reach
  // the real browser, otherwise WebKit sees HTML and can enter a refresh loop.
  await page.context().route(url => url.pathname === "/v1/client/handshake" &&
    url.hostname === process.env.CLERK_FAPI, async route => {
    if (!route.request().isNavigationRequest()) return route.fallback();
    const url = new URL(route.request().url());
    if (process.env.CLERK_TESTING_TOKEN)
      url.searchParams.set("__clerk_testing_token", process.env.CLERK_TESTING_TOKEN);
    await route.continue({ url: url.href });
  });
  handshakeContexts.add(page.context());
}

// Return only the response, never serialize a session token into the runner.
export async function sessionRequest(page: Page, route: string, method = "GET", caption?: string) {
  return page.evaluate(async ({ api, route, method, caption }) => {
    const token = await window.Clerk.session?.getToken();
    if (!token) throw new Error("Expected a genuine Clerk session");
    const body = caption === undefined ? undefined : new FormData();
    if (body) body.set("caption", caption!);
    const response = await fetch(`${api}${route}`, {
      method,
      headers: { Authorization: `Bearer ${token}` },
      body,
    });
    return { status: response.status, data: await response.json() };
  }, { api: API, route, method, caption });
}

export async function helperSignIn(page: Page, emailAddress: string) {
  await prepareClerkBrowser(page);
  await page.goto("/");
  try {
    await clerk.signIn({ page, emailAddress });
  } catch {
    throw new Error("Clerk helper sign-in failed; check the dedicated development account");
  }
  // Clerk's session promise can settle before React finishes the identity change.
  await expect(page.locator(".cl-userButtonTrigger")).toBeVisible();
}

export async function formSignIn(page: Page, email: string) {
  await prepareClerkBrowser(page);
  await page.goto("/sign-in");
  await page.locator('input[name="identifier"]').fill(email);
  const prepared = page.waitForResponse((response) =>
    response.url().includes("/prepare_first_factor") &&
    response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  const code = page.getByRole("textbox", { name: "Enter verification code" });
  const alternate = page.getByRole("link", { name: /use another method/i });
  await expect(code.or(alternate)).toBeVisible();
  if (await alternate.isVisible()) {
    await alternate.click();
    await page.getByRole("button", { name: /email code to/i }).click();
  }
  expect((await prepared).status()).toBe(200);
  await code.pressSequentially("424242");
  await expect(page).toHaveURL(/\/me$/);
  expect((await sessionRequest(page, "/users/me")).status).toBe(200);
}

export async function formSignOut(page: Page) {
  await page.locator(".cl-userButtonTrigger").click();
  await page.getByRole("button", { name: /Sign out$/i }).click();
  await expect.poll(() => page.evaluate(() => Boolean(window.Clerk.session))).toBe(false);
  // Let Clerk's sign-out redirect finish before starting another navigation.
  await page.waitForURL(/\/$/, { waitUntil: "load" });
  await expect(page.getByRole("link", { name: "Sign in", exact: true })).toBeVisible();
  // Use the actual navigation control after sign-out rather than starting a
  // competing full-document navigation during development cookie handoffs.
  await page.getByRole("link", { name: "My album", exact: true }).click();
  await expect(page).toHaveURL(/\/me$/);
  await expect(page.getByRole("heading", { name: "Make yourself at home." })).toBeVisible();
}

type ClerkUser = { id: string; email_addresses: { email_address: string }[] };

export async function findClerkUsers(email: string): Promise<ClerkUser[]> {
  const url = new URL("https://api.clerk.com/v1/users");
  url.searchParams.set("email_address", email);
  let response: Response;
  try {
    response = await fetch(url, { headers: { Authorization: `Bearer ${process.env.CLERK_SECRET_KEY}` } });
  } catch {
    throw new Error("Clerk user lookup failed; check network access");
  }
  if (!response.ok) throw new Error(`Clerk user lookup failed (HTTP ${response.status})`);
  return await response.json() as ClerkUser[];
}

export async function deleteGeneratedUser(email: string) {
  // Caller supplies this run's random address, never either persistent test account.
  if (!/^pixshare-phase6-[a-f0-9-]+\+clerk_test@example\.com$/.test(email))
    throw new Error("Refusing to clean up an address outside the generated test namespace");
  for (const user of await findClerkUsers(email)) {
    if (user.email_addresses.length !== 1 || user.email_addresses[0].email_address !== email)
      throw new Error("Refusing to delete an unexpected Clerk user");
    // The instance may require organization onboarding. Remove only the exact
    // random organization named by this run and associated with its own user.
    try {
      const memberships = await fetch(`https://api.clerk.com/v1/users/${encodeURIComponent(user.id)}/organization_memberships`, {
        headers: { Authorization: `Bearer ${process.env.CLERK_SECRET_KEY}` },
      });
      if (!memberships.ok) throw new Error();
      const { data } = await memberships.json() as {
        data: { organization: { id: string; name: string } }[];
      };
      for (const { organization } of data) {
        if (organization.name !== email.split("+")[0]) continue;
        const removed = await fetch(`https://api.clerk.com/v1/organizations/${encodeURIComponent(organization.id)}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${process.env.CLERK_SECRET_KEY}` },
        });
        if (!removed.ok) throw new Error();
      }
    } catch {
      throw new Error("Generated signup organization cleanup failed; inspect the development dashboard");
    }
    let response: Response;
    try {
      response = await fetch(`https://api.clerk.com/v1/users/${encodeURIComponent(user.id)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${process.env.CLERK_SECRET_KEY}` },
      });
    } catch {
      throw new Error("Generated Clerk user cleanup failed; inspect the development dashboard");
    }
    if (!response.ok) throw new Error(`Generated Clerk user cleanup failed (HTTP ${response.status})`);
  }
}

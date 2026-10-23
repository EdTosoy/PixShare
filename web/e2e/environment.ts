import { existsSync } from "node:fs";
import path from "node:path";

// Playwright does not load Next.js environment files. Keep shell values first.
for (const name of [".env.e2e.local", ".env.local", ".env"]) {
  const file = path.resolve(__dirname, "..", name);
  if (existsSync(file)) process.loadEnvFile(file);
}

export const publishableKey =
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ||
  process.env.CLERK_PUBLISHABLE_KEY;

export const missingAuth = [
  ...(!publishableKey ? ["NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"] : []),
  ...["CLERK_SECRET_KEY", "E2E_USER_EMAIL", "E2E_OTHER_USER_EMAIL"].filter(
    (name) => !process.env[name],
  ),
];

export function validateAuthEnvironment() {
  if (
    (publishableKey && !publishableKey.startsWith("pk_test_")) ||
    (process.env.CLERK_SECRET_KEY &&
      !process.env.CLERK_SECRET_KEY.startsWith("sk_test_"))
  )
    throw new Error("Clerk browser tests require development-instance keys");
  if (
    process.env.CLERK_PUBLISHABLE_KEY &&
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY &&
    process.env.CLERK_PUBLISHABLE_KEY !==
      process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
  )
    throw new Error("Clerk frontend and testing publishable keys must match");
  if (missingAuth.length) return;
  const emails = [process.env.E2E_USER_EMAIL!, process.env.E2E_OTHER_USER_EMAIL!];
  if (emails[0].toLowerCase() === emails[1].toLowerCase())
    throw new Error("Ownership tests require two distinct Clerk accounts");
  if (emails.some((email) => !/\+clerk_test[^@]*@/i.test(email)))
    throw new Error("Use dedicated +clerk_test addresses for Clerk browser tests");
}

import { expect, test as setup } from "@playwright/test";
import { clerkSetup } from "@clerk/testing/playwright";
import { missingAuth, publishableKey } from "./environment";
import { findClerkUsers, sanitizeDiagnostic } from "./auth-helpers";

setup("Clerk development-instance setup", async () => {
  setup.skip(missingAuth.length > 0, `Missing: ${missingAuth.join(", ")}`);
  const diagnostic = sanitizeDiagnostic("FAPI failed: https://example.com/v1/client/sessions/private-session/touch?__clerk_db_jwt=private-query-token\n  body: private-response");
  for (const value of ["private-session", "private-query-token", "private-response"])
    expect(diagnostic).not.toContain(value);
  try {
    await clerkSetup({ dotenv: false, publishableKey });
  } catch {
    // SDK errors may contain request details. Never print credentials/tokens.
    throw new Error("Clerk setup failed; check development keys and network access");
  }
  const users = await Promise.all([
    findClerkUsers(process.env.E2E_USER_EMAIL!),
    findClerkUsers(process.env.E2E_OTHER_USER_EMAIL!),
  ]);
  if (users.some((matches) => matches.length !== 1))
    throw new Error("Create both dedicated test users in the matching Clerk development instance");
  if (users[0][0].id === users[1][0].id)
    throw new Error("Ownership verification requires distinct Clerk user IDs");
});

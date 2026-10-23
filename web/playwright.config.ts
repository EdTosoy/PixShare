import { defineConfig, devices } from "@playwright/test";
import { missingAuth, validateAuthEnvironment } from "./e2e/environment";

validateAuthEnvironment();
if (process.env.E2E_REQUIRE_AUTH === "1" && missingAuth.length)
  throw new Error(`Missing Clerk E2E configuration: ${missingAuth.join(", ")}`);

const chromiumLaunch = {
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
  chromiumSandbox: true,
};
const privateArtifacts = { trace: "off" as const, screenshot: "off" as const, video: "off" as const };
const crossBrowserProjects = process.env.E2E_CROSS_BROWSER === "1"
  ? (["firefox", "webkit"] as const).flatMap(browserName => [
      { name: `${browserName}-public`, testMatch: /public\.spec\.ts/, use: { browserName } },
      { name: `${browserName}-auth`, testMatch: /authenticated\.spec\.ts/, dependencies: ["setup"], timeout: 180_000, use: { browserName, ...privateArtifacts } },
    ])
  : [];

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "setup",
      testMatch: /global\.setup\.ts/,
      timeout: 60_000,
      use: { ...privateArtifacts, launchOptions: chromiumLaunch },
    },
    {
      name: "auth",
      testMatch: /authenticated\.spec\.ts/,
      dependencies: ["setup"],
      timeout: 120_000,
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: chromiumLaunch,
        trace: "off",
        screenshot: "off",
        video: "off",
      },
    },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], launchOptions: chromiumLaunch },
      testMatch: /public\.spec\.ts/,
    },
    {
      name: "tablet",
      use: { ...devices["iPad Mini"], defaultBrowserType: "chromium", launchOptions: chromiumLaunch },
      testMatch: /public\.spec\.ts/,
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"], defaultBrowserType: "chromium", launchOptions: chromiumLaunch },
      testMatch: /public\.spec\.ts/,
    },
    ...crossBrowserProjects,
  ],
  // Start API + migrated/seeded test PostgreSQL separately; never seed user data here.
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: "node scripts/start.mjs",
        url: "http://localhost:3000",
        reuseExistingServer: false,
        timeout: 60_000,
      },
});

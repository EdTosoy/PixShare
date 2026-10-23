// Next standalone omits these assets intentionally. Include them for local start.
import { cp, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import path from "node:path";

const root = process.cwd();
// Standalone changes cwd; load local runtime secrets first using Next's loader.
const require = createRequire(import.meta.url);
const nextRequire = createRequire(require.resolve("next/package.json"));
const { loadEnvConfig } = nextRequire("@next/env");
loadEnvConfig(root);
const standalone = path.join(root, ".next/standalone");
await mkdir(path.join(standalone, ".next"), { recursive: true });
await cp(path.join(root, ".next/static"), path.join(standalone, ".next/static"), { recursive: true });
await cp(path.join(root, "public"), path.join(standalone, "public"), { recursive: true });
// Match the browser origin so Clerk's same-origin rewrite stays internal.
process.env.HOSTNAME = process.env.PIXSHARE_HOST || "localhost";
await import(pathToFileURL(path.join(standalone, "server.js")).href);

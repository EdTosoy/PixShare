import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

// Separate ephemeral local state: never use --remote or touch production R2.
const temporary = await mkdtemp(join(tmpdir(), "pixshare-reader-smoke-"));
const key = "pixshare/media/0123456789abcdef0123456789abcdef/original.png";
const image = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aHZkAAAAASUVORK5CYII=",
  "base64",
);
const env = { ...process.env, WRANGLER_SEND_METRICS: "false" };
let server;
let output = "";

function wrangler(args) {
  const child = spawn(process.execPath, ["node_modules/wrangler/bin/wrangler.js", ...args], {
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  child.stdout.on("data", data => { output += data; });
  child.stderr.on("data", data => { output += data; });
  return child;
}

try {
  const fixture = join(temporary, "fixture.png");
  const state = join(temporary, "state");
  await writeFile(fixture, image);
  const seed = wrangler([
    "r2", "object", "put", `pixshare-media/${key}`,
    "--local", "--persist-to", state, "--file", fixture, "--content-type", "image/png",
  ]);
  const seedTimeout = setTimeout(() => seed.kill("SIGKILL"), 30_000);
  try {
    assert.equal((await once(seed, "exit"))[0], 0, "Local R2 fixture setup failed");
  } finally {
    clearTimeout(seedTimeout);
  }

  const listener = createServer();
  listener.listen(0, "127.0.0.1");
  await once(listener, "listening");
  const { port } = listener.address();
  await new Promise(resolve => listener.close(resolve));

  server = wrangler([
    "dev", "--local", "--ip", "127.0.0.1", "--port", String(port),
    "--inspector-port", "0", "--persist-to", state,
  ]);
  const base = `http://127.0.0.1:${port}`;
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error("Wrangler exited before it was ready");
    try {
      const probe = await fetch(`${base}/`, { signal: AbortSignal.timeout(500) });
      if (probe.status === 404) { ready = true; break; }
    } catch { /* Wait for workerd to finish startup. */ }
    await delay(200);
  }
  assert.ok(ready, "Wrangler did not become ready");

  const get = await fetch(`${base}/${key}?v=smoke`);
  assert.equal(get.status, 200);
  assert.equal(get.headers.get("Content-Type"), "image/png");
  assert.equal(get.headers.get("Cache-Control"), "public, max-age=31536000, immutable");
  assert.equal(get.headers.get("Content-Length"), String(image.length));
  assert.equal(get.headers.get("X-Content-Type-Options"), "nosniff");
  assert.match(get.headers.get("ETag"), /^".+"$/);
  assert.deepEqual(Buffer.from(await get.arrayBuffer()), image);

  const head = await fetch(`${base}/${key}`, { method: "HEAD" });
  assert.equal(head.status, 200);
  assert.equal(head.headers.get("Content-Length"), String(image.length));
  assert.equal(head.headers.get("Content-Type"), get.headers.get("Content-Type"));
  assert.equal(head.headers.get("ETag"), get.headers.get("ETag"));
  assert.equal(await head.text(), "");

  const missing = await fetch(`${base}/${key.replace("original.png", "original.jpg")}`);
  assert.equal(missing.status, 404);
  assert.equal(missing.headers.get("Cache-Control"), "no-store");

  const manifest = await fetch(`${base}/${key.replace("original.png", "manifest.json")}`);
  assert.equal(manifest.status, 404);

  const post = await fetch(`${base}/${key}`, { method: "POST" });
  assert.equal(post.status, 405);
  assert.equal(post.headers.get("Allow"), "GET, HEAD");
  console.log("PASS: 5 local Wrangler scenarios (GET, HEAD, missing object, manifest, POST); isolated local R2 only.");
} catch (error) {
  console.error(output);
  throw error;
} finally {
  if (server && server.exitCode === null) {
    const exited = once(server, "exit");
    server.kill("SIGTERM");
    const killTimeout = setTimeout(() => server.kill("SIGKILL"), 5000);
    await exited;
    clearTimeout(killTimeout);
  }
  await rm(temporary, { recursive: true, force: true });
}

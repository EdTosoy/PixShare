import assert from "node:assert/strict";
import { test } from "node:test";
import worker from "../src/index.ts";

const group = "pixshare/media/0123456789abcdef0123456789abcdef";
const immutable = "public, max-age=31536000, immutable";
const bytes = new Uint8Array([1, 2, 3, 4]);

function binding({ missing = false, failure = false } = {}) {
  const calls = [];
  const metadata = {
    size: bytes.length,
    httpEtag: '"image-etag"',
    customMetadata: { "pixshare-upload": "private-operation-marker" },
    httpMetadata: {
      contentType: "text/html",
      cacheControl: "private",
      contentDisposition: "attachment; filename=internal-name",
    },
  };
  function lookup(method, key) {
    calls.push({ method, key });
    if (failure) throw new Error("Internal storage error: private-operation-marker");
    if (missing) return null;
    return method === "get"
      ? { ...metadata, body: new Response(bytes).body }
      : metadata;
  }
  return {
    calls,
    MEDIA: {
      async get(key) { return lookup("get", key); },
      async head(key) { return lookup("head", key); },
      // Any attempt to list, write or delete fails the test immediately.
      list() { assert.fail("Listing is forbidden"); },
      put() { assert.fail("Writing is forbidden"); },
      delete() { assert.fail("Deleting is forbidden"); },
    },
  };
}

function request(path, method = "GET") {
  // Keep the serialized path intact to exercise the handler's traversal guard.
  // Real Request/URL implementations may normalize dot segments before fetch.
  return { url: `https://media.example.invalid${path}`, method };
}

for (const [file, type] of [
  ["original.jpg", "image/jpeg"],
  ["original.png", "image/png"],
  ["original.webp", "image/webp"],
  ...[1, 319, 320, 640, 1000, 1280, 1919, 1920].map(edge => [
    `variants/v1-${edge}.webp`, "image/webp",
  ]),
]) {
  for (const method of ["GET", "HEAD"]) {
    test(`${method} ${file} delivers only public image headers`, async () => {
      const env = binding();
      const key = `${group}/${file}`;
      const response = await worker.fetch(new Request(`https://media.example.invalid/${key}`, { method }), env);
      assert.equal(response.status, 200);
      assert.equal(response.headers.get("Content-Type"), type);
      assert.equal(response.headers.get("Cache-Control"), immutable);
      assert.equal(response.headers.get("Content-Length"), String(bytes.length));
      assert.equal(response.headers.get("ETag"), '"image-etag"');
      assert.equal(response.headers.get("X-Content-Type-Options"), "nosniff");
      assert.deepEqual([...response.headers.keys()].sort(), [
        "cache-control", "content-length", "content-type", "etag", "x-content-type-options",
      ]);
      assert.deepEqual(env.calls, [{ method: method.toLowerCase() === "get" ? "get" : "head", key }]);
      if (method === "HEAD") {
        assert.equal(response.body, null);
        assert.equal(await response.text(), "");
      } else {
        assert.deepEqual(new Uint8Array(await response.arrayBuffer()), bytes);
      }
    });
  }
}

for (const path of [
  "/", "/favicon.ico", "/pixshare/media", `/${group}/`,
  `/${group}/manifest.json`, `/${group}/variants/manifest.json`,
  `/${group}/original.jpeg`, `/${group}/original.gif`, `/${group}/original.svg`,
  `/${group}/original.JPG`, `/${group}/original.jpg/`,
  `/${group}/variants/v1-0.webp`, `/${group}/variants/v1-0320.webp`,
  `/${group}/variants/v1-1921.webp`, `/${group}/variants/v1-20000.webp`,
  `/${group}/variants/v1--1.webp`, `/${group}/variants/v1-1.5.webp`,
  `/${group}/variants/v2-320.webp`, `/${group}/variants/v1-320.png`,
  "/other/media/0123456789abcdef0123456789abcdef/original.jpg",
  "/pixshare/media/01234567-89ab-cdef-0123-456789abcdef/original.jpg",
  "/pixshare/media/0123456789ABCDEF0123456789ABCDEF/original.jpg",
  "/pixshare/media/abc/original.jpg",
  `//${group}/original.jpg`, `/${group}//original.jpg`,
  `/${group}/../original.jpg`, `/unexpected/../${group}/original.jpg`,
  `/${group}/%2e%2e/original.jpg`, `/${group}/%252e%252e/original.jpg`,
  `/${group}/original%2ejpg`, `/${group}%2foriginal.jpg`,
  `/${group}/original.jpg%00`, `/${group}/original.jpg%`,
  `/${group}\\original.jpg`, `/${group}/original.jpg\n`,
]) {
  test(`rejects path ${JSON.stringify(path)} before accessing R2`, async () => {
    const env = binding();
    const response = await worker.fetch(request(path), env);
    assert.equal(response.status, 404);
    assert.equal(response.headers.get("Cache-Control"), "no-store");
    assert.equal(await response.text(), "Not found");
    assert.deepEqual(env.calls, []);
  });
}

for (const method of ["POST", "PUT", "DELETE", "PATCH", "OPTIONS"]) {
  test(`rejects ${method} without accessing R2`, async () => {
    const env = binding();
    const response = await worker.fetch(request(`/${group}/original.jpg`, method), env);
    assert.equal(response.status, 405);
    assert.equal(response.headers.get("Allow"), "GET, HEAD");
    assert.equal(response.headers.get("Cache-Control"), "no-store");
    assert.deepEqual(env.calls, []);
  });
}

for (const method of ["GET", "HEAD"]) {
  for (const [options, status, text] of [
    [{ missing: true }, 404, "Not found"],
    [{ failure: true }, 503, "Media temporarily unavailable"],
  ]) {
    test(`${method} returns safe ${status} on storage lookup`, async () => {
      const env = binding(options);
      const response = await worker.fetch(request(`/${group}/original.jpg`, method), env);
      assert.equal(response.status, status);
      assert.equal(response.headers.get("Cache-Control"), "no-store");
      assert.equal(response.headers.get("Content-Type"), "text/plain; charset=utf-8");
      assert.equal(await response.text(), method === "HEAD" ? "" : text);
      assert.equal(env.calls.length, 1);
    });
  }
}

test("HEAD rejection has no body and makes no storage calls", async () => {
  const env = binding();
  const response = await worker.fetch(request(`/${group}/manifest.json`, "HEAD"), env);
  assert.equal(response.status, 404);
  assert.equal(response.body, null);
  assert.deepEqual(env.calls, []);
});

for (const query of ["?v=1", "?key=manifest.json&content-type=text/html", "?path=../../manifest.json", "?bad=%00%zz"]) {
  test(`query ${query} does not alter the object key or image headers`, async () => {
    const env = binding();
    const key = `${group}/original.png`;
    const response = await worker.fetch(request(`/${key}${query}`), env);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("Content-Type"), "image/png");
    assert.equal(response.headers.get("Cache-Control"), immutable);
    assert.deepEqual(env.calls, [{ method: "get", key }]);
  });
}

test("a query cannot turn a manifest path into an image", async () => {
  const env = binding();
  const response = await worker.fetch(request(`/${group}/manifest.json?path=original.jpg`), env);
  assert.equal(response.status, 404);
  assert.deepEqual(env.calls, []);
});

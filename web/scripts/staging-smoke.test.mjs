import { test } from "node:test";
import assert from "node:assert/strict";
import { origin, mediaGroup } from "./staging-smoke.mjs";

test("staging origins require HTTPS without credentials, paths or tokens", () => {
  for (const value of ["http://stage.example.invalid", "https://localhost", "https://example.invalid/path", "https://test:password@example.invalid", "https://example.invalid/?secret=example"])
    assert.throws(() => origin(value));
  assert.equal(origin("https://stage.example.invalid"), "https://stage.example.invalid");
});

test("only exact staging media origin and generated group paths are accepted", () => {
  const group = "pixshare/staging/" + "a".repeat(32) + "/";
  assert.equal(mediaGroup(`https://media.example.invalid/${group}original.png`, "https://media.example.invalid"), group);
  for (const value of [`https://other.invalid/${group}original.png`, `https://media.example.invalid/${group}original.png?token=example`, "https://media.example.invalid/pixshare/production/original.png", "https://media.example.invalid/pixshare/staging/../original.png"])
    assert.throws(() => mediaGroup(value, "https://media.example.invalid"));
});

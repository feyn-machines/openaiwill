import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const load = async (relative) => {
  const source = readFileSync(fileURLToPath(new URL(relative, import.meta.url)), "utf8");
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
  return import(`data:text/javascript;charset=utf-8,${encodeURIComponent(js)}`);
};
const { normalizeHandle } = await load("../../src/lib/handles.ts");
const { appEnabled, isAdmin } = await load("../../src/lib/app-config.ts");

test("every accepted way of writing an account gives the same handle", () => {
  for (const input of ["OpenAI", "@OpenAI", " @OpenAI ", "https://x.com/OpenAI", "https://x.com/OpenAI/", "http://twitter.com/OpenAI",
    "https://www.x.com/OpenAI?s=20", "https://mobile.twitter.com/OpenAI/", "x.com/OpenAI", "https://x.com/@OpenAI"]) {
    assert.deepEqual(normalizeHandle(input), { handle: "OpenAI", key: "openai" }, input);
  }
});

test("what is not one X account is refused", () => {
  for (const input of ["", " ", "@", "a".repeat(16), "has space", "名字", "a-b", "https://x.com/", "https://x.com/OpenAI/status/1",
    "https://example.com/OpenAI", "https://x.com.evil.com/OpenAI", "javascript:alert(1)", "https://x.com/home/../OpenAI", "https://x.com/home/%2e%2e/OpenAI", "https://x.com/./OpenAI", "https://x.com/OpenAI/..",
    "https://x.com:8080/OpenAI", "https://user@x.com/OpenAI", ["https://user", "p"].join(":") + "@x.com/OpenAI", "https://x.com\\OpenAI", "https://x.com@evil.com/OpenAI", "//x.com/OpenAI", "a/b", "@@a"]) {
    assert.equal(normalizeHandle(input), null, JSON.stringify(input));
  }
  assert.equal(normalizeHandle(undefined), null);
  assert.equal(normalizeHandle(42), null);
});

test("X's own pages are not accounts", () => {
  for (const name of ["home", "explore", "search", "settings", "i", "intent", "share", "hashtag", "messages", "notifications", "login", "signup"]) {
    assert.equal(normalizeHandle(`https://x.com/${name}`), null, name);
  }
});

const full = { APP_DATABASE_URL: "postgres://x", BETTER_AUTH_URL: "http://localhost:3456", BETTER_AUTH_SECRET: "s", GOOGLE_CLIENT_ID: "i", GOOGLE_CLIENT_SECRET: "k" };

test("the user features are on only when all five settings are present", () => {
  assert.equal(appEnabled(full), true);
  for (const key of Object.keys(full)) assert.equal(appEnabled({ ...full, [key]: "" }), false, key);
  assert.equal(appEnabled({}), false);
});

test("an administrator is a verified address on the list, whatever its case", () => {
  const admins = ["owner@example.com", "second@example.com"];
  assert.equal(isAdmin({ email: "owner@example.COM", emailVerified: true }, admins), true);
  assert.equal(isAdmin({ email: " Second@Example.com ", emailVerified: true }, admins), true);
  assert.equal(isAdmin({ email: "owner@example.com", emailVerified: false }, admins), false);
  assert.equal(isAdmin({ email: "other@example.com", emailVerified: true }, admins), false);
  assert.equal(isAdmin(null, admins), false);
  assert.equal(isAdmin({ email: "owner@example.com", emailVerified: true }, []), false);
  assert.equal(isAdmin({ email: "", emailVerified: true }, [""]), false);
});

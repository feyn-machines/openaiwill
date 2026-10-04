import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import ts from "typescript";

// Real PostgreSQL, in a scratch database with a throwaway role. The owner's working database and the
// real oaw_app role are never touched. Skipped when the local admin password file is absent.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const PASSWORD_FILE = `${ROOT}data/postgres/password`;
const SKIP = existsSync(PASSWORD_FILE) ? false : "no local PostgreSQL (data/postgres/password)";
const require = createRequire(import.meta.url);

let store;
let pool;
let admin;
let names;

const transpile = (path) =>
  ts.transpileModule(readFileSync(path, "utf8"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;

before(async () => {
  if (SKIP) return;
  const { Client, Pool } = require("pg");
  const token = randomBytes(6).toString("hex");
  const password = randomBytes(16).toString("hex");
  names = { database: `openaiwill_store_test_${token}`, role: `oaw_store_test_${token}`, password };
  const adminPassword = readFileSync(PASSWORD_FILE, "utf8").trim();
  const connect = (database) => new Client({ host: "127.0.0.1", port: 7543, user: "openaiwill", password: adminPassword, database });
  admin = connect("postgres");
  await admin.connect();
  await admin.query(`CREATE DATABASE "${names.database}"`);
  const inner = connect(names.database);
  await inner.connect();
  try {
    await inner.query(`CREATE ROLE "${names.role}" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '${password}'`);
    await inner.query(`ALTER ROLE "${names.role}" SET search_path = app`);
    await inner.query(`GRANT CONNECT ON DATABASE "${names.database}" TO "${names.role}"`);
    await inner.query(`CREATE SCHEMA app AUTHORIZATION "${names.role}"`);
  } finally {
    await inner.end();
  }
  pool = new Pool({ host: "127.0.0.1", port: 7543, user: names.role, password, database: names.database, max: 6 });
  await pool.query(readFileSync(`${ROOT}db/app/001_app.sql`, "utf8"));
  const js = transpile(`${ROOT}src/lib/app-store.ts`);
  store = await import(`data:text/javascript;charset=utf-8,${encodeURIComponent(js)}`);
});

after(async () => {
  if (SKIP) return;
  await pool?.end();
  if (admin && names) {
    await admin.query(`DROP DATABASE IF EXISTS "${names.database}" WITH (FORCE)`);
    await admin.query(`DROP ROLE IF EXISTS "${names.role}"`);
  }
  await admin?.end();
});

let counter = 0;
async function user() {
  counter += 1;
  const id = `u${counter}-${randomBytes(3).toString("hex")}`;
  await pool.query(
    'INSERT INTO app."user" (id, name, email, "emailVerified") VALUES ($1, $2, $3, true)',
    [id, `User ${counter}`, `${id}@example.com`],
  );
  return id;
}
const input = (userId, handle, extra = {}) => ({ userId, handle, key: handle.toLowerCase(), ownerKind: "person", note: null, ...extra });

test("a new account is created and listed", { skip: SKIP }, async () => {
  const id = await user();
  const made = await store.createSubmission(pool, input(id, "OpenAI", { note: "why" }));
  assert.equal(made.result, "created");
  assert.equal(made.submission.handle, "OpenAI");
  assert.equal(made.submission.status, "pending");
  assert.equal(made.submission.note, "why");
  assert.equal(made.submission.reason, null);
  assert.equal(made.submission.decidedAt, null);
  assert.equal(typeof made.submission.id, "string");
});

test("the same account again is a duplicate and returns the first row", { skip: SKIP }, async () => {
  const id = await user();
  const first = await store.createSubmission(pool, input(id, "Anthropic", { ownerKind: "organization" }));
  const again = await store.createSubmission(pool, input(id, "Anthropic", { ownerKind: "person", note: "later" }));
  assert.equal(again.result, "duplicate");
  assert.deepEqual(again.submission, first.submission);
  const { rows } = await pool.query("SELECT count(*)::int AS n FROM app.submissions WHERE user_id = $1", [id]);
  assert.equal(rows[0].n, 1);
});

test("the caller passes a lower-case key; display case is kept, comparison is on the key", { skip: SKIP }, async () => {
  const id = await user();
  await store.createSubmission(pool, input(id, "SamA"));
  const { rows } = await pool.query("SELECT handle, display_handle FROM app.submissions WHERE user_id = $1", [id]);
  assert.deepEqual(rows[0], { handle: "sama", display_handle: "SamA" });
  const again = await store.createSubmission(pool, { ...input(id, "SAMA"), key: "sama" });
  assert.equal(again.result, "duplicate");
  assert.equal(again.submission.handle, "SamA");
});

test("ten pending is the limit; a decision frees a place", { skip: SKIP }, async () => {
  const id = await user();
  for (let n = 0; n < store.PENDING_LIMIT; n += 1) {
    assert.equal((await store.createSubmission(pool, input(id, `acct_${n}`))).result, "created");
  }
  assert.equal((await store.createSubmission(pool, input(id, "acct_extra"))).result, "limit");
  // An existing account is still reported as a duplicate at the limit.
  assert.equal((await store.createSubmission(pool, input(id, "acct_3"))).result, "duplicate");
  await pool.query(
    "UPDATE app.submissions SET status = 'approved', decided_at = now() WHERE user_id = $1 AND handle = 'acct_0'",
    [id],
  );
  assert.equal((await store.createSubmission(pool, input(id, "acct_extra"))).result, "created");
});

test("two concurrent submits of one account give one created and one duplicate", { skip: SKIP }, async () => {
  const id = await user();
  const results = await Promise.all([
    store.createSubmission(pool, input(id, "Race")),
    store.createSubmission(pool, input(id, "Race")),
    store.createSubmission(pool, input(id, "Race")),
  ]);
  assert.deepEqual(results.map((r) => r.result).sort(), ["created", "duplicate", "duplicate"]);
});

test("concurrent submits cannot pass the limit", { skip: SKIP }, async () => {
  const id = await user();
  const results = await Promise.all(Array.from({ length: 14 }, (_, n) => store.createSubmission(pool, input(id, `burst_${n}`))));
  assert.equal(results.filter((r) => r.result === "created").length, store.PENDING_LIMIT);
  assert.equal(results.filter((r) => r.result === "limit").length, 4);
});

test("listing returns only the user's rows, newest first, with ISO timestamps", { skip: SKIP }, async () => {
  const mine = await user();
  const other = await user();
  await store.createSubmission(pool, input(mine, "first_one"));
  await store.createSubmission(pool, input(other, "not_mine"));
  await store.createSubmission(pool, input(mine, "second_one", { ownerKind: "organization" }));
  await pool.query(
    "UPDATE app.submissions SET status = 'rejected', decision_reason = 'no', decided_at = now() WHERE user_id = $1 AND handle = 'first_one'",
    [mine],
  );
  const list = await store.listSubmissions(pool, mine);
  assert.deepEqual(list.map((s) => s.handle), ["second_one", "first_one"]);
  assert.equal(list[0].ownerKind, "organization");
  for (const row of list) assert.equal(new Date(row.createdAt).toISOString(), row.createdAt);
  assert.equal(list[1].status, "rejected");
  assert.equal(list[1].reason, "no");
  assert.equal(new Date(list[1].decidedAt).toISOString(), list[1].decidedAt);
  assert.deepEqual(await store.listSubmissions(pool, "nobody"), []);
});

test("a submit for a user that does not exist is no_user and writes nothing", { skip: SKIP }, async () => {
  const made = await store.createSubmission(pool, input("ghost-user", "Ghost"));
  assert.deepEqual(made, { result: "no_user" });
  const { rows } = await pool.query("SELECT count(*)::int AS n FROM app.submissions WHERE handle = 'ghost'");
  assert.equal(rows[0].n, 0);
});

const sub = (userId, extra = {}) => ({ userId, language: "en", updates: false, weekly: false, ...extra });
const rows = async (userId) =>
  (await pool.query("SELECT topic, language, subscribed_at, unsubscribed_at FROM app.subscriptions WHERE user_id = $1 ORDER BY topic", [userId])).rows;

test("subscribing to both topics stores two active rows", { skip: SKIP }, async () => {
  const id = await user();
  assert.deepEqual(await store.getSubscriptions(pool, id), { updates: false, weekly: false });
  assert.deepEqual(await store.setSubscriptions(pool, sub(id, { updates: true, weekly: true })), { updates: true, weekly: true });
  const stored = await rows(id);
  assert.deepEqual(stored.map((r) => r.topic), ["updates", "weekly"]);
  for (const row of stored) assert.equal(row.unsubscribed_at, null);
  assert.deepEqual(store.TOPICS, ["updates", "weekly"]);
});

test("unsubscribing keeps the row and reports false; saving again keeps subscribed_at", { skip: SKIP }, async () => {
  const id = await user();
  await store.setSubscriptions(pool, sub(id, { updates: true, weekly: true }));
  const before = await rows(id);
  assert.deepEqual(await store.setSubscriptions(pool, sub(id, { updates: true, weekly: false })), { updates: true, weekly: false });
  const after = await rows(id);
  assert.equal(after.length, 2);
  assert.equal(after[1].topic, "weekly");
  assert.ok(after[1].unsubscribed_at instanceof Date);
  assert.equal(after[0].unsubscribed_at, null);
  assert.deepEqual(after[0].subscribed_at, before[0].subscribed_at);
  // Unsubscribing again does not move the first unsubscribe time.
  await store.setSubscriptions(pool, sub(id, { updates: true, weekly: false }));
  assert.deepEqual((await rows(id))[1].unsubscribed_at, after[1].unsubscribed_at);
});

test("unsubscribing a topic never subscribed creates no row", { skip: SKIP }, async () => {
  const id = await user();
  assert.deepEqual(await store.setSubscriptions(pool, sub(id)), { updates: false, weekly: false });
  assert.deepEqual(await rows(id), []);
  await store.setSubscriptions(pool, sub(id, { weekly: true }));
  assert.deepEqual((await rows(id)).map((r) => r.topic), ["weekly"]);
});

test("re-subscribing clears unsubscribed_at and renews subscribed_at; language follows the last save", { skip: SKIP }, async () => {
  const id = await user();
  await store.setSubscriptions(pool, sub(id, { updates: true }));
  const first = (await rows(id))[0];
  await store.setSubscriptions(pool, sub(id));
  await new Promise((resolve) => setTimeout(resolve, 10));
  assert.deepEqual(await store.setSubscriptions(pool, sub(id, { updates: true, language: "zh-CN" })), { updates: true, weekly: false });
  const again = (await rows(id))[0];
  assert.equal(again.unsubscribed_at, null);
  assert.ok(again.subscribed_at > first.subscribed_at);
  assert.equal(again.language, "zh-CN");
  // Changing language while active keeps the date.
  await store.setSubscriptions(pool, sub(id, { updates: true, language: "en" }));
  const last = (await rows(id))[0];
  assert.equal(last.language, "en");
  assert.deepEqual(last.subscribed_at, again.subscribed_at);
});

test("one user's subscriptions do not affect another's", { skip: SKIP }, async () => {
  const a = await user();
  const b = await user();
  await store.setSubscriptions(pool, sub(a, { updates: true }));
  assert.deepEqual(await store.getSubscriptions(pool, b), { updates: false, weekly: false });
});

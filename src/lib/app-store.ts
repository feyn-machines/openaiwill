import type { Pool } from "pg";
import type { OwnerKind } from "./handles";

/**
 * Reader submissions in schema `app`. Every function takes the pool first so the tests can pass their
 * own. Imports are type-only: the tests transpile this file and load it as it is.
 */

export type Submission = {
  id: string;
  handle: string;
  ownerKind: OwnerKind;
  note: string | null;
  status: "pending" | "approved" | "rejected";
  reason: string | null;
  createdAt: string;
  decidedAt: string | null;
};

export type CreateResult =
  | { result: "created"; submission: Submission }
  | { result: "duplicate"; submission: Submission }
  | { result: "limit" }
  | { result: "no_user" };

export const PENDING_LIMIT = 10;

type Row = {
  id: string;
  display_handle: string;
  owner_kind: OwnerKind;
  note: string | null;
  status: Submission["status"];
  decision_reason: string | null;
  created_at: Date;
  decided_at: Date | null;
};

const COLUMNS = "id, display_handle, owner_kind, note, status, decision_reason, created_at, decided_at";

function toSubmission(row: Row): Submission {
  return {
    id: String(row.id),
    handle: row.display_handle,
    ownerKind: row.owner_kind,
    note: row.note,
    status: row.status,
    reason: row.decision_reason,
    createdAt: row.created_at.toISOString(),
    decidedAt: row.decided_at ? row.decided_at.toISOString() : null,
  };
}

/** The user's submissions, newest first. */
export async function listSubmissions(db: Pool, userId: string): Promise<Submission[]> {
  const { rows } = await db.query<Row>(
    `SELECT ${COLUMNS} FROM app.submissions WHERE user_id = $1 ORDER BY created_at DESC, id DESC`,
    [userId],
  );
  return rows.map(toSubmission);
}

/**
 * One transaction per call. The lock on the user's row serialises that user's submits, so the
 * duplicate check and the pending count cannot be raced. `key` is the lower-case handle.
 */
export async function createSubmission(
  db: Pool,
  input: { userId: string; handle: string; key: string; ownerKind: OwnerKind; note: string | null },
): Promise<CreateResult> {
  const client = await db.connect();
  try {
    await client.query("BEGIN");
    const locked = await client.query('SELECT 1 FROM app."user" WHERE id = $1 FOR UPDATE', [input.userId]);
    if (locked.rows.length === 0) {
      await client.query("ROLLBACK");
      return { result: "no_user" };
    }
    const existing = await client.query<Row>(
      `SELECT ${COLUMNS} FROM app.submissions WHERE user_id = $1 AND platform = 'x' AND handle = $2`,
      [input.userId, input.key],
    );
    if (existing.rows[0]) {
      await client.query("COMMIT");
      return { result: "duplicate", submission: toSubmission(existing.rows[0]) };
    }
    const pending = await client.query<{ n: number }>(
      "SELECT count(*)::int AS n FROM app.submissions WHERE user_id = $1 AND status = 'pending'",
      [input.userId],
    );
    if (pending.rows[0].n >= PENDING_LIMIT) {
      await client.query("COMMIT");
      return { result: "limit" };
    }
    const made = await client.query<Row>(
      `INSERT INTO app.submissions (user_id, handle, display_handle, owner_kind, note)
       VALUES ($1, $2, $3, $4, $5) RETURNING ${COLUMNS}`,
      [input.userId, input.key, input.handle, input.ownerKind, input.note],
    );
    await client.query("COMMIT");
    return { result: "created", submission: toSubmission(made.rows[0]) };
  } catch (error) {
    await client.query("ROLLBACK").catch(() => undefined);
    throw error;
  } finally {
    client.release();
  }
}

export const TOPICS = ["updates", "weekly"] as const;
export type Topic = (typeof TOPICS)[number];
export type Subscriptions = { updates: boolean; weekly: boolean };

/** Which topics the user is subscribed to now. */
export async function getSubscriptions(db: Pool, userId: string): Promise<Subscriptions> {
  const { rows } = await db.query<{ topic: Topic }>(
    "SELECT topic FROM app.subscriptions WHERE user_id = $1 AND unsubscribed_at IS NULL",
    [userId],
  );
  const active = new Set(rows.map((row) => row.topic));
  return { updates: active.has("updates"), weekly: active.has("weekly") };
}

/**
 * Sets both topics at once. On: upsert, active again, language as given; `subscribed_at` is kept while
 * the topic stays active and renewed when it was unsubscribed. Off: marks the row unsubscribed only if
 * it is active; a topic never subscribed gets no row.
 */
export async function setSubscriptions(
  db: Pool,
  input: { userId: string; language: "en" | "zh-CN"; updates: boolean; weekly: boolean },
): Promise<Subscriptions> {
  const client = await db.connect();
  try {
    await client.query("BEGIN");
    for (const topic of TOPICS) {
      if (input[topic]) {
        await client.query(
          `INSERT INTO app.subscriptions (user_id, topic, language) VALUES ($1, $2, $3)
           ON CONFLICT (user_id, topic) DO UPDATE SET
             language = EXCLUDED.language,
             subscribed_at = CASE WHEN app.subscriptions.unsubscribed_at IS NULL THEN app.subscriptions.subscribed_at ELSE now() END,
             unsubscribed_at = NULL`,
          [input.userId, topic, input.language],
        );
      } else {
        await client.query(
          "UPDATE app.subscriptions SET unsubscribed_at = now() WHERE user_id = $1 AND topic = $2 AND unsubscribed_at IS NULL",
          [input.userId, topic],
        );
      }
    }
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK").catch(() => undefined);
    throw error;
  } finally {
    client.release();
  }
  return getSubscriptions(db, input.userId);
}

export type AdminGroup = {
  handle: string;
  displayHandle: string;
  ownerKind: OwnerKind;
  status: "pending" | "approved" | "rejected";
  count: number;
  firstAt: string;
  decidedAt: string | null;
  decidedBy: string | null;
  reason: string | null;
  importedAt: string | null;
  requests: { name: string; email: string; note: string | null; createdAt: string }[];
};

type GroupRow = {
  handle: string;
  display_handle: string;
  owner_kind: OwnerKind;
  status: AdminGroup["status"];
  count: number;
  first_at: Date;
  decided_at: Date | null;
  decided_by: string | null;
  reason: string | null;
  imported_at: Date | null;
  requests: { name: string; email: string; note: string | null; createdAt: string }[];
};

const MAX_DECIDED_GROUPS = 200;

/**
 * Pending: one group per account and kind, oldest first. Decided: one group per account, kind and
 * decision moment, newest first, at most 200. `decidedBy` is the deciding user's address.
 */
export async function adminGroups(db: Pool, view: "pending" | "decided"): Promise<AdminGroup[]> {
  const pending = view === "pending";
  const { rows } = await db.query<GroupRow>(
    `SELECT s.handle, min(s.display_handle) AS display_handle, s.owner_kind, s.status,
            count(*)::int AS count, min(s.created_at) AS first_at,
            s.decided_at, min(d.email) AS decided_by, min(s.decision_reason) AS reason, min(s.imported_at) AS imported_at,
            json_agg(json_build_object('name', u.name, 'email', u.email, 'note', s.note, 'createdAt', s.created_at)
                     ORDER BY s.created_at, s.id) AS requests
       FROM app.submissions s
       JOIN app."user" u ON u.id = s.user_id
       LEFT JOIN app."user" d ON d.id = s.decided_by
      WHERE s.platform = 'x' AND ${pending ? "s.status = 'pending'" : "s.status <> 'pending'"}
      GROUP BY s.handle, s.owner_kind, s.status, s.decided_at
      ORDER BY ${pending ? "min(s.created_at), s.handle" : "s.decided_at DESC, s.handle"}
      ${pending ? "" : `LIMIT ${MAX_DECIDED_GROUPS}`}`,
  );
  return rows.map((row) => ({
    handle: row.handle,
    displayHandle: row.display_handle,
    ownerKind: row.owner_kind,
    status: row.status,
    count: row.count,
    firstAt: row.first_at.toISOString(),
    decidedAt: row.decided_at ? row.decided_at.toISOString() : null,
    decidedBy: row.decided_by,
    reason: row.reason,
    importedAt: row.imported_at ? row.imported_at.toISOString() : null,
    requests: row.requests,
  }));
}

/**
 * Decides every pending row of the account and kind in one statement; returns how many rows changed.
 * 0 means someone decided it first. Decided rows are not touched (the trigger would refuse them).
 */
export async function decide(
  db: Pool,
  input: { handle: string; ownerKind: OwnerKind; decision: "approved" | "rejected"; reason: string | null; adminId: string },
): Promise<number> {
  const { rowCount } = await db.query(
    `UPDATE app.submissions
        SET status = $1, decided_by = $2, decision_reason = $3, decided_at = now()
      WHERE platform = 'x' AND handle = $4 AND owner_kind = $5 AND status = 'pending'`,
    [input.decision, input.adminId, input.decision === "rejected" ? input.reason : null, input.handle, input.ownerKind],
  );
  return rowCount ?? 0;
}

/** Active subscriptions only; `total` counts each user once. */
export async function subscriberCounts(db: Pool): Promise<{ total: number; updates: number; weekly: number }> {
  const { rows } = await db.query<{ total: number; updates: number; weekly: number }>(
    `SELECT count(DISTINCT user_id)::int AS total,
            (count(*) FILTER (WHERE topic = 'updates'))::int AS updates,
            (count(*) FILTER (WHERE topic = 'weekly'))::int AS weekly
       FROM app.subscriptions WHERE unsubscribed_at IS NULL`,
  );
  return rows[0];
}

/** One row per user with an active subscription; topics joined with "+", the earliest active date. */
export async function subscriberRows(
  db: Pool,
): Promise<{ email: string; name: string; language: string; topics: string; subscribedAt: string }[]> {
  const { rows } = await db.query<{ email: string; name: string; language: string; topics: string; subscribed_at: Date }>(
    `SELECT u.email, u.name,
            (array_agg(s.language ORDER BY s.subscribed_at DESC, s.topic))[1] AS language,
            string_agg(s.topic, '+' ORDER BY s.topic) AS topics,
            min(s.subscribed_at) AS subscribed_at
       FROM app.subscriptions s JOIN app."user" u ON u.id = s.user_id
      WHERE s.unsubscribed_at IS NULL
      GROUP BY u.id, u.email, u.name
      ORDER BY min(s.subscribed_at), u.email`,
  );
  return rows.map((row) => ({ email: row.email, name: row.name, language: row.language, topics: row.topics, subscribedAt: row.subscribed_at.toISOString() }));
}

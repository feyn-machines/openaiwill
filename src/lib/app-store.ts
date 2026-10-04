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

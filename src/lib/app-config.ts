/**
 * Whether the signed-in features exist in this process, and who administers them.
 * No imports: the unit tests load this source directly.
 */
type Env = Record<string, string | undefined>;

const REQUIRED = ["APP_DATABASE_URL", "BETTER_AUTH_URL", "BETTER_AUTH_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"] as const;

/** Sign-in, submissions and subscriptions need all five; without them the site is the public pages only. */
export function appEnabled(env: Env = process.env): boolean {
  return REQUIRED.every((key) => Boolean(env[key]));
}

/** A Google address that Google reports as verified and that is on the administrator list (`app.admins`). */
export function isAdmin(user: { email?: string | null; emailVerified?: boolean | null } | null | undefined, admins: readonly string[]): boolean {
  if (!user?.email || user.emailVerified !== true) return false;
  const email = user.email.trim().toLowerCase();
  return email !== "" && admins.some((entry) => entry.trim().toLowerCase() === email);
}

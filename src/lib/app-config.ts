/**
 * Whether the signed-in features exist in this process, and who administers them.
 * No imports: the unit tests load this source directly.
 */
type Env = Record<string, string | undefined>;

const REQUIRED = ["APP_DATABASE_URL", "BETTER_AUTH_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"] as const;

/** Sign-in, submissions and subscriptions need all four; without them the site is the public pages only. */
export function appEnabled(env: Env = process.env): boolean {
  return REQUIRED.every((key) => Boolean(env[key]));
}

export function adminEmails(env: Env = process.env): string[] {
  return (env.ADMIN_EMAILS ?? "").split(",").map((entry) => entry.trim().toLowerCase()).filter(Boolean);
}

/** A Google address that Google reports as verified and that is on the list. */
export function isAdmin(user: { email?: string | null; emailVerified?: boolean | null } | null | undefined, env: Env = process.env): boolean {
  if (!user?.email || user.emailVerified !== true) return false;
  return adminEmails(env).includes(user.email.trim().toLowerCase());
}

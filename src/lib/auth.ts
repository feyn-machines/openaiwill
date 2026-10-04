import { betterAuth } from "better-auth";
import { Pool } from "pg";
import { appEnabled } from "./app-config";

/**
 * Sign-in with Google. Better Auth keeps users and sessions in schema `app`; the role `oaw_app`
 * has `search_path = app`, so the table names it uses unqualified resolve there.
 */

type Auth = ReturnType<typeof build>;
type Held = { pool?: Pool; auth?: Auth };
const key = Symbol.for("openaiwill.app-auth");
const held = ((globalThis as Record<symbol, Held | undefined>)[key] ??= {});

/** The one pool for `APP_DATABASE_URL`; Better Auth and the app store share it. */
export function appPool(): Pool {
  if (held.pool) return held.pool;
  const url = process.env.APP_DATABASE_URL;
  if (!url) throw new Error("APP_DATABASE_URL is not set");
  const pool = new Pool({
    connectionString: url,
    max: 5,
    connectionTimeoutMillis: 5000,
    idleTimeoutMillis: 30000,
    query_timeout: 30000,
    application_name: "openaiwill-app",
  });
  pool.on("error", (error) => console.error(`[auth] idle connection error: ${error.message}`));
  held.pool = pool;
  return pool;
}

function build() {
  const baseURL = process.env.BETTER_AUTH_URL;
  if (!baseURL) throw new Error("BETTER_AUTH_URL is not set");
  return betterAuth({
    database: appPool(),
    baseURL,
    secret: process.env.BETTER_AUTH_SECRET,
    trustedOrigins: [new URL(baseURL).origin],
    socialProviders: {
      google: { clientId: process.env.GOOGLE_CLIENT_ID as string, clientSecret: process.env.GOOGLE_CLIENT_SECRET as string },
    },
    session: { expiresIn: 60 * 60 * 24 * 30 },
  });
}

export function getAuth(): Auth {
  if (!appEnabled()) throw new Error("sign-in is not configured");
  return (held.auth ??= build());
}

export type SessionUser = { id: string; email: string; name: string; image: string | null; emailVerified: boolean };

/** The signed-in user of this request; null when sign-in is off, nobody is signed in, or the lookup fails. */
export async function currentUser(request: Request): Promise<SessionUser | null> {
  if (!appEnabled()) return null;
  try {
    const session = await getAuth().api.getSession({ headers: request.headers });
    const user = session?.user;
    if (!user) return null;
    return { id: user.id, email: user.email, name: user.name, image: user.image ?? null, emailVerified: user.emailVerified === true };
  } catch (error) {
    console.error(`[auth] session lookup failed: ${error instanceof Error ? error.message : "unknown error"}`);
    return null;
  }
}

/** A verified address with a row in `app.admins`. One query per call, so a list change applies at once. */
export async function isAdminUser(user: { email?: string | null; emailVerified?: boolean | null } | null | undefined): Promise<boolean> {
  if (!user?.email || user.emailVerified !== true || !appEnabled()) return false;
  const { rowCount } = await appPool().query("SELECT 1 FROM app.admins WHERE email = lower($1)", [user.email.trim()]);
  return (rowCount ?? 0) > 0;
}

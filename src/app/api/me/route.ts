import { json } from "@/lib/api";
import { appEnabled } from "@/lib/app-config";
import { currentUser, isAdminUser } from "@/lib/auth";

export const dynamic = "force-dynamic";

const NONE = { updates: false, weekly: false };

export async function GET(request: Request) {
  if (!appEnabled()) return json({ enabled: false, user: null, admin: false, subscriptions: NONE });
  const user = await currentUser(request);
  if (!user) return json({ enabled: true, user: null, admin: false, subscriptions: NONE });
  let admin = false;
  try {
    admin = await isAdminUser(user);
  } catch (error) {
    console.error(`[auth] administrator lookup failed: ${error instanceof Error ? error.message : "unknown error"}`);
  }
  return json({ enabled: true, user: { name: user.name, email: user.email, image: user.image }, admin, subscriptions: NONE });
}

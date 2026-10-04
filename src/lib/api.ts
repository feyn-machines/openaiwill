/** Shared pieces of the JSON route handlers under `/api/`. */

const HEADERS = { "Cache-Control": "no-store", "X-Robots-Tag": "noindex" } as const;

/** A JSON answer that no cache may keep and no search engine may index. */
export function json(body: unknown, status = 200): Response {
  return Response.json(body, { status, headers: HEADERS });
}

export function notFound(): Response {
  return json({ error: "not_found" }, 404);
}

/** True when the request names an `Origin` and it is this site's own. */
export function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return false;
  try {
    return new URL(origin).origin === new URL(process.env.BETTER_AUTH_URL ?? request.url).origin;
  } catch {
    return false;
  }
}

const hits = new Map<string, number[]>();

/** In-memory, per process. Returns false once `key` has made `limit` calls within `windowMs`. */
export function rateLimit(key: string, limit: number, windowMs: number): boolean {
  const now = Date.now();
  for (const [name, times] of hits) {
    const recent = times.filter((time) => now - time < windowMs);
    if (recent.length === 0) hits.delete(name);
    else if (name !== key) hits.set(name, recent);
  }
  const recent = (hits.get(key) ?? []).filter((time) => now - time < windowMs);
  if (recent.length >= limit) {
    hits.set(key, recent);
    return false;
  }
  recent.push(now);
  hits.set(key, recent);
  return true;
}

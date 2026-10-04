/** The public address. Not a secret and not per-environment: a candidate build names the same canonical pages. */
export const SITE_URL = "https://openaiwill.com";

const WWW_HOST = `www.${new URL(SITE_URL).host}`;

/**
 * The one host that is redirected to `SITE_URL`: `www.` plus the site's own host, with or without a port or a
 * trailing dot; no other suffix or prefix matches. `host` is a `Host` header value.
 */
export function isWwwHost(host: string | null | undefined): boolean {
  if (!host) return false;
  // A trailing dot and a port name the same host.
  const name = host.split(",")[0].trim().toLowerCase().replace(/:\d+$/, "").replace(/\.$/, "");
  return name === WWW_HOST;
}

/** `https://openaiwill.com` + the request's path and query; never built from the Host header. */
export function apexLocation(pathname: string, search: string): string {
  return `${SITE_URL}${pathname}${search}`;
}

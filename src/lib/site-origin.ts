/** The public address. Not a secret and not per-environment: a candidate build names the same canonical pages. */
export const SITE_URL = "https://openaiwill.com";

const WWW_HOST = `www.${new URL(SITE_URL).host}`;

/**
 * The one host that is redirected to `SITE_URL`: `www.` plus the site's own host, exactly (a port or
 * any other suffix or prefix does not match). `host` is a `Host`/`X-Forwarded-Host` value; with a list
 * (`a, b`) the first entry is the one the client addressed.
 */
export function isWwwHost(host: string | null | undefined): boolean {
  if (!host) return false;
  return host.split(",")[0].trim().toLowerCase() === WWW_HOST;
}

/** `https://openaiwill.com` + the request's path and query; never built from the Host header. */
export function apexLocation(pathname: string, search: string): string {
  return `${SITE_URL}${pathname}${search}`;
}

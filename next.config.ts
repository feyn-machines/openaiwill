import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * Statically typed links. Three `href` strings pointed at routes that had
   * been deleted - `/updates` in the header on every page, `/updates` again on
   * the homepage, `/domains/:id` in a component - and every one of them
   * survived a full `pnpm check`, because nothing in the suite reads an href.
   * A dead link renders as a working link and only fails for the reader.
   *
   * With this on, `typecheck` rejects an href that no route serves, so the
   * check that catches it is the one that already runs.
   *
   * Off while the pages sit under `/[lang]`: the route tree now only knows
   * `/en/...` addresses, so every unprefixed href is rejected. The language-aware
   * link helper restores the guarantee.
   */
  typedRoutes: false,

  /** The 404 for addresses no route matches, which no layout can render around. */
  experimental: { globalNotFound: true },
};

export default nextConfig;

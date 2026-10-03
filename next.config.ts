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
   * The pages sit under `/[lang]`, so the generated route tree only knows
   * `/en/...` and `/zh-CN/...` addresses and a bare `href="/markets"` is
   * rejected. Links go through `href()` in `src/lib/routes.ts`, which checks the
   * path as it would be under `/en` and adds the reader's language prefix, so
   * the guarantee above holds for every link built that way.
   */
  typedRoutes: true,

  /** The 404 for addresses no route matches, which no layout can render around. */
  experimental: { globalNotFound: true },
};

export default nextConfig;

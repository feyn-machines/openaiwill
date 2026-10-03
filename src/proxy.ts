import { NextResponse, type NextRequest } from "next/server";
import { LANGUAGE_COOKIE, LANGUAGE_COOKIE_MAX_AGE, languageRoute } from "./lib/i18n";

/**
 * Only a top-level navigation is a reader choosing a language. Speculative
 * prefetches and client-side data requests must not rewrite the saved choice
 * or be bounced to another language.
 */
function isNavigation(request: NextRequest) {
  const destination = request.headers.get("sec-fetch-dest");
  const purpose = request.headers.get("sec-purpose") ?? request.headers.get("purpose") ?? "";
  return (destination === null || destination === "document") && !purpose.includes("prefetch");
}

/**
 * English is served at unprefixed addresses and Chinese under `/zh-CN`; the
 * pages themselves live under `/[lang]`. The rules are in `languageRoute`.
 */
export function proxy(request: NextRequest) {
  const route = languageRoute({
    pathname: request.nextUrl.pathname,
    search: request.nextUrl.search,
    savedLanguage: request.cookies.get(LANGUAGE_COOKIE)?.value,
    navigation: isNavigation(request),
  });

  let response: NextResponse;
  if (route.kind === "redirect") {
    // `route.location` is a path on this host (see `languageRoute`). Next
    // resolves the Location it is given against the request, so it needs an
    // absolute URL here and turns a same-host one back into a relative Location.
    response = NextResponse.redirect(new URL(route.location, request.url), route.status);
    if (route.save) {
      response.cookies.set({
        name: LANGUAGE_COOKIE,
        value: route.save,
        path: "/",
        maxAge: LANGUAGE_COOKIE_MAX_AGE,
        sameSite: "lax",
      });
    }
  } else if (route.kind === "rewrite") {
    const url = request.nextUrl.clone();
    url.pathname = route.pathname;
    response = NextResponse.rewrite(url);
  } else {
    response = NextResponse.next();
  }

  // Only the production service may be indexed; a candidate build must not be.
  if (process.env.SITE_ENV !== "production") response.headers.set("X-Robots-Tag", "noindex");
  return response;
}

/**
 * Files that are not pages are named one by one. "Anything with an extension"
 * would be wrong: occupation addresses such as /occupations/11-1011.00 contain
 * a dot. The 32-hex `.txt` is the IndexNow key file in `public/`.
 */
export const config = {
  matcher: [
    "/((?!_next/|og/|healthz$|robots\\.txt$|sitemap\\.xml$|llms\\.txt$|icon\\.svg$|[0-9a-f]{32}\\.txt$).*)",
  ],
};

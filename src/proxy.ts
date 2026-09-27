import { NextResponse, type NextRequest } from "next/server";
import {
  LANGUAGE_COOKIE,
  LANGUAGE_COOKIE_MAX_AGE,
  LANGUAGE_HEADER,
  REQUEST_URL_HEADER,
  urlLanguage,
} from "./lib/i18n";

/** Next's own parameter on client navigations; never part of a shareable URL. */
const RSC_PARAM = "_rsc";

/**
 * Only a top-level navigation is a reader choosing a language. Speculative
 * prefetches and client-side data requests must not rewrite the saved choice.
 * Next strips its `RSC` / `Next-Router-Prefetch` headers before the proxy runs,
 * so the browser's own fetch metadata is what is left to read.
 */
function isNavigation(request: NextRequest) {
  const destination = request.headers.get("sec-fetch-dest");
  const purpose = request.headers.get("sec-purpose") ?? request.headers.get("purpose") ?? "";
  return (destination === null || destination === "document") && !purpose.includes("prefetch");
}

/**
 * A root layout cannot read `searchParams`, so an explicit `?lang=` in a shared
 * link is validated here and handed to the render as a request header. The path
 * travels with it so the language switch can keep the reader where they are.
 *
 * An explicit choice is also saved, so following one bilingual link does not
 * leave the rest of the site in the other language.
 */
export function proxy(request: NextRequest) {
  const requested = urlLanguage(request.nextUrl.search);

  const url = new URL(request.nextUrl);
  url.searchParams.delete(RSC_PARAM);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(REQUEST_URL_HEADER, `${url.pathname}${url.search}`);
  // Never trust an inbound value for this header.
  if (requested) requestHeaders.set(LANGUAGE_HEADER, requested);
  else requestHeaders.delete(LANGUAGE_HEADER);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  if (requested && isNavigation(request)) {
    response.cookies.set({
      name: LANGUAGE_COOKIE,
      value: requested,
      path: "/",
      maxAge: LANGUAGE_COOKIE_MAX_AGE,
      sameSite: "lax",
    });
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg).*)"],
};

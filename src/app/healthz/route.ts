import { dataRelease } from "@/lib/snapshot";

export const dynamic = "force-dynamic";

/**
 * Which code build is answering and which data release it is serving. The release
 * id is fixed when the build runs. With `SITE_REQUIRE_DATABASE=1` a server that is
 * not serving a release from the database answers 503, so a misconfigured one
 * cannot pass for a healthy one.
 */
export function GET() {
  const data = dataRelease();
  const required = process.env.SITE_REQUIRE_DATABASE === "1";
  const ok = !required || (data.source === "database" && data.releaseId !== null);
  return Response.json(
    { ok, release: process.env.RELEASE_ID ?? "dev", data },
    { status: ok ? 200 : 503, headers: { "Cache-Control": "no-store" } },
  );
}

import { dataRelease } from "@/lib/snapshot";

export const dynamic = "force-dynamic";

/** Which code build is answering and which data release it is serving. The release id is fixed when the build runs. */
export function GET() {
  return Response.json(
    { ok: true, release: process.env.RELEASE_ID ?? "dev", data: dataRelease() },
    { headers: { "Cache-Control": "no-store" } },
  );
}

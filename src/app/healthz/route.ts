export const dynamic = "force-static";

/** Which build is answering. The release id is fixed when the build runs. */
export function GET() {
  return Response.json({ ok: true, release: process.env.RELEASE_ID ?? "dev" });
}

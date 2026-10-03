import { join } from "node:path";
import { dataRelease, replaceSnapshot } from "./lib/snapshot";
import { activeReleaseId, loadFromDatabase, loadFromFiles } from "./lib/snapshot-source";

/**
 * Loads the data release and keeps it current. `register()` waits for it, so a
 * server that cannot load its data does not stay up.
 */
export async function loadData() {
  try {
    await load();
  } catch (error) {
    // The standalone server is already listening when this runs and would answer every
    // request with a 500 for good. A server that cannot load its data must not stay up.
    console.error(`[data-release] cannot load the data release, exiting: ${(error as Error).message}`);
    process.exit(1);
  }
}

async function load() {
  const url = process.env.DATABASE_URL;
  if (!url) {
    // Development, tests and CI: the published snapshot files, or no data at all.
    // The ignore comment keeps the file tracer from copying the whole project beside the server.
    const dir = process.env.SNAPSHOT_DIR ?? join(/* turbopackIgnore: true */ process.cwd(), "datasets", "published", "latest");
    try {
      const loaded = loadFromFiles(dir);
      replaceSnapshot(loaded?.payload ?? null, { releaseId: loaded?.releaseId ?? null, source: "files" });
    } catch (error) {
      // A malformed snapshot must not take the site down; the pages show the gap.
      console.error(`[data-release] snapshot files not loaded: ${(error as Error).message}`);
      replaceSnapshot(null, { releaseId: null, source: "none" });
    }
    return;
  }

  // An unreachable database throws here and stops the server; an empty one is the no-data state.
  const first = await loadFromDatabase(url);
  replaceSnapshot(first?.payload ?? null, { releaseId: first?.releaseId ?? null, source: "database" });
  console.log(`[data-release] loaded ${first?.releaseId ?? "no active release"} from the database`);

  const seconds = Number(process.env.SNAPSHOT_POLL_SECONDS);
  const interval = (Number.isFinite(seconds) && seconds > 0 ? seconds : 30) * 1000;
  let busy = false;
  setInterval(async () => {
    if (busy) return;
    busy = true;
    try {
      const id = await activeReleaseId(url);
      if (id && id !== dataRelease().releaseId) {
        const next = await loadFromDatabase(url);
        if (next && next.releaseId !== dataRelease().releaseId) {
          replaceSnapshot(next.payload, { releaseId: next.releaseId, source: "database" });
          console.log(`[data-release] now serving ${next.releaseId}`);
        }
      }
    } catch (error) {
      console.error(`[data-release] poll failed, keeping ${dataRelease().releaseId ?? "no data"}: ${(error as Error).message}`);
    } finally {
      busy = false;
    }
  }, interval).unref();
}

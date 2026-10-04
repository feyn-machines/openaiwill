"use client";

import { useEffect, useSyncExternalStore } from "react";
import type { Submission } from "@/lib/app-store";

type Snapshot = { state: "idle" | "ready"; list: Submission[] };

const EMPTY: Submission[] = [];
let snapshot: Snapshot = { state: "idle", list: EMPTY };
let started = false;
const listeners = new Set<() => void>();

function publish(next: Snapshot) {
  snapshot = next;
  listeners.forEach((listener) => listener());
}

/** One shared fetch of the signed-in reader's submissions. A signed-out answer is an empty list. */
export async function refreshSubmissions(): Promise<void> {
  started = true;
  try {
    const response = await fetch("/api/submissions", { cache: "no-store" });
    const body = response.ok ? ((await response.json()) as { submissions: Submission[] }) : { submissions: EMPTY };
    publish({ state: "ready", list: body.submissions });
  } catch {
    publish({ state: "ready", list: EMPTY });
  }
}

const IDLE: Snapshot = { state: "idle", list: EMPTY };

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

/** The shared list; loading starts the first time a signed-in reader (`active`) asks. */
export function useSubmissions(active: boolean): Snapshot {
  const current = useSyncExternalStore(subscribe, () => snapshot, () => IDLE);
  useEffect(() => {
    if (active && !started) void refreshSubmissions();
  }, [active]);
  return active ? current : IDLE;
}

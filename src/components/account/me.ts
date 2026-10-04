"use client";

import { useSyncExternalStore } from "react";

export type Me = {
  enabled: boolean;
  user: { name: string; email: string; image: string | null } | null;
  admin: boolean;
  subscriptions: { updates: boolean; weekly: boolean };
};

type Snapshot = { state: "loading" | "ready"; me: Me };

const EMPTY: Me = { enabled: false, user: null, admin: false, subscriptions: { updates: false, weekly: false } };
let snapshot: Snapshot = { state: "loading", me: EMPTY };
let started = false;
const listeners = new Set<() => void>();

function publish(next: Snapshot) {
  snapshot = next;
  listeners.forEach((listener) => listener());
}

/** One shared fetch of /api/me; every component that asks gets the same answer. */
export async function refreshMe(): Promise<void> {
  started = true;
  try {
    const response = await fetch("/api/me", { cache: "no-store" });
    const body = response.ok ? ((await response.json()) as Me) : EMPTY;
    publish({ state: "ready", me: body });
  } catch {
    publish({ state: "ready", me: EMPTY });
  }
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  if (!started) void refreshMe();
  return () => listeners.delete(listener);
};
const loading: Snapshot = { state: "loading", me: EMPTY };

export function useMe(): Snapshot {
  return useSyncExternalStore(subscribe, () => snapshot, () => loading);
}

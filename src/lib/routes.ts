import type { Route } from "next";

/** Site paths for the things a reader can open. One place, so a link and the page it points at cannot disagree. */
export const workSlug = (activityId: string) => activityId.replace(/^oaw:market:/, "");
export const workHref = (activityId: string) => `/work/${workSlug(activityId)}` as Route;
export const updateHref = (eventId: string) => `/updates/${eventId}` as Route;
export const marketHref = (marketId: string) => `/markets/${marketId.replace(/^oaw:market:/, "")}` as Route;

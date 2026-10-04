import { toNextJsHandler } from "better-auth/next-js";
import { notFound } from "@/lib/api";
import { appEnabled } from "@/lib/app-config";
import { getAuth } from "@/lib/auth";

export const dynamic = "force-dynamic";

function handler(method: "GET" | "POST") {
  return (request: Request) => {
    if (!appEnabled()) return notFound();
    return toNextJsHandler(getAuth())[method](request);
  };
}

export const GET = handler("GET");
export const POST = handler("POST");

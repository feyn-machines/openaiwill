import { createAuthClient } from "better-auth/react";

/** Same-origin client: the base URL is the address the page was loaded from. */
export const authClient = createAuthClient();

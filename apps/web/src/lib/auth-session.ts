import { headers } from "next/headers";

import { auth } from "@/lib/auth";
import { ensureAuthSchema } from "@/lib/signup";

export async function getServerSession() {
  try {
    await ensureAuthSchema();
    const hdrs = await headers();
    return await auth.api.getSession({
      headers: hdrs,
      query: { disableCookieCache: true },
    });
  } catch {
    return null;
  }
}

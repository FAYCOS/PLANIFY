import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";
import { ensureAuthSchema } from "@/lib/signup";
import { hasRole } from "@/lib/roles";

export async function requireAdmin(headers: Headers) {
  try {
    await ensureAuthSchema();
    const session = await auth.api.getSession({
      headers,
      query: { disableCookieCache: true },
    });
    const role = (session as { user?: { role?: string } } | null)?.user?.role;
    if (!session || !hasRole(role, "admin")) {
      return NextResponse.json({ error: "acces refuse" }, { status: 403 });
    }
    return null;
  } catch {
    return NextResponse.json({ error: "acces refuse" }, { status: 403 });
  }
}

export async function getAdminSession(headers: Headers) {
  try {
    await ensureAuthSchema();
    const session = await auth.api.getSession({
      headers,
      query: { disableCookieCache: true },
    });
    const role = (session as { user?: { role?: string } } | null)?.user?.role;
    if (!session || !hasRole(role, "admin")) {
      return null;
    }
    return session as { user: { id: string; orgId?: string | null; role?: string } };
  } catch {
    return null;
  }
}

import { NextResponse } from "next/server";
import { desc, eq, sql } from "drizzle-orm";

import { db } from "@/db";
import { teamMember, user } from "@/db/schema";
import { auth } from "@/lib/auth";
import { getAdminSession, requireAdmin } from "@/lib/require-admin";
import { ROLE_OPTIONS } from "@/lib/roles";
import { ensureDefaultTeam } from "@/lib/teams";

export async function GET(req: Request) {
  const guard = await requireAdmin(req.headers);
  if (guard) return guard;
  const session = await getAdminSession(req.headers);
  if (!session) {
    return NextResponse.json({ error: "acces refuse" }, { status: 403 });
  }
  const orgId = session.user.orgId ?? null;

  const baseQuery = db
    .select({
      id: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
      mustChangePassword: user.mustChangePassword,
      createdAt: user.createdAt,
    })
    .from(user);
  const rows = orgId
    ? await baseQuery.where(eq(user.orgId, orgId)).orderBy(desc(user.createdAt))
    : await baseQuery.orderBy(desc(user.createdAt));
  return NextResponse.json(rows);
}

export async function POST(req: Request) {
  const guard = await requireAdmin(req.headers);
  if (guard) return guard;
  const session = await getAdminSession(req.headers);
  const adminOrgId = session?.user?.orgId ?? null;

  const body = await req.json();
  const email = String(body?.email || "").trim().toLowerCase();
  const name = String(body?.name || "").trim();
  const roleRaw = String(body?.role || "member").trim();
  const allowedRoles = new Set(ROLE_OPTIONS.map((roleOption) => roleOption.value));
  const role = allowedRoles.has(roleRaw) ? roleRaw : "member";
  const password = String(body?.password || "");

  if (!email || !name || !password) {
    return NextResponse.json(
      { error: "Email, nom et mot de passe requis." },
      { status: 400 },
    );
  }

  let createdUser: any = null;
  try {
    const created = await auth.api.signUpEmail({
      headers: new Headers(),
      body: {
        email,
        name,
        password,
        rememberMe: false,
      },
    });
    createdUser = (created as any)?.user ?? (created as any)?.data?.user;
  } catch {
    return NextResponse.json(
      { error: "Creation utilisateur impossible." },
      { status: 400 },
    );
  }
  if (!createdUser?.id) {
    return NextResponse.json(
      { error: "Creation utilisateur impossible." },
      { status: 400 },
    );
  }

  await db
    .update(user)
    .set({
      role,
      emailVerified: true,
      mustChangePassword: true,
      orgId: adminOrgId,
      updatedAt: sql`now()`,
    })
    .where(eq(user.id, createdUser.id));

  if (adminOrgId) {
    const defaultTeam = await ensureDefaultTeam(adminOrgId, session?.user?.id);
    if (defaultTeam?.id) {
      await db
        .insert(teamMember)
        .values({
          teamId: defaultTeam.id,
          userId: createdUser.id,
          role,
        })
        .onConflictDoNothing();
    }
  }

  return NextResponse.json({ id: createdUser.id });
}

import { NextResponse } from "next/server";
import { desc, eq, sql } from "drizzle-orm";

import { db } from "@/db";
import { team, teamMember } from "@/db/schema";
import { requireOrg } from "@/lib/auth-guard";
import { getAdminSession, requireAdmin } from "@/lib/require-admin";

export async function GET() {
  const guard = await requireOrg();
  if ("response" in guard) return guard.response;

  const rows = await db
    .select({
      id: team.id,
      name: team.name,
      description: team.description,
      createdAt: team.createdAt,
      membersCount: sql<number>`COUNT(${teamMember.id})`,
    })
    .from(team)
    .leftJoin(teamMember, eq(teamMember.teamId, team.id))
    .where(eq(team.orgId, guard.orgId))
    .groupBy(team.id)
    .orderBy(desc(team.createdAt));

  return NextResponse.json(rows);
}

export async function POST(req: Request) {
  const guard = await requireAdmin(req.headers);
  if (guard) return guard;
  const session = await getAdminSession(req.headers);
  if (!session?.user?.orgId) {
    return NextResponse.json({ error: "Organisation manquante." }, { status: 403 });
  }

  const body = await req.json();
  const name = String(body?.name || "").trim();
  const description = String(body?.description || "").trim() || null;

  if (!name) {
    return NextResponse.json({ error: "Nom d'equipe requis." }, { status: 400 });
  }

  const [created] = await db
    .insert(team)
    .values({
      orgId: session.user.orgId,
      name,
      description,
      createdByUserId: session.user.id,
    })
    .returning();

  return NextResponse.json(created, { status: 201 });
}

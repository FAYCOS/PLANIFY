import { NextResponse } from "next/server";
import { and, desc, eq, ilike, or } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { client } from "@/db/schema";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

const clientSchema = z.object({
  nom: z.string().min(1),
  prenom: z.string().optional().nullable(),
  email: z.string().email().optional().nullable(),
  telephone: z.string().optional().nullable(),
  adresseFacturation: z.string().optional().nullable(),
  categories: z.string().optional().nullable(),
  notes: z.string().optional().nullable(),
});

export async function GET(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q")?.trim();
  const limit = Number(searchParams.get("limit") ?? 100);
  const baseQuery = tenantDb
    .select()
    .from(client)
    .where(eq(client.orgId, guard.orgId));
  const filteredQuery = q
    ? baseQuery.where(
        and(
          eq(client.orgId, guard.orgId),
          or(
            ilike(client.nom, `%${q}%`),
            ilike(client.email, `%${q}%`),
            ilike(client.telephone, `%${q}%`),
          ),
        ),
      )
    : baseQuery;

  const rows = await filteredQuery
    .orderBy(desc(client.createdAt))
    .limit(Number.isFinite(limit) ? Math.min(limit, 200) : 100);
  return NextResponse.json(rows);
}

export async function POST(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const payload = await req.json();
  const data = clientSchema.parse(payload);
  const hdrs = await headers();
  const session = guard.session;

  const [created] = await tenantDb
    .insert(client)
    .values({
      orgId: guard.orgId,
      nom: data.nom,
      prenom: data.prenom ?? null,
      email: data.email ?? null,
      telephone: data.telephone ?? null,
      adresseFacturation: data.adresseFacturation ?? null,
      categories: data.categories ?? null,
      notes: data.notes ?? null,
    })
    .returning();

  await logAudit({
    action: "client.created",
    entityType: "client",
    entityId: created.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { email: created.email, nom: created.nom, prenom: created.prenom },
  });

  return NextResponse.json(created);
}

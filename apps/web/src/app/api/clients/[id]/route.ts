import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { client } from "@/db/schema";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

const updateSchema = z.object({
  nom: z.string().min(1).optional(),
  prenom: z.string().optional().nullable(),
  email: z.string().email().optional().nullable(),
  telephone: z.string().optional().nullable(),
  adresseFacturation: z.string().optional().nullable(),
  categories: z.string().optional().nullable(),
  notes: z.string().optional().nullable(),
});

type Params = { params: Promise<{ id: string }> };

export async function GET(_: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const [row] = await tenantDb
    .select()
    .from(client)
    .where(and(eq(client.id, id), eq(client.orgId, guard.orgId)))
    .limit(1);
  if (!row) {
    return NextResponse.json({ error: "client introuvable" }, { status: 404 });
  }
  return NextResponse.json(row);
}

export async function PUT(req: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const payload = await req.json();
  const data = updateSchema.parse(payload);
  const hdrs = await headers();
  const session = guard.session;

  const [updated] = await tenantDb
    .update(client)
    .set({
      nom: data.nom,
      prenom: data.prenom ?? null,
      email: data.email ?? null,
      telephone: data.telephone ?? null,
      adresseFacturation: data.adresseFacturation ?? null,
      categories: data.categories ?? null,
      notes: data.notes ?? null,
      updatedAt: new Date(),
    })
    .where(and(eq(client.id, id), eq(client.orgId, guard.orgId)))
    .returning();

  if (!updated) {
    return NextResponse.json({ error: "client introuvable" }, { status: 404 });
  }

  await logAudit({
    action: "client.updated",
    entityType: "client",
    entityId: updated.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { email: updated.email, nom: updated.nom, prenom: updated.prenom },
  });

  return NextResponse.json(updated);
}

export async function DELETE(_: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const hdrs = await headers();
  const session = guard.session;
  const [deleted] = await tenantDb
    .delete(client)
    .where(and(eq(client.id, id), eq(client.orgId, guard.orgId)))
    .returning();

  if (!deleted) {
    return NextResponse.json({ error: "client introuvable" }, { status: 404 });
  }

  await logAudit({
    action: "client.deleted",
    entityType: "client",
    entityId: deleted.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { email: deleted.email, nom: deleted.nom, prenom: deleted.prenom },
  });

  return NextResponse.json({ ok: true });
}

import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { client, facture, prestation } from "@/db/schema";
import { getNextDocumentNumber } from "@/lib/sequences";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

const updateSchema = z.object({
  numero: z.string().optional(),
  clientId: z.string().uuid().optional(),
  prestationId: z.string().uuid().optional().nullable(),
  prestationTitre: z.string().optional(),
  montantHt: z.string().optional(),
  montantTtc: z.string().optional(),
  statut: z.string().optional(),
});

type Params = { params: Promise<{ id: string }> };

export async function GET(_: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const [row] = await tenantDb
    .select()
    .from(facture)
    .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)))
    .limit(1);
  if (!row) {
    return NextResponse.json({ error: "facture introuvable" }, { status: 404 });
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

  const [existing] = await tenantDb
    .select()
    .from(facture)
    .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)))
    .limit(1);
  if (!existing) {
    return NextResponse.json({ error: "facture introuvable" }, { status: 404 });
  }
  if (existing.statut === "envoye" || existing.statut === "paye") {
    return NextResponse.json(
      { error: "facture verrouillee" },
      { status: 400 },
    );
  }

  const clientId = data.clientId ?? existing.clientId;
  let clientNom = existing.clientNom;
  let clientEmail = existing.clientEmail;
  let clientTelephone = existing.clientTelephone;
  let clientAdresse = existing.clientAdresse;

  if (clientId && clientId !== existing.clientId) {
    const [clientRow] = await tenantDb
      .select()
      .from(client)
      .where(and(eq(client.id, clientId), eq(client.orgId, guard.orgId)))
      .limit(1);
    if (!clientRow) {
      return NextResponse.json({ error: "client introuvable" }, { status: 400 });
    }
    clientNom =
      [clientRow.prenom, clientRow.nom].filter(Boolean).join(" ") ||
      clientRow.nom;
    clientEmail = clientRow.email ?? null;
    clientTelephone = clientRow.telephone ?? null;
    clientAdresse = clientRow.adresseFacturation ?? null;
  }

  let prestationTitre = data.prestationTitre ?? existing.prestationTitre;
  if (data.prestationId && !data.prestationTitre) {
    const [mission] = await tenantDb
      .select()
      .from(prestation)
      .where(and(eq(prestation.id, data.prestationId), eq(prestation.orgId, guard.orgId)))
      .limit(1);
    prestationTitre = mission
      ? `Mission ${mission.id.slice(0, 8)}`
      : prestationTitre;
  }

  const numero = data.numero?.trim()
    ? data.numero
    : existing.numero || (await getNextDocumentNumber("facture", guard.orgId, tenantDb));

  const [updated] = await tenantDb
    .update(facture)
    .set({
      numero,
      clientId,
      clientNom,
      clientEmail,
      clientTelephone,
      clientAdresse,
      prestationId: data.prestationId ?? existing.prestationId ?? null,
      prestationTitre,
      montantHt: data.montantHt ?? existing.montantHt ?? "0",
      montantTtc: data.montantTtc ?? existing.montantTtc ?? "0",
      statut: data.statut ?? existing.statut ?? "brouillon",
      updatedAt: new Date(),
    })
    .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)))
    .returning();

  await logAudit({
    action: "facture.updated",
    entityType: "facture",
    entityId: updated.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { numero: updated.numero, statut: updated.statut },
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
  const [existing] = await tenantDb
    .select()
    .from(facture)
    .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)))
    .limit(1);
  if (!existing) {
    return NextResponse.json({ error: "facture introuvable" }, { status: 404 });
  }
  if (existing.statut === "envoye" || existing.statut === "paye") {
    return NextResponse.json(
      { error: "facture verrouillee" },
      { status: 400 },
    );
  }
  await tenantDb
    .delete(facture)
    .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)));

  await logAudit({
    action: "facture.deleted",
    entityType: "facture",
    entityId: existing.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { numero: existing.numero, statut: existing.statut },
  });

  return NextResponse.json({ ok: true });
}

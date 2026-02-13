import { NextResponse } from "next/server";
import { and, desc, eq } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { client, facture, prestation } from "@/db/schema";
import { getNextDocumentNumber } from "@/lib/sequences";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

const factureSchema = z.object({
  numero: z.string().optional(),
  clientId: z.string().uuid(),
  prestationId: z.string().uuid().optional().nullable(),
  prestationTitre: z.string().min(1),
  montantHt: z.string().optional(),
  montantTtc: z.string().optional(),
  statut: z.string().optional(),
});

export async function GET() {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const rows = await tenantDb
    .select()
    .from(facture)
    .where(eq(facture.orgId, guard.orgId))
    .orderBy(desc(facture.dateCreation))
    .limit(100);
  return NextResponse.json(rows);
}

export async function POST(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const payload = await req.json();
  const data = factureSchema.parse(payload);
  const hdrs = await headers();
  const session = guard.session;

  const [clientRow] = await tenantDb
    .select()
    .from(client)
    .where(and(eq(client.id, data.clientId), eq(client.orgId, guard.orgId)))
    .limit(1);

  if (!clientRow) {
    return NextResponse.json({ error: "client introuvable" }, { status: 400 });
  }

  let prestationTitre = data.prestationTitre;
  if (data.prestationId && !prestationTitre) {
    const [mission] = await tenantDb
      .select()
      .from(prestation)
      .where(and(eq(prestation.id, data.prestationId), eq(prestation.orgId, guard.orgId)))
      .limit(1);
    prestationTitre = mission
      ? `Mission ${mission.id.slice(0, 8)}`
      : "Mission";
  }

  const numero = data.numero?.trim()
    ? data.numero
    : await getNextDocumentNumber("facture", guard.orgId, tenantDb);

  const [created] = await tenantDb
    .insert(facture)
    .values({
      orgId: guard.orgId,
      numero,
      clientId: clientRow.id,
      clientNom:
        [clientRow.prenom, clientRow.nom].filter(Boolean).join(" ") ||
        clientRow.nom,
      clientEmail: clientRow.email ?? null,
      clientTelephone: clientRow.telephone ?? null,
      clientAdresse: clientRow.adresseFacturation ?? null,
      prestationId: data.prestationId ?? null,
      prestationTitre,
      montantHt: data.montantHt ?? "0",
      montantTtc: data.montantTtc ?? "0",
      statut: data.statut ?? "brouillon",
    })
    .returning();

  await logAudit({
    action: "facture.created",
    entityType: "facture",
    entityId: created.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { numero: created.numero, clientEmail: created.clientEmail },
  });

  return NextResponse.json(created);
}

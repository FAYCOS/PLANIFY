import { NextResponse } from "next/server";
import { and, desc, eq } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { devis, facture, paiement } from "@/db/schema";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

const paiementSchema = z.object({
  factureId: z.string().optional().nullable(),
  devisId: z.string().optional().nullable(),
  montant: z.string().optional(),
  mode: z.string().optional(),
  statut: z.string().optional(),
  reference: z.string().optional().nullable(),
});

export async function GET() {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const rows = await tenantDb
    .select()
    .from(paiement)
    .where(eq(paiement.orgId, guard.orgId))
    .orderBy(desc(paiement.createdAt))
    .limit(100);
  return NextResponse.json(rows);
}

export async function POST(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const payload = await req.json();
  const data = paiementSchema.parse(payload);
  const hdrs = await headers();
  const session = guard.session;

  if (data.factureId) {
    const [invoice] = await tenantDb
      .select({ id: facture.id })
      .from(facture)
      .where(and(eq(facture.id, data.factureId), eq(facture.orgId, guard.orgId)))
      .limit(1);
    if (!invoice) {
      return NextResponse.json({ error: "facture introuvable" }, { status: 404 });
    }
  }
  if (data.devisId) {
    const [quote] = await tenantDb
      .select({ id: devis.id })
      .from(devis)
      .where(and(eq(devis.id, data.devisId), eq(devis.orgId, guard.orgId)))
      .limit(1);
    if (!quote) {
      return NextResponse.json({ error: "devis introuvable" }, { status: 404 });
    }
  }

  const [created] = await tenantDb
    .insert(paiement)
    .values({
      orgId: guard.orgId,
      factureId: data.factureId ?? null,
      devisId: data.devisId ?? null,
      montant: data.montant ?? "0",
      mode: data.mode ?? null,
      statut: data.statut ?? "en_attente",
      reference: data.reference ?? null,
    })
    .returning();

  await logAudit({
    action: "paiement.created",
    entityType: "paiement",
    entityId: created.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: {
      factureId: created.factureId,
      devisId: created.devisId,
      montant: created.montant,
      mode: created.mode,
    },
  });

  return NextResponse.json(created);
}

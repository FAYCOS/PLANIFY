import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { facture, paiement } from "@/db/schema";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

const payloadSchema = z.object({
  montant: z.string().optional(),
  mode: z.string().optional(),
  reference: z.string().optional(),
});

type Params = { params: Promise<{ id: string }> };

export async function POST(req: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const payload = await req.json();
  const data = payloadSchema.parse(payload);
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

  const montant = data.montant ?? existing.montantTtc?.toString() ?? "0";

  await tenantDb.insert(paiement).values({
    orgId: guard.orgId,
    factureId: id,
    montant,
    mode: data.mode ?? "manuel",
    statut: "paye",
    reference: data.reference ?? null,
  });

  const [updated] = await tenantDb
    .update(facture)
    .set({
      montantPaye: montant,
      statut: "paye",
      datePaiement: new Date().toISOString().slice(0, 10),
      updatedAt: new Date(),
    })
    .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)))
    .returning();

  await logAudit({
    action: "facture.paid",
    entityType: "facture",
    entityId: id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { montant, mode: data.mode ?? "manuel", reference: data.reference },
  });

  return NextResponse.json(updated);
}

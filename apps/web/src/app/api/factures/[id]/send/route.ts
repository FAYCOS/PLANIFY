import crypto from "crypto";

import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { headers } from "next/headers";

import { facture } from "@/db/schema";
import { sendTransactionalEmail } from "@/lib/email";
import { factureSentTemplate } from "@/lib/email-templates";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

type Params = { params: Promise<{ id: string }> };

export async function POST(_: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const [existing] = await tenantDb
    .select()
    .from(facture)
    .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)))
    .limit(1);

  if (!existing) {
    return NextResponse.json({ error: "facture introuvable" }, { status: 404 });
  }

  if (!existing.clientEmail) {
    return NextResponse.json(
      { error: "email client manquant" },
      { status: 400 },
    );
  }

  let publicToken = existing.paymentToken;
  if (!publicToken) {
    publicToken = crypto.randomBytes(32).toString("hex");
    await tenantDb
      .update(facture)
      .set({ paymentToken: publicToken, updatedAt: new Date() })
      .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)));
  }

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";
  const pdfLink = `${appUrl}/api/factures/${id}/pdf?token=${publicToken}&orgId=${guard.orgId}`;
  const html = factureSentTemplate({
    appUrl,
    numero: existing.numero,
    link: pdfLink,
    recipientName: existing.clientNom,
    totalTtc: existing.montantTtc?.toString() ?? null,
  });

  await sendTransactionalEmail({
    to: existing.clientEmail,
    subject: `Votre facture ${existing.numero}`,
    html,
  });

  const [updated] = await tenantDb
    .update(facture)
    .set({
      statut: "envoye",
      dateEnvoi: new Date(),
      updatedAt: new Date(),
    })
    .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)))
    .returning();

  const hdrs = await headers();
  await logAudit({
    action: "facture.sent",
    entityType: "facture",
    entityId: id,
    userId: guard.session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { numero: existing.numero, email: existing.clientEmail },
  });

  return NextResponse.json(updated ?? existing);
}

import crypto from "crypto";

import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { headers } from "next/headers";

import { devis } from "@/db/schema";
import { sendTransactionalEmail } from "@/lib/email";
import { devisReminderTemplate } from "@/lib/email-templates";
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
    .from(devis)
    .where(and(eq(devis.id, id), eq(devis.orgId, guard.orgId)))
    .limit(1);

  if (!existing) {
    return NextResponse.json({ error: "devis introuvable" }, { status: 404 });
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
  }

  let signatureToken = existing.signatureToken;
  if (!signatureToken) {
    signatureToken = crypto.randomBytes(32).toString("hex");
  }

  if (!existing.paymentToken || !existing.signatureToken) {
    await tenantDb
      .update(devis)
      .set({
        paymentToken: publicToken,
        signatureToken,
        updatedAt: new Date(),
      })
      .where(and(eq(devis.id, id), eq(devis.orgId, guard.orgId)));
  }

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";
  const pdfLink = `${appUrl}/api/devis/${id}/pdf?token=${publicToken}&orgId=${guard.orgId}`;
  const signLink = `${appUrl}/public/devis/sign?token=${signatureToken}&orgId=${guard.orgId}`;
  const html = devisReminderTemplate({
    appUrl,
    numero: existing.numero,
    link: pdfLink,
    recipientName: existing.clientNom,
    signLink,
  });

  await sendTransactionalEmail({
    to: existing.clientEmail,
    subject: `Rappel devis ${existing.numero}`,
    html,
  });

  const hdrs = await headers();
  await logAudit({
    action: "devis.remind",
    entityType: "devis",
    entityId: id,
    userId: guard.session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { numero: existing.numero, email: existing.clientEmail },
  });

  return NextResponse.json({ ok: true });
}

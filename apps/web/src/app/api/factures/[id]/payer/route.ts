import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { headers } from "next/headers";

import { facture } from "@/db/schema";
import { stripe } from "@/lib/stripe";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

export async function POST(
  _req: Request,
  context: { params: Promise<{ id: string }> },
) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const params = await context.params;
  const [invoice] = await tenantDb
    .select()
    .from(facture)
    .where(and(eq(facture.id, params.id), eq(facture.orgId, guard.orgId)))
    .limit(1);

  if (!invoice) {
    return NextResponse.json({ error: "Facture introuvable" }, { status: 404 });
  }

  const amount = Math.round(Number(invoice.montantTtc ?? "0") * 100);

  const successUrl =
    process.env.NEXT_PUBLIC_APP_URL +
    "/finance/factures?status=success&facture=" +
    invoice.id;
  const cancelUrl =
    process.env.NEXT_PUBLIC_APP_URL +
    "/finance/factures?status=cancel&facture=" +
    invoice.id;

  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    success_url: successUrl,
    cancel_url: cancelUrl,
    metadata: {
      factureId: invoice.id,
      orgId: guard.orgId,
    },
    line_items: [
      {
        quantity: 1,
        price_data: {
          currency: "eur",
          unit_amount: amount,
          product_data: {
            name: `Facture ${invoice.numero}`,
          },
        },
      },
    ],
  });

  await tenantDb
    .update(facture)
    .set({
      stripePaymentIntentId: session.payment_intent?.toString() ?? null,
      stripePaymentLink: session.url ?? null,
      modePaiementSouhaite: "stripe",
    })
    .where(and(eq(facture.id, invoice.id), eq(facture.orgId, guard.orgId)));

  const hdrs = await headers();
  await logAudit({
    action: "facture.checkout_created",
    entityType: "facture",
    entityId: invoice.id,
    userId: guard.session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { numero: invoice.numero, stripeSession: session.id },
  });

  return NextResponse.json({ url: session.url });
}

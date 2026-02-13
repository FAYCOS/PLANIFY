import { headers } from "next/headers";
import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { facture, paiement, stripeEvent } from "@/db/schema";
import { stripe } from "@/lib/stripe";
import { getOrgDbById } from "@/lib/tenant";

export async function POST(req: Request) {
  const signature = (await headers()).get("stripe-signature");
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!signature || !webhookSecret) {
    return NextResponse.json({ error: "Missing webhook signature" }, { status: 400 });
  }

  const body = await req.text();
  let event;

  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch {
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  const inserted = await db
    .insert(stripeEvent)
    .values({
      eventId: event.id,
      type: event.type,
      payload: event.data as any,
    })
    .onConflictDoNothing()
    .returning({ eventId: stripeEvent.eventId });

  if (inserted.length === 0) {
    return NextResponse.json({ received: true, deduplicated: true });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    const factureId = session.metadata?.factureId;
    const orgId = session.metadata?.orgId;
    if (factureId && orgId) {
      const orgDb = await getOrgDbById(orgId);
      if (orgDb) {
        const tenantDb = orgDb.db;
        const [invoice] = await tenantDb
          .select({ orgId: facture.orgId })
          .from(facture)
          .where(eq(facture.id, factureId))
          .limit(1);
        await tenantDb
          .update(facture)
          .set({
            statut: "paye",
            datePaiement: new Date().toISOString().slice(0, 10),
            montantPaye: session.amount_total
              ? (session.amount_total / 100).toFixed(2)
              : "0",
            modePaiement: "stripe",
            referencePaiement: session.payment_intent?.toString() ?? null,
          })
          .where(eq(facture.id, factureId));

        await tenantDb.insert(paiement).values({
          orgId: invoice?.orgId ?? null,
          factureId,
          montant: session.amount_total
            ? (session.amount_total / 100).toFixed(2)
            : "0",
          mode: "stripe",
          statut: "reussi",
          reference: session.payment_intent?.toString() ?? null,
        });
      }
    }
  }

  return NextResponse.json({ received: true });
}

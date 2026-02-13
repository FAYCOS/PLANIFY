import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { devis } from "@/db/schema";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

const payloadSchema = z.object({
  signatureImage: z.string().min(1).max(2_000_000),
});

type Params = { params: Promise<{ id: string }> };

export async function POST(req: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const payload = await req.json();
  const data = payloadSchema.parse(payload);
  const signatureIp =
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    req.headers.get("x-real-ip") ||
    null;

  const [existing] = await tenantDb
    .select()
    .from(devis)
    .where(and(eq(devis.id, id), eq(devis.orgId, guard.orgId)))
    .limit(1);

  if (!existing) {
    return NextResponse.json({ error: "devis introuvable" }, { status: 404 });
  }

  if (existing.estSigne || existing.statut === "signe") {
    return NextResponse.json({ error: "devis deja signe" }, { status: 400 });
  }

  const [updated] = await tenantDb
    .update(devis)
    .set({
      signatureImage: data.signatureImage,
      signatureDate: new Date(),
      signatureIp,
      estSigne: true,
      statut: "signe",
      dateAcceptation: new Date(),
      updatedAt: new Date(),
    })
    .where(and(eq(devis.id, id), eq(devis.orgId, guard.orgId)))
    .returning();

  if (!updated) {
    return NextResponse.json({ error: "devis introuvable" }, { status: 404 });
  }

  const hdrs = await headers();
  await logAudit({
    action: "devis.signed",
    entityType: "devis",
    entityId: updated.id,
    userId: guard.session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { numero: updated.numero, statut: updated.statut },
  });
  return NextResponse.json(updated);
}

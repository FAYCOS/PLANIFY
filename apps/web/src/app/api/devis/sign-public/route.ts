import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { devis } from "@/db/schema";
import { getOrgDbById } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";
import { getRequestIp, rateLimit } from "@/lib/rate-limit";

const payloadSchema = z.object({
  token: z.string().min(10),
  orgId: z.string().uuid(),
  signatureImage: z.string().min(1).max(2_000_000),
});

export async function POST(req: Request) {
  const ip = getRequestIp(req);
  const limit = rateLimit(`devis:sign-public:${ip}`, 10, 60_000);
  if (!limit.allowed) {
    return NextResponse.json(
      { error: "Trop de tentatives. Reessayez plus tard." },
      {
        status: 429,
        headers: {
          "Retry-After": Math.ceil((limit.reset - Date.now()) / 1000).toString(),
        },
      },
    );
  }
  const payload = await req.json();
  const data = payloadSchema.parse(payload);
  const signatureIp =
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    req.headers.get("x-real-ip") ||
    null;

  const orgDb = await getOrgDbById(data.orgId);
  if (!orgDb) {
    return NextResponse.json({ error: "Organisation introuvable." }, { status: 404 });
  }

  const [existing] = await orgDb.db
    .select()
    .from(devis)
    .where(and(eq(devis.signatureToken, data.token), eq(devis.orgId, data.orgId)))
    .limit(1);

  if (!existing) {
    return NextResponse.json({ error: "Lien invalide." }, { status: 404 });
  }
  if (existing.estSigne || existing.statut === "signe") {
    return NextResponse.json({ error: "Devis deja signe." }, { status: 400 });
  }

  const [updated] = await orgDb.db
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
    .where(and(eq(devis.id, existing.id), eq(devis.orgId, data.orgId)))
    .returning();

  const hdrs = await headers();
  await logAudit({
    action: "devis.signed_public",
    entityType: "devis",
    entityId: updated?.id ?? existing.id,
    userId: null,
    orgId: data.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { numero: existing.numero, statut: "signe" },
  });

  return NextResponse.json({ ok: true });
}

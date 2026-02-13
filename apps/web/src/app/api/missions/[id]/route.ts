import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { client, prestation } from "@/db/schema";
import { computeRoute } from "@/lib/geo";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

const updateSchema = z.object({
  clientId: z.string().uuid().optional().nullable(),
  clientNom: z.string().optional().nullable(),
  clientEmail: z.string().email().optional().nullable(),
  clientTelephone: z.string().optional().nullable(),
  lieu: z.string().optional().nullable(),
  dateDebut: z.string().optional().nullable(),
  dateFin: z.string().optional().nullable(),
  heureDebut: z.string().optional().nullable(),
  heureFin: z.string().optional().nullable(),
  statut: z.string().optional().nullable(),
  notes: z.string().optional().nullable(),
});

type Params = { params: Promise<{ id: string }> };

export async function GET(_: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const [row] = await tenantDb
    .select()
    .from(prestation)
    .where(and(eq(prestation.id, id), eq(prestation.orgId, guard.orgId)))
    .limit(1);
  if (!row) {
    return NextResponse.json({ error: "mission introuvable" }, { status: 404 });
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

  const clientId = data.clientId ?? null;
  let clientNom = data.clientNom ?? null;
  let clientEmail = data.clientEmail ?? null;
  let clientTelephone = data.clientTelephone ?? null;

  if (clientId && !clientNom) {
    const [existing] = await tenantDb
      .select()
      .from(client)
      .where(and(eq(client.id, clientId), eq(client.orgId, guard.orgId)))
      .limit(1);
    if (existing) {
      clientNom =
        [existing.prenom, existing.nom].filter(Boolean).join(" ") ||
        existing.nom;
      clientEmail = clientEmail ?? existing.email ?? null;
      clientTelephone = clientTelephone ?? existing.telephone ?? null;
    }
  }

  if (!clientId || !clientNom) {
    return NextResponse.json(
      { error: "client nom manquant" },
      { status: 400 },
    );
  }

  const route = data.lieu
    ? await computeRoute(data.lieu, guard.orgId, tenantDb)
    : null;

  const [updated] = await tenantDb
    .update(prestation)
    .set({
      clientId,
      clientNom,
      clientEmail,
      clientTelephone,
      lieu: data.lieu ?? null,
      lieuLat: route?.destination.lat
        ? route.destination.lat.toString()
        : null,
      lieuLng: route?.destination.lng
        ? route.destination.lng.toString()
        : null,
      dateDebut: data.dateDebut ?? null,
      dateFin: data.dateFin ?? null,
      heureDebut: data.heureDebut ?? null,
      heureFin: data.heureFin ?? null,
      statut: data.statut ?? null,
      notes: data.notes ?? null,
      distanceKm: route?.distanceKm?.toFixed(2) ?? null,
      distanceSource: route?.source ?? null,
      updatedAt: new Date(),
    })
    .where(and(eq(prestation.id, id), eq(prestation.orgId, guard.orgId)))
    .returning();

  if (!updated) {
    return NextResponse.json({ error: "mission introuvable" }, { status: 404 });
  }

  await logAudit({
    action: "mission.updated",
    entityType: "mission",
    entityId: updated.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { clientId: updated.clientId, statut: updated.statut },
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
  const [deleted] = await tenantDb
    .delete(prestation)
    .where(and(eq(prestation.id, id), eq(prestation.orgId, guard.orgId)))
    .returning();
  if (!deleted) {
    return NextResponse.json({ error: "mission introuvable" }, { status: 404 });
  }

  await logAudit({
    action: "mission.deleted",
    entityType: "mission",
    entityId: deleted.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { clientId: deleted.clientId, statut: deleted.statut },
  });

  return NextResponse.json({ ok: true });
}

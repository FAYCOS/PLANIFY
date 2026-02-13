import { NextResponse } from "next/server";
import { and, desc, eq } from "drizzle-orm";
import { z } from "zod";
import { headers } from "next/headers";

import { client, prestation } from "@/db/schema";
import { computeRoute } from "@/lib/geo";
import { requireOrgDb } from "@/lib/tenant";
import { logAudit } from "@/lib/audit";

const newClientSchema = z.object({
  nom: z.string().min(1),
  prenom: z.string().min(1),
  email: z.string().email(),
  telephone: z.string().min(1),
  adresseFacturation: z.string().min(1),
});

const prestationSchema = z.object({
  clientId: z.string().uuid().optional().nullable(),
  client: newClientSchema.optional(),
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

export async function GET() {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const rows = await tenantDb
    .select()
    .from(prestation)
    .where(eq(prestation.orgId, guard.orgId))
    .orderBy(desc(prestation.createdAt))
    .limit(50);
  return NextResponse.json(rows);
}

export async function POST(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;

  const payload = await req.json();
  const data = prestationSchema.parse(payload);
  const hdrs = await headers();
  const session = guard.session;

  let clientId = data.clientId ?? null;
  let clientNom = data.clientNom ?? "";
  let clientEmail = data.clientEmail ?? null;
  let clientTelephone = data.clientTelephone ?? null;

  if (!clientId && data.client) {
    const fullName = [data.client.prenom, data.client.nom]
      .filter(Boolean)
      .join(" ");
    const [createdClient] = await tenantDb
      .insert(client)
      .values({
        orgId: guard.orgId,
        nom: data.client.nom,
        prenom: data.client.prenom,
        email: data.client.email,
        telephone: data.client.telephone,
        adresseFacturation: data.client.adresseFacturation,
      })
      .returning();
    clientId = createdClient.id;
    clientNom = fullName || createdClient.nom;
    clientEmail = createdClient.email;
    clientTelephone = createdClient.telephone;
  }

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

  const values = {
    orgId: guard.orgId,
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
    statut: data.statut ?? "planifiee",
    notes: data.notes ?? null,
    distanceKm: route?.distanceKm?.toFixed(2) ?? null,
    distanceSource: route?.source ?? null,
  } as unknown as typeof prestation.$inferInsert;

  const [created] = await tenantDb
    .insert(prestation)
    .values(values)
    .returning();

  await logAudit({
    action: "mission.created",
    entityType: "mission",
    entityId: created.id,
    userId: session?.user?.id ?? null,
    orgId: guard.orgId,
    ipAddress: hdrs.get("x-forwarded-for") ?? null,
    userAgent: hdrs.get("user-agent") ?? null,
    metadata: { clientId: created.clientId, lieu: created.lieu },
  });

  return NextResponse.json(created);
}

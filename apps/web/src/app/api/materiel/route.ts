import { NextResponse } from "next/server";
import { desc, eq } from "drizzle-orm";
import { z } from "zod";

import { materiel } from "@/db/schema";
import { requireOrgDb } from "@/lib/tenant";

const materielSchema = z.object({
  nom: z.string().min(1),
  categorie: z.string().optional().nullable(),
  quantite: z.coerce.number().optional(),
  prixLocation: z.string().optional(),
  numeroSerie: z.string().optional().nullable(),
  codeBarre: z.string().optional().nullable(),
  statut: z.string().optional().nullable(),
});

export async function GET() {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const rows = await tenantDb
    .select()
    .from(materiel)
    .where(eq(materiel.orgId, guard.orgId))
    .orderBy(desc(materiel.createdAt))
    .limit(200);
  return NextResponse.json(rows);
}

export async function POST(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const payload = await req.json();
  const data = materielSchema.parse(payload);

  const [created] = await tenantDb
    .insert(materiel)
    .values({
      orgId: guard.orgId,
      nom: data.nom,
      categorie: data.categorie ?? null,
      quantite: data.quantite ?? 1,
      prixLocation: data.prixLocation ?? "0",
      numeroSerie: data.numeroSerie ?? null,
      codeBarre: data.codeBarre ?? null,
      statut: data.statut ?? "disponible",
    })
    .returning();

  return NextResponse.json(created);
}

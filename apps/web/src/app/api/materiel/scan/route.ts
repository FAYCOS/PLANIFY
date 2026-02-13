import { NextResponse } from "next/server";
import { and, eq, or } from "drizzle-orm";
import { z } from "zod";

import { materiel, mouvementMateriel } from "@/db/schema";
import { requireOrgDb } from "@/lib/tenant";

const scanSchema = z.object({
  code: z.string().min(1),
  type: z.enum(["entree", "sortie"]),
  prestationId: z.string().optional().nullable(),
});

export async function POST(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const payload = await req.json();
  const data = scanSchema.parse(payload);

  const [item] = await tenantDb
    .select()
    .from(materiel)
    .where(
      and(
        eq(materiel.orgId, guard.orgId),
        or(
          eq(materiel.codeBarre, data.code),
          eq(materiel.numeroSerie, data.code),
        ),
      ),
    )
    .limit(1);

  if (!item) {
    return NextResponse.json(
      { error: "Materiel introuvable" },
      { status: 404 },
    );
  }

  const [movement] = await tenantDb
    .insert(mouvementMateriel)
    .values({
      materielId: item.id,
      typeMouvement: data.type,
      quantite: 1,
      numeroSerie: item.numeroSerie ?? data.code,
      codeBarre: item.codeBarre ?? data.code,
      prestationId: data.prestationId ?? null,
    })
    .returning();

  const nextStatus = data.type === "sortie" ? "en_sortie" : "disponible";
  await tenantDb
    .update(materiel)
    .set({ statut: nextStatus })
    .where(eq(materiel.id, item.id));

  return NextResponse.json({
    status: "ok",
    materiel: { ...item, statut: nextStatus },
    movement,
  });
}

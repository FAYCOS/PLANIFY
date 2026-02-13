export const runtime = "nodejs";

import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { pdf } from "@react-pdf/renderer";

import { facture } from "@/db/schema";
import { FacturePdf } from "@/lib/pdf/facture";
import { getOrgDbById, requireOrgDb } from "@/lib/tenant";

type Params = { params: Promise<{ id: string }> };

export async function GET(req: Request, context: Params) {
  const { id } = await context.params;
  const url = new URL(req.url);
  const token = url.searchParams.get("token")?.trim();
  const orgIdParam = url.searchParams.get("orgId")?.trim();

  if (token) {
    if (!orgIdParam) {
      return NextResponse.json({ error: "orgId manquant" }, { status: 400 });
    }
    const orgDb = await getOrgDbById(orgIdParam);
    if (!orgDb) {
      return NextResponse.json({ error: "organisation introuvable" }, { status: 404 });
    }
    const [row] = await orgDb.db
      .select()
      .from(facture)
      .where(and(eq(facture.id, id), eq(facture.paymentToken, token)))
      .limit(1);
    if (!row) {
      return NextResponse.json({ error: "acces refuse" }, { status: 403 });
    }

    const document = FacturePdf({ facture: row });
    const buffer = await pdf(document).toBuffer();
    const body = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);

    return new Response(body, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `inline; filename=${row.numero}.pdf`,
      },
    });
  }

  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const [row] = await tenantDb
    .select()
    .from(facture)
    .where(and(eq(facture.id, id), eq(facture.orgId, guard.orgId)))
    .limit(1);
  if (!row) {
    return NextResponse.json({ error: "facture introuvable" }, { status: 404 });
  }

  const document = FacturePdf({ facture: row });
  const buffer = await pdf(document).toBuffer();
  const body = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);

  return new Response(body, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `inline; filename=${row.numero}.pdf`,
    },
  });
}

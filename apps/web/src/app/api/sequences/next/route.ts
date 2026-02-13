import { NextResponse } from "next/server";
import { z } from "zod";

import { getNextDocumentNumber } from "@/lib/sequences";
import { requireOrgDb } from "@/lib/tenant";

const payloadSchema = z.object({
  type: z.enum(["devis", "facture"]),
});

export async function POST(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const payload = await req.json();
  const data = payloadSchema.parse(payload);

  const numero = await getNextDocumentNumber(data.type, guard.orgId, tenantDb);
  return NextResponse.json({ numero });
}

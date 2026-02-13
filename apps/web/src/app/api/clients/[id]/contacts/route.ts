import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { z } from "zod";

import { client, clientContact } from "@/db/schema";
import { requireOrgDb } from "@/lib/tenant";

const contactSchema = z.object({
  nom: z.string().min(1),
  email: z.string().email().optional().nullable(),
  telephone: z.string().optional().nullable(),
  role: z.string().optional().nullable(),
});

type Params = { params: Promise<{ id: string }> };

export async function GET(_: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const [owner] = await tenantDb
    .select({ id: client.id })
    .from(client)
    .where(and(eq(client.id, id), eq(client.orgId, guard.orgId)))
    .limit(1);
  if (!owner) {
    return NextResponse.json({ error: "client introuvable" }, { status: 404 });
  }
  const rows = await tenantDb
    .select()
    .from(clientContact)
    .where(eq(clientContact.clientId, id));
  return NextResponse.json(rows);
}

export async function POST(req: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const payload = await req.json();
  const data = contactSchema.parse(payload);
  const [owner] = await tenantDb
    .select({ id: client.id })
    .from(client)
    .where(and(eq(client.id, id), eq(client.orgId, guard.orgId)))
    .limit(1);
  if (!owner) {
    return NextResponse.json({ error: "client introuvable" }, { status: 404 });
  }

  const [created] = await tenantDb
    .insert(clientContact)
    .values({
      clientId: id,
      nom: data.nom,
      email: data.email ?? null,
      telephone: data.telephone ?? null,
      role: data.role ?? null,
    })
    .returning();

  return NextResponse.json(created);
}

export async function DELETE(req: Request, context: Params) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const { id } = await context.params;
  const payload = await req.json();
  const contactId = z
    .object({ id: z.string().uuid() })
    .parse(payload).id;
  const [owner] = await tenantDb
    .select({ id: client.id })
    .from(client)
    .where(and(eq(client.id, id), eq(client.orgId, guard.orgId)))
    .limit(1);
  if (!owner) {
    return NextResponse.json({ error: "client introuvable" }, { status: 404 });
  }

  const [deleted] = await tenantDb
    .delete(clientContact)
    .where(eq(clientContact.id, contactId))
    .returning();

  if (!deleted || deleted.clientId !== id) {
    return NextResponse.json({ error: "contact introuvable" }, { status: 404 });
  }

  return NextResponse.json({ ok: true });
}

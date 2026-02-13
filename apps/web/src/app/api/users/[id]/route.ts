import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { z } from "zod";

import { db } from "@/db";
import { user } from "@/db/schema";
import { getAdminSession, requireAdmin } from "@/lib/require-admin";
import { ROLE_OPTIONS } from "@/lib/roles";

const payloadSchema = z.object({
  role: z.string().optional(),
  name: z.string().optional(),
});

type Params = { params: Promise<{ id: string }> };

export async function PUT(req: Request, context: Params) {
  const guard = await requireAdmin(req.headers);
  if (guard) return guard;
  const session = await getAdminSession(req.headers);
  if (!session) {
    return NextResponse.json({ error: "acces refuse" }, { status: 403 });
  }

  const { id } = await context.params;
  const payload = await req.json();
  const data = payloadSchema.parse(payload);
  const allowedRoles = new Set(ROLE_OPTIONS.map((roleOption) => roleOption.value));
  const role = data.role && allowedRoles.has(data.role) ? data.role : undefined;

  const orgId = session.user.orgId ?? null;
  const [updated] = await db
    .update(user)
    .set({
      role,
      name: data.name ?? undefined,
      updatedAt: new Date(),
    })
    .where(orgId ? and(eq(user.id, id), eq(user.orgId, orgId)) : eq(user.id, id))
    .returning();

  if (!updated) {
    return NextResponse.json({ error: "utilisateur introuvable" }, { status: 404 });
  }

  return NextResponse.json(updated);
}

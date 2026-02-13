import { NextResponse } from "next/server";
import { eq, sql } from "drizzle-orm";

import { db } from "@/db";
import { user } from "@/db/schema";
import { auth } from "@/lib/auth";

export async function PATCH(req: Request) {
  const session = await auth.api.getSession({ headers: req.headers });
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Non autorise." }, { status: 401 });
  }

  await db
    .update(user)
    .set({ mustChangePassword: false, updatedAt: sql`now()` })
    .where(eq(user.id, session.user.id));

  return NextResponse.json({ ok: true });
}

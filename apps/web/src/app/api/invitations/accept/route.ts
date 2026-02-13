import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { invitation, teamMember, user } from "@/db/schema";
import { requireSession } from "@/lib/auth-guard";
import { hashInviteToken } from "@/lib/invitations";

export async function POST(req: Request) {
  const guard = await requireSession();
  if ("response" in guard) return guard.response;

  const body = await req.json();
  const token = String(body?.token || "").trim();
  if (!token) {
    return NextResponse.json({ error: "Token manquant." }, { status: 400 });
  }

  const [invite] = await db
    .select()
    .from(invitation)
    .where(eq(invitation.tokenHash, hashInviteToken(token)))
    .limit(1);

  if (!invite || invite.status !== "pending") {
    return NextResponse.json({ error: "Invitation invalide." }, { status: 400 });
  }

  if (invite.expiresAt && new Date(invite.expiresAt) < new Date()) {
    await db
      .update(invitation)
      .set({ status: "expired" })
      .where(eq(invitation.id, invite.id));
    return NextResponse.json({ error: "Invitation expiree." }, { status: 400 });
  }

  const userId = guard.userId;
  const sessionEmail = guard.session.user?.email?.toLowerCase();

  if (invite.email && sessionEmail && invite.email.toLowerCase() !== sessionEmail) {
    return NextResponse.json(
      { error: "Email different de l'invitation." },
      { status: 400 },
    );
  }
  const [existing] = await db
    .select({ orgId: user.orgId })
    .from(user)
    .where(eq(user.id, userId))
    .limit(1);

  if (existing?.orgId && existing.orgId !== invite.orgId) {
    return NextResponse.json(
      { error: "Utilisateur deja rattache a une autre organisation." },
      { status: 400 },
    );
  }

  await db.transaction(async (tx) => {
    await tx
      .update(user)
      .set({ orgId: invite.orgId, role: invite.role, updatedAt: new Date() })
      .where(eq(user.id, userId));

    if (invite.teamId) {
      await tx
        .insert(teamMember)
        .values({ teamId: invite.teamId, userId, role: invite.role })
        .onConflictDoNothing();
    }

    await tx
      .update(invitation)
      .set({
        status: "accepted",
        acceptedByUserId: userId,
        acceptedAt: new Date(),
      })
      .where(eq(invitation.id, invite.id));
  });

  return NextResponse.json({ status: "accepted" });
}

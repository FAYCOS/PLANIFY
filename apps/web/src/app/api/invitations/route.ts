import { NextResponse } from "next/server";
import { and, desc, eq } from "drizzle-orm";

import { db } from "@/db";
import { invitation } from "@/db/schema";
import { sendTransactionalEmail } from "@/lib/email";
import { generateInviteToken, getInviteExpiryDate, hashInviteToken } from "@/lib/invitations";
import { getAdminSession, requireAdmin } from "@/lib/require-admin";
import { ROLE_OPTIONS } from "@/lib/roles";
import { ensureDefaultTeam } from "@/lib/teams";

const appUrl =
  process.env.NEXT_PUBLIC_APP_URL ||
  process.env.BETTER_AUTH_URL ||
  "http://localhost:3000";

export async function GET(req: Request) {
  const guard = await requireAdmin(req.headers);
  if (guard) return guard;
  const session = await getAdminSession(req.headers);
  if (!session?.user?.orgId) {
    return NextResponse.json({ error: "Organisation manquante." }, { status: 403 });
  }

  const rows = await db
    .select()
    .from(invitation)
    .where(eq(invitation.orgId, session.user.orgId))
    .orderBy(desc(invitation.createdAt));

  return NextResponse.json(rows);
}

export async function POST(req: Request) {
  const guard = await requireAdmin(req.headers);
  if (guard) return guard;
  const session = await getAdminSession(req.headers);
  if (!session?.user?.orgId) {
    return NextResponse.json({ error: "Organisation manquante." }, { status: 403 });
  }

  const body = await req.json();
  const email = String(body?.email || "").trim().toLowerCase();
  const roleRaw = String(body?.role || "member").trim();
  const allowedRoles = new Set(ROLE_OPTIONS.map((roleOption) => roleOption.value));
  const role = allowedRoles.has(roleRaw) ? roleRaw : "member";
  const teamId = String(body?.teamId || "").trim();

  if (!email) {
    return NextResponse.json({ error: "Email requis." }, { status: 400 });
  }

  const [existing] = await db
    .select({ id: invitation.id })
    .from(invitation)
    .where(
      and(
        eq(invitation.orgId, session.user.orgId),
        eq(invitation.email, email),
        eq(invitation.status, "pending"),
      ),
    )
    .limit(1);
  if (existing) {
    return NextResponse.json(
      { error: "Une invitation est deja en attente pour cet email." },
      { status: 400 },
    );
  }

  const token = generateInviteToken();
  const tokenHash = hashInviteToken(token);
  const expiresAt = getInviteExpiryDate();

  const defaultTeam = teamId
    ? { id: teamId }
    : await ensureDefaultTeam(session.user.orgId, session.user.id);

  const [created] = await db
    .insert(invitation)
    .values({
      orgId: session.user.orgId,
      email,
      role,
      teamId: defaultTeam?.id || null,
      tokenHash,
      status: "pending",
      expiresAt,
      createdByUserId: session.user.id,
    })
    .returning();

  const inviteUrl = `${appUrl}/invite?token=${token}`;

  try {
    await sendTransactionalEmail({
      to: email,
      subject: "Invitation Planify",
      html: `
        <div style="font-family:Arial,sans-serif">
          <h2>Vous avez ete invite sur Planify</h2>
          <p>Utilisez ce lien pour rejoindre l'organisation :</p>
          <p><a href="${inviteUrl}">${inviteUrl}</a></p>
          <p>Ce lien expire dans 7 jours.</p>
        </div>
      `,
    });
  } catch (error) {
    await db.delete(invitation).where(eq(invitation.id, created.id));
    return NextResponse.json(
      { error: "Impossible d'envoyer l'invitation." },
      { status: 500 },
    );
  }

  return NextResponse.json(created, { status: 201 });
}

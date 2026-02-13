import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { invitation, signupFlow, teamMember, user } from "@/db/schema";
import {
  ensureSignupSchema,
  getAttemptRemaining,
  getMaxAttempts,
  getNextStep,
  hashVerificationCode,
} from "@/lib/signup";
import { getRequestIp, rateLimit } from "@/lib/rate-limit";

export async function POST(req: Request) {
  const ip = getRequestIp(req);
  const limit = rateLimit(`signup:verify:${ip}`, 10, 60_000);
  if (!limit.allowed) {
    return NextResponse.json(
      { error: "Trop de tentatives. Reessayez plus tard." },
      {
        status: 429,
        headers: {
          "Retry-After": Math.ceil((limit.reset - Date.now()) / 1000).toString(),
        },
      },
    );
  }
  await ensureSignupSchema();

  const body = await req.json();
  const flowId = String(body?.flowId || "").trim();
  const code = String(body?.code || "").trim();
  console.info("[signup:verify] request", { flowId, codePresent: Boolean(code) });

  if (!flowId || !code) {
    console.warn("[signup:verify] missing_fields", {
      flowIdPresent: Boolean(flowId),
      codePresent: Boolean(code),
    });
    return NextResponse.json(
      { error: "Flow ou code manquant." },
      { status: 400 },
    );
  }

  const [flow] = await db
    .select()
    .from(signupFlow)
    .where(eq(signupFlow.id, flowId))
    .limit(1);

  if (!flow) {
    console.warn("[signup:verify] flow_not_found", { flowId });
    return NextResponse.json({ error: "Flow invalide." }, { status: 401 });
  }

  if (flow.status === "completed") {
    console.info("[signup:verify] already_completed", { flowId });
    return NextResponse.json({
      status: flow.status,
      nextStep: getNextStep(flow.status),
    });
  }

  if (flow.codeExpiresAt && new Date(flow.codeExpiresAt) < new Date()) {
    console.warn("[signup:verify] code_expired", { flowId });
    await db
      .update(signupFlow)
      .set({ status: "expired", updatedAt: new Date() })
      .where(eq(signupFlow.id, flowId));
    return NextResponse.json(
      { error: "Code expire." },
      { status: 401 },
    );
  }

  if (flow.attemptsCount >= getMaxAttempts()) {
    console.warn("[signup:verify] attempts_exceeded", {
      flowId,
      attempts: flow.attemptsCount,
    });
    return NextResponse.json(
      { error: "Trop de tentatives." },
      { status: 429 },
    );
  }

  if (!flow.codeHash || flow.codeHash !== hashVerificationCode(code)) {
    console.warn("[signup:verify] invalid_code", {
      flowId,
      attempts: flow.attemptsCount + 1,
    });
    await db
      .update(signupFlow)
      .set({
        attemptsCount: flow.attemptsCount + 1,
        updatedAt: new Date(),
      })
      .where(eq(signupFlow.id, flowId));
    return NextResponse.json(
      {
        error: "Code invalide.",
        attemptsRemaining: getAttemptRemaining(flow.attemptsCount + 1),
      },
      { status: 400 },
    );
  }

  if (flow.invitationId) {
    const [invite] = await db
      .select()
      .from(invitation)
      .where(eq(invitation.id, flow.invitationId))
      .limit(1);

    if (!invite || invite.status !== "pending") {
      return NextResponse.json(
        { error: "Invitation invalide." },
        { status: 400 },
      );
    }

    if (invite.expiresAt && new Date(invite.expiresAt) < new Date()) {
      await db
        .update(invitation)
        .set({ status: "expired" })
        .where(eq(invitation.id, invite.id));
      return NextResponse.json(
        { error: "Invitation expiree." },
        { status: 400 },
      );
    }

    if (invite.email && invite.email.toLowerCase() !== flow.email) {
      return NextResponse.json(
        { error: "Email different de l'invitation." },
        { status: 400 },
      );
    }

    try {
      await db.transaction(async (tx) => {
        if (flow.userId) {
          const [existing] = await tx
            .select({ orgId: user.orgId })
            .from(user)
            .where(eq(user.id, flow.userId))
            .limit(1);
          if (existing?.orgId && existing.orgId !== invite.orgId) {
            throw new Error("Utilisateur deja rattache a une autre organisation.");
          }
          await tx
            .update(user)
            .set({
              emailVerified: true,
              orgId: invite.orgId,
              role: invite.role,
              updatedAt: new Date(),
            })
            .where(eq(user.id, flow.userId));
        }

        if (invite.teamId && flow.userId) {
          await tx
            .insert(teamMember)
            .values({
              teamId: invite.teamId,
              userId: flow.userId,
              role: invite.role,
            })
            .onConflictDoNothing();
        }

        await tx
          .update(invitation)
          .set({
            status: "accepted",
            acceptedByUserId: flow.userId,
            acceptedAt: new Date(),
          })
          .where(eq(invitation.id, invite.id));

        await tx
          .update(signupFlow)
          .set({
            status: "completed",
            codeHash: null,
            codeExpiresAt: null,
            attemptsCount: 0,
            orgId: invite.orgId,
            updatedAt: new Date(),
          })
          .where(eq(signupFlow.id, flowId));
      });
    } catch (error: any) {
      return NextResponse.json(
        { error: error?.message || "Invitation impossible." },
        { status: 400 },
      );
    }

    console.info("[signup:verify] invited_user_completed", {
      flowId,
      userId: flow.userId,
      orgId: invite.orgId,
    });

    return NextResponse.json({
      status: "completed",
      nextStep: getNextStep("completed"),
    });
  }

  await db
    .update(signupFlow)
    .set({
      status: "verified",
      codeHash: null,
      codeExpiresAt: null,
      attemptsCount: 0,
      updatedAt: new Date(),
    })
    .where(eq(signupFlow.id, flowId));

  if (flow.userId) {
    await db
      .update(user)
      .set({ emailVerified: true, updatedAt: new Date() })
      .where(eq(user.id, flow.userId));
  }
  console.info("[signup:verify] verified", { flowId, userId: flow.userId });

  return NextResponse.json({
    status: "verified",
    nextStep: getNextStep("verified"),
  });
}

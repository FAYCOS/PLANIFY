import crypto from "crypto";

import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";

import { auth } from "@/lib/auth";
import { sendTransactionalEmail } from "@/lib/email";
import { hashInviteToken } from "@/lib/invitations";
import { getRequestIp, rateLimit } from "@/lib/rate-limit";
import {
  ensureAuthSchema,
  ensureDefaultPlans,
  ensureSignupSchema,
  generateVerificationCode,
  getCodeExpiryDate,
  getResendAvailableAt,
  getNextStep,
  hashVerificationCode,
} from "@/lib/signup";
import { db } from "@/db";
import { invitation, signupFlow, user } from "@/db/schema";

export async function POST(req: Request) {
  const ip = getRequestIp(req);
  const limit = rateLimit(`signup:start:${ip}`, 5, 60_000);
  if (!limit.allowed) {
    return NextResponse.json(
      { error: "Trop de requetes. Reessayez plus tard." },
      {
        status: 429,
        headers: {
          "Retry-After": Math.ceil((limit.reset - Date.now()) / 1000).toString(),
        },
      },
    );
  }
  await ensureSignupSchema();
  await ensureAuthSchema();
  await ensureDefaultPlans();

  const body = await req.json();
  const email = String(body?.email || "").trim().toLowerCase();
  const password = String(body?.password || "");
  const companyName = String(body?.companyName || "").trim();
  const country = String(body?.country || "").trim() || null;
  const address = String(body?.address || "").trim() || null;
  const phone = String(body?.phone || "").trim() || null;
  const size = String(body?.size || "").trim() || null;
  const sector = String(body?.sector || "").trim() || null;
  const inviteToken = String(body?.inviteToken || "").trim();
  console.info("[signup:start] request", {
    email,
    companyName,
    hasPassword: Boolean(password),
  });

  if (!email || !password || (!inviteToken && !companyName) || (!inviteToken && !country)) {
    console.warn("[signup:start] missing_fields", {
      emailPresent: Boolean(email),
      passwordPresent: Boolean(password),
      companyNamePresent: Boolean(companyName),
      countryPresent: Boolean(country),
    });
    return NextResponse.json(
      { error: "Email, mot de passe, entreprise et pays requis." },
      { status: 400 },
    );
  }

  let inviteRecord:
    | (typeof invitation.$inferSelect & { id: string })
    | null = null;
  if (inviteToken) {
    const [invite] = await db
      .select()
      .from(invitation)
      .where(eq(invitation.tokenHash, hashInviteToken(inviteToken)))
      .limit(1);
    if (!invite || invite.status !== "pending") {
      return NextResponse.json({ error: "Invitation invalide." }, { status: 400 });
    }
    if (invite.expiresAt && new Date(invite.expiresAt) < new Date()) {
      return NextResponse.json({ error: "Invitation expiree." }, { status: 400 });
    }
    if (invite.email && invite.email.toLowerCase() !== email) {
      return NextResponse.json(
        { error: "Email different de l'invitation." },
        { status: 400 },
      );
    }
    inviteRecord = invite as typeof invitation.$inferSelect;
  }

  const existing = await db
    .select({ id: user.id })
    .from(user)
    .where(eq(user.email, email))
    .limit(1);

  if (existing.length > 0) {
    console.warn("[signup:start] email_exists", { email });
    return NextResponse.json(
      { error: "Cet email est deja utilise." },
      { status: 400 },
    );
  }

  let createdUser: any = null;
  try {
    const created = await auth.api.signUpEmail({
      headers: new Headers(),
      body: {
        email,
        name: email.split("@")[0] || "Utilisateur",
        password,
        rememberMe: false,
      },
    });
    createdUser = (created as any)?.user ?? (created as any)?.data?.user;
  } catch (error: any) {
    const errorPayload =
      typeof error === "object" && error !== null
        ? {
            message: error.message,
            code: error.code,
            status: error.status,
          }
        : { message: String(error) };
    console.error("Signup user creation failed:", {
      email,
      error: errorPayload,
    });
    const message =
      typeof error?.message === "string"
        ? error.message
        : "Creation utilisateur impossible.";
    return NextResponse.json(
      {
        error: message,
        details: process.env.NODE_ENV === "development" ? errorPayload : undefined,
      },
      { status: 400 },
    );
  }

  if (!createdUser?.id) {
    console.error("[signup:start] user_create_missing_id", { email });
    return NextResponse.json(
      { error: "Creation utilisateur impossible." },
      { status: 400 },
    );
  }

  const flowId = crypto.randomUUID();
  const code = generateVerificationCode();
  const now = new Date();

  await db.insert(signupFlow).values({
    id: flowId,
    email,
    userId: createdUser.id,
    orgId: inviteRecord?.orgId ?? null,
    invitationId: inviteRecord?.id ?? null,
    companyName,
    country,
    address,
    phone,
    size,
    sector,
    status: "code_sent",
    codeHash: hashVerificationCode(code),
    codeExpiresAt: getCodeExpiryDate(),
    attemptsCount: 0,
    lastSentAt: now,
    resendAvailableAt: getResendAvailableAt(),
    provisioningStatus: "pending",
    createdAt: now,
    updatedAt: now,
  });
  console.info("[signup:start] flow_created", { flowId, email });

  try {
    await sendTransactionalEmail({
      to: email,
      subject: "Votre code de verification Planify",
      html: `
        <div style="font-family:Arial,sans-serif">
          <h2>Confirmez votre email</h2>
          <p>Votre code de verification :</p>
          <p style="font-size:24px; font-weight:bold">${code}</p>
          <p>Ce code expire dans 10 minutes.</p>
        </div>
      `,
    });
    console.info("[signup:start] verification_sent", { flowId, email });
  } catch (error) {
    console.error("[signup:start] email_send_failed", {
      flowId,
      email,
      error: (error as any)?.message || error,
    });
    await db.delete(signupFlow).where(eq(signupFlow.id, flowId));
    if (createdUser?.id) {
      await db.delete(user).where(eq(user.id, createdUser.id));
    }
    return NextResponse.json(
      {
        error: "Impossible d'envoyer l'email de verification.",
        details:
          process.env.NODE_ENV === "development"
            ? { message: (error as any)?.message }
            : undefined,
      },
      { status: 500 },
    );
  }

  const response = NextResponse.json({
    flowId,
    status: "code_sent",
    nextStep: getNextStep("code_sent"),
  });
  response.cookies.set("planify_flow_id", flowId, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return response;
}

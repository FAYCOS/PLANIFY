import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { signupFlow } from "@/db/schema";
import { sendTransactionalEmail } from "@/lib/email";
import {
  ensureSignupSchema,
  generateVerificationCode,
  getCodeExpiryDate,
  getResendAvailableAt,
  getResendCooldownSeconds,
  hashVerificationCode,
} from "@/lib/signup";
import { getRequestIp, rateLimit } from "@/lib/rate-limit";

export async function POST(req: Request) {
  const ip = getRequestIp(req);
  const limit = rateLimit(`signup:resend:${ip}`, 5, 60_000);
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
  console.info("[signup:resend] request", { flowId });

  if (!flowId) {
    console.warn("[signup:resend] missing_flow");
    return NextResponse.json({ error: "Flow manquant." }, { status: 400 });
  }

  const [flow] = await db
    .select()
    .from(signupFlow)
    .where(eq(signupFlow.id, flowId))
    .limit(1);

  if (!flow) {
    console.warn("[signup:resend] flow_not_found", { flowId });
    return NextResponse.json({ error: "Flow invalide." }, { status: 401 });
  }

  if (flow.status === "verified" || flow.status === "completed") {
    console.info("[signup:resend] already_verified", { flowId, status: flow.status });
    return NextResponse.json(
      { error: "Email deja verifie." },
      { status: 400 },
    );
  }

  if (flow.resendAvailableAt && new Date(flow.resendAvailableAt) > new Date()) {
    const remaining =
      Math.ceil(
        (new Date(flow.resendAvailableAt).getTime() - Date.now()) / 1000,
      ) || getResendCooldownSeconds();
    return NextResponse.json(
      { error: "Cooldown actif.", cooldownSeconds: remaining },
      { status: 429 },
    );
  }

  const code = generateVerificationCode();
  const now = new Date();

  await db
    .update(signupFlow)
    .set({
      status: "code_sent",
      codeHash: hashVerificationCode(code),
      codeExpiresAt: getCodeExpiryDate(),
      attemptsCount: 0,
      lastSentAt: now,
      resendAvailableAt: getResendAvailableAt(),
      updatedAt: now,
    })
    .where(eq(signupFlow.id, flowId));

  try {
    await sendTransactionalEmail({
      to: flow.email,
      subject: "Votre code de verification Planify",
      html: `
        <div style="font-family:Arial,sans-serif">
          <h2>Confirmez votre email</h2>
          <p>Votre nouveau code :</p>
          <p style="font-size:24px; font-weight:bold">${code}</p>
          <p>Ce code expire dans 10 minutes.</p>
        </div>
      `,
    });
    console.info("[signup:resend] email_sent", { flowId, email: flow.email });
  } catch (error) {
    console.error("[signup:resend] email_send_failed", {
      flowId,
      email: flow.email,
      error: (error as any)?.message || error,
    });
    return NextResponse.json(
      {
        error: "Impossible d'envoyer l'email.",
        details:
          process.env.NODE_ENV === "development"
            ? { message: (error as any)?.message }
            : undefined,
      },
      { status: 500 },
    );
  }

  return NextResponse.json({
    status: "code_sent",
    cooldownSeconds: getResendCooldownSeconds(),
  });
}

import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { signupFlow } from "@/db/schema";
import {
  createOrgAndPlan,
  ensureDefaultPlans,
  ensureSignupSchema,
  findPlanByCode,
  getNextStep,
} from "@/lib/signup";

export async function POST(req: Request) {
  await ensureSignupSchema();
  await ensureDefaultPlans();

  const body = await req.json();
  const flowId = String(body?.flowId || "").trim();
  const planCode = String(body?.planCode || "").trim();
  console.info("[signup:plan] request", { flowId, planCode });

  if (!flowId || !planCode) {
    console.warn("[signup:plan] missing_fields", {
      flowIdPresent: Boolean(flowId),
      planCodePresent: Boolean(planCode),
    });
    return NextResponse.json(
      { error: "Flow ou plan manquant." },
      { status: 400 },
    );
  }

  const [flow] = await db
    .select()
    .from(signupFlow)
    .where(eq(signupFlow.id, flowId))
    .limit(1);

  if (!flow) {
    console.warn("[signup:plan] flow_not_found", { flowId });
    return NextResponse.json({ error: "Flow invalide." }, { status: 401 });
  }

  if (flow.status === "plan_selected" && flow.orgId) {
    console.info("[signup:plan] already_selected", { flowId, orgId: flow.orgId });
    return NextResponse.json({
      status: "plan_selected",
      nextStep: getNextStep("plan_selected"),
    });
  }

  if (flow.status !== "verified") {
    console.warn("[signup:plan] not_verified", { flowId, status: flow.status });
    return NextResponse.json(
      { error: "Verification email requise." },
      { status: 400 },
    );
  }

  if (flow.invitationId) {
    return NextResponse.json(
      { error: "Invitation deja rattachee a une organisation." },
      { status: 400 },
    );
  }

  if (!flow.userId) {
    console.warn("[signup:plan] missing_user", { flowId });
    return NextResponse.json(
      { error: "Utilisateur manquant." },
      { status: 400 },
    );
  }

  const selectedPlan = await findPlanByCode(planCode);
  if (!selectedPlan) {
    console.warn("[signup:plan] plan_not_found", { flowId, planCode });
    return NextResponse.json({ error: "Plan introuvable." }, { status: 404 });
  }

  let org;
  try {
    org = await createOrgAndPlan({ flow, planId: selectedPlan.id });
  } catch (error) {
    console.error("[signup:plan] create_org_failed", {
      flowId,
      planCode,
      error: (error as any)?.message || error,
    });
    return NextResponse.json(
      {
        error: "Creation organisation impossible.",
        details:
          process.env.NODE_ENV === "development"
            ? { message: (error as any)?.message }
            : undefined,
      },
      { status: 500 },
    );
  }

  await db
    .update(signupFlow)
    .set({
      orgId: org.id,
      planId: selectedPlan.id,
      status: "plan_selected",
      updatedAt: new Date(),
    })
    .where(eq(signupFlow.id, flowId));
  console.info("[signup:plan] success", { flowId, orgId: org.id });

  return NextResponse.json({
    status: "plan_selected",
    nextStep: getNextStep("plan_selected"),
  });
}

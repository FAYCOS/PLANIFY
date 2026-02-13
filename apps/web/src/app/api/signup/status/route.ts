import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { signupFlow } from "@/db/schema";
import { ensureSignupSchema, getNextStep } from "@/lib/signup";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const cookieStore = await cookies();
  const flowIdParam = url.searchParams.get("flowId")?.trim();
  const flowIdCookie = cookieStore.get("planify_flow_id")?.value;
  const flowId = flowIdParam || flowIdCookie;
  const fromQuery = Boolean(flowIdParam);

  if (!flowId) {
    return NextResponse.json({
      flowId: null,
      status: "draft",
      nextStep: "/signup",
    });
  }

  await ensureSignupSchema();

  const [flow] = await db
    .select()
    .from(signupFlow)
    .where(eq(signupFlow.id, flowId))
    .limit(1);

  if (!flow) {
    console.warn("[signup:status] flow_not_found", { flowId });
    const response = NextResponse.json({
      flowId: null,
      status: "draft",
      nextStep: "/signup",
    });
    response.cookies.set("planify_flow_id", "", {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
    return response;
  }

  let status = flow.status;
  if (status === "code_sent" && flow.codeExpiresAt) {
    if (new Date(flow.codeExpiresAt) < new Date()) {
      status = "expired";
      await db
        .update(signupFlow)
        .set({ status: "expired", updatedAt: new Date() })
        .where(eq(signupFlow.id, flow.id));
    }
  }

  if (status === "completed" && !fromQuery) {
    const response = NextResponse.json({
      flowId: null,
      status: "draft",
      nextStep: "/signup",
    });
    response.cookies.set("planify_flow_id", "", {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
    return response;
  }

  const response = NextResponse.json({
    flowId: flow.id,
    email: flow.email,
    status,
    nextStep: getNextStep(status),
    planId: flow.planId,
    orgId: flow.orgId,
    provisioningStatus: flow.provisioningStatus,
    resendAvailableAt: flow.resendAvailableAt,
    attemptsCount: flow.attemptsCount,
  });
  if (status === "completed" || status === "expired") {
    response.cookies.set("planify_flow_id", "", {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
  }
  return response;
}

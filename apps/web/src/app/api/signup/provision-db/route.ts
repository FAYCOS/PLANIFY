import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { organization, signupFlow } from "@/db/schema";
import {
  buildSearchPathUrl,
  createSchemaForOrg,
  ensureSignupSchema,
  getNextStep,
} from "@/lib/signup";

export async function POST(req: Request) {
  await ensureSignupSchema();

  const body = await req.json();
  const flowId = String(body?.flowId || "").trim();
  console.info("[signup:provision] request", { flowId });

  if (!flowId) {
    console.warn("[signup:provision] missing_flow");
    return NextResponse.json({ error: "Flow manquant." }, { status: 400 });
  }

  const [flow] = await db
    .select()
    .from(signupFlow)
    .where(eq(signupFlow.id, flowId))
    .limit(1);

  if (!flow) {
    console.warn("[signup:provision] flow_not_found", { flowId });
    return NextResponse.json({ error: "Flow invalide." }, { status: 401 });
  }

  if (!flow.orgId) {
    console.warn("[signup:provision] missing_org", { flowId });
    return NextResponse.json(
      { error: "Organisation non definie." },
      { status: 400 },
    );
  }

  if (flow.status !== "plan_selected" && flow.status !== "provisioning" && flow.status !== "completed") {
    console.warn("[signup:provision] invalid_status", { flowId, status: flow.status });
    return NextResponse.json(
      { error: "Choix de plan requis." },
      { status: 400 },
    );
  }

  if (flow.status === "completed") {
    console.info("[signup:provision] already_completed", { flowId });
    return NextResponse.json({
      status: flow.status,
      nextStep: getNextStep(flow.status),
    });
  }

  const schemaName = `org_${flow.orgId.replace(/-/g, "").slice(0, 12)}`;
  const baseUrl = process.env.DATABASE_URL;
  if (!baseUrl) {
    console.error("[signup:provision] missing_database_url");
    return NextResponse.json(
      { error: "DATABASE_URL manquant." },
      { status: 500 },
    );
  }

  await db
    .update(signupFlow)
    .set({ status: "provisioning", updatedAt: new Date() })
    .where(eq(signupFlow.id, flowId));

  try {
    await createSchemaForOrg(schemaName);
    const dbUrl = buildSearchPathUrl(baseUrl, schemaName);

    await db
      .update(signupFlow)
      .set({
        status: "completed",
        provisioningStatus: "success",
        dbSchema: schemaName,
        dbUrl,
        updatedAt: new Date(),
      })
      .where(eq(signupFlow.id, flowId));
    await db
      .update(organization)
      .set({
        dbSchema: schemaName,
        dbUrl,
        updatedAt: new Date(),
      })
      .where(eq(organization.id, flow.orgId));
    console.info("[signup:provision] success", { flowId, schemaName });

    return NextResponse.json({
      status: "completed",
      nextStep: getNextStep("completed"),
      dbSchema: schemaName,
    });
  } catch (error) {
    console.error("[signup:provision] failed", {
      flowId,
      error: (error as any)?.message || error,
    });
    await db
      .update(signupFlow)
      .set({
        status: "provisioning",
        provisioningStatus: "failed",
        lastError: "Provisioning failed",
        updatedAt: new Date(),
      })
      .where(eq(signupFlow.id, flowId));
    return NextResponse.json(
      {
        error: "Provisioning impossible.",
        details:
          process.env.NODE_ENV === "development"
            ? { message: (error as any)?.message }
            : undefined,
      },
      { status: 500 },
    );
  }
}

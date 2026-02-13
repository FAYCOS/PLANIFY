import { NextResponse } from "next/server";

import { computeRoute } from "@/lib/geo";
import { requireOrgDb } from "@/lib/tenant";

export async function GET(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;

  const { searchParams } = new URL(req.url);
  const destination = searchParams.get("destination");
  if (!destination) {
    return NextResponse.json({ error: "destination required" }, { status: 400 });
  }

  const result = await computeRoute(destination, guard.orgId, guard.db);
  if (!result) {
    return NextResponse.json(
      { error: "route unavailable" },
      { status: 422 },
    );
  }

  return NextResponse.json(result);
}

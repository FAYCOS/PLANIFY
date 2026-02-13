import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";

import { db, dbForSchema } from "@/db";
import { organization } from "@/db/schema";
import { requireOrg } from "@/lib/auth-guard";

type OrgDbContext = {
  orgId: string;
  dbSchema: string;
  db: ReturnType<typeof dbForSchema>;
};

function buildSearchPathUrl(baseUrl: string, schemaName: string) {
  const url = new URL(baseUrl);
  const existing = url.searchParams.get("options");
  const searchPath = `-c search_path=${schemaName},public`;
  const merged = existing ? `${existing} ${searchPath}` : searchPath;
  url.searchParams.set("options", merged);
  return url.toString();
}

export async function getOrgDbById(orgId: string): Promise<OrgDbContext | null> {
  const [org] = await db
    .select({
      id: organization.id,
      dbSchema: organization.dbSchema,
      dbUrl: organization.dbUrl,
    })
    .from(organization)
    .where(eq(organization.id, orgId))
    .limit(1);

  if (!org) return null;

  const schemaName = org.dbSchema?.trim() || "public";

  if (!org.dbSchema) {
    const baseUrl = process.env.DATABASE_URL;
    const dbUrl = baseUrl ? buildSearchPathUrl(baseUrl, schemaName) : null;
    await db
      .update(organization)
      .set({
        dbSchema: schemaName,
        dbUrl: dbUrl ?? null,
        updatedAt: new Date(),
      })
      .where(eq(organization.id, orgId));
  }

  return { orgId, dbSchema: schemaName, db: dbForSchema(schemaName) };
}

export async function requireOrgDb() {
  const base = await requireOrg();
  if ("response" in base) return base;
  const orgId = base.orgId;
  const orgDb = await getOrgDbById(orgId);
  if (!orgDb) {
    return {
      response: NextResponse.json(
        { error: "Organisation introuvable." },
        { status: 403 },
      ),
    };
  }
  return { ...base, ...orgDb };
}

import { eq } from "drizzle-orm";

import { db } from "@/db";
import { team } from "@/db/schema";

export async function ensureDefaultTeam(orgId: string, createdByUserId?: string | null) {
  const [existing] = await db
    .select()
    .from(team)
    .where(eq(team.orgId, orgId))
    .limit(1);
  if (existing) {
    return existing;
  }
  const [created] = await db
    .insert(team)
    .values({
      orgId,
      name: "Equipe principale",
      description: "Equipe par defaut",
      createdByUserId: createdByUserId || null,
    })
    .returning();
  return created;
}

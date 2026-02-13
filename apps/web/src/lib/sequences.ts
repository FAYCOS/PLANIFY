import { and, eq, sql } from "drizzle-orm";

import { db } from "@/db";
import { documentSequence } from "@/db/schema";

type SequenceType = "devis" | "facture";

const PREFIXES: Record<SequenceType, string> = {
  devis: "D",
  facture: "F",
};

function formatNumber(prefix: string, currentNumber: number) {
  const year = new Date().getFullYear();
  return `${prefix}-${year}-${String(currentNumber).padStart(5, "0")}`;
}

export async function getNextDocumentNumber(
  type: SequenceType,
  orgId: string,
  tenantDb = db,
) {
  const prefix = PREFIXES[type];

  return tenantDb.transaction(async (tx) => {
    const existing = await tx
      .select()
      .from(documentSequence)
      .where(and(eq(documentSequence.type, type), eq(documentSequence.orgId, orgId)))
      .limit(1);

    if (existing.length === 0) {
      const [created] = await tx
        .insert(documentSequence)
        .values({
          orgId,
          type,
          prefix,
          currentNumber: 1,
        })
        .returning();
      return formatNumber(created.prefix ?? prefix, created.currentNumber);
    }

    const [updated] = await tx
      .update(documentSequence)
      .set({
        currentNumber: sql`${documentSequence.currentNumber} + 1`,
        updatedAt: sql`now()`,
      })
      .where(and(eq(documentSequence.type, type), eq(documentSequence.orgId, orgId)))
      .returning();

    return formatNumber(updated.prefix ?? prefix, updated.currentNumber);
  });
}

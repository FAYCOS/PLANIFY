import { db } from "@/db";
import { auditLog } from "@/db/schema";

type AuditInput = {
  action: string;
  entityType: string;
  entityId?: string | null;
  userId?: string | null;
  orgId?: string | null;
  ipAddress?: string | null;
  userAgent?: string | null;
  metadata?: Record<string, unknown> | null;
};

export async function logAudit(input: AuditInput) {
  try {
    await db.insert(auditLog).values({
      action: input.action,
      entityType: input.entityType,
      entityId: input.entityId ?? null,
      userId: input.userId ?? null,
      orgId: input.orgId ?? null,
      ipAddress: input.ipAddress ?? null,
      userAgent: input.userAgent ?? null,
      metadata: input.metadata ?? null,
    });
  } catch (error) {
    console.error("[audit] insert_failed", {
      action: input.action,
      entityType: input.entityType,
      entityId: input.entityId,
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

import { NextResponse } from "next/server";
import { sql } from "drizzle-orm";

import { db } from "@/db";
import { s3, s3Bucket } from "@/lib/s3";

export async function GET() {
  try {
    await db.execute(sql`select 1`);
    const emailConfigured = Boolean(
      process.env.GMAIL_CLIENT_ID ||
        process.env.RESEND_API_KEY ||
        process.env.MAILGUN_API_KEY,
    );
    const storageConfigured = Boolean(s3 && s3Bucket);
    return NextResponse.json({
      status: "ok",
      timestamp: new Date().toISOString(),
      checks: {
        db: "ok",
        email: emailConfigured ? "configured" : "missing",
        storage: storageConfigured ? "configured" : "missing",
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        status: "error",
        error: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    );
  }
}

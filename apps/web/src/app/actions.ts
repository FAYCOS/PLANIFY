"use server";

import { neon } from "@neondatabase/serverless";

export async function getData() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL manquant.");
  }
  const sql = neon(process.env.DATABASE_URL);
  const data = await sql`SELECT 1 as ok`;
  return data;
}

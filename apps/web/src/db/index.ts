import { Pool } from "pg";
import { drizzle } from "drizzle-orm/node-postgres";
import * as schema from "./schema";

const globalForDb = globalThis as unknown as { pool?: Pool };

const connectionString = process.env.DATABASE_URL;
if (!connectionString) {
  throw new Error("DATABASE_URL is not set");
}

const pool =
  globalForDb.pool ??
  new Pool({
    connectionString,
  });

if (process.env.NODE_ENV !== "production") {
  globalForDb.pool = pool;
}

export const db = drizzle(pool, { schema });
export { pool, schema };

const schemaPools = new Map<string, Pool>();

export function dbForSchema(schemaName: string) {
  const key = schemaName.trim();
  if (!key) {
    return db;
  }
  const existing = schemaPools.get(key);
  if (existing) {
    return drizzle(existing, { schema });
  }
  const url = new URL(connectionString);
  const searchPath = `-c search_path=${key},public`;
  const currentOptions = url.searchParams.get("options");
  url.searchParams.set(
    "options",
    currentOptions ? `${currentOptions} ${searchPath}` : searchPath,
  );
  const tenantPool = new Pool({ connectionString: url.toString() });
  schemaPools.set(key, tenantPool);
  return drizzle(tenantPool, { schema });
}

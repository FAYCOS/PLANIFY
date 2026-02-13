import crypto from "crypto";

import { and, eq, sql } from "drizzle-orm";

import { db, pool } from "@/db";
import {
  organization,
  orgPlan,
  plan,
  signupFlow,
  team,
  teamMember,
  user,
} from "@/db/schema";

const CODE_TTL_MINUTES = 10;
const MAX_ATTEMPTS = 5;
const RESEND_COOLDOWN_SECONDS = 60;

const PLAN_DEFINITIONS = [
  { code: "starter", name: "Starter" },
  { code: "team", name: "Team" },
  { code: "business", name: "Business" },
];

const TENANT_TABLES = [
  "clients",
  "client_contacts",
  "prestations",
  "devis",
  "factures",
  "paiements",
  "avoirs",
  "materiels",
  "materiels_prestations",
  "mouvements_materiel",
  "parametres_entreprise",
  "document_sequences",
  "prestation_ratings",
];

export function getSignupSecret() {
  return (
    process.env.SIGNUP_CODE_SECRET ||
    process.env.BETTER_AUTH_SECRET ||
    "planify-signup"
  );
}

let authSchemaReady: Promise<void> | null = null;
let signupSchemaReady: Promise<void> | null = null;

export function generateVerificationCode() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

export function hashVerificationCode(code: string) {
  return crypto
    .createHash("sha256")
    .update(`${code}:${getSignupSecret()}`)
    .digest("hex");
}

export function getCodeExpiryDate() {
  return new Date(Date.now() + CODE_TTL_MINUTES * 60 * 1000);
}

export function getResendAvailableAt() {
  return new Date(Date.now() + RESEND_COOLDOWN_SECONDS * 1000);
}

export function getNextStep(status: string) {
  switch (status) {
    case "code_sent":
    case "draft":
      return "/signup/verify";
    case "verified":
      return "/signup/plan";
    case "plan_selected":
    case "provisioning":
      return "/signup/provisioning";
    case "completed":
      return "/signup/success";
    default:
      return "/signup";
  }
}

export function buildSearchPathUrl(baseUrl: string, schemaName: string) {
  const url = new URL(baseUrl);
  const existing = url.searchParams.get("options");
  const searchPath = `-c search_path=${schemaName},public`;
  const merged = existing ? `${existing} ${searchPath}` : searchPath;
  url.searchParams.set("options", merged);
  return url.toString();
}

export async function ensureSignupSchema() {
  if (signupSchemaReady) {
    return signupSchemaReady;
  }
  signupSchemaReady = (async () => {
    await ensureAuthSchema();

    await pool.query(`
      CREATE TABLE IF NOT EXISTS plans (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code varchar(32) NOT NULL UNIQUE,
        name text NOT NULL,
        status varchar(16) NOT NULL DEFAULT 'active',
        price_cents integer NOT NULL DEFAULT 0,
        currency varchar(8) NOT NULL DEFAULT 'EUR',
        created_at timestamptz NOT NULL DEFAULT now()
      );
    `);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS org_plans (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        plan_id uuid NOT NULL REFERENCES plans(id) ON DELETE RESTRICT,
        status varchar(16) NOT NULL DEFAULT 'active',
        started_at timestamptz NOT NULL DEFAULT now(),
        ends_at timestamptz
      );
    `);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS signup_flows (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        email text NOT NULL,
        user_id uuid REFERENCES "user"(id) ON DELETE SET NULL,
        org_id uuid REFERENCES organizations(id) ON DELETE SET NULL,
        invitation_id uuid REFERENCES invitations(id) ON DELETE SET NULL,
        company_name text,
        country text,
        address text,
        phone varchar(32),
        size text,
        sector text,
        status varchar(32) NOT NULL DEFAULT 'draft',
        code_hash text,
        code_expires_at timestamptz,
        attempts_count integer NOT NULL DEFAULT 0,
        last_sent_at timestamptz,
        resend_available_at timestamptz,
        plan_id uuid REFERENCES plans(id) ON DELETE SET NULL,
        provisioning_status varchar(32) NOT NULL DEFAULT 'pending',
        db_schema text,
        db_url text,
        last_error text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      );
    `);

    await pool.query(
      `ALTER TABLE signup_flows ADD COLUMN IF NOT EXISTS invitation_id uuid REFERENCES invitations(id) ON DELETE SET NULL;`,
    );
    await pool.query(
      `ALTER TABLE signup_flows ADD COLUMN IF NOT EXISTS country text;`,
    );
  })();
  return signupSchemaReady;
}

export async function ensureAuthSchema() {
  if (authSchemaReady) {
    return authSchemaReady;
  }
  authSchemaReady = (async () => {
    await pool.query(`CREATE EXTENSION IF NOT EXISTS pgcrypto;`);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS organizations (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name text NOT NULL,
        country text,
        address text,
        phone varchar(32),
        size text,
        sector text,
        created_by_user_id uuid,
        db_schema text,
        db_url text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      );
    `);
    await pool.query(
      `ALTER TABLE organizations ADD COLUMN IF NOT EXISTS country text;`,
    );
    await pool.query(
      `ALTER TABLE organizations ADD COLUMN IF NOT EXISTS db_schema text;`,
    );
    await pool.query(
      `ALTER TABLE organizations ADD COLUMN IF NOT EXISTS db_url text;`,
    );

    await pool.query(`
      CREATE TABLE IF NOT EXISTS "user" (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        email text NOT NULL,
        email_verified boolean NOT NULL DEFAULT false,
        name text NOT NULL,
        image text,
        role varchar(32) NOT NULL DEFAULT 'member',
        nom text,
        prenom text,
        telephone varchar(32),
        must_change_password boolean NOT NULL DEFAULT false,
        org_id uuid REFERENCES organizations(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      );
    `);
    await pool.query(
      `ALTER TABLE "user" ALTER COLUMN role SET DEFAULT 'member';`,
    );
    await pool.query(
      `ALTER TABLE "user" ADD COLUMN IF NOT EXISTS must_change_password boolean NOT NULL DEFAULT false;`,
    );
    await pool.query(
      `CREATE UNIQUE INDEX IF NOT EXISTS user_email_unique ON "user"(email);`,
    );

    await pool.query(`
      CREATE TABLE IF NOT EXISTS account (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        provider_id text NOT NULL,
        account_id text NOT NULL,
        user_id uuid NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        access_token text,
        refresh_token text,
        id_token text,
        access_token_expires_at timestamptz,
        refresh_token_expires_at timestamptz,
        scope text,
        password text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      );
    `);
    await pool.query(
      `CREATE UNIQUE INDEX IF NOT EXISTS account_provider_unique ON account(provider_id, account_id);`,
    );

    await pool.query(`
      CREATE TABLE IF NOT EXISTS session (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        expires_at timestamptz NOT NULL,
        token text NOT NULL,
        ip_address text,
        user_agent text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      );
    `);
    await pool.query(
      `CREATE UNIQUE INDEX IF NOT EXISTS session_token_unique ON session(token);`,
    );

    await pool.query(`
      CREATE TABLE IF NOT EXISTS verification (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        identifier text NOT NULL,
        value text NOT NULL,
        expires_at timestamptz NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      );
    `);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS audit_logs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id uuid REFERENCES organizations(id),
        user_id uuid REFERENCES "user"(id) ON DELETE SET NULL,
        action varchar(64) NOT NULL,
        entity_type varchar(64) NOT NULL,
        entity_id uuid,
        ip_address text,
        user_agent text,
        metadata jsonb,
        created_at timestamptz NOT NULL DEFAULT now()
      );
    `);
    await pool.query(
      `CREATE INDEX IF NOT EXISTS audit_logs_org_idx ON audit_logs(org_id);`,
    );
    await pool.query(
      `CREATE INDEX IF NOT EXISTS audit_logs_entity_idx ON audit_logs(entity_type, entity_id);`,
    );

    await pool.query(`
      CREATE TABLE IF NOT EXISTS stripe_events (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        event_id text NOT NULL UNIQUE,
        type text NOT NULL,
        payload jsonb,
        created_at timestamptz NOT NULL DEFAULT now()
      );
    `);
    await pool.query(
      `CREATE UNIQUE INDEX IF NOT EXISTS stripe_events_event_unique ON stripe_events(event_id);`,
    );

    await pool.query(`
      CREATE TABLE IF NOT EXISTS teams (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        name text NOT NULL,
        description text,
        created_by_user_id uuid REFERENCES "user"(id) ON DELETE SET NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      );
    `);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS team_members (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        user_id uuid NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        role varchar(32) NOT NULL DEFAULT 'member',
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (team_id, user_id)
      );
    `);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS invitations (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        email text NOT NULL,
        role varchar(32) NOT NULL DEFAULT 'member',
        team_id uuid REFERENCES teams(id) ON DELETE SET NULL,
        token_hash text NOT NULL,
        status varchar(16) NOT NULL DEFAULT 'pending',
        expires_at timestamptz NOT NULL,
        created_by_user_id uuid REFERENCES "user"(id) ON DELETE SET NULL,
        accepted_by_user_id uuid REFERENCES "user"(id) ON DELETE SET NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        accepted_at timestamptz
      );
    `);
    await pool.query(
      `CREATE UNIQUE INDEX IF NOT EXISTS invitations_token_unique ON invitations(token_hash);`,
    );
    await pool.query(
      `CREATE INDEX IF NOT EXISTS invitations_org_idx ON invitations(org_id);`,
    );
    await pool.query(
      `CREATE INDEX IF NOT EXISTS invitations_email_idx ON invitations(email);`,
    );
  })();
  return authSchemaReady;
}

export async function ensureDefaultPlans() {
  for (const definition of PLAN_DEFINITIONS) {
    await db
      .insert(plan)
      .values({
        code: definition.code,
        name: definition.name,
        status: "active",
        priceCents: 0,
        currency: "EUR",
      })
      .onConflictDoNothing();
  }
}

export function getPlanDefinition(code: string) {
  return PLAN_DEFINITIONS.find((planDef) => planDef.code === code);
}

export async function findPlanByCode(code: string) {
  const [found] = await db.select().from(plan).where(eq(plan.code, code)).limit(1);
  return found;
}

export async function createOrgAndPlan({
  flow,
  planId,
}: {
  flow: typeof signupFlow.$inferSelect;
  planId: string;
}) {
  return db.transaction(async (tx) => {
    const [org] = await tx
      .insert(organization)
      .values({
        name: flow.companyName || "Planify",
        country: flow.country,
        address: flow.address,
        phone: flow.phone,
        size: flow.size,
        sector: flow.sector,
        createdByUserId: flow.userId || null,
      })
      .returning();

    await tx.insert(orgPlan).values({
      orgId: org.id,
      planId,
      status: "active",
    });

    const [defaultTeam] = await tx
      .insert(team)
      .values({
        orgId: org.id,
        name: "Equipe principale",
        description: "Equipe par defaut",
        createdByUserId: flow.userId || null,
      })
      .returning();

    if (flow.userId) {
      await tx
        .update(user)
        .set({
          orgId: org.id,
          role: "admin",
          emailVerified: true,
          updatedAt: sql`now()`,
        })
        .where(eq(user.id, flow.userId));

      if (defaultTeam?.id) {
        await tx
          .insert(teamMember)
          .values({
            teamId: defaultTeam.id,
            userId: flow.userId,
            role: "admin",
          })
          .onConflictDoNothing();
      }
    }

    return org;
  });
}

export async function createSchemaForOrg(schemaName: string) {
  await pool.query(`CREATE SCHEMA IF NOT EXISTS ${schemaName};`);

  for (const tableName of TENANT_TABLES) {
    await pool.query(
      `CREATE TABLE IF NOT EXISTS ${schemaName}.${tableName} (LIKE public.${tableName} INCLUDING ALL);`,
    );
  }
}

export async function loadSignupFlowById(flowId: string) {
  const [flow] = await db
    .select()
    .from(signupFlow)
    .where(eq(signupFlow.id, flowId))
    .limit(1);
  return flow;
}

export async function loadActiveSignupFlowByUserId(userId: string) {
  const [flow] = await db
    .select()
    .from(signupFlow)
    .where(
      and(eq(signupFlow.userId, userId), sql`status <> 'completed'`),
    )
    .limit(1);
  return flow;
}

export function getAttemptRemaining(attempts: number) {
  return Math.max(0, MAX_ATTEMPTS - attempts);
}

export function getMaxAttempts() {
  return MAX_ATTEMPTS;
}

export function getResendCooldownSeconds() {
  return RESEND_COOLDOWN_SECONDS;
}

import { NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { z } from "zod";

import { parametresEntreprise } from "@/db/schema";
import { requireOrgDb } from "@/lib/tenant";
import {
  decryptSensitive,
  encryptSensitive,
  isMaskedInput,
  maskSensitive,
} from "@/lib/crypto";

const paramSchema = z.object({
  nomEntreprise: z.string().optional().nullable(),
  adresse: z.string().optional().nullable(),
  codePostal: z.string().optional().nullable(),
  ville: z.string().optional().nullable(),
  email: z.string().email().optional().nullable(),
  telephone: z.string().optional().nullable(),
  emailSignature: z.string().optional().nullable(),
  stripePublicKey: z.string().optional().nullable(),
  stripeSecretKey: z.string().optional().nullable(),
  ribIban: z.string().optional().nullable(),
  ribBic: z.string().optional().nullable(),
  ribTitulaire: z.string().optional().nullable(),
  ribBanque: z.string().optional().nullable(),
});

export async function GET() {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const [row] = await tenantDb
    .select()
    .from(parametresEntreprise)
    .where(eq(parametresEntreprise.orgId, guard.orgId))
    .limit(1);
  if (!row) return NextResponse.json(null);
  return NextResponse.json({
    ...row,
    stripeSecretKey: maskSensitive(decryptSensitive(row.stripeSecretKey)),
    ribIban: maskSensitive(decryptSensitive(row.ribIban)),
    ribBic: maskSensitive(decryptSensitive(row.ribBic)),
    ribTitulaire: maskSensitive(decryptSensitive(row.ribTitulaire)),
    ribBanque: maskSensitive(decryptSensitive(row.ribBanque)),
  });
}

export async function POST(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  const tenantDb = guard.db;
  const payload = await req.json();
  const data = paramSchema.parse(payload);
  const encryptOrKeep = (value: string | null | undefined, existing?: string | null) => {
    if (!value || isMaskedInput(value)) return existing ?? null;
    return encryptSensitive(value);
  };
  let encryptedValues: {
    stripeSecretKey: string | null;
    ribIban: string | null;
    ribBic: string | null;
    ribTitulaire: string | null;
    ribBanque: string | null;
  } | null = null;

  try {
    encryptedValues = {
      stripeSecretKey: encryptOrKeep(data.stripeSecretKey, null),
      ribIban: encryptOrKeep(data.ribIban, null),
      ribBic: encryptOrKeep(data.ribBic, null),
      ribTitulaire: encryptOrKeep(data.ribTitulaire, null),
      ribBanque: encryptOrKeep(data.ribBanque, null),
    };
  } catch (error) {
    return NextResponse.json(
      {
        error: "Chiffrement indisponible. Configurez APP_ENCRYPTION_KEY.",
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    );
  }

  const [existing] = await tenantDb
    .select()
    .from(parametresEntreprise)
    .where(eq(parametresEntreprise.orgId, guard.orgId))
    .limit(1);
  if (existing) {
    const [updated] = await tenantDb
      .update(parametresEntreprise)
      .set({
        nomEntreprise: data.nomEntreprise ?? existing.nomEntreprise,
        adresse: data.adresse ?? existing.adresse,
        codePostal: data.codePostal ?? existing.codePostal,
        ville: data.ville ?? existing.ville,
        email: data.email ?? existing.email,
        telephone: data.telephone ?? existing.telephone,
        emailSignature: data.emailSignature ?? existing.emailSignature,
        stripePublicKey: data.stripePublicKey ?? existing.stripePublicKey,
        stripeSecretKey:
          data.stripeSecretKey || isMaskedInput(data.stripeSecretKey)
            ? encryptedValues?.stripeSecretKey ?? existing.stripeSecretKey
            : existing.stripeSecretKey,
        ribIban:
          data.ribIban || isMaskedInput(data.ribIban)
            ? encryptedValues?.ribIban ?? existing.ribIban
            : existing.ribIban,
        ribBic:
          data.ribBic || isMaskedInput(data.ribBic)
            ? encryptedValues?.ribBic ?? existing.ribBic
            : existing.ribBic,
        ribTitulaire:
          data.ribTitulaire || isMaskedInput(data.ribTitulaire)
            ? encryptedValues?.ribTitulaire ?? existing.ribTitulaire
            : existing.ribTitulaire,
        ribBanque:
          data.ribBanque || isMaskedInput(data.ribBanque)
            ? encryptedValues?.ribBanque ?? existing.ribBanque
            : existing.ribBanque,
      })
      .where(
        and(
          eq(parametresEntreprise.id, existing.id),
          eq(parametresEntreprise.orgId, guard.orgId),
        ),
      )
      .returning();
    return NextResponse.json(updated);
  }

  const [created] = await tenantDb
    .insert(parametresEntreprise)
    .values({
      orgId: guard.orgId,
      nomEntreprise: data.nomEntreprise ?? "Planify",
      adresse: data.adresse ?? null,
      codePostal: data.codePostal ?? null,
      ville: data.ville ?? null,
      email: data.email ?? null,
      telephone: data.telephone ?? null,
      emailSignature: data.emailSignature ?? null,
      stripePublicKey: data.stripePublicKey ?? null,
      stripeSecretKey: encryptedValues?.stripeSecretKey ?? null,
      ribIban: encryptedValues?.ribIban ?? null,
      ribBic: encryptedValues?.ribBic ?? null,
      ribTitulaire: encryptedValues?.ribTitulaire ?? null,
      ribBanque: encryptedValues?.ribBanque ?? null,
    })
    .returning();

  return NextResponse.json(created);
}

import { NextResponse } from "next/server";
import { sql } from "drizzle-orm";

import { db } from "@/db";
import { organization, team, teamMember, user } from "@/db/schema";
import { auth } from "@/lib/auth";
import { ensureAuthSchema } from "@/lib/signup";

export async function POST(req: Request) {
  await ensureAuthSchema();
  const bootstrapToken = process.env.BOOTSTRAP_ADMIN_TOKEN;
  const providedToken = req.headers.get("x-bootstrap-token");
  if (!bootstrapToken || providedToken !== bootstrapToken) {
    return NextResponse.json({ error: "acces refuse" }, { status: 403 });
  }

  let countResult = { count: 0 };
  try {
    countResult =
      (await db.select({ count: sql<number>`count(*)` }).from(user))[0] ||
      { count: 0 };
  } catch (error) {
    console.error("Bootstrap admin failed to read users:", error);
    return NextResponse.json(
      { error: "Base de donnees non disponible." },
      { status: 500 },
    );
  }

  if (Number(countResult.count) > 0) {
    return NextResponse.json(
      { error: "Creation reservee a l'administrateur." },
      { status: 403 },
    );
  }

  const body = await req.json();
  const email = String(body?.email || "").trim().toLowerCase();
  let name = String(body?.name || "").trim();
  const password = String(body?.password || "");

  if (!email || !password) {
    return NextResponse.json(
      { error: "Email et mot de passe requis." },
      { status: 400 },
    );
  }
  if (!name) {
    name = email.split("@")[0] || "Admin";
  }

  let createdUser: any = null;
  try {
    const created = await auth.api.signUpEmail({
      headers: new Headers(),
      body: {
        email,
        name,
        password,
        rememberMe: false,
      },
    });
    createdUser = (created as any)?.user ?? (created as any)?.data?.user;
  } catch (error) {
    console.error("Bootstrap admin signUp failed:", {
      email,
      error:
        typeof error === "object" && error !== null
          ? {
              message: (error as any).message,
              code: (error as any).code,
              status: (error as any).status,
            }
          : error,
    });
    return NextResponse.json(
      {
        error: "Creation utilisateur impossible.",
        details:
          process.env.NODE_ENV === "development"
            ? {
                message: (error as any)?.message,
                code: (error as any)?.code,
                status: (error as any)?.status,
              }
            : undefined,
      },
      { status: 400 },
    );
  }

  if (!createdUser?.id) {
    return NextResponse.json(
      { error: "Creation utilisateur impossible." },
      { status: 400 },
    );
  }

  await db
    .transaction(async (tx) => {
      const [org] = await tx
        .insert(organization)
        .values({
          name: "Planify",
          createdByUserId: createdUser.id,
        })
        .returning();

      const [defaultTeam] = await tx
        .insert(team)
        .values({
          orgId: org.id,
          name: "Equipe principale",
          description: "Equipe par defaut",
          createdByUserId: createdUser.id,
        })
        .returning();

      await tx
        .update(user)
        .set({
          role: "admin",
          emailVerified: true,
          mustChangePassword: true,
          orgId: org.id,
          updatedAt: sql`now()`,
        })
        .where(sql`id = ${createdUser.id}`);

      if (defaultTeam?.id) {
        await tx.insert(teamMember).values({
          teamId: defaultTeam.id,
          userId: createdUser.id,
          role: "admin",
        });
      }
    });

  return NextResponse.json({ id: createdUser.id });
}

import { NextResponse } from "next/server";

import { getServerSession } from "@/lib/auth-session";

type GuardSuccess = {
  session: NonNullable<Awaited<ReturnType<typeof getServerSession>>>;
  userId: string;
  orgId?: string;
};

type GuardResult =
  | { response: NextResponse }
  | GuardSuccess;

type OrgGuardSuccess = GuardSuccess & { orgId: string };

type OrgGuardResult =
  | { response: NextResponse }
  | OrgGuardSuccess;

export async function requireSession(): Promise<GuardResult> {
  const session = await getServerSession();
  const userId = session?.user?.id;
  if (!session || !userId) {
    return {
      response: NextResponse.json({ error: "Non autorise." }, { status: 401 }),
    };
  }
  return { session: session as GuardSuccess["session"], userId };
}

export async function requireOrg(): Promise<OrgGuardResult> {
  const base = await requireSession();
  if ("response" in base) {
    return base;
  }
  const orgId = base.session.user?.orgId;
  if (!orgId) {
    return {
      response: NextResponse.json(
        { error: "Organisation manquante." },
        { status: 403 },
      ),
    };
  }
  return { ...base, orgId } as OrgGuardSuccess;
}

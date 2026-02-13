import { redirect } from "next/navigation";
import { desc, eq } from "drizzle-orm";

import { db } from "@/db";
import { user } from "@/db/schema";
import { getServerSession } from "@/lib/auth-session";
import UsersClient from "@/components/parametres/users-client";

export const dynamic = "force-dynamic";

export default async function UtilisateursPage() {
  const session = await getServerSession();
  if (!session?.user?.id) {
    redirect("/login");
  }
  if (session.user.role !== "admin") {
    redirect("/dashboard");
  }
  const orgId = (session?.user as { orgId?: string } | undefined)?.orgId;
  if (!orgId) {
    redirect("/signup");
  }

  const users = await db
    .select({
      id: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
      mustChangePassword: user.mustChangePassword,
      createdAt: user.createdAt,
    })
    .from(user)
    .where(eq(user.orgId, orgId))
    .orderBy(desc(user.createdAt));

  return <UsersClient initialUsers={users} />;
}

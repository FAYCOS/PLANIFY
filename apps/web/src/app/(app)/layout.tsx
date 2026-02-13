import { redirect } from "next/navigation";

import { SubNav } from "@/components/shell/sub-nav";
import { TopNav } from "@/components/shell/top-nav";
import { db } from "@/db";
import { signupFlow } from "@/db/schema";
import { getServerSession } from "@/lib/auth-session";
import { ensureSignupSchema, getNextStep } from "@/lib/signup";
import { and, eq, sql } from "drizzle-orm";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession();
  if (!session) {
    redirect("/login");
  }
  const user = session.user as { id?: string; mustChangePassword?: boolean | null };
  if (user?.mustChangePassword) {
    redirect("/first-login");
  }
  const userId = user?.id;
  if (userId) {
    await ensureSignupSchema();
    const [flow] = await db
      .select()
      .from(signupFlow)
      .where(and(eq(signupFlow.userId, userId), sql`status <> 'completed'`))
      .limit(1);
    if (flow) {
      let status = flow.status;
      if (status === "code_sent" && flow.codeExpiresAt) {
        if (new Date(flow.codeExpiresAt) < new Date()) {
          status = "expired";
          await db
            .update(signupFlow)
            .set({ status: "expired", updatedAt: new Date() })
            .where(eq(signupFlow.id, flow.id));
        }
      }
      if (status === "expired") {
        redirect("/signup");
      }
      redirect(getNextStep(status));
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNav />
      <SubNav />
      <main className="mx-auto w-full max-w-6xl px-6 py-8">
        {children}
      </main>
    </div>
  );
}

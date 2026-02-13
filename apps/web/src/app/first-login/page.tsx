import { redirect } from "next/navigation";

import FirstLoginForm from "./first-login-form";
import { getServerSession } from "@/lib/auth-session";

export default async function FirstLoginPage() {
  const session = await getServerSession();
  if (!session) {
    redirect("/login");
  }

  if (!(session.user as any)?.mustChangePassword) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto flex min-h-screen w-full max-w-6xl items-center justify-center px-6 py-12">
        <FirstLoginForm email={session.user.email ?? ""} />
      </main>
    </div>
  );
}

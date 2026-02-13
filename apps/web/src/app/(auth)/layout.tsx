import Image from "next/image";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <Image
              src="/planify-logo.png"
              alt="Planify"
              width={64}
              height={64}
              className="rounded-2xl bg-white p-1.5 shadow-sm ring-1 ring-black/5"
              priority
            />
            <Badge variant="secondary">Beta</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" asChild className="hidden md:inline-flex">
              <Link href="/login">Se connecter</Link>
            </Button>
            <Button asChild>
              <Link href="/signup">Essayer Planify</Link>
            </Button>
          </div>
        </div>
      </header>
      <div className="flex min-h-[calc(100vh-72px)] items-center justify-center p-6">
        {children}
      </div>
    </div>
  );
}

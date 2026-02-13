"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { getSectionFromPath, topNavItems } from "@/components/shell/nav-config";

export function TopNav() {
  const pathname = usePathname();
  const activeSection = getSectionFromPath(pathname);

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/dashboard" className="flex items-center gap-2">
          <Image
            src="/planify-logo.png"
            alt="Planify"
            width={48}
            height={48}
            className="rounded-2xl bg-white p-1 shadow-sm ring-1 ring-black/5"
            priority
          />
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto">
          {topNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.section;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2 rounded-full px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

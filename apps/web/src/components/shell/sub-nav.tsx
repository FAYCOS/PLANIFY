"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { getSectionFromPath, subNavMap } from "@/components/shell/nav-config";

export function SubNav() {
  const pathname = usePathname();
  const section = getSectionFromPath(pathname);
  const items = subNavMap[section];

  if (!items?.length) return null;

  return (
    <div className="border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl gap-2 overflow-x-auto px-6 py-3">
        {items.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm transition-colors",
                isActive
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-transparent bg-muted/50 text-muted-foreground hover:bg-muted",
              )}
            >
              {item.icon ? <item.icon className="h-4 w-4" /> : null}
              {item.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

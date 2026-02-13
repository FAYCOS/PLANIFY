"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ClipboardList,
  Boxes,
  CreditCard,
  FileText,
  Receipt,
  Users,
  Settings,
} from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { label: "Accueil", href: "/dashboard", icon: LayoutDashboard },
  { label: "Missions", href: "/missions", icon: ClipboardList },
  { label: "Materiel", href: "/materiel", icon: Boxes },
  { label: "Devis", href: "/finance/devis", icon: FileText },
  { label: "Factures", href: "/finance/factures", icon: Receipt },
  { label: "Paiements", href: "/finance/paiements", icon: CreditCard },
  { label: "Clients", href: "/clients", icon: Users },
  { label: "Parametres", href: "/parametres", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 flex-col border-r bg-white/70 px-3 py-6 backdrop-blur">
      <div className="px-3 pb-6">
        <div className="flex items-center gap-2">
          <Image
            src="/planify-logo.png"
            alt="Planify"
            width={28}
            height={28}
            className="rounded-lg"
            priority
          />
          <div className="text-lg font-semibold">Planify</div>
        </div>
        <div className="text-xs text-muted-foreground">Operations & Finance</div>
      </div>
      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-3 pt-4 text-xs text-muted-foreground">v2 Next</div>
    </aside>
  );
}

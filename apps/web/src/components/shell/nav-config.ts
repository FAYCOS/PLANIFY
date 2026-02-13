import {
  LayoutDashboard,
  ClipboardList,
  Boxes,
  CreditCard,
  Users,
  Settings,
  FileText,
  Receipt,
} from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  section: string;
};

export const topNavItems: NavItem[] = [
  {
    label: "Accueil",
    href: "/dashboard",
    icon: LayoutDashboard,
    section: "dashboard",
  },
  {
    label: "Missions",
    href: "/missions",
    icon: ClipboardList,
    section: "missions",
  },
  {
    label: "Materiel",
    href: "/materiel",
    icon: Boxes,
    section: "materiel",
  },
  {
    label: "Finance",
    href: "/finance/factures",
    icon: CreditCard,
    section: "finance",
  },
  {
    label: "Clients",
    href: "/clients",
    icon: Users,
    section: "clients",
  },
  {
    label: "Parametres",
    href: "/parametres",
    icon: Settings,
    section: "parametres",
  },
];

export const subNavMap: Record<
  string,
  { label: string; href: string; icon?: typeof FileText }[]
> = {
  finance: [
    { label: "Devis", href: "/finance/devis", icon: FileText },
    { label: "Factures", href: "/finance/factures", icon: Receipt },
    { label: "Paiements", href: "/finance/paiements", icon: CreditCard },
  ],
  materiel: [
    { label: "Catalogue", href: "/materiel" },
    { label: "Scan", href: "/materiel/scan" },
  ],
  parametres: [
    { label: "Entreprise", href: "/parametres" },
    { label: "Utilisateurs", href: "/parametres/utilisateurs" },
  ],
};

export function getSectionFromPath(pathname: string) {
  if (pathname.startsWith("/finance")) return "finance";
  if (pathname.startsWith("/missions")) return "missions";
  if (pathname.startsWith("/materiel")) return "materiel";
  if (pathname.startsWith("/clients")) return "clients";
  if (pathname.startsWith("/parametres")) return "parametres";
  return "dashboard";
}

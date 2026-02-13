export const ROLE_ALIASES: Record<string, string> = {
  dj: "member",
  technicien: "member",
};

export const ROLE_ORDER = ["viewer", "member", "manager", "admin"] as const;
export type Role = (typeof ROLE_ORDER)[number];

export function normalizeRole(role?: string | null): Role {
  const raw = (role || "").toLowerCase().trim();
  const mapped = ROLE_ALIASES[raw] || raw;
  if (ROLE_ORDER.includes(mapped as Role)) {
    return mapped as Role;
  }
  return "viewer";
}

export function roleRank(role?: string | null) {
  return ROLE_ORDER.indexOf(normalizeRole(role));
}

export function hasRole(role: string | null | undefined, required: Role) {
  return roleRank(role) >= ROLE_ORDER.indexOf(required);
}

export const ROLE_OPTIONS: { value: string; label: string }[] = [
  { value: "admin", label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "member", label: "Member" },
  { value: "viewer", label: "Viewer" },
  { value: "dj", label: "Legacy: DJ" },
  { value: "technicien", label: "Legacy: Technicien" },
];

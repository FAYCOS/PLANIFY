"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ROLE_OPTIONS } from "@/lib/roles";

type UserRow = {
  id: string;
  email: string;
  name: string;
  role: string;
  mustChangePassword?: boolean;
  createdAt: string;
};

type InvitationRow = {
  id: string;
  email: string;
  role: string;
  status: string;
  createdAt: string;
  expiresAt?: string | null;
};

const roles = ROLE_OPTIONS;

export default function UsersClient({ initialUsers }: { initialUsers: UserRow[] }) {
  const [users, setUsers] = useState<UserRow[]>(initialUsers);
  const [invites, setInvites] = useState<InvitationRow[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [formEmail, setFormEmail] = useState("");
  const [formName, setFormName] = useState("");
  const [formRole, setFormRole] = useState("member");
  const [formPassword, setFormPassword] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviteStatus, setInviteStatus] = useState<string | null>(null);

  const load = async () => {
    const res = await fetch("/api/users");
    if (!res.ok) {
      setStatus("Acces refuse ou erreur API.");
      return;
    }
    const data = (await res.json()) as UserRow[];
    setUsers(data);
  };

  const loadInvites = async () => {
    const res = await fetch("/api/invitations");
    if (!res.ok) {
      return;
    }
    const data = (await res.json()) as InvitationRow[];
    setInvites(data);
  };

  useEffect(() => {
    let active = true;
    const fetchInvites = async () => {
      const res = await fetch("/api/invitations");
      if (!res.ok || !active) {
        return;
      }
      const data = (await res.json()) as InvitationRow[];
      if (active) {
        setInvites(data);
      }
    };
    fetchInvites();
    return () => {
      active = false;
    };
  }, []);

  const handleInvite = async () => {
    setInviteStatus(null);
    const res = await fetch("/api/invitations", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        email: inviteEmail,
        role: inviteRole,
      }),
    });
    if (!res.ok) {
      setInviteStatus("Impossible d'envoyer l'invitation.");
      return;
    }
    setInviteStatus("Invitation envoyee.");
    setInviteEmail("");
    setInviteRole("member");
    await loadInvites();
  };

  const handleRoleChange = async (userId: string, role: string) => {
    const res = await fetch(`/api/users/${userId}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ role }),
    });
    if (!res.ok) {
      setStatus("Impossible de mettre a jour le role.");
      return;
    }
    setStatus("Role mis a jour.");
    await load();
  };

  const handleCreate = async () => {
    setStatus(null);
    const res = await fetch("/api/users", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        email: formEmail,
        name: formName,
        role: formRole,
        password: formPassword,
      }),
    });
    if (!res.ok) {
      setStatus("Impossible de creer l'utilisateur.");
      return;
    }
    setStatus("Utilisateur cree.");
    setFormEmail("");
    setFormName("");
    setFormRole("member");
    setFormPassword("");
    await load();
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Utilisateurs</CardTitle>
        <Button onClick={load} variant="outline">
          Rafraichir
        </Button>
      </CardHeader>
      <CardContent>
        {status ? (
          <div className="mb-4 text-sm text-muted-foreground">{status}</div>
        ) : null}
        <div className="mb-6 grid gap-4 rounded-lg border border-border bg-white p-4 md:grid-cols-4">
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Email</label>
            <input
              className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
              value={formEmail}
              onChange={(event) => setFormEmail(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Nom complet</label>
            <input
              className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
              value={formName}
              onChange={(event) => setFormName(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Role</label>
            <select
              className="w-full rounded-md border border-border bg-white px-2 py-2 text-sm"
              value={formRole}
              onChange={(event) => setFormRole(event.target.value)}
            >
              {roles.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">
              Mot de passe temporaire
            </label>
            <input
              className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
              value={formPassword}
              onChange={(event) => setFormPassword(event.target.value)}
              type="password"
            />
          </div>
          <div className="md:col-span-4">
            <Button onClick={handleCreate}>Creer l&apos;utilisateur</Button>
          </div>
        </div>
        <div className="mb-6 grid gap-4 rounded-lg border border-border bg-white p-4 md:grid-cols-4">
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Email a inviter</label>
            <input
              className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
              value={inviteEmail}
              onChange={(event) => setInviteEmail(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Role</label>
            <select
              className="w-full rounded-md border border-border bg-white px-2 py-2 text-sm"
              value={inviteRole}
              onChange={(event) => setInviteRole(event.target.value)}
            >
              {roles.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2 flex items-end">
            <Button onClick={handleInvite}>Inviter par email</Button>
          </div>
          {inviteStatus ? (
            <div className="md:col-span-4 text-sm text-muted-foreground">
              {inviteStatus}
            </div>
          ) : null}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2">Nom</th>
                <th className="py-2">Email</th>
                <th className="py-2">Role</th>
                <th className="py-2">Mdp requis</th>
                <th className="py-2">Cree le</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b">
                  <td className="py-2 font-medium">{user.name}</td>
                  <td className="py-2">{user.email}</td>
                  <td className="py-2">
                    <select
                      className="rounded-md border border-border bg-white px-2 py-1 text-sm"
                      value={user.role}
                      onChange={(event) =>
                        handleRoleChange(user.id, event.target.value)
                      }
                    >
                      {roles.map((role) => (
                        <option key={role.value} value={role.value}>
                          {role.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2">
                    {user.mustChangePassword ? "Oui" : "Non"}
                  </td>
                  <td className="py-2">
                    {new Date(user.createdAt).toLocaleDateString("fr-FR")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-8">
          <div className="mb-2 text-sm font-semibold">Invitations en attente</div>
          {invites.length === 0 ? (
            <div className="text-sm text-muted-foreground">Aucune invitation.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2">Email</th>
                    <th className="py-2">Role</th>
                    <th className="py-2">Statut</th>
                    <th className="py-2">Expire le</th>
                  </tr>
                </thead>
                <tbody>
                  {invites.map((invite) => (
                    <tr key={invite.id} className="border-b">
                      <td className="py-2">{invite.email}</td>
                      <td className="py-2">{invite.role}</td>
                      <td className="py-2">{invite.status}</td>
                      <td className="py-2">
                        {invite.expiresAt
                          ? new Date(invite.expiresAt).toLocaleDateString("fr-FR")
                          : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

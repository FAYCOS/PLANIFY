"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Props = {
  email: string;
};

export default function FirstLoginForm({ email }: Props) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch("/api/auth/change-password", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          currentPassword,
          newPassword,
          revokeOtherSessions: true,
        }),
      });
      if (!res.ok) {
        setMessage("Mot de passe invalide ou trop court.");
        return;
      }

      const mark = await fetch("/api/users/me", { method: "PATCH" });
      if (!mark.ok) {
        setMessage("Mot de passe mis a jour, mais statut non synchronise.");
        return;
      }

      window.location.href = "/dashboard";
    } catch {
      setMessage("Erreur reseau.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Finaliser votre compte</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-sm text-muted-foreground">
          Compte : <span className="font-medium text-foreground">{email}</span>
        </div>
        <div className="space-y-2">
          <Label>Mot de passe temporaire</Label>
          <Input
            type="password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Nouveau mot de passe</Label>
          <Input
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
          />
        </div>
        <Button className="w-full" onClick={handleSubmit} disabled={loading}>
          Mettre a jour le mot de passe
        </Button>
        {message ? (
          <div className="text-sm text-muted-foreground">{message}</div>
        ) : null}
      </CardContent>
    </Card>
  );
}

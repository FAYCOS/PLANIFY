"use client";

import { useState } from "react";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function RegisterPage() {
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (!email || !password) {
      setMessage("Email et mot de passe requis.");
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch("/api/users/bootstrap", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          name: [prenom, nom].filter(Boolean).join(" "),
        }),
      });
      if (!res.ok) {
        let errorMessage = "Creation impossible. Verifiez les informations.";
        try {
          const data = (await res.json()) as { error?: string };
          if (data?.error) {
            errorMessage = data.error;
          }
        } catch {
          // ignore JSON parse issues
        }
        setMessage(errorMessage);
      } else {
        setMessage("Compte admin cree. Vous pouvez vous connecter.");
      }
    } catch {
      setMessage("Erreur reseau.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Creer un compte</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Prenom</Label>
            <Input value={prenom} onChange={(e) => setPrenom(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Nom</Label>
            <Input value={nom} onChange={(e) => setNom(e.target.value)} />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Email</Label>
          <Input
            type="email"
            placeholder="email@exemple.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Mot de passe</Label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <Button className="w-full" onClick={handleRegister} disabled={loading}>
          Creer le compte admin
        </Button>
        <div className="text-sm text-muted-foreground">
          Deja un compte ?{" "}
          <Link className="text-primary underline" href="/login">
            Se connecter
          </Link>
        </div>
        {message ? (
          <div className="text-sm text-muted-foreground">{message}</div>
        ) : null}
      </CardContent>
    </Card>
  );
}

"use client";

import { useState } from "react";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePasswordLogin = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch("/api/auth/sign-in/email", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        let errorMessage = "Connexion impossible. Verifiez vos identifiants.";
        try {
          const data = (await res.json()) as {
            error?: string | { message?: string; code?: string };
            message?: string;
            code?: string;
          };
          const rawMessage =
            typeof data?.error === "string"
              ? data.error
              : data?.error?.message || data?.message || data?.code || "";
          if (
            res.status === 403 ||
            /EMAIL_NOT_VERIFIED/i.test(rawMessage || "")
          ) {
            errorMessage =
              "Email non verifie. Terminez l'inscription via le code recu.";
          } else if (rawMessage) {
            errorMessage = rawMessage;
          }
        } catch {
          // ignore JSON parse issues
        }
        setMessage(errorMessage);
      } else {
        window.location.href = "/dashboard";
      }
    } catch {
      setMessage("Erreur reseau.");
    } finally {
      setLoading(false);
    }
  };

  const handleMagicLink = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch("/api/auth/sign-in/magic-link", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        setMessage("Impossible d'envoyer le lien.");
      } else {
        setMessage("Lien envoye. Verifiez votre boite mail.");
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
        <CardTitle>Connexion Planify</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Email</Label>
          <Input
            type="email"
            placeholder="email@exemple.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Mot de passe</Label>
          <Input
            type="password"
            placeholder="Votre mot de passe"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <Button
          className="w-full"
          onClick={handlePasswordLogin}
          disabled={loading}
        >
          Se connecter
        </Button>
        <Button
          className="w-full"
          variant="outline"
          onClick={handleMagicLink}
          disabled={loading || !email}
        >
          Recevoir un lien magique
        </Button>
        <div className="text-sm text-muted-foreground">
          Pas encore de compte ?{" "}
          <Link className="text-primary underline" href="/signup">
            Demarrer l&apos;inscription
          </Link>
        </div>
        {message ? (
          <div className="text-sm text-muted-foreground">{message}</div>
        ) : null}
      </CardContent>
    </Card>
  );
}

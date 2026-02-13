"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function InviteAcceptPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "auth" | "error"
  >(() => (token ? "idle" : "error"));
  const [message, setMessage] = useState<string | null>(() =>
    token ? null : "Token d'invitation manquant.",
  );

  useEffect(() => {
    if (!token) return;

    const run = async () => {
      setStatus("loading");
      try {
        const res = await fetch("/api/invitations/accept", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ token }),
        });
        if (res.status === 401) {
          setStatus("auth");
          return;
        }
        const data = (await res.json().catch(() => null)) as { error?: string } | null;
        if (!res.ok) {
          setStatus("error");
          setMessage(data?.error || "Impossible d'accepter l'invitation.");
          return;
        }
        setStatus("success");
        setMessage("Invitation acceptee. Redirection...");
        setTimeout(() => router.push("/dashboard"), 800);
      } catch {
        setStatus("error");
        setMessage("Erreur reseau.");
      }
    };

    run();
  }, [router, token]);

  return (
    <Card className="w-full max-w-lg">
      <CardHeader>
        <CardTitle>Invitation Planify</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {status === "loading" && (
          <div className="text-sm text-muted-foreground">Validation en cours...</div>
        )}
        {status === "success" && (
          <div className="text-sm text-muted-foreground">{message}</div>
        )}
        {status === "error" && (
          <div className="text-sm text-muted-foreground">{message}</div>
        )}
        {status === "auth" && (
          <div className="space-y-3">
            <div className="text-sm text-muted-foreground">
              Connectez-vous ou creez un compte pour accepter l&apos;invitation.
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button asChild variant="outline">
                <Link href={`/login?invite=${encodeURIComponent(token)}`}>
                  Se connecter
                </Link>
              </Button>
              <Button asChild>
                <Link href={`/signup?invite=${encodeURIComponent(token)}`}>
                  Creer un compte
                </Link>
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

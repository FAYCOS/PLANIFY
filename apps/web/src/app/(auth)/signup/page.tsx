"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  clearFlowId,
  loadFlowId,
  loadInviteToken,
  saveFlowId,
  saveInviteToken,
} from "@/lib/signup-client";

export default function SignupPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [companyName, setCompanyName] = useState("");
  const [country, setCountry] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [size, setSize] = useState("");
  const [sector, setSector] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const inviteToken = searchParams.get("invite") || loadInviteToken();

  useEffect(() => {
    if (inviteToken) {
      saveInviteToken(inviteToken);
    }
    const existingFlow = loadFlowId();
    const statusUrl = existingFlow
      ? `/api/signup/status?flowId=${existingFlow}`
      : "/api/signup/status";
    fetch(statusUrl)
      .then(async (res) => {
        if (!res.ok) {
          clearFlowId();
          return null;
        }
        return (await res.json()) as { flowId?: string; nextStep?: string; status?: string } | null;
      })
      .then((data) => {
        if (!data) return;
        if (data.status === "expired") {
          clearFlowId();
          return;
        }
        if (data.status === "completed") {
          clearFlowId();
          return;
        }
        if (data.flowId && !existingFlow) {
          saveFlowId(data.flowId);
        }
        if (data?.nextStep && data.nextStep !== "/signup") {
          router.replace(data.nextStep);
        }
      })
      .catch(() => null);
  }, [inviteToken, router]);

  const handleSignup = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch("/api/signup/start", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          companyName,
          country,
          address,
          phone,
          size,
          sector,
          inviteToken,
        }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as {
          error?: string;
        } | null;
        setMessage(data?.error || "Creation impossible.");
        return;
      }
      const data = (await res.json()) as { flowId: string };
      saveFlowId(data.flowId);
      router.push("/signup/verify");
    } catch {
      setMessage("Erreur reseau.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-lg">
      <CardHeader>
        <CardTitle>Creer votre espace Planify</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {inviteToken ? (
          <div className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
            Invitation detectee. Renseignez votre email et un mot de passe pour
            rejoindre l&apos;organisation.
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <Label>Nom de l&apos;entreprise</Label>
              <Input
                value={companyName}
                onChange={(event) => setCompanyName(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Pays</Label>
              <Input
                value={country}
                onChange={(event) => setCountry(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Adresse</Label>
              <Input
                value={address}
                onChange={(event) => setAddress(event.target.value)}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Telephone</Label>
                <Input
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Taille</Label>
                <Input
                  value={size}
                  onChange={(event) => setSize(event.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Secteur</Label>
              <Input
                value={sector}
                onChange={(event) => setSector(event.target.value)}
              />
            </div>
          </>
        )}
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
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <Button className="w-full" onClick={handleSignup} disabled={loading}>
          Demarrer l&apos;inscription
        </Button>
        {message ? (
          <div className="text-sm text-muted-foreground">{message}</div>
        ) : null}
      </CardContent>
    </Card>
  );
}

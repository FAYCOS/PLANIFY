"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import SignaturePad from "@/components/finance/signature-pad";

export default function PublicDevisSignPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const orgId = searchParams.get("orgId") || "";

  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">(
    "idle",
  );
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (signatureImage: string) => {
    if (!token || !orgId) {
      setStatus("error");
      setMessage("Lien invalide.");
      return;
    }
    setStatus("loading");
    setMessage(null);
    try {
      const res = await fetch("/api/devis/sign-public", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ token, orgId, signatureImage }),
      });
      const data = (await res.json().catch(() => null)) as { error?: string } | null;
      if (!res.ok) {
        setStatus("error");
        setMessage(data?.error || "Signature impossible.");
        return;
      }
      setStatus("success");
      setMessage("Merci, votre devis est signe.");
    } catch {
      setStatus("error");
      setMessage("Erreur reseau.");
    }
  };

  return (
    <Card className="w-full max-w-lg">
      <CardHeader>
        <CardTitle>Signature du devis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        {!token || !orgId ? (
          <div>Lien invalide ou incomplet.</div>
        ) : null}
        {status === "success" ? (
          <div>{message}</div>
        ) : (
          <>
            <div>Signez ci-dessous pour valider le devis.</div>
            <SignaturePad onSubmit={handleSubmit} />
            {status === "loading" ? (
              <Button disabled className="w-full">
                Enregistrement...
              </Button>
            ) : null}
          </>
        )}
        {message && status !== "success" ? <div>{message}</div> : null}
      </CardContent>
    </Card>
  );
}

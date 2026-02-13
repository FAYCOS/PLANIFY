"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { SignaturePad } from "@/components/signature/signature-pad";

type DevisActionsProps = {
  id: string;
  locked: boolean;
  statut?: string | null;
};

export function DevisActions({ id, locked, statut }: DevisActionsProps) {
  const [signature, setSignature] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  const handleSend = async () => {
    const res = await fetch(`/api/devis/${id}/send`, { method: "POST" });
    setStatus(res.ok ? "Devis envoye." : "Erreur lors de l'envoi.");
  };

  const handleSign = async () => {
    if (!signature) return;
    const res = await fetch(`/api/devis/${id}/sign`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ signatureImage: signature }),
    });
    setStatus(res.ok ? "Devis signe." : "Erreur de signature.");
  };

  const handleRemind = async () => {
    const res = await fetch(`/api/devis/${id}/remind`, { method: "POST" });
    setStatus(res.ok ? "Relance envoyee." : "Erreur relance.");
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" asChild>
          <a href={`/api/devis/${id}/pdf`} target="_blank" rel="noreferrer">
            PDF
          </a>
        </Button>
        {!locked ? (
          <>
            <Button onClick={handleSend} variant="outline">
              Envoyer
            </Button>
            <Button onClick={handleSign}>Signer</Button>
          </>
        ) : null}
        {statut === "envoye" ? (
          <Button onClick={handleRemind} variant="outline">
            Relancer
          </Button>
        ) : null}
      </div>
      {!locked ? (
        <div>
          <p className="text-sm text-muted-foreground">
            Signature du client
          </p>
          <SignaturePad onChange={setSignature} />
        </div>
      ) : null}
      {status ? <div className="text-sm text-muted-foreground">{status}</div> : null}
    </div>
  );
}

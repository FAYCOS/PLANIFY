"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

type FactureActionsProps = {
  id: string;
  locked: boolean;
  montantTtc?: string | null;
  statut?: string | null;
};

export function FactureActions({
  id,
  locked,
  montantTtc,
  statut,
}: FactureActionsProps) {
  const [status, setStatus] = useState<string | null>(null);

  const handleSend = async () => {
    const res = await fetch(`/api/factures/${id}/send`, { method: "POST" });
    setStatus(res.ok ? "Facture envoyee." : "Erreur lors de l'envoi.");
  };

  const handlePay = async () => {
    const res = await fetch(`/api/factures/${id}/pay`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ montant: montantTtc ?? "0" }),
    });
    setStatus(res.ok ? "Facture payee." : "Erreur paiement.");
  };

  const handleRemind = async () => {
    const res = await fetch(`/api/factures/${id}/remind`, { method: "POST" });
    setStatus(res.ok ? "Relance envoyee." : "Erreur relance.");
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" asChild>
          <a href={`/api/factures/${id}/pdf`} target="_blank" rel="noreferrer">
            PDF
          </a>
        </Button>
        {!locked ? (
          <>
            <Button variant="outline" onClick={handleSend}>
              Envoyer
            </Button>
            <Button onClick={handlePay}>Marquer payee</Button>
          </>
        ) : null}
        {statut === "envoye" ? (
          <Button variant="outline" onClick={handleRemind}>
            Relancer
          </Button>
        ) : null}
      </div>
      {status ? <div className="text-sm text-muted-foreground">{status}</div> : null}
    </div>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

type FactureRow = {
  id: string;
  numero: string;
  statut: string | null;
};

export default function FactureDetailClient({
  facture,
}: {
  facture: FactureRow;
}) {
  const [status, setStatus] = useState(facture.statut ?? "brouillon");

  const handleSend = async () => {
    const res = await fetch(`/api/factures/${facture.id}/send`, {
      method: "POST",
    });
    if (res.ok) {
      setStatus("envoye");
    }
  };

  const handlePay = async () => {
    const res = await fetch(`/api/factures/${facture.id}/pay`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    if (res.ok) {
      setStatus("paye");
    }
  };

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-sm text-muted-foreground">
        Statut: <span className="font-medium text-foreground">{status}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" asChild>
          <Link href={`/finance/factures/${facture.id}/modifier`}>Modifier</Link>
        </Button>
        <Button variant="outline" asChild>
          <a href={`/api/factures/${facture.id}/pdf`} target="_blank">
            PDF
          </a>
        </Button>
        <Button onClick={handleSend} disabled={status !== "brouillon"}>
          Envoyer
        </Button>
        <Button onClick={handlePay} disabled={status !== "envoye"}>
          Marquer payee
        </Button>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import SignaturePad from "@/components/finance/signature-pad";

type DevisRow = {
  id: string;
  numero: string;
  statut: string | null;
  estSigne: boolean | null;
  signatureImage: string | null;
};

export default function DevisDetailClient({ devis }: { devis: DevisRow }) {
  const [status, setStatus] = useState(devis.statut ?? "brouillon");
  const [signed, setSigned] = useState(Boolean(devis.estSigne));

  const handleSend = async () => {
    const res = await fetch(`/api/devis/${devis.id}/send`, {
      method: "POST",
    });
    if (res.ok) {
      setStatus("envoye");
    }
  };

  const handleSign = async (signatureImage: string) => {
    const res = await fetch(`/api/devis/${devis.id}/sign`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ signatureImage }),
    });
    if (res.ok) {
      setSigned(true);
      setStatus("signe");
    }
  };

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-sm text-muted-foreground">
        Statut: <span className="font-medium text-foreground">{status}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" asChild>
          <Link href={`/finance/devis/${devis.id}/modifier`}>Modifier</Link>
        </Button>
        <Button variant="outline" asChild>
          <a href={`/api/devis/${devis.id}/pdf`} target="_blank">
            PDF
          </a>
        </Button>
        <Button onClick={handleSend} disabled={status !== "brouillon"}>
          Envoyer
        </Button>
      </div>
      {!signed ? (
        <div className="w-full sm:w-auto">
          <SignaturePad onSubmit={handleSign} />
        </div>
      ) : null}
    </div>
  );
}

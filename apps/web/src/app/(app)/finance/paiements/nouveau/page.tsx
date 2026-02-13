"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function NouveauPaiementPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    factureId: "",
    devisId: "",
    montant: "0",
    mode: "virement",
    statut: "en_attente",
    reference: "",
  });

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    const res = await fetch("/api/paiements", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      router.push("/finance/paiements");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Nouveau paiement</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label>Facture ID</Label>
          <Input
            value={form.factureId}
            onChange={(event) => handleChange("factureId", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Devis ID</Label>
          <Input
            value={form.devisId}
            onChange={(event) => handleChange("devisId", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Montant</Label>
          <Input
            value={form.montant}
            onChange={(event) => handleChange("montant", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Mode</Label>
          <Input
            value={form.mode}
            onChange={(event) => handleChange("mode", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Statut</Label>
          <Input
            value={form.statut}
            onChange={(event) => handleChange("statut", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Reference</Label>
          <Input
            value={form.reference}
            onChange={(event) => handleChange("reference", event.target.value)}
          />
        </div>
        <div className="md:col-span-2">
          <Button onClick={handleSubmit}>Creer</Button>
        </div>
      </CardContent>
    </Card>
  );
}

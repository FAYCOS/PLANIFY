"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type FacturePayload = {
  numero: string;
  clientId: string;
  prestationTitre: string;
  montantHt: string;
  montantTtc: string;
  statut: string;
};

export default function ModifierFacturePage({
  params,
}: {
  params: { id: string };
}) {
  const router = useRouter();
  const [form, setForm] = useState<FacturePayload>({
    numero: "",
    clientId: "",
    prestationTitre: "",
    montantHt: "0",
    montantTtc: "0",
    statut: "brouillon",
  });

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`/api/factures/${params.id}`);
      if (!res.ok) return;
      const data = await res.json();
      setForm({
        numero: data.numero ?? "",
        clientId: data.clientId ?? "",
        prestationTitre: data.prestationTitre ?? "",
        montantHt: data.montantHt?.toString() ?? "0",
        montantTtc: data.montantTtc?.toString() ?? "0",
        statut: data.statut ?? "brouillon",
      });
    };
    load();
  }, [params.id]);

  const handleChange = (field: keyof FacturePayload, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    const res = await fetch(`/api/factures/${params.id}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      router.push(`/finance/factures/${params.id}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Modifier facture</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label>Numero</Label>
          <Input
            value={form.numero}
            onChange={(event) => handleChange("numero", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Prestation</Label>
          <Input
            value={form.prestationTitre}
            onChange={(event) =>
              handleChange("prestationTitre", event.target.value)
            }
          />
        </div>
        <div className="space-y-2">
          <Label>Montant HT</Label>
          <Input
            value={form.montantHt}
            onChange={(event) => handleChange("montantHt", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Montant TTC</Label>
          <Input
            value={form.montantTtc}
            onChange={(event) => handleChange("montantTtc", event.target.value)}
          />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label>Statut</Label>
          <Input
            value={form.statut}
            onChange={(event) => handleChange("statut", event.target.value)}
          />
        </div>
        <div className="md:col-span-2">
          <Button onClick={handleSubmit}>Enregistrer</Button>
        </div>
      </CardContent>
    </Card>
  );
}

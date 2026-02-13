"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function NouveauMaterielPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    nom: "",
    categorie: "",
    quantite: "1",
    prixLocation: "0",
    numeroSerie: "",
    codeBarre: "",
    statut: "disponible",
  });

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    const res = await fetch("/api/materiel", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      router.push("/materiel");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Nouveau materiel</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label>Nom</Label>
          <Input
            value={form.nom}
            onChange={(event) => handleChange("nom", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Categorie</Label>
          <Input
            value={form.categorie}
            onChange={(event) => handleChange("categorie", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Quantite</Label>
          <Input
            type="number"
            value={form.quantite}
            onChange={(event) => handleChange("quantite", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Prix location HT</Label>
          <Input
            value={form.prixLocation}
            onChange={(event) => handleChange("prixLocation", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Numero serie</Label>
          <Input
            value={form.numeroSerie}
            onChange={(event) => handleChange("numeroSerie", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Code barre</Label>
          <Input
            value={form.codeBarre}
            onChange={(event) => handleChange("codeBarre", event.target.value)}
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
          <Button onClick={handleSubmit}>Creer</Button>
        </div>
      </CardContent>
    </Card>
  );
}

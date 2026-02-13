"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type ClientPayload = {
  nom: string;
  prenom?: string | null;
  email?: string | null;
  telephone?: string | null;
  adresseFacturation?: string | null;
  categories?: string | null;
  notes?: string | null;
};

export default function ModifierClientPage({
  params,
}: {
  params: { id: string };
}) {
  const router = useRouter();
  const [form, setForm] = useState<ClientPayload>({
    nom: "",
    prenom: "",
    email: "",
    telephone: "",
    adresseFacturation: "",
    categories: "",
    notes: "",
  });

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`/api/clients/${params.id}`);
      if (!res.ok) return;
      const data = await res.json();
      setForm({
        nom: data.nom ?? "",
        prenom: data.prenom ?? "",
        email: data.email ?? "",
        telephone: data.telephone ?? "",
        adresseFacturation: data.adresseFacturation ?? "",
        categories: data.categories ?? "",
        notes: data.notes ?? "",
      });
    };
    load();
  }, [params.id]);

  const handleChange = (field: keyof ClientPayload, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    const res = await fetch(`/api/clients/${params.id}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      router.push(`/clients/${params.id}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Modifier le client</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label>Prenom</Label>
          <Input
            value={form.prenom ?? ""}
            onChange={(event) => handleChange("prenom", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Nom</Label>
          <Input
            value={form.nom}
            onChange={(event) => handleChange("nom", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Email</Label>
          <Input
            value={form.email ?? ""}
            onChange={(event) => handleChange("email", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Telephone</Label>
          <Input
            value={form.telephone ?? ""}
            onChange={(event) => handleChange("telephone", event.target.value)}
          />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label>Adresse de facturation</Label>
          <Input
            value={form.adresseFacturation ?? ""}
            onChange={(event) =>
              handleChange("adresseFacturation", event.target.value)
            }
          />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label>Categories</Label>
          <Input
            value={form.categories ?? ""}
            onChange={(event) => handleChange("categories", event.target.value)}
          />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label>Notes</Label>
          <Textarea
            value={form.notes ?? ""}
            onChange={(event) => handleChange("notes", event.target.value)}
          />
        </div>
        <div className="md:col-span-2">
          <Button onClick={handleSubmit}>Enregistrer</Button>
        </div>
      </CardContent>
    </Card>
  );
}

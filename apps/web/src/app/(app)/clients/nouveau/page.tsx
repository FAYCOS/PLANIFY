"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function NouveauClientPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    nom: "",
    prenom: "",
    email: "",
    telephone: "",
    adresseFacturation: "",
    categories: "",
    notes: "",
  });

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    const res = await fetch("/api/clients", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      router.push("/clients");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Nouveau client</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Prenom</Label>
            <Input
              value={form.prenom}
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
              type="email"
              value={form.email}
              onChange={(event) => handleChange("email", event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Telephone</Label>
            <Input
              value={form.telephone}
              onChange={(event) => handleChange("telephone", event.target.value)}
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label>Adresse de facturation</Label>
            <Input
              value={form.adresseFacturation}
              onChange={(event) =>
                handleChange("adresseFacturation", event.target.value)
              }
            />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Categories</Label>
          <Input
            value={form.categories}
            onChange={(event) => handleChange("categories", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Notes</Label>
          <Textarea
            value={form.notes}
            onChange={(event) => handleChange("notes", event.target.value)}
          />
        </div>
        <Button onClick={handleSubmit}>Creer</Button>
      </CardContent>
    </Card>
  );
}

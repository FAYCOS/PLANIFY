"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type ContactFormProps = {
  clientId: string;
};

export default function ContactForm({ clientId }: ContactFormProps) {
  const [form, setForm] = useState({
    nom: "",
    email: "",
    telephone: "",
    role: "",
  });

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    const res = await fetch(`/api/clients/${clientId}/contacts`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      window.location.reload();
    }
  };

  return (
    <div className="grid gap-3 md:grid-cols-2">
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
      <div className="space-y-2">
        <Label>Role</Label>
        <Input
          value={form.role}
          onChange={(event) => handleChange("role", event.target.value)}
        />
      </div>
      <div className="md:col-span-2">
        <Button onClick={handleSubmit}>Ajouter contact</Button>
      </div>
    </div>
  );
}

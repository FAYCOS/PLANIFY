"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function ParametresPage() {
  const [form, setForm] = useState({
    nomEntreprise: "",
    adresse: "",
    codePostal: "",
    ville: "",
    email: "",
    telephone: "",
    emailSignature: "",
  });

  useEffect(() => {
    const load = async () => {
      const res = await fetch("/api/parametres/entreprise");
      if (!res.ok) return;
      const data = await res.json();
      if (!data) return;
      setForm({
        nomEntreprise: data.nomEntreprise ?? "",
        adresse: data.adresse ?? "",
        codePostal: data.codePostal ?? "",
        ville: data.ville ?? "",
        email: data.email ?? "",
        telephone: data.telephone ?? "",
        emailSignature: data.emailSignature ?? "",
      });
    };
    load();
  }, []);

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    await fetch("/api/parametres/entreprise", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(form),
    });
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Entreprise</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label>Nom de l&apos;entreprise</Label>
            <Input
              placeholder="Planify"
              value={form.nomEntreprise}
              onChange={(event) =>
                handleChange("nomEntreprise", event.target.value)
              }
            />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2 md:col-span-2">
              <Label>Adresse</Label>
              <Input
                placeholder="12 rue des Evenements"
                value={form.adresse}
                onChange={(event) => handleChange("adresse", event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label>Code postal</Label>
              <Input
                value={form.codePostal}
                onChange={(event) =>
                  handleChange("codePostal", event.target.value)
                }
              />
            </div>
            <div className="grid gap-2">
              <Label>Ville</Label>
              <Input
                value={form.ville}
                onChange={(event) => handleChange("ville", event.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label>Email</Label>
              <Input
                placeholder="contact@planify.app"
                value={form.email}
                onChange={(event) => handleChange("email", event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label>Telephone</Label>
              <Input
                value={form.telephone}
                onChange={(event) =>
                  handleChange("telephone", event.target.value)
                }
              />
            </div>
          </div>
          <div className="grid gap-2">
            <Label>Signature email</Label>
            <Textarea
              placeholder="Signature..."
              value={form.emailSignature}
              onChange={(event) =>
                handleChange("emailSignature", event.target.value)
              }
            />
          </div>
          <Button onClick={handleSubmit}>Enregistrer</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Integrations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div className="rounded-lg border border-dashed p-3">
            Stripe (paiements uniques)
          </div>
          <div className="rounded-lg border border-dashed p-3">
            Resend (emails)
          </div>
          <div className="rounded-lg border border-dashed p-3">
            Analytics (Plausible, PostHog, Meta)
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type MissionPayload = {
  clientId: string;
  clientNom: string;
  lieu: string;
  dateDebut: string;
  dateFin: string;
  heureDebut: string;
  heureFin: string;
  statut: string;
  notes: string;
};

export default function ModifierMissionPage({
  params,
}: {
  params: { id: string };
}) {
  const router = useRouter();
  const [form, setForm] = useState<MissionPayload>({
    clientId: "",
    clientNom: "",
    lieu: "",
    dateDebut: "",
    dateFin: "",
    heureDebut: "",
    heureFin: "",
    statut: "planifiee",
    notes: "",
  });

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`/api/missions/${params.id}`);
      if (!res.ok) return;
      const data = await res.json();
      setForm({
        clientId: data.clientId ?? "",
        clientNom: data.clientNom ?? "",
        lieu: data.lieu ?? "",
        dateDebut: data.dateDebut ?? "",
        dateFin: data.dateFin ?? "",
        heureDebut: data.heureDebut ?? "",
        heureFin: data.heureFin ?? "",
        statut: data.statut ?? "planifiee",
        notes: data.notes ?? "",
      });
    };
    load();
  }, [params.id]);

  const handleChange = (field: keyof MissionPayload, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    const res = await fetch(`/api/missions/${params.id}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        ...form,
        clientId: form.clientId,
      }),
    });
    if (res.ok) {
      router.push(`/missions/${params.id}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Modifier mission</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2 md:col-span-2">
          <Label>Client</Label>
          <Input value={form.clientNom} readOnly />
        </div>
        <div className="space-y-2">
          <Label>Lieu</Label>
          <Input
            value={form.lieu}
            onChange={(event) => handleChange("lieu", event.target.value)}
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
          <Label>Date debut</Label>
          <Input
            type="date"
            value={form.dateDebut}
            onChange={(event) => handleChange("dateDebut", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Date fin</Label>
          <Input
            type="date"
            value={form.dateFin}
            onChange={(event) => handleChange("dateFin", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Heure debut</Label>
          <Input
            value={form.heureDebut}
            onChange={(event) => handleChange("heureDebut", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Heure fin</Label>
          <Input
            value={form.heureFin}
            onChange={(event) => handleChange("heureFin", event.target.value)}
          />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label>Notes</Label>
          <Textarea
            value={form.notes}
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

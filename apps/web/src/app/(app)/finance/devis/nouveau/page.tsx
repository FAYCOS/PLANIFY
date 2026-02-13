"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type ClientRow = {
  id: string;
  nom: string;
  prenom?: string | null;
};

type MissionRow = {
  id: string;
  lieu?: string | null;
};

export default function NouveauDevisPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    numero: "",
    clientId: "",
    prestationId: "",
    prestationTitre: "",
    montantHt: "0",
    montantTtc: "0",
  });
  const [clients, setClients] = useState<ClientRow[]>([]);
  const [missions, setMissions] = useState<MissionRow[]>([]);

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleMissionChange = (value: string) => {
    setForm((prev) => {
      const mission = missions.find((item) => item.id === value);
      const fallbackTitle =
        mission && !prev.prestationTitre
          ? `Mission ${mission.id.slice(0, 8)}${mission.lieu ? ` - ${mission.lieu}` : ""}`
          : prev.prestationTitre;
      return {
        ...prev,
        prestationId: value,
        prestationTitre: fallbackTitle,
      };
    });
  };

  useEffect(() => {
    const load = async () => {
      const [clientsRes, missionsRes, seqRes] = await Promise.all([
        fetch("/api/clients"),
        fetch("/api/missions"),
        fetch("/api/sequences/next", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ type: "devis" }),
        }),
      ]);
      if (clientsRes.ok) setClients(await clientsRes.json());
      if (missionsRes.ok) setMissions(await missionsRes.json());
      if (seqRes.ok) {
        const data = await seqRes.json();
        setForm((prev) => ({ ...prev, numero: data.numero }));
      }
    };
    load();
  }, []);

  const handleSubmit = async () => {
    if (!form.clientId) return;
    const payload = {
      ...form,
      prestationId: form.prestationId || null,
    };
    const res = await fetch("/api/devis", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      router.push("/finance/devis");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Nouveau devis</CardTitle>
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
          <Label>Client</Label>
          <select
            className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
            value={form.clientId}
            onChange={(event) => handleChange("clientId", event.target.value)}
          >
            <option value="">-- Choisir --</option>
            {clients.map((client) => (
              <option key={client.id} value={client.id}>
                {[client.prenom, client.nom].filter(Boolean).join(" ") ||
                  client.nom}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label>Mission (optionnel)</Label>
          <select
            className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
            value={form.prestationId}
            onChange={(event) =>
              handleMissionChange(event.target.value)
            }
          >
            <option value="">-- Aucune --</option>
            {missions.map((mission) => (
              <option key={mission.id} value={mission.id}>
                Mission {mission.id.slice(0, 8)}{" "}
                {mission.lieu ? `- ${mission.lieu}` : ""}
              </option>
            ))}
          </select>
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
        <div className="md:col-span-2">
          <Button onClick={handleSubmit}>Creer</Button>
        </div>
      </CardContent>
    </Card>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import RouteMap from "@/components/missions/route-map";

type ClientRow = {
  id: string;
  nom: string;
  prenom?: string | null;
  email?: string | null;
  telephone?: string | null;
  adresseFacturation?: string | null;
};

type RoutePreview = {
  origin: { lat: number; lng: number; address: string };
  destination: { lat: number; lng: number; address: string };
  distanceKm: number | null;
  durationMin: number | null;
  source: string;
  geometry: Array<[number, number]> | null;
};

export default function NouvelleMissionPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    lieu: "",
    dateDebut: "",
    dateFin: "",
    heureDebut: "",
    heureFin: "",
    statut: "planifiee",
    notes: "",
  });
  const [clients, setClients] = useState<ClientRow[]>([]);
  const [clientMode, setClientMode] = useState<"existing" | "new">("existing");
  const [clientId, setClientId] = useState("");
  const [newClient, setNewClient] = useState({
    prenom: "",
    nom: "",
    email: "",
    telephone: "",
    adresseFacturation: "",
  });
  const [route, setRoute] = useState<RoutePreview | null>(null);
  const [routeStatus, setRouteStatus] = useState<
    "idle" | "loading" | "error"
  >("idle");
  const hasLieu = form.lieu.trim().length > 0;
  const displayedRoute = hasLieu ? route : null;
  const displayedRouteStatus = hasLieu ? routeStatus : "idle";

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleClientChange = (field: string, value: string) => {
    setNewClient((prev) => ({ ...prev, [field]: value }));
  };

  const selectedClient = useMemo(
    () => clients.find((client) => client.id === clientId) ?? null,
    [clients, clientId],
  );

  useEffect(() => {
    const loadClients = async () => {
      const res = await fetch("/api/clients");
      if (!res.ok) return;
      const data = (await res.json()) as ClientRow[];
      setClients(data);
    };
    loadClients();
  }, []);

  useEffect(() => {
    if (!form.lieu) return;

    const handler = window.setTimeout(async () => {
      setRouteStatus("loading");
      const res = await fetch(
        `/api/geo/route?destination=${encodeURIComponent(form.lieu)}`,
      );
      if (!res.ok) {
        setRoute(null);
        setRouteStatus("error");
        return;
      }
      const data = (await res.json()) as RoutePreview;
      setRoute(data);
      setRouteStatus("idle");
    }, 600);

    return () => window.clearTimeout(handler);
  }, [form.lieu]);

  const handleSubmit = async () => {
    const payload: Record<string, unknown> = { ...form };

    if (clientMode === "existing") {
      if (!clientId) return;
      payload.clientId = clientId;
      if (selectedClient) {
        payload.clientNom =
          [selectedClient.prenom, selectedClient.nom].filter(Boolean).join(" ") ||
          selectedClient.nom;
        payload.clientEmail = selectedClient.email ?? null;
        payload.clientTelephone = selectedClient.telephone ?? null;
      }
    } else {
      if (!newClient.nom || !newClient.prenom || !newClient.email) return;
      payload.client = { ...newClient };
      payload.clientNom = [newClient.prenom, newClient.nom]
        .filter(Boolean)
        .join(" ");
      payload.clientEmail = newClient.email;
      payload.clientTelephone = newClient.telephone;
    }

    const res = await fetch("/api/missions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      router.push("/missions");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Nouvelle mission</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <div className="space-y-3">
            <Label>Client</Label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant={clientMode === "existing" ? "default" : "outline"}
                onClick={() => setClientMode("existing")}
              >
                Existant
              </Button>
              <Button
                type="button"
                variant={clientMode === "new" ? "default" : "outline"}
                onClick={() => setClientMode("new")}
              >
                Nouveau
              </Button>
            </div>
            {clientMode === "existing" ? (
              <div className="space-y-2">
                <Label>Selectionner un client</Label>
                <select
                  className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
                  value={clientId}
                  onChange={(event) => setClientId(event.target.value)}
                >
                  <option value="">-- Choisir --</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {[client.prenom, client.nom].filter(Boolean).join(" ") ||
                        client.nom}
                    </option>
                  ))}
                </select>
                {selectedClient ? (
                  <div className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
                    {selectedClient.email ?? "Email non renseigne"} ·{" "}
                    {selectedClient.telephone ?? "Telephone non renseigne"}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Prenom</Label>
                  <Input
                    value={newClient.prenom}
                    onChange={(event) =>
                      handleClientChange("prenom", event.target.value)
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Nom</Label>
                  <Input
                    value={newClient.nom}
                    onChange={(event) =>
                      handleClientChange("nom", event.target.value)
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={newClient.email}
                    onChange={(event) =>
                      handleClientChange("email", event.target.value)
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Telephone</Label>
                  <Input
                    value={newClient.telephone}
                    onChange={(event) =>
                      handleClientChange("telephone", event.target.value)
                    }
                  />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label>Adresse de facturation</Label>
                  <Input
                    value={newClient.adresseFacturation}
                    onChange={(event) =>
                      handleClientChange(
                        "adresseFacturation",
                        event.target.value,
                      )
                    }
                  />
                </div>
              </div>
            )}
          </div>
        <div className="space-y-2">
          <Label>Lieu</Label>
          <Input
            value={form.lieu}
            onChange={(event) => handleChange("lieu", event.target.value)}
          />
        </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Date debut</Label>
              <Input
                type="date"
                value={form.dateDebut}
                onChange={(event) =>
                  handleChange("dateDebut", event.target.value)
                }
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
                type="time"
                value={form.heureDebut}
                onChange={(event) =>
                  handleChange("heureDebut", event.target.value)
                }
              />
            </div>
            <div className="space-y-2">
              <Label>Heure fin</Label>
              <Input
                type="time"
                value={form.heureFin}
                onChange={(event) =>
                  handleChange("heureFin", event.target.value)
                }
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea
              value={form.notes}
              onChange={(event) => handleChange("notes", event.target.value)}
            />
          </div>
          <Button onClick={handleSubmit}>Creer</Button>
        </div>
        <div className="space-y-4">
            <div className="rounded-xl border bg-white p-4 text-sm">
              <div className="font-medium">Itineraire</div>
            {displayedRouteStatus === "loading" ? (
              <div className="text-muted-foreground">Calcul en cours…</div>
            ) : displayedRouteStatus === "error" ? (
              <div className="text-destructive">
                Impossible de calculer l&apos;itineraire. Verifie l&apos;adresse
                ou l&apos;adresse entreprise.
              </div>
            ) : displayedRoute ? (
              <div className="text-muted-foreground">
                {displayedRoute.distanceKm
                  ? `${displayedRoute.distanceKm.toFixed(1)} km`
                  : "Distance inconnue"}
                {displayedRoute.durationMin
                  ? ` · ${Math.round(displayedRoute.durationMin)} min`
                  : ""}
                {displayedRoute.source ? ` · ${displayedRoute.source}` : ""}
              </div>
            ) : (
              <div className="text-muted-foreground">
                Renseigne un lieu pour afficher la carte.
              </div>
            )}
          </div>
          <RouteMap
            origin={
              displayedRoute
                ? ([
                    displayedRoute.origin.lat,
                    displayedRoute.origin.lng,
                  ] as [number, number])
                : undefined
            }
            destination={
              displayedRoute
                ? ([
                    displayedRoute.destination.lat,
                    displayedRoute.destination.lng,
                  ] as [number, number])
                : undefined
            }
            geometry={displayedRoute?.geometry ?? null}
          />
        </div>
      </CardContent>
    </Card>
  );
}

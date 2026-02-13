"use client";

import Image from "next/image";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const LOGOS = [
  { label: "Stripe", src: "/logos/stripe.svg", width: 92 },
  { label: "Google", src: "/logos/google.svg", width: 98 },
  { label: "Notion", src: "/logos/notion.svg", width: 88 },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <Image
              src="/planify-logo.png"
              alt="Planify"
              width={72}
              height={72}
              className="rounded-2xl bg-white p-1.5 shadow-sm ring-1 ring-black/5"
              priority
            />
            <Badge variant="secondary">Beta</Badge>
          </div>

          <nav className="hidden items-center gap-6 text-sm md:flex">
            <a href="#produit" className="text-muted-foreground hover:text-foreground">
              Produit
            </a>
            <a
              href="#integrations"
              className="text-muted-foreground hover:text-foreground"
            >
              Integrations
            </a>
            <a href="#securite" className="text-muted-foreground hover:text-foreground">
              Securite
            </a>
            <a href="#tarifs" className="text-muted-foreground hover:text-foreground">
              Tarifs
            </a>
            <a href="#faq" className="text-muted-foreground hover:text-foreground">
              FAQ
            </a>
          </nav>

          <div className="flex items-center gap-2">
            <Button variant="ghost" asChild className="hidden md:inline-flex">
              <Link href="/login">Se connecter</Link>
            </Button>
            <Button asChild>
              <Link href="/signup">Essayer Planify</Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4">
        <section className="grid items-center gap-10 py-16 md:grid-cols-2">
          <div>
            <Badge className="mb-4" variant="secondary">
              Missions · Operations · Clients · Equipes · Ressources
            </Badge>
            <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
              Pilotez vos missions, equipes, clients et operations.
              <span className="text-muted-foreground"> Sans outils disperses.</span>
            </h1>
            <p className="mt-4 text-lg text-muted-foreground">
              Planify remplace les tableurs, les outils fragmentes et les relances
              manuelles par un pilotage unifie des missions, du planning, des
              contrats et de la facturation.
            </p>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" asChild>
                <Link href="/signup">Commencer a piloter les missions</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <a href="#demo">Voir la demo</a>
              </Button>
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>✅ Sans carte</span>
              <span>•</span>
              <span>✅ Deploiement en 5 minutes</span>
              <span>•</span>
              <span>✅ Import/Export CSV</span>
            </div>
          </div>

          <div className="relative">
            <div className="rounded-2xl border bg-card shadow-sm">
              <div className="flex items-center justify-between border-b px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-muted-foreground/40" />
                  <div className="h-2 w-2 rounded-full bg-muted-foreground/30" />
                  <div className="h-2 w-2 rounded-full bg-muted-foreground/20" />
                </div>
                <span className="text-xs text-muted-foreground">Dashboard</span>
              </div>
              <div className="p-4">
                <div className="grid gap-3 md:grid-cols-2">
                  {[
                    "Performance du mois",
                    "Propositions en attente",
                    "Factures en retard",
                    "Missions de la semaine",
                  ].map((title) => (
                    <Card key={title} className="rounded-xl">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                          {title}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="h-7 w-24 rounded bg-muted" />
                        <div className="mt-3 h-2 w-full rounded bg-muted/70" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </div>

            <div className="absolute -bottom-4 -left-4 rounded-2xl border bg-background px-4 py-3 shadow-sm">
              <div className="text-xs text-muted-foreground">Derniere activite</div>
              <div className="text-sm font-medium">Mission validee ✓</div>
            </div>
          </div>
        </section>

        <section id="integrations" className="py-6">
          <p className="text-sm text-muted-foreground">
            Se connecte a votre stack existante :
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-6">
            {LOGOS.map((logo) => (
              <Image
                key={logo.label}
                src={logo.src}
                alt={logo.label}
                width={logo.width}
                height={28}
                className="h-6 w-auto opacity-90"
              />
            ))}
          </div>
        </section>

        <div className="my-10 h-px w-full bg-border" role="separator" />

        <section id="produit" className="py-10">
          <h2 className="text-2xl font-semibold">
            Tout ce qu il faut pour executer une mission, du debut a la fin.
          </h2>
          <p className="mt-2 text-muted-foreground">
            Unifie pour gagner en visibilite, en vitesse et en fiabilite.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Propositions → Contrats → Facturation</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Centralisez devis, signatures et factures pour reduire les delais et
                securiser la tresorerie.
              </CardContent>
            </Card>
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Planning & allocation des ressources</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Planifiez la capacite, assignez les equipes et ressources, et evitez
                les conflits de charge.
              </CardContent>
            </Card>
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Paiements & suivi operationnel</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Suivez paiements, statuts et jalons en temps reel pour piloter chaque
                mission.
              </CardContent>
            </Card>
          </div>
        </section>
      </main>
    </div>
  );
}

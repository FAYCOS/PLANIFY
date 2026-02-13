import Image from "next/image";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const LOGOS = [
  "Stripe",
  "Google Calendar",
  "Slack",
  "Notion",
  "Zapier",
  "Supabase",
  "PostHog",
];

export default function LandingClean() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top bar */}
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <Image
              src="/planify-logo.png"
              alt="Planify"
              width={32}
              height={32}
              className="rounded-xl"
              priority
            />
            <span className="font-semibold tracking-tight">Planify</span>
            <Badge variant="secondary" className="ml-2">
              Beta
            </Badge>
          </div>

          <nav className="hidden items-center gap-6 text-sm md:flex">
            <a href="#produit" className="text-muted-foreground hover:text-foreground">
              Produit
            </a>
            <a
              href="#integrations"
              className="text-muted-foreground hover:text-foreground"
            >
              Intégrations
            </a>
            <a href="#securite" className="text-muted-foreground hover:text-foreground">
              Sécurité
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

      {/* Hero */}
      <main className="mx-auto max-w-6xl px-4">
        <section className="grid items-center gap-10 py-16 md:grid-cols-2">
          <div>
            <Badge className="mb-4" variant="secondary">
              Missions • Opérations • Clients • Équipes • Ressources
            </Badge>
            <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
              Pilotez vos missions, équipes, clients et opérations.
              <span className="text-muted-foreground"> Sans outils dispersés.</span>
            </h1>
            <p className="mt-4 text-lg text-muted-foreground">
              Planify remplace les tableurs, les outils fragmentés et les relances
              manuelles par un pilotage unifié des missions, du planning, des
              contrats et de la facturation.
            </p>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" asChild>
                <Link href="/signup">Commencer à piloter les missions</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <a href="#demo">Voir la démo</a>
              </Button>
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>✅ Sans carte</span>
              <span>•</span>
              <span>✅ Déploiement en 5 minutes</span>
              <span>•</span>
              <span>✅ Import/Export CSV</span>
            </div>
          </div>

          {/* “Screenshot” placeholder */}
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
              <div className="text-xs text-muted-foreground">Dernière activité</div>
              <div className="text-sm font-medium">Mission validée ✓</div>
            </div>
          </div>
        </section>

        {/* Logos */}
        <section className="py-6">
          <p className="text-sm text-muted-foreground">
            Se connecte à votre stack existant :
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {LOGOS.map((logo) => (
              <div
                key={logo}
                className="rounded-full border px-3 py-1 text-sm text-muted-foreground"
              >
                {logo}
              </div>
            ))}
          </div>
        </section>

        <div className="my-10 h-px w-full bg-border" role="separator" />

        {/* Produit */}
        <section id="produit" className="py-10">
          <h2 className="text-2xl font-semibold">
            Tout ce qu’il faut pour exécuter une mission, du début à la fin.
          </h2>
          <p className="mt-2 text-muted-foreground">
            Unifié pour gagner en visibilité, en vitesse et en fiabilité.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Propositions → Contrats → Facturation</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Centralisez devis, signatures et factures pour réduire les délais et
                sécuriser la trésorerie.
              </CardContent>
            </Card>
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Planning & allocation des ressources</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Planifiez la capacité, assignez les équipes et ressources, et évitez
                les conflits de charge.
              </CardContent>
            </Card>
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Paiements & suivi opérationnel</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Suivez paiements, statuts et jalons en temps réel pour piloter chaque
                mission avec précision.
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Integrations */}
        <section id="integrations" className="py-10">
          <h2 className="text-2xl font-semibold">Intégrations</h2>
          <p className="mt-2 text-muted-foreground">
            Planify s’intègre à vos outils existants pour un flux de travail fluide.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {[
              {
                title: "Stripe",
                desc: "Paiements sécurisés, liens de règlement et relances automatisées.",
              },
              {
                title: "Google Calendar + iCal",
                desc: "Synchronisation du planning et des disponibilités en temps réel.",
              },
              {
                title: "Resend",
                desc: "Emails transactionnels et notifications client fiables.",
              },
              {
                title: "PostHog / Plausible",
                desc: "Analytique d’usage pour optimiser l’adoption et la performance.",
              },
            ].map((item) => (
              <Card key={item.title} className="rounded-2xl">
                <CardHeader>
                  <CardTitle>{item.title}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {item.desc}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Sécurité */}
        <section id="securite" className="py-10">
          <h2 className="text-2xl font-semibold">Sécurité & gouvernance</h2>
          <p className="mt-2 text-muted-foreground">
            Accès maîtrisés, traçabilité complète et infrastructure scalable.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {[
              "Contrôle d’accès par rôle",
              "Audit & traçabilité des actions",
              "Données fiables (PostgreSQL/Supabase)",
            ].map((item) => (
              <Card key={item} className="rounded-2xl">
                <CardContent className="pt-6 text-sm text-muted-foreground">
                  {item}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Pricing */}
        <section id="tarifs" className="py-10">
          <h2 className="text-2xl font-semibold">Tarifs</h2>
          <p className="mt-2 text-muted-foreground">
            Clairs, prévisibles et conçus pour accompagner votre croissance.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {[
              {
                name: "Solo",
                price: "€19",
                desc: "Idéal pour structurer vos premières missions",
                cta: "Démarrer",
              },
              {
                name: "Team",
                price: "€49",
                desc: "Pour coordonner une équipe et gagner en visibilité",
                cta: "Passer à Team",
              },
              {
                name: "Pro",
                price: "€99",
                desc: "Contrôle avancé, intégrations et reporting",
                cta: "Parler à un expert",
              },
            ].map((plan) => (
              <Card key={plan.name} className="rounded-2xl">
                <CardHeader>
                  <CardTitle className="flex items-baseline justify-between">
                    <span>{plan.name}</span>
                    <span className="text-2xl font-semibold">
                      {plan.price}
                      <span className="text-sm text-muted-foreground">/mois</span>
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {plan.desc}
                  <div className="mt-4">
                    <Button className="w-full">{plan.cta}</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="py-10">
          <h2 className="text-2xl font-semibold">FAQ</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {[
              {
                q: "L’onboarding est-il rapide ?",
                a: "Oui. Vous pouvez configurer vos clients, missions et équipe en quelques minutes.",
              },
              {
                q: "Puis-je migrer mes données ?",
                a: "Oui : import depuis vos tableurs et export CSV à tout moment.",
              },
              {
                q: "Comment gérer les accès équipe ?",
                a: "Rôles et permissions pour chaque équipe, avec traçabilité des actions.",
              },
              {
                q: "Planify est-il adapté à la croissance ?",
                a: "Oui. L’infrastructure et les workflows évoluent avec vos volumes.",
              },
            ].map((faq) => (
              <Card key={faq.q} className="rounded-2xl">
                <CardHeader>
                  <CardTitle className="text-base">{faq.q}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {faq.a}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* CTA final */}
        <section className="py-14">
          <div className="rounded-3xl border bg-card p-8 md:p-10">
            <h3 className="text-2xl font-semibold">
              Donnez de la clarté et du contrôle à vos opérations.
            </h3>
            <p className="mt-2 text-muted-foreground">
              Centralisez vos missions et obtenez une visibilité complète, en temps
              réel, pour décider plus vite.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" asChild>
                <Link href="/signup">Essayer Planify gratuitement</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/contact">Demander une démo</Link>
              </Button>
            </div>
          </div>
        </section>

        <footer className="border-t py-10 text-sm text-muted-foreground">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <span>© {new Date().getFullYear()} Planify</span>
            <div className="flex gap-4">
              <a className="hover:text-foreground" href="#">
                RGPD
              </a>
              <a className="hover:text-foreground" href="#">
                CGV
              </a>
              <a className="hover:text-foreground" href="#">
                Contact
              </a>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}

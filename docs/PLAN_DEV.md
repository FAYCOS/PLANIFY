# PLAN DE DÉVELOPPEMENT COMPLET — PLANIFY (Version Hybride)

## Objectif
Migrer Planify depuis une application monolithique Flask/SQLite vers une architecture moderne full-stack, tout en conservant :
- la logique métier éprouvée,
- les fonctionnalités existantes,
- la possibilité de migrer les données historiques.

---

## 1) Vision globale

### 1.1 Objectifs produit
- Logiciel de gestion d’activité pour prestations événementielles & techniques  
- Cible : PME / freelances / équipes techniques  

**Priorités :**
- Fiabilité métier (devis, factures, planning)
- UX fluide & moderne
- Scalabilité
- Intégrations (paiement, calendrier, analytics, IA)

### 1.2 Philosophie de migration
- ❌ Pas de “big rewrite” aveugle  
- ✅ Migration progressive  
- ✅ Réutilisation des concepts métiers existants  
- ✅ Séparation claire frontend / backend / data  

---

## 2) Stack technique cible (nouvelle version)

### 2.1 Frontend
- Next.js (App Router)
- TypeScript
- shadcn/ui (Radix + Tailwind)
- GSAP (animations UI avancées)
- Server Components + Server Actions
- Responsive desktop-first

### 2.2 Backend & Auth
- Next.js API routes / Server Actions
- better-auth
  - Auth email/password
  - Magic links
  - OAuth (Google)
  - Gestion des rôles
- Stripe
  - Paiements
  - Webhooks
  - Abonnements (futur)

### 2.3 Base de données
- PostgreSQL  
- Hébergement :
  - Supabase (par défaut)
  - ou Neon  
- ORM :
  - Drizzle ORM  
- Migrations versionnées

### 2.4 Emails & Notifications
- Resend
- Templates email transactionnels
- Webhooks (paiement, devis signé, rappel)

### 2.5 Analytics & Tracking
- PostHog (produit)
- Plausible (trafic)
- Datafast.st (events business)
- Meta Pixel (ads & retargeting)

### 2.6 IA (phase 2)
- Assistant IA contextuel
- Analyse planning / prix / logistique
- Suggestions automatiques

---

## 3) Architecture générale

apps/
 ├─ web/                 # Next.js (frontend + backend)
 │   ├─ app/
 │   ├─ components/
 │   ├─ actions/         # Server Actions
 │   ├─ api/             # API routes
 │   ├─ lib/
 │   └─ styles/
 │
 ├─ db/
 │   ├─ schema/          # Drizzle schemas
 │   ├─ migrations/
 │   └─ seed/
 │
 ├─ services/
 │   ├─ stripe/
 │   ├─ calendar/
 │   ├─ email/
 │   ├─ pdf/
 │   └─ ai/
 │
 ├─ legacy/
 │   ├─ flask_app/       # Code historique en lecture seule
 │   └─ migration/
 │
 └─ docs/
     ├─ architecture.md
     ├─ migration.md
     └─ api.md

---

## 4) Modélisation des données (Drizzle + Postgres)

### 4.1 Tables principales

### users
- id
- email
- password_hash
- role (admin | manager | dj | technician)
- created_at

### clients
- id
- type (individual | company)
- name
- email
- phone
- address
- siret
- tva
- created_at

### missions
- id
- client_id
- title
- description
- start_datetime
- end_datetime
- location
- status (draft | planned | completed | canceled)
- created_at

### quotes (devis)
- id
- client_id
- mission_id
- number
- total_ht
- total_ttc
- status (draft | sent | signed | expired)
- signed_at
- created_at

### invoices
- id
- quote_id
- number
- total
- paid_amount
- status (unpaid | partial | paid)
- created_at

### payments
- id
- invoice_id
- provider (stripe)
- amount
- status
- reference
- created_at

### equipment
- id
- name
- serial_number
- status
- maintenance_due

---

## 5) Authentification & rôles (better-auth)

### 5.1 Rôles

| Rôle        | Droits                                  |
|-------------|------------------------------------------|
| admin       | accès total                              |
| manager     | gestion clients, devis, planning         |
| dj          | accès missions assignées                 |
| technician  | matériel & missions                      |

### 5.2 Sécurité
- Sessions JWT
- CSRF via Server Actions
- Permissions vérifiées côté serveur
- Logs d’actions sensibles

---

## 6) Fonctionnalités (mapping ancien → nouveau)

### 6.1 Prestations / Missions
- CRUD via Server Actions
- Vue calendrier
- Assignation ressources
- Vérification conflits planning

### 6.2 Devis
- Génération PDF (server-side)
- Signature électronique
- Verrouillage post-signature
- Envoi email via Resend

### 6.3 Factures
- Génération PDF
- Paiement Stripe
- Webhooks Stripe → update DB
- Avoirs

### 6.4 Matériel
- Inventaire
- Sorties / retours
- Disponibilités

### 6.5 Exports & backups
- Export CSV / Excel
- Dump Postgres
- Import depuis SQLite legacy

---

## 7) Migration depuis Flask / SQLite

### 7.1 Principe
- SQLite = source historique
- Postgres = nouvelle source de vérité

### 7.2 Étapes
1. Analyse schéma SQLite
2. Mapping tables → Drizzle
3. Script d’import (Python ou Node)
4. Vérification données
5. Gel de l’ancienne version

---

## 8) Analytics & tracking

### 8.1 Events business
- Devis créé
- Devis signé
- Facture payée
- Mission terminée

### 8.2 Outils
- PostHog → funnel & UX
- Plausible → trafic
- Datafast → KPIs business
- Meta Pixel → marketing

---

## 9) IA (phase ultérieure)
- Chat assistant interne
- Analyse historique devis/prix
- Optimisation planning
- Recommandations matériel

---

## 10) Roadmap de développement

### Phase 1 — Fondations
- Setup Next.js
- Auth
- DB Postgres + Drizzle
- UI shadcn

### Phase 2 — Cœur métier
- Clients
- Missions
- Devis
- Factures

### Phase 3 — Paiement & intégrations
- Stripe
- Emails
- Calendriers

### Phase 4 — Migration
- Import SQLite
- Validation
- Mise en prod

### Phase 5 — IA & analytics avancées

---

## 11) Résultat attendu
- Application moderne, scalable
- UX fluide & animée
- Données propres
- Sécurité renforcée
- Base saine pour SaaS

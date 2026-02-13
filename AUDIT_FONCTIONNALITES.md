# Audit fonctionnalités Planify (2026-02-02)

## Méthodologie
- Lecture du code + inspection des routes et templates.
- Tests automatisés exécutés: 83/83 PASS.
- Limites: services externes (Groq, Google Calendar, SMTP), matériel (caméra), et environnements mobiles non testés en conditions réelles.

## Barème
- 20/20: fonctionnalité complète + testée automatiquement.
- 18–19/20: fonctionnel, quelques écarts mineurs (tests manuels/externe manquants).
- 15–17/20: présent mais validation partielle / dépendances externes.
- 0/20: non implémentée.

## Liste des fonctionnalités (par modules)
| Module / Fonctionnalité | Preuve (routes/tests) | Note /20 | Actions si < 18 |
|---|---|---:|---|
| Initialisation base (création, sélection, ouverture DB) | `/db/*` + scripts init | 16 | Ajouter tests end-to-end (create/open/superuser), valider flux complet UI, logs d’erreurs explicites. |
| Authentification + sessions | `/login`, `/logout`, tests auth | 18 | Ajouter tests de sécurité (rate limit, brute-force, session fixation). |
| Gestion utilisateurs + rôles | `/users`, CRUD + tests basiques | 18 | Ajouter tests de permissions par rôle sur tous les CRUD. |
| Gestion DJs (profil, assignation) | `/djs`, `/detail_dj`, tests | 18 | Ajouter tests de modification/suppression DJ. |
| Prestations CRUD + statuts | `/prestations`, `/nouvelle_prestation`, tests | 19 | Ajouter tests de transitions de statut et conflits planning. |
| Matériel inventaire + maintenance | `/materiels`, `/scan`, tests | 18 | Ajouter tests de maintenance + indisponibilités en conflit. |
| Locaux (CRUD) | `/locaux`, tests | 18 | Ajouter tests de suppression avec matériel associé. |
| Devis CRUD | `/nouveau_devis`, `/modifier_devis`, tests | 19 | Ajouter tests d’édition avancée (contenu HTML). |
| Devis PDF + signature électronique | `/devis/<id>/pdf`, `/devis/<id>/signature` | 18 | Ajouter tests de signature complète (lien + validation). |
| Factures CRUD + paiements | `/nouvelle_facture`, `/detail_facture`, tests | 19 | Ajouter tests paiements partiels/modes multiples. |
| Factures PDF | `/factures/<id>/pdf`, tests PDF | 19 | Ajouter tests d’envoi par email (mock SMTP). |
| Réservations clients (public + admin) | `/reservation`, `/api/reservation`, tests | 19 | Ajouter tests anti-spam (rate limit + captcha si besoin). |
| Recherche globale | `/recherche`, API recherche | 18 | Ajouter tests cas limites (vide, accents, pagination). |
| Exports CSV/Excel | `/export/*`, tests exports | 19 | Ajouter tests sur fichiers volumineux. |
| Export iCalendar | `/export/icalendar/*`, tests | 19 | Ajouter tests avec fuseaux horaires. |
| Backups + restauration | `/backup`, `BackupManager`, tests | 19 | Ajouter test de restauration via UI (mock). |
| Notifications email | `email_service`, tests unitaires | 17 | Ajouter test d’intégration SMTP + templates HTML. |
| Google Calendar sync | `/auth/google/*`, tests basiques | 15 | Implémenter tests OAuth + sync réelle (sandbox Google). |
| QR Code matériel (génération + scan) | PDF QR + UI scan | 16 | Test manuel caméra + fallback saisie, ajouter tests JS unitaires. |
| Tableau de bord admin | `/admin`, tests pages | 18 | Ajouter tests de widgets IA (mock API). |
| Tableau de bord DJ | `/dj/dashboard`, tests pages | 18 | Ajouter tests notifications et calendrier DJ. |
| Mobile UI (dashboard) | `index_mobile.html`, tests API | 16 | Tests visuels responsive + parcours mobile. |
| IA Chat assistant (public) | `/api/chat/*`, tests | 18 | Tests Groq réels via clé de test + monitoring latency. |
| IA Smart assistant (prix/DJ/matériel/conflits) | `/api/ai/*`, tests | 18 | Ajouter tests UI sur écrans (prestation/devis). |
| Synchronisation offline / serveur | `/sync`, `/api/sync/*`, tests | 18 | Ajouter tests de conflits + résolution. |
| Sécurité applicative (CSRF, upload, SQLi) | modules `security_*` | 17 | Tests dédiés (fuzz/inputs invalides) + audit dépendances. |
| Stripe paiements | Champs modèles + migrations | 0 | Implémenter routes, UI paiement, webhooks + tests. |

## Points à corriger pour atteindre >= 18
1. **DB multi-tenant (create/open/superuser)**: ajouter tests E2E et messages d’erreur clairs; valider le flux UI complet.
2. **Notifications email**: intégrer un mode SMTP de test + templates HTML, tests d’envoi réels (mock).
3. **Google Calendar**: ajouter intégration OAuth en environnement de test + tests de synchronisation.
4. **QR code scan**: test caméra réel + fallback robuste, tests JS pour scanner.
5. **Mobile UI**: tests responsive + parcours (checklists) + corriger les cas limites.
6. **Sécurité**: tests d’injection, rate limit, upload malveillant.
7. **Stripe**: module non implémenté → à développer (routes, webhooks, UI, tests).


# Planify (Ancienne version Flask/SQLite)

Documentation de la version **historique** (avant la refonte).  
Stack principale : **Flask + SQLAlchemy + SQLite** avec templates Jinja2.

> Remarque : ce document décrit volontairement **l'ancienne version** et ignore les frameworks ajoutés lors de la refonte.

---

## 1) Vue d'ensemble

Planify est un logiciel de gestion d'activite pour prestations (evenementiel / technique) qui couvre :
- **Missions/Prestations** : creation, planification, statuts, affectations.
- **Clients** : fiches clients, informations, historique devis/factures.
- **Devis/Factures** : creation, edition, PDF, signatures, avoirs.
- **Paiements** : suivi, statuts, rapprochement, references.
- **Materiel/Logistique** : inventaire, sorties/retours, disponibilites.
- **Utilisateurs & roles** : admin, manager, dj, technicien.
- **Exports/Backups** : CSV/Excel, sauvegardes/restauration.
- **IA** : assistants IA, recommandations, analyses.
- **Integrations** : Google Calendar, iCalendar, email, Stripe.

La base de donnees locale par defaut est : `instance/dj_prestations.db`.

---

## 2) Stack technique (ancienne version)

- **Backend** : Flask
- **ORM** : SQLAlchemy
- **DB** : SQLite
- **Templates** : Jinja2 + HTML/CSS
- **PDF** : ReportLab
- **Exports** : pandas / openpyxl
- **QR codes** : qrcode + pillow
- **Crypto** : cryptography (chiffrement des donnees sensibles)
- **Paiement** : Stripe (integration existante)
- **Calendrier** : Google Calendar + iCalendar

Dependances principales (voir `requirements.txt`) :
```
flask
flask_sqlalchemy
sqlalchemy
werkzeug
jinja2
waitress
google-api-python-client
google-auth
google-auth-oauthlib
google-auth-httplib2
icalendar
qrcode
pillow
reportlab
pandas
openpyxl
cryptography
stripe
```

---

## 3) Structure du projet (anciennes sources)

- `app.py` : application Flask monolithique (routes, models, logique metier)
- `templates/` : templates Jinja2 (UI)
- `static/` : CSS/JS/Assets
- `instance/` : DB SQLite (`dj_prestations.db`) + fichiers runtime
- `scripts/` : scripts d'import/audit/outils
- `tools/` : utilitaires (PDF, md, etc.)
- `tests/` : tests unitaires/func
- `start.py` : lanceur principal (port 5000/5001)
- `run.py` / `run_production.py` : lancement alternatif

---

## 4) Fonctionnalites principales

### 4.1 Auth & roles
- Authentification, sessions
- Roles : admin, manager, dj, technicien
- Permissions par role sur CRUD et dashboards

### 4.2 Prestations / Missions
- Creation, modification, suppression
- Statuts, dates/heures, lieux
- Affectation ressources (personnel, materiel)
- Verifications de disponibilite

### 4.3 Devis
- CRUD complet
- Signature electronique
- PDF conforme
- Verrouillage apres signature
- Acomptes, remises, frais

### 4.4 Factures
- CRUD complet
- PDF facture
- Paiements partiels / statuts
- Avoirs (notes de credit)

### 4.5 Materiel / Logistique
- Inventaire materiel
- Codes barre / numero serie
- Mouvements sortie/retour (batch)
- Disponibilite / maintenance

### 4.6 Clients
- Fiches clients
- Historique devis/factures
- Donnees entreprise (SIRET, TVA, adresse)

### 4.7 Exports / Backups
- Exports CSV/Excel
- Sauvegardes + restauration

### 4.8 IA
- Chat assistant
- Suggestions / recommandations
- Analyses et optimisations (logistique, prix, planning)

### 4.9 Integrations
- Google Calendar (OAuth)
- iCalendar export
- Stripe (paiement)
- Email (SMTP)

---

## 5) Configuration (.env)

Un exemple est fourni : `.env.example`

Variables principales :
```
FLASK_ENV=development
SECRET_KEY=change_me

PLANIFY_API_KEY=change_me

MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_password
MAIL_USE_TLS=true

GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

---

## 6) Lancement

### 6.1 Installation
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 6.2 Lancer l'app
Commande recommandee :
```
python3 start.py
```

`start.py` tente **port 5000**, sinon 5001 (et libere les ports si necessaire).

Alternatives :
```
python3 run.py
python3 run_production.py
```

---

## 7) Base de donnees

Par defaut :
```
instance/dj_prestations.db
```

Scripts utiles :
- `reset_db_with_test_data.py`
- `reset_init.py`
- `populate_test_data.py`
- `migrate_*.py` (migrations diverses)

---

## 8) Exports / PDFs

Scripts et modules :
- `pdf_generator.py` : generation devis/factures PDF
- `invoice_generator.py`
- `excel_export.py`
- `client_export.py`

---

## 9) Securite

Modules :
- `security_*` (CSRF, uploads, rate limiting, SQLi, sessions)
- chiffrement via `cryptography`

---

## 10) Tests

```
./run_tests.sh
```

---

## 11) Notes importantes

- L'ancienne version est **monolithique** (toutes les routes dans `app.py`).
- Le SQLite est la source de verite pour cette version.
- Les integrations externes (Google, Stripe, SMTP) necessitent des cles valides.

---

## 12) Annexes (inventaire rapide)

Fichiers principaux :
- `app.py` (routes + models + logique)
- `templates/` (UI)
- `static/` (assets)
- `instance/` (DB)

Fichiers d'audit (ancienne version) :
- `AUDIT_FONCTIONNALITES.md`
- `AUDIT_API_ROUTES.md`


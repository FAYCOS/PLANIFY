# Rapport de corrections - Planify

## Contexte
- Audit premium avec seed de donnees locales.
- Objectif: corriger les bugs et incoherences listes dans l'audit, stabiliser les pages critiques et securiser les routes sensibles.

## Corrections appliquees
- Ajout de la page de gestion des sauvegardes admin.
- Ajout de la page demo universelle manquante.
- Suppression du conflit de routes `/backup` (route legacy renommee).
- Protection admin sur la restauration de base.
- Protection login sur la page notifications.
- Lien de sauvegardes dans les parametres pointe vers l'interface admin.
- PDF devis: conditions de paiement adaptees a l'acompte reel.
- PDF devis: section acompte/solde ajoutee quand l'acompte est requis.
- Page restore: support des fichiers `.db` et `.db.gz`, restauration via BackupManager.
- Page backup: affichage taille/date et actions sur les sauvegardes reelles.
- API recherche: protection login et correction du local manquant.
- API stats/notifications/settings: protection login pour limiter les fuites.
- Recherche: redirection vers la fiche materiel.
- Ajout login requis sur les pages materiel/locaux/djs/prestations (listes, fiches, CRUD).
- API materiel local protegee.
- Bouton restore utilise un style coherent (btn-danger).
- Role_required ajoute sur creation/modification/suppression pour prestations, materiels, djs, locaux.
- Optimisation requetes: chargement eager des locaux materiels pour limiter les N+1.
- Statut prestation annulee normalise (annulee) + coherence UI.
- Styles bouton danger harmonises (btn-danger).
- Liste prestations alignee avec la palette via variables CSS.
- UX mobile: CTA plus lisibles (pill height/size), listes plus denses, recherche mobile scrollable.
- Couleurs mobiles harmonisees sur la nouvelle palette (hero badge, tabs, highlights).
- Mobile: liens prestations corriges (detail/modifier/nouvelle).
- APIs scanner/materiel durcies (role_required technicien/manager/admin).
- Perf: eager loading devis/factures/facturation pour limiter les N+1.
- Mobile: toasts typés (success/error/warning) et accessibilité du FAB.
- Chargement de mobile.js conditionnel (uniquement sur user-agent mobile).
- Rapports: encart "Pro" enrichi + boutons d'export rapides.
- Layout global: suppression sidebar, ajout top-rail avec navigation centrale et actions.
- CSS: header/page title ajustés pour le nouveau layout.

## Details techniques
- `templates/backup.html` : page complete pour lister, telecharger, restaurer, supprimer les sauvegardes.
- `templates/demo_universal.html` : template de demo pour eviter les erreurs 500.
- `app.py` :
  - route legacy backup deplacee vers `/backup/legacy` (admin).
  - `/restore` restreint aux admins.
  - `/notifications` protege par login.
- `templates/settings.html` : bouton sauvegarde dirige vers l'interface admin.
- `pdf_generator.py` :
  - paiement conditionnel selon `acompte_requis` et `acompte_pourcentage`.
  - tableau supplementaire "Acompte / Solde" si applicable.
- `templates/restore.html` : accepte `.db` et `.db.gz`, liste de sauvegardes structuree.
- `app.py` :
  - backup legacy passe par `backup_manager` (chemin DB coherent).
  - `/api/stats`, `/api/notifications`, `/settings`, `/settings/update`, `/recherche`, `/api/recherche` proteges.

## Points verifies apres correctifs
- `/backup` : OK (200).
- `/demo-universal` : OK (200).
- `/restore` : OK (200) et limite admin.
- PDF devis: generation OK (200) avec contenu supplementaire.

## Limites de test
- Envoi d'email reel non teste (SMTP non configure).
- Camera/scan sur device non teste.
- OAuth Google Calendar non teste.

## Note projet (apres correctifs)
- Estimee a 14/20.
- Reste a relever: tests mails, camera/scan, OAuth, durcissement securite global, UX micro-details.
